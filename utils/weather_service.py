import os
import requests
import json
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, Optional, Tuple
import pvlib
from pvlib.location import Location
import pytz
import logging
import pickle
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not found in environment variables")

        self.base_url = "http://api.openweathermap.org/data/2.5"
        self._location_cache = None
        self._weather_cache = {}
        self._cache_duration = timedelta(minutes=30)
        self._last_cache_time = None
        self._cache_file = Path('.DB/location_cache.pkl')
        self._last_api_call = 0
        self._api_call_interval = 1.0  # Minimum interval between API calls in seconds
        self._max_retries = 3  # Maximum number of API call retries
        self._retry_delay = 2  # Delay between retries in seconds
        self._load_cached_location()

    def _wait_for_rate_limit(self):
        """Implement rate limiting for API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self._last_api_call
        if time_since_last_call < self._api_call_interval:
            time.sleep(self._api_call_interval - time_since_last_call)
        self._last_api_call = time.time()

    def _load_cached_location(self):
        """Load cached location from file"""
        try:
            if self._cache_file.exists():
                logger.debug("Loading location from cache file")
                with open(self._cache_file, 'rb') as f:
                    self._location_cache = pickle.load(f)
                logger.info(f"Loaded cached location: {self._location_cache}")
        except Exception as e:
            logger.warning(f"Failed to load cached location: {str(e)}")

    def _save_cached_location(self):
        """Save location to cache file"""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, 'wb') as f:
                pickle.dump(self._location_cache, f)
            logger.debug("Location saved to cache file")
        except Exception as e:
            logger.warning(f"Failed to save location to cache: {str(e)}")

    def get_location_from_ip(self) -> Tuple[float, float]:
        """Get location coordinates using IP geolocation with enhanced error handling"""
        if self._location_cache:
            logger.debug(f"Using cached location: {self._location_cache}")
            return self._location_cache

        logger.info("Attempting to get location from IP")
        self._wait_for_rate_limit()

        # Try multiple geolocation services with rate limiting
        geolocation_services = [
            ('https://ipapi.co/json/', lambda x: (x.get('latitude'), x.get('longitude'))),
            ('https://ip-api.com/json/', lambda x: (x.get('lat'), x.get('lon'))),
            ('https://ipinfo.io/json', lambda x: tuple(map(float, x.get('loc', '0,0').split(','))))
        ]

        for service_url, extract_coords in geolocation_services:
            try:
                response = requests.get(service_url, timeout=5)
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError("Invalid response format")

                lat, lon = extract_coords(data)
                if lat is None or lon is None:
                    raise ValueError("Missing coordinates in response")

                self._location_cache = (float(lat), float(lon))
                logger.info(f"Successfully obtained location from {service_url}: {self._location_cache}")
                self._save_cached_location()
                return self._location_cache

            except Exception as e:
                logger.warning(f"Location service {service_url} failed: {str(e)}")
                time.sleep(1)  # Wait before trying next service

        # Default to Amsterdam coordinates if all attempts fail
        default_location = (52.3676, 4.9041)
        logger.warning(f"Using default location (Amsterdam): {default_location}")
        self._location_cache = default_location
        self._save_cached_location()
        return default_location

    def get_weather_data(self, lat: float, lon: float) -> Dict:
        """Get weather data from OpenWeatherMap API with enhanced error handling and retries"""
        cache_key = f"{lat},{lon}"
        current_time = datetime.now()

        # Check cache
        if (self._last_cache_time and cache_key in self._weather_cache and
                current_time - self._last_cache_time < self._cache_duration):
            return self._weather_cache[cache_key]

        for retry in range(self._max_retries):
            try:
                self._wait_for_rate_limit()
                
                response = requests.get(
                    f"{self.base_url}/forecast",
                    params={
                        'lat': lat,
                        'lon': lon,
                        'appid': self.api_key,
                        'units': 'metric'
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                # Validate response structure
                if not isinstance(data, dict):
                    raise ValueError("Invalid response format: not a dictionary")

                if 'list' not in data:
                    raise ValueError("Invalid response format: missing 'list' key")

                if not isinstance(data['list'], list) or not data['list']:
                    raise ValueError("Invalid response format: empty or invalid forecast list")

                # Cache the validated response
                self._weather_cache[cache_key] = data
                self._last_cache_time = current_time

                return data

            except requests.RequestException as e:
                logger.warning(f"API request failed (attempt {retry + 1}/{self._max_retries}): {str(e)}")
                if retry < self._max_retries - 1:
                    time.sleep(self._retry_delay * (retry + 1))
            except ValueError as e:
                logger.error(f"Invalid API response: {str(e)}")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                break

        # Return cached data if available, otherwise raise exception
        if cache_key in self._weather_cache:
            logger.warning("Using cached weather data due to API failure")
            return self._weather_cache[cache_key]
        
        raise Exception("Failed to fetch weather data after multiple attempts")

    def calculate_solar_production(self, weather_data: Dict, max_watt_peak: float,
                                 lat: float, lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data with enhanced error handling"""
        try:
            # Validate input parameters
            if not isinstance(weather_data, dict):
                raise ValueError("Weather data must be a dictionary")
            if not isinstance(max_watt_peak, (int, float)) or max_watt_peak <= 0:
                raise ValueError("Invalid max_watt_peak value")

            # Create location object
            location = Location(latitude=lat, longitude=lon)
            production = {}
            
            # Get timezone for the location
            timezone = pytz.timezone(self._get_timezone(lat, lon))

            # Validate weather data structure
            if 'list' not in weather_data:
                raise ValueError("Missing 'list' key in weather data")

            for forecast in weather_data['list']:
                try:
                    # Validate required forecast data
                    if not isinstance(forecast, dict):
                        logger.warning("Invalid forecast entry format")
                        continue

                    required_keys = ['dt', 'clouds', 'main']
                    if not all(key in forecast for key in required_keys):
                        logger.warning(f"Missing required keys in forecast: {required_keys}")
                        continue

                    # Process timestamp
                    timestamp = datetime.fromtimestamp(forecast['dt'])
                    timestamp = timezone.localize(timestamp)

                    # Get solar position
                    solar_position = location.get_solarposition(timestamp)
                    
                    # Validate solar position data
                    if solar_position.empty:
                        logger.warning(f"Empty solar position data for timestamp: {timestamp}")
                        continue

                    # Extract and validate cloud cover
                    try:
                        clouds = forecast['clouds'].get('all', 100) / 100.0
                        clearness_index = 1 - (clouds * 0.75)
                    except (KeyError, TypeError, ValueError) as e:
                        logger.warning(f"Error processing cloud cover: {str(e)}")
                        clearness_index = 0.25  # Conservative default

                    # Determine if it's daytime
                    zenith = solar_position['apparent_zenith'].iloc[0]
                    is_day = zenith < 90

                    if is_day:
                        try:
                            # Calculate clear sky radiation
                            clearsky = location.get_clearsky(timestamp)
                            if clearsky.empty:
                                raise ValueError("Empty clearsky data")
                            
                            ghi = clearsky['ghi'].iloc[0] * clearness_index

                            # Apply visibility factor if available
                            if 'visibility' in forecast:
                                visibility_factor = min(forecast['visibility'] / 10000.0, 1.0)
                                ghi *= visibility_factor

                        except Exception as e:
                            logger.warning(f"Error calculating GHI: {str(e)}")
                            ghi = 0.0
                    else:
                        ghi = 0.0

                    # Calculate solar irradiance components
                    try:
                        disc_output = pvlib.irradiance.disc(
                            ghi=ghi,
                            solar_zenith=zenith,
                            datetime_or_doy=timestamp
                        )
                        
                        dni = disc_output['dni']
                        dhi = ghi - (dni * np.cos(np.radians(zenith)))

                        # Calculate total irradiance
                        total_irrad = pvlib.irradiance.get_total_irradiance(
                            surface_tilt=30,
                            surface_azimuth=180,  # Assuming south-facing
                            dni=dni,
                            ghi=ghi,
                            dhi=dhi,
                            solar_zenith=zenith,
                            solar_azimuth=solar_position['azimuth'].iloc[0]
                        )

                        # Apply system efficiency and thermal derating
                        system_efficiency = 0.75
                        temperature_coefficient = -0.0040

                        # Get temperature and apply thermal derating
                        try:
                            ambient_temp = forecast['main'].get('temp', 25)
                            cell_temperature = ambient_temp + (total_irrad['poa_global'] / 800.0) * 30
                            temperature_factor = 1 + temperature_coefficient * (cell_temperature - 25)
                        except (KeyError, TypeError) as e:
                            logger.warning(f"Error calculating temperature factor: {str(e)}")
                            temperature_factor = 1.0

                        # Calculate final power output
                        dc_power = (
                            total_irrad['poa_global'] * max_watt_peak / 1000.0  # Convert to kW
                            * system_efficiency * temperature_factor
                        )

                        # Store non-negative production value
                        production[timestamp] = max(0, dc_power)

                    except Exception as e:
                        logger.warning(f"Error in irradiance calculations: {str(e)}")
                        # Fallback to simplified calculation
                        if is_day:
                            production[timestamp] = max_watt_peak * 0.2 * clearness_index / 1000.0
                        else:
                            production[timestamp] = 0.0

                except Exception as e:
                    logger.error(f"Error processing forecast at {timestamp}: {str(e)}")
                    continue

            if not production:
                logger.warning("No production values were calculated")
                return {}

            return production

        except Exception as e:
            logger.error(f"Error calculating solar production: {str(e)}")
            return {}

    def _get_timezone(self, lat: float, lon: float) -> str:
        """Get timezone string for given coordinates with retries"""
        for retry in range(self._max_retries):
            try:
                self._wait_for_rate_limit()
                response = requests.get(
                    "http://api.timezonedb.com/v2.1/get-time-zone",
                    params={
                        'key': os.getenv('TIMEZONEDB_API_KEY', 'dummy'),
                        'format': 'json',
                        'by': 'position',
                        'lat': lat,
                        'lng': lon
                    },
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()
                timezone = data.get('zoneName')
                if timezone:
                    return timezone
            except Exception as e:
                logger.warning(f"Error getting timezone (attempt {retry + 1}/{self._max_retries}): {str(e)}")
                if retry < self._max_retries - 1:
                    time.sleep(self._retry_delay)

        logger.warning("Using default timezone: Europe/Amsterdam")
        return 'Europe/Amsterdam'

    def get_pv_forecast(self, max_watt_peak: float) -> Dict[datetime, float]:
        """Get PV production forecast for the next 36 hours with enhanced error handling"""
        try:
            # Validate input
            if not isinstance(max_watt_peak, (int, float)):
                raise ValueError("Invalid max_watt_peak type")

            if max_watt_peak <= 0:
                logger.info("No PV installation configured (max_watt_peak <= 0)")
                return {}

            # Get location with retry
            for retry in range(self._max_retries):
                try:
                    lat, lon = self.get_location_from_ip()
                    break
                except Exception as e:
                    if retry == self._max_retries - 1:
                        logger.error(f"Failed to get location after {self._max_retries} attempts: {str(e)}")
                        return {}
                    time.sleep(self._retry_delay)

            # Get weather data with retry
            try:
                weather_data = self.get_weather_data(lat, lon)
            except Exception as e:
                logger.error(f"Failed to get weather data: {str(e)}")
                return {}

            # Calculate production
            production = self.calculate_solar_production(weather_data, max_watt_peak, lat, lon)
            
            if not production:
                logger.warning("No production values calculated, returning empty forecast")
                return {}

            return production

        except Exception as e:
            logger.error(f"Error getting PV forecast: {str(e)}")
            return {}
