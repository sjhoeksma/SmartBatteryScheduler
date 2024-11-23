"""EcactusEcos constants"""

API_HOST_EU = "api-ecos-eu.weiheng-tech.com"
API_HOST_CN = "api-ecos-hu.weiheng-tech.com"
API_HOST_AU = "api-ecos-au.weiheng-tech.com"

API_HOSTS = [
    API_HOST_EU,
    API_HOST_CN,
    API_HOST_AU,
]

DEVICE_ALIAS_NAME = "deviceAliasName"

AUTH_ACCESS_TOKEN = "accessToken"

AUTHENTICATION_PATH = "/api/client/guide/login"
"""Path to perform authentication. Result is a user id and an auth token"""
"""Default source types to fetch if none are specified."""

CUSTOMER_OVERVIEW_PATH = "/api/client/settings/user/info"
"""Path to request details of the customer."""

DEVICE_LIST_PATH = "/api/client/home/device/list"

ACTUALS_PATH = "/api/client/home/now/device/runData"
"""Path to request actual values."""

DAY_A_HEAD_PATH = "/api/client/customize/dayAheadPrice"
"""Path to day a head pricing"""

STRATEGY_INFO_PATH = "/api/client/customize/info"
"""Path to the info for (un)load strategy"""

INSIGHT_PATH = "/api/client/insight/compute/latestDayDeviceEnergyHeatmap"
"""Path to the insight information"""

DEVICE_INSIGHT_PATH = "/api/client/insight/compute/latestDayDeviceEnergy"
"""Path to the insight information per device"""

DEVICE_REALTIME_PATH = "/api/client/home/now/device/realtime"
"""Path to the realtime data for this day"""

SURCHARGE_KWH = 0
"""The surcharge per kwh"""

SURCHARGE_PERCENTAGE = 0
"""The surcharge percentage per kwh"""

AUTH_TOKEN_HEADER = "Authorization"
"""Header which should contain (in request) the authentication token"""

SOURCE_TYPE_BATTERY_SOC = "batterySoc"
SOURCE_TYPE_BATTERY_POWER = "batteryPower"
SOURCE_TYPE_EPS_POWER = "epsPower"
SOURCE_TYPE_GRID_POWER = "gridPower"
SOURCE_TYPE_HOME_POWER = "homePower"
SOURCE_TYPE_METER_POWER = "meterPower"
SOURCE_TYPE_SOLAR_POWER = "solarPower"

DEFAULT_SOURCE_TYPES = [
    SOURCE_TYPE_BATTERY_SOC,
    SOURCE_TYPE_BATTERY_POWER,
    SOURCE_TYPE_EPS_POWER,
    SOURCE_TYPE_GRID_POWER,
    SOURCE_TYPE_HOME_POWER,
    SOURCE_TYPE_METER_POWER,
    SOURCE_TYPE_SOLAR_POWER,
]
"""Default source types to fetch if none are specified."""
