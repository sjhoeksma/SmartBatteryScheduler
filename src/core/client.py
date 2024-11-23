# type: ignore
"""
Client to connect with EcactusEcos

This class provides an interface to interact with the EcactusEcos API. It handles authentication, fetching customer and device information, retrieving actuals data, and managing charge/discharge strategies.

The class provides the following methods:
- `authenticate()`: Authenticates the client using the provided username and password.
- `customer_overview()`: Retrieves the customer overview information.
- `device_overview()`: Retrieves the list of devices associated with the authenticated user.
- `day_a_head()`: Retrieves the day-ahead data for a specified region and time interval.
- `get_strategy_info()`: Retrieves the strategy information for a specific device.
- `set_strategy_info()`: Updates the strategy information for a specific device.
- `clear_charge_strategy()`: Clears the charge and/or discharge lists for a specific device.
- `set_self_power_strategy()`: Sets the charge mode to self-power strategy for a specific device.
- `set_time_based_strategy()`: Sets the charge mode to time-based strategy for a specific device.
- `set_backup_power_strategy()`: Sets the charge mode to backup-power strategy for a specific device.
- `pause_battery()`: Pause the battery by forcing unload on low power.
- `resume_battery()`: Resume from pause by removing the unload stratergy.
- `actuals()`: Retrieves the actual values of the configured source types for all devices.
- `current_measurements()`: Retrieves the relevant actual values of the configured source types for the specified devices.
"""

import asyncio
import aiohttp
import time
from yarl import URL
from pytz import country_timezones

from .const import (
    API_HOST_EU,
    AUTHENTICATION_PATH,
    ACTUALS_PATH,
    AUTH_ACCESS_TOKEN,
    CUSTOMER_OVERVIEW_PATH,
    DEVICE_LIST_PATH,
    AUTH_TOKEN_HEADER,
    DEFAULT_SOURCE_TYPES,
    DEVICE_ALIAS_NAME,
    DAY_A_HEAD_PATH,
    STRATEGY_INFO_PATH,
    SURCHARGE_KWH,
    SURCHARGE_PERCENTAGE,
    INSIGHT_PATH,
    DEVICE_INSIGHT_PATH,
    DEVICE_REALTIME_PATH,
)

from .exceptions import (
    EcactusEcosConnectionException,
    EcactusEcosException,
    EcactusEcosUnauthenticatedException,
    EcactusEcosDataException,
)

# Used to deterim country base on time zone, could also be done based on devicelocation
timezone_countries = {
    timezone: country
    for country, timezones in country_timezones.items()
    for timezone in timezones
}


class Client:
    """Client to connect with EcactusEcos"""

    def __init__(
        self,
        username: str,
        password: str,
        api_host: str = API_HOST_EU,
        api_scheme: str = "https",
        api_port: int = 443,
        request_timeout: int = 10,
        source_types=DEFAULT_SOURCE_TYPES,
    ):
        self.api_scheme = api_scheme
        self.api_host = api_host
        self.api_port = api_port
        self.request_timeout = request_timeout
        self.source_types = source_types

        self._username = username
        self._password = password
        self._clear()

    def _clear(self):
        self._customer_info = None
        self._auth_token = None
        self._devices = None
        self._sources = None
        self._day_a_head = None
        self._strategy_info = None
        self._insights = None
        self._devices_insight = None
        self._devices_realtime = None

    async def authenticate(self) -> None:
        """Log in using username and password.

        If succesfull, the authentication is saved and is_authenticated() returns true
        """
        # Make sure all data is cleared
        self.invalidate_authentication()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=AUTHENTICATION_PATH,
        )

        # auth request, password grant type
        data = {
            "email": self._username,
            "password": self._password,
        }

        data = await self.request(
            "POST",
            url,
            data=data,
            callback=self._handle_data_response,
        )
        self._auth_token = data[AUTH_ACCESS_TOKEN]
        return self._auth_token

    async def customer_overview(self):
        """Request the customer overview."""
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException(
                "Authentication required")

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=CUSTOMER_OVERVIEW_PATH,
        )

        self._customer_info = await self.request(
            "GET", url, callback=self._handle_data_response)
        return self._customer_info

    async def device_overview(self):
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException(
                "Authentication required")

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=DEVICE_LIST_PATH,
        )
        self._devices = dict()
        data = await self.request("GET",
                                  url,
                                  callback=self._handle_data_response)
        for device in data:
            self._devices[device["deviceId"]] = device
        return self._devices

    async def get_day_a_head(
        self,
        region: str = None,
        surcharge: float = SURCHARGE_KWH,
        surcharge_percentage: float = SURCHARGE_PERCENTAGE,
        interval: int = 3600,
        time: int = 0,
    ):
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException(
                "Authentication required")

        # Get the region of the user timezone name
        if region is None and self._customer_info is None:
            await self.customer_overview()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=DAY_A_HEAD_PATH,
        )

        self._day_a_head = await self.request(
            "POST",
            url,
            data={
                "intervalSeconds":
                interval,
                "time":
                time,
                "region": [
                    region if region is not None else
                    timezone_countries[self._customer_info["timezoneName"]]
                ],
            },
            callback=self._handle_data_response,
        )
        # Now we need to concert mwh to _day_a_head to kwh + the surcharge
        for price in self._day_a_head:
            price["average"] = (price["average"] / 1000) * (
                1 + (surcharge_percentage / 100)) + surcharge

        return self._day_a_head

    async def get_insight(self,
                          deviceId: str = None,
                          cache: bool = True,
                          offsetDay: int = -7):
        """Get the insight"""
        if not self.is_authenticated():
            await self.authenticate()

        if deviceId is None:
            deviceId = await self.get_master()

        if cache and self._insights is not None:
            return self._insights[deviceId]

        if not self._devices:
            await self.device_overview()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=INSIGHT_PATH,
        )

        self._insights = dict()
        for device_id in self.get_device_ids():
            self._insights[device_id] = await self.request(
                "GET",
                url,
                data={
                    "deviceId": device_id,
                    "offsetDay": offsetDay,
                },
                callback=self._handle_data_response,
            )
        return self._insights[deviceId]

    async def get_device_insight(self,
                                 deviceId: str = None,
                                 cache: bool = True,
                                 offsetDay: int = -7):
        """Get the device insights"""
        if not self.is_authenticated():
            await self.authenticate()

        if deviceId is None:
            deviceId = await self.get_master()

        if cache and self._devices_insight is not None:
            return self._devices_insight[deviceId]

        if not self._devices:
            await self.device_overview()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=DEVICE_INSIGHT_PATH,
        )

        self._devices_insight = dict()
        for device_id in self.get_device_ids():
            self._devices_insight[device_id] = await self.request(
                "GET",
                url,
                data={
                    "deviceId": device_id,
                    "offsetDay": offsetDay,
                },
                callback=self._handle_data_response,
            )
        return self._devices_insight[deviceId]

    async def get_device_realtime(self,
                                  deviceId: str = None,
                                  cache: bool = True):
        """Get the device realtime data"""
        if not self.is_authenticated():
            await self.authenticate()

        if deviceId is None:
            deviceId = await self.get_master()

        if cache and self._devices_realtime is not None:
            return self._devices_realtime[deviceId]

        if not self._devices:
            await self.device_overview()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=DEVICE_REALTIME_PATH,
        )

        self._devices_realtime = dict()
        for device_id in self.get_device_ids():
            self._devices_realtime[device_id] = await self.request(
                "POST",
                url,
                data={
                    "deviceId": device_id,
                },
                callback=self._handle_data_response,
            )
        return self._devices_realtime[deviceId]

    async def get_strategy_info(self,
                                deviceId: str = None,
                                cache: bool = True):
        """Get the strategy_info"""
        if cache and self._strategy_info is not None:
            return self._strategy_info

        if not self.is_authenticated():
            await self.authenticate()

        if deviceId is None:
            deviceId = await self.get_master()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=STRATEGY_INFO_PATH,
        )

        self._strategy_info = await self.request(
            "GET",
            url,
            data={
                "deviceId": deviceId,
            },
            callback=self._handle_data_response,
        )
        return self._strategy_info

    async def set_strategy_info(self, strategy: dict, deviceId: str = None):
        if not self.is_authenticated():
            await self.authenticate()

        if deviceId is None:
            deviceId = await self.get_master()

        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=STRATEGY_INFO_PATH,
        )
        # Just update the strategy record
        self._strategy_info = self._strategy_info | strategy
        data = dict(self._strategy_info)
        data["deviceId"] = deviceId
        for i in ["emsSoftwareVersion", "dsp1SoftwareVersion", "ratedPower"]:
            del data[i]

        success = await self.request(
            "POST",
            url,
            data,
            callback=self._handle_success_response,
        )
        if not success:
            self._strategy_info = None
        return success

    async def clear_charge_strategy(self,
                                    charge: bool = True,
                                    discharge: bool = True,
                                    deviceId: str = None):
        """Clear the charge and/or discharge lists"""
        info = dict(await self.get_strategy_info(deviceId))
        if charge:
            info["chargingList"] = []
        if discharge:
            info["dischargingList"] = []
        return await self.set_strategy_info(info, deviceId)

    async def set_self_power_strategy(self, deviceId: str = None):
        """Change to self_power strategy"""
        info = dict(await self.get_strategy_info(deviceId))
        info["chargeUseMode"] = 0
        return await self.set_strategy_info(info, deviceId)

    async def set_time_based_strategy(self, deviceId: str = None):
        """Change to time_based strategy"""
        info = dict(await self.get_strategy_info(deviceId))
        info["chargeUseMode"] = 1
        return await self.set_strategy_info(info, deviceId)

    async def set_backup_power_strategy(self, deviceId: str = None):
        """Change to backup_power strategy"""
        info = dict(await self.get_strategy_info(deviceId))
        info["chargeUseMode"] = 2
        return await self.set_strategy_info(info, deviceId)

    async def pause_battery_strategy(self, deviceId: str = None):
        """Pause the battery, by forcing discharge on very low power"""
        info = dict(await self.get_strategy_info(deviceId))
        info["chargeUseMode"] = 1
        info["dischargeToGridFlag"] = 1
        info["dischargingList"] = [{
            "startHour": 0,
            "startMinute": 0,
            "endHour": 23,
            "endMinute": 59,
            "power": 1,
            "abandonPv": 0,
        }]
        return await self.set_strategy_info(info, deviceId)

    async def resume_battery_strategy(self, deviceId: str = None):
        """Resume the battery, by clearing discharge"""
        info = dict(await self.get_strategy_info(deviceId))
        info["chargeUseMode"] = 1
        info["dischargingList"] = []
        return await self.set_strategy_info(info, deviceId)

    async def disable_discharge_battery(self, deviceId: str = None):
        """Disable discharge of the battery"""
        info = dict(await self.get_strategy_info(deviceId))
        info["dischargeToGridFlag"] = 0
        info["dischargingList"] = []
        return await self.set_strategy_info(info, deviceId)

    async def create_dynamic_strategy(
        self,
        battery_capacity: int,
        inverter_capacity: int,
        charge: int = 95,
        charge_price: float = 0,
        discharge: int = 0,
        discharge_price: float = 0,
        profit: float = 0,
        surcharge: float = SURCHARGE_KWH,
        surcharge_percentage: float = SURCHARGE_PERCENTAGE,
        deviceId: str = None,
    ):
        """Create the dynamic stratergy, see STRATEGY.md"""
        # Step 0: Get the current strategy
        info = dict(await self.get_strategy_info(deviceId=deviceId))
        now = int(time.time() / 3600) * 3600  # Truncated to Hour
        charge_list = []
        discharge_list = []

        # Step 1a: Create usage prediction model for next 48 based on
        # Average Consumption and Poduction of last week
        # device_insight = await self.get_insight(deviceId=deviceId)
        # usage_model = dict()
        # today = device_insight["today"]
        # next_day = (today + 1) % 7
        # for device_id, data in self._insights.items():
        #     for i in range(0, 11):
        #         data["weekEnergyOfHour"][today][i]
        #     for i in range(0, 11):
        #         data["weekEnergyOfHour"][next_day][i]
        # We need today and ((today + 1) % 7) + 1

        # Step 1b: Create a SOC model for the next 48 hours, decreasing SOC
        # soc_model = dict()
        # for i in range(0, 47):
        #     soc_model[now + (i * 3600)] = {
        #         "SOC": 0,
        #     }

        # Step 2: Solar prediction

        # Step 3: Usage prediction

        # Step 4: Day a head pricing
        if self._day_a_head is None:
            await self.get_day_a_head(
                surcharge=surcharge, surcharge_percentage=surcharge_percentage)
            # print("Day a Head %s" % self._day_a_head)

        # Step 4a: Find if there is a time periode for discharging

        # Step 4b: Find if there is a time periode for charging
        for price in self._day_a_head:
            allowed = []
            if price["startTimeUnix"] >= now and price[
                    "average"] >= charge_price:
                allowed += {
                    "startTimeUnix": price["startTimeUnix"],
                    "price": price["average"],
                }
            # Do whe have enough SOC to reach loading time

        # Step 5c: Find if there is a periode to make a profit

        info["chargingList"] = charge_list
        # When discharge is disabled remove the strategy
        if discharge == 0:
            info["dischargeToGridFlag"] = 0
            info["dischargingList"] = []
        else:
            info["dischargeToGridFlag"] = 1
            info["dischargingList"] = discharge_list
        return info

    async def update_dynamic_strategy(
        self,
        battery_capacity: int,
        inverter_capacity: int,
        charge: int = 95,
        charge_price: float = 0,
        discharge: int = 0,
        discharge_price: float = 0,
        profit: float = 0,
        surcharge: float = SURCHARGE_KWH,
        surcharge_percentage: float = SURCHARGE_PERCENTAGE,
        deviceId: str = None,
    ):
        info = await self.create_dynamic_strategy(
            battery_capacity,
            inverter_capacity,
            charge,
            charge_price,
            discharge,
            discharge_price,
            profit,
            surcharge,
            surcharge_percentage,
            deviceId,
        )
        return await self.set_strategy_info(info, deviceId)

    async def actuals(self):
        """Request the actual values of the sources of the types configured in this instance (source_types)."""
        if not self.is_authenticated():
            raise EcactusEcosUnauthenticatedException(
                "Authentication required")

        if not self._devices:
            await self.device_overview()

        actuals = dict()
        url = URL.build(
            scheme=self.api_scheme,
            host=self.api_host,
            port=self.api_port,
            path=ACTUALS_PATH,
        )
        for device_id in self.get_device_ids():
            actuals[device_id] = await self.request(
                "POST",
                url,
                data={"deviceId": device_id},
                callback=self._handle_data_response,
            )
        return actuals

    async def current_measurements(self, deviceIds=None):
        """Wrapper method which returns the relevant actual values of sources.

        When required, this method attempts to authenticate."""
        try:
            if not self.is_authenticated():
                await self.authenticate()

            if not self._devices:
                await self.device_overview()

            actuals = await self.actuals()
            current_measurements = dict()

            # When we have multiple devices we return the sum
            for source_type in self.source_types:
                match source_type:
                    case "batterySoc":
                        current_measurements[source_type] = (min(
                            actual[source_type]
                            for deviceId, actual in actuals.items()
                            if (deviceIds is None or deviceId in deviceIds)) *
                                                             100)
                    case _:
                        current_measurements[source_type] = sum(
                            actual[source_type]
                            for deviceId, actual in actuals.items()
                            if deviceIds is None or deviceId in deviceIds)
            # When no deviceIds are given we add all devices by alias if we have more then one device connected
            if deviceIds is None and len(self._devices) > 1:
                for source_type in self.source_types:
                    for deviceId, actual in actuals.items():
                        if (self._devices[deviceId] is not None
                                and self._devices[deviceId][DEVICE_ALIAS_NAME]
                                is not None):
                            match source_type:
                                case "batterySoc":
                                    current_measurements[
                                        f"{self._devices[deviceId][DEVICE_ALIAS_NAME].lower()}{source_type[:1].upper() + source_type[1:]}"] = actual[
                                            source_type] * 100
                                case _:
                                    current_measurements[
                                        f"{self._devices[deviceId][DEVICE_ALIAS_NAME].lower()}{source_type[:1].upper() + source_type[1:]}"] = actual[
                                            source_type]
            return current_measurements

        except EcactusEcosUnauthenticatedException as exception:
            self.invalidate_authentication()
            raise exception

    async def get_master(self):
        if not self.is_authenticated():
            await self.authenticate()

        if not self._devices:
            await self.device_overview()

        # We need to find the master, this is the first device or the first one with VPP = false
        for id, value in self._devices.items():
            if not value["vpp"]:
                return id
        raise EcactusEcosDataException("No master device found")

    async def _handle_data_response(self, response, params):
        """Handle a json data request response"""
        json = await response.json()
        if json is None or not json["success"]:
            raise EcactusEcosDataException("Invalid data response", json)
        return json["data"]

    async def _handle_success_response(self, response, params):
        """Handle a success execution response"""
        json = await response.json()
        if json is None:
            raise EcactusEcosDataException("Invalid success response", json)
        return json["success"]

    async def request(
        self,
        method: str,
        url: URL,
        data: dict = None,
        callback=None,
        params: dict = None,
    ):
        headers = {}
        json: dict = {
            **{
                "_t": int(time.time()),
                "clientType": "BROWSER",
                "clientVersion": "1.0",
            },
            **(data if data else {}),
        }

        # Insert authentication
        if self._auth_token is not None:
            headers[AUTH_TOKEN_HEADER] = "Bearer %s" % self._auth_token
        try:
            async with async_timeout.timeout(self.request_timeout):
                async with aiohttp.ClientSession() as session:
                    req = (session.request(
                        method,
                        url,
                        json=json,
                        headers=headers,
                    ) if method != "GET" else session.request(
                        method,
                        url,
                        params=json,
                        headers=headers,
                    ))
                    async with req as response:
                        status = response.status
                        is_json = "application/json" in response.headers.get(
                            "Content-Type", "")

                        if (status == 401) or (status == 403):
                            raise EcactusEcosUnauthenticatedException(
                                await response.text())

                        if not is_json:
                            raise EcactusEcosException("Response is not json",
                                                       await response.text())

                        if not is_json or (status // 100) in [4, 5]:
                            raise EcactusEcosException(
                                "Response is not success",
                                response.status,
                                await response.text(),
                            )

                        if callback is not None:
                            return await callback(response, params)

        except asyncio.TimeoutError as exception:
            raise EcactusEcosConnectionException(
                "Timeout occurred while communicating with EcactusEcos"
            ) from exception
        except aiohttp.ClientError as exception:
            raise EcactusEcosConnectionException(
                "Error occurred while communicating with EcactusEcos"
            ) from exception

    def is_authenticated(self):
        """Returns whether this instance is authenticated

        Note: despite this method returning true, requests could still fail to an authentication error."""
        return self._auth_token is not None

    def get_customer_info(self):
        """Returns the unique id of the currently authenticated user"""
        return self._customer_info

    def invalidate_authentication(self):
        """Invalidate the current authentication tokens and account details."""
        self._clear()

    def get_device(self, device_id):
        """Gets the id of the device which belongs to the given source type, if present."""
        return (self._devices[device_id] if self._devices is not None
                and device_id in self._devices else None)

    def get_device_ids(self):
        """Gets the ids of the devices, if present."""
        return list(
            self._devices.keys()) if self._devices is not None else None

    def get_source_ids(self):
        """Gets the ids of the sources which belong to self.source_types, if present."""
        return [
            source_id
            for source_id in map(self.get_source_id, self.source_types)
            if source_id is not None
        ]

    def get_source_id(self, source_type):
        """Gets the id of the source which belongs to the given source type, if present."""
        return (self._sources[source_type] if self._sources is not None
                and source_type in self._sources else None)
