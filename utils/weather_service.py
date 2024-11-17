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
import streamlit as st
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherService:

    def __init__(self, cache_ttl: int = 3600):  # Default 1-hour cache TTL
        self.api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenWeatherMap API key not found in environment variables")

        self.base_url = "http://api.openweathermap.org/data/2.5"
        self._location_cache = None
        self._weather_cache = {}
        self._cache_ttl = timedelta(seconds=cache_ttl)
        self._last_cache_time = {}
        self._cache_file = Path('.DB/location_cache.pkl')
        self._last_api_call = 0
        self._base_delay = 1.0
        self._max_retries = 3
        self._timezone_cache = {}
        self._default_location = (52.3025, 4.6889)  # Netherlands coordinates
        self._load_cached_location()

    def _cleanup_cache(self):
        """Remove expired entries from weather cache"""
        current_time = datetime.now()
        expired_keys = [
            key for key, last_time in self._last_cache_time.items()
            if current_time - last_time > self._cache_ttl
        ]
        for key in expired_keys:
            self._weather_cache.pop(key, None)
            self._last_cache_time.pop(key, None)

    def _exponential_backoff(self, retry: int) -> float:
        """Calculate exponential backoff delay"""
        return min(300, self._base_delay * (2**retry))

    def _wait_for_rate_limit(self, retry: int = 0):
        """Implement rate limiting with exponential backoff"""
        current_time = time.time()
        delay = self._exponential_backoff(retry)
        time_since_last_call = current_time - self._last_api_call
        if time_since_last_call < delay:
            time.sleep(delay - time_since_last_call)
        self._last_api_call = time.time()

    def _load_cached_location(self):
        """Load cached location from file"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    if isinstance(cache_data, dict):
                        if cache_data.get('timestamp') and \
                           datetime.now() - cache_data['timestamp'] < timedelta(days=1):
                            self._location_cache = cache_data.get('location')
                            logger.info(
                                f"Loaded valid cached location: {self._location_cache}"
                            )
                            return
                    logger.info("Cache expired or invalid")
        except Exception as e:
            logger.warning(f"Failed to load cached location: {str(e)}")

    def _save_cached_location(self, location: Tuple[float, float]):
        """Save location to cache file"""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {'location': location, 'timestamp': datetime.now()}
            with open(self._cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            self._location_cache = location
            logger.info(f"Saved location to cache: {location}")
        except Exception as e:
            logger.warning(f"Failed to save location to cache: {str(e)}")

    def get_location_from_ip(self) -> Tuple[float, float]:
        """Get location with Netherlands as default"""
        # Return default location (Netherlands)
        logger.info(
            f"Using default location (Netherlands): {self._default_location}")
        self._save_cached_location(self._default_location)
        return self._default_location

    def _get_timezone(self, lat: float, lon: float) -> str:
        """Get timezone string for given coordinates"""
        cache_key = f"{lat},{lon}"
        if cache_key in self._timezone_cache:
            return self._timezone_cache[cache_key]

        try:
            import timezonefinder
            tf = timezonefinder.TimezoneFinder()
            timezone_str = tf.timezone_at(lat=lat, lng=lon)
            if timezone_str:
                self._timezone_cache[cache_key] = timezone_str
                return timezone_str
        except Exception as e:
            logger.warning(f"TimezoneFinder failed: {str(e)}")

        # Default to Europe/Amsterdam for Netherlands
        default_tz = 'Europe/Amsterdam'
        self._timezone_cache[cache_key] = default_tz
        return default_tz

    def calculate_solar_production(self, weather_data: Dict,
                                   max_watt_peak: float, lat: float,
                                   lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data"""
        try:
            if not isinstance(weather_data,
                              dict) or 'list' not in weather_data:
                raise ValueError("Invalid weather data format")

            # Create location object for solar calculations
            location = Location(latitude=lat, longitude=lon)
            tz_name = self._get_timezone(lat, lon)
            timezone = pytz.timezone(tz_name)
            production = {}

            for forecast in weather_data['list']:
                try:
                    if not isinstance(forecast, dict):
                        continue

                    # Convert timestamp to timezone-aware datetime
                    timestamp = datetime.fromtimestamp(forecast['dt'],
                                                       tz=pytz.UTC)
                    if tz_name != 'UTC':
                        timestamp = timestamp.astimezone(timezone)

                    # Create a pandas DatetimeIndex for solar calculations
                    times = pd.DatetimeIndex([timestamp])

                    # Get solar position using pandas DataFrame
                    solar_position = location.get_solarposition(times)

                    # Calculate clearness index from cloud cover
                    clouds = forecast.get('clouds', {}).get('all', 100) / 100.0
                    clearness_index = 1 - (clouds * 0.75)

                    # Get scalar zenith value and determine daytime
                    zenith = float(solar_position['apparent_zenith'].iloc[0])
                    is_day = zenith < 90

                    if is_day:
                        # Calculate clear sky radiation using pandas DataFrame
                        clearsky = location.get_clearsky(times)
                        if not clearsky.empty:
                            ghi = float(
                                clearsky['ghi'].iloc[0]) * clearness_index

                            # Apply weather conditions
                            weather_condition = forecast.get(
                                'weather', [{}])[0].get('main', '').lower()
                            condition_factors = {
                                'clear': 1.0,
                                'clouds': 0.8,
                                'rain': 0.4,
                                'snow': 0.3,
                                'mist': 0.6,
                                'fog': 0.5
                            }
                            weather_factor = condition_factors.get(
                                weather_condition, 0.7)
                            ghi *= weather_factor

                            # Calculate irradiance components using scalar inputs
                            disc_output = pvlib.irradiance.disc(
                                ghi=ghi,
                                solar_zenith=zenith,
                                datetime_or_doy=times)

                            # Extract scalar DNI value
                            dni = float(disc_output['dni'].iloc[0])
                            dhi = ghi - (dni * np.cos(np.radians(zenith)))

                            # Calculate total irradiance on tilted surface
                            total_irrad = pvlib.irradiance.get_total_irradiance(
                                surface_tilt=
                                30,  # Assuming 30-degree tilt for panels
                                surface_azimuth=180,  # Assuming south-facing
                                dni=dni,
                                ghi=ghi,
                                dhi=dhi,
                                solar_zenith=zenith,
                                solar_azimuth=float(
                                    solar_position['azimuth'].iloc[0]))

                            # Apply system efficiency and temperature derating
                            system_efficiency = 0.75  # Standard system efficiency
                            temperature_coefficient = -0.0040  # Temperature coefficient for power

                            # Temperature correction
                            ambient_temp = forecast.get('main',
                                                        {}).get('temp', 25)
                            cell_temperature = ambient_temp + (
                                total_irrad['poa_global'] / 800.0) * 30
                            temperature_factor = 1 + temperature_coefficient * (
                                cell_temperature - 25)

                            # Calculate final power output
                            dc_power = (
                                total_irrad['poa_global'] * max_watt_peak /
                                1000.0  # Convert to kW
                                * system_efficiency * temperature_factor *
                                weather_factor)

                            production[timestamp] = max(0, dc_power)
                        else:
                            # Simplified calculation for missing clearsky data
                            daytime_factor = np.cos(
                                np.radians(zenith)) if zenith < 90 else 0
                            production[
                                timestamp] = max_watt_peak * 0.2 * clearness_index * daytime_factor / 1000.0
                    else:
                        production[timestamp] = 0.0

                except Exception as e:
                    logger.warning(
                        f"Error processing forecast at {timestamp}: {str(e)}")
                    continue

            return production

        except Exception as e:
            logger.error(f"Error calculating solar production: {str(e)}")
            return {}

    def get_pv_forecast(self, max_watt_peak: float) -> Dict[datetime, float]:
        """Get PV production forecast with error handling"""
        try:
            if not isinstance(max_watt_peak,
                              (int, float)) or max_watt_peak <= 0:
                return {}

            lat, lon = self.get_location_from_ip()
            weather_data = None

            for retry in range(self._max_retries):
                try:
                    self._wait_for_rate_limit(retry)
                    weather_data = self.get_weather_data(lat, lon)
                    if weather_data:
                        break
                except Exception as e:
                    logger.warning(
                        f"Weather data fetch attempt {retry + 1} failed: {str(e)}"
                    )
                    if retry < self._max_retries - 1:
                        time.sleep(self._exponential_backoff(retry))

            if not weather_data:
                return {}

            return self.calculate_solar_production(weather_data, max_watt_peak,
                                                   lat, lon)

        except Exception as e:
            logger.error(f"Error in PV forecast: {str(e)}")
            return {}

    def get_weather_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Get weather data with improved caching and rate limiting"""
        try:
            cache_key = f"{lat},{lon}"
            current_time = datetime.now()

            # Clean up expired cache entries
            self._cleanup_cache()

            # Check cache validity
            if (cache_key in self._weather_cache
                    and cache_key in self._last_cache_time
                    and current_time - self._last_cache_time[cache_key]
                    < self._cache_ttl):
                return self._weather_cache[cache_key]

            for retry in range(self._max_retries):
                try:
                    self._wait_for_rate_limit(retry)

                    response = requests.get(f"{self.base_url}/forecast",
                                            params={
                                                'lat': lat,
                                                'lon': lon,
                                                'appid': self.api_key,
                                                'units': 'metric'
                                            },
                                            timeout=10)

                    if response.status_code == 429:
                        logger.warning("OpenWeatherMap API rate limit reached")
                        if retry < self._max_retries - 1:
                            time.sleep(self._exponential_backoff(retry))
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if not isinstance(data, dict) or 'list' not in data:
                        raise ValueError("Invalid API response format")

                    # Update cache with new data
                    self._weather_cache[cache_key] = data
                    self._last_cache_time[cache_key] = current_time

                    return data

                except Exception as e:
                    logger.warning(
                        f"Weather API request failed (attempt {retry + 1}): {str(e)}"
                    )
                    if retry < self._max_retries - 1:
                        time.sleep(self._exponential_backoff(retry))

            raise Exception("Failed to fetch weather data after all retries")

        except Exception as e:
            logger.error(f"Error in get_weather_data: {str(e)}")
            return None
