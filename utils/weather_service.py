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
            raise ValueError("OpenWeatherMap API key not found in environment variables")

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

    def calculate_solar_production(self, weather_data: Dict, max_watt_peak: float, lat: float, lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data with enhanced solar calculations"""
        if not isinstance(weather_data, dict) or 'list' not in weather_data:
            logger.error("Invalid weather data format")
            return {}

        # Get timezone for the location
        tz_name = self._get_timezone(lat, lon)
        try:
            timezone = pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {tz_name}, falling back to UTC")
            timezone = pytz.UTC

        # Create location object for solar calculations
        location = Location(latitude=lat, longitude=lon, tz=tz_name, altitude=10)
        production = {}

        for forecast in weather_data['list']:
            try:
                if not isinstance(forecast, dict):
                    continue

                # Convert timestamp to timezone-aware datetime
                timestamp = datetime.fromtimestamp(forecast['dt'], tz=pytz.UTC)
                local_timestamp = timestamp.astimezone(timezone)

                # Create a pandas DatetimeIndex for solar calculations
                times = pd.DatetimeIndex([local_timestamp])

                # Calculate solar position
                solar_position = location.get_solarposition(times=times, temperature=forecast.get('main', {}).get('temp', 25))
                
                # Calculate extra terrestrial DNI
                dni_extra = pvlib.irradiance.get_extra_radiation(times)

                # Check if sun is below horizon
                if solar_position['apparent_elevation'].iloc[0] <= 0:
                    production[timestamp] = 0.0
                    logger.debug(f"Night time at {local_timestamp}, production: 0.0 kW")
                    continue

                # Get cloud cover with validation
                clouds = forecast.get('clouds', {}).get('all', 100)
                if not isinstance(clouds, (int, float)):
                    clouds = 100
                clouds = min(max(0, clouds), 100) / 100.0

                # Calculate clearness index with seasonal adjustment
                day_of_year = local_timestamp.timetuple().tm_yday
                seasonal_factor = 1.0 + 0.03 * np.sin(2 * np.pi * (day_of_year - 81) / 365)
                clearness_index = max(0.1, (1.0 - (clouds * 0.75)) * seasonal_factor)

                # Get clear sky radiation with enhanced model
                clearsky = location.get_clearsky(times, model='ineichen', dni_extra=dni_extra)
                if clearsky.empty:
                    logger.warning(f"No clearsky data available for {local_timestamp}")
                    production[timestamp] = 0.0
                    continue

                # Calculate DNI and DHI
                dni = float(clearsky['dni'].iloc[0]) * clearness_index
                ghi = float(clearsky['ghi'].iloc[0]) * clearness_index
                dhi = float(clearsky['dhi'].iloc[0]) * clearness_index

                # Apply weather conditions with detailed factors
                weather_condition = forecast.get('weather', [{}])[0].get('main', '').lower()
                condition_factors = {
                    'clear': 1.0,
                    'clouds': 0.8,
                    'rain': 0.4,
                    'snow': 0.3,
                    'mist': 0.6,
                    'fog': 0.5,
                    'drizzle': 0.5,
                    'thunderstorm': 0.2
                }
                weather_factor = condition_factors.get(weather_condition, 0.7)

                # Calculate total irradiance on tilted surface with enhanced model
                surface_tilt = 30  # Typical tilt for Netherlands
                surface_azimuth = 180  # South-facing
                total_irrad = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=surface_tilt,
                    surface_azimuth=surface_azimuth,
                    dni=dni,
                    ghi=ghi,
                    dhi=dhi,
                    solar_zenith=solar_position['apparent_zenith'].iloc[0],
                    solar_azimuth=solar_position['azimuth'].iloc[0],
                    dni_extra=dni_extra.iloc[0],
                    model='haydavies'
                )

                # Calculate cell temperature using Sandia model
                wind_speed = forecast.get('wind', {}).get('speed', 1.0)
                temp_cell = pvlib.temperature.sapm_cell(
                    poa_global=total_irrad['poa_global'],
                    temp_air=forecast.get('main', {}).get('temp', 25),
                    wind_speed=wind_speed,
                    a=-3.56,  # SAPM temperature model coefficient
                    b=-0.075  # SAPM temperature model coefficient
                )

                # Calculate temperature-adjusted efficiency
                temp_coefficient = -0.0040  # Standard temperature coefficient for power
                temp_factor = 1 + temp_coefficient * (float(temp_cell) - 25)

                # Calculate final power output with enhanced efficiency model
                system_efficiency = 0.75  # Base system efficiency
                soiling_factor = 0.98  # Account for panel soiling
                mismatch_factor = 0.98  # Account for panel mismatch
                wiring_factor = 0.98  # Account for wiring losses
                inverter_efficiency = 0.96  # Typical inverter efficiency

                dc_power = (
                    total_irrad['poa_global'] * max_watt_peak / 1000.0  # Convert to kW
                    * system_efficiency
                    * temp_factor
                    * weather_factor
                    * soiling_factor
                    * mismatch_factor
                    * wiring_factor
                    * inverter_efficiency
                )

                production[timestamp] = max(0, float(dc_power))
                logger.info(f"Calculated production for {local_timestamp}: {float(dc_power):.2f} kW "
                          f"(clearness: {clearness_index:.2f}, weather: {weather_condition})")

            except Exception as e:
                logger.error(f"Error processing forecast at {timestamp}: {str(e)}")
                production[timestamp] = 0.0

        return production

    def get_pv_forecast(self, max_watt_peak: float) -> float:
        """Get PV production forecast for current hour"""
        try:
            if not isinstance(max_watt_peak, (int, float)) or max_watt_peak <= 0:
                return 0.0

            # Get current hour in UTC
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            current_hour = current_hour.astimezone(pytz.UTC)

            lat, lon = self.get_location_from_ip()
            weather_data = None

            # Attempt to get weather data with retries
            for retry in range(self._max_retries):
                try:
                    self._wait_for_rate_limit(retry)
                    weather_data = self.get_weather_data(lat, lon)
                    if weather_data:
                        break
                except Exception as e:
                    logger.warning(f"Weather data fetch attempt {retry + 1} failed: {str(e)}")
                    if retry < self._max_retries - 1:
                        time.sleep(self._exponential_backoff(retry))

            if not weather_data:
                logger.error("Failed to get weather data after all retries")
                return 0.0

            # Calculate production for all hours
            pv_forecast = self.calculate_solar_production(weather_data, max_watt_peak, lat, lon)
            
            # Return current hour production
            if current_hour in pv_forecast:
                return pv_forecast[current_hour]
            
            logger.warning(f"No production data available for current hour: {current_hour}")
            return 0.0

        except Exception as e:
            logger.error(f"Error in PV forecast: {str(e)}")
            return 0.0

    def get_weather_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Get weather data with improved validation and error handling"""
        try:
            cache_key = f"{lat},{lon}"
            current_time = datetime.now()

            # Clean up expired cache entries
            self._cleanup_cache()

            # Check cache validity
            if (cache_key in self._weather_cache
                    and cache_key in self._last_cache_time
                    and current_time - self._last_cache_time[cache_key] < self._cache_ttl):
                return self._weather_cache[cache_key]

            for retry in range(self._max_retries):
                try:
                    self._wait_for_rate_limit(retry)

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

                    if response.status_code == 429:
                        logger.warning("OpenWeatherMap API rate limit reached")
                        if retry < self._max_retries - 1:
                            time.sleep(self._exponential_backoff(retry))
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Validate response format
                    if not isinstance(data, dict):
                        raise ValueError("Invalid API response format: not a dictionary")
                    if 'list' not in data:
                        raise ValueError("Invalid API response format: missing 'list' key")
                    if not isinstance(data['list'], list):
                        raise ValueError("Invalid API response format: 'list' is not an array")
                    if not data['list']:
                        raise ValueError("Invalid API response format: empty forecast list")

                    # Validate forecast entries
                    for entry in data['list']:
                        if not isinstance(entry, dict):
                            continue
                        if 'dt' not in entry:
                            logger.warning("Missing timestamp in forecast entry")
                        if 'main' not in entry or not isinstance(entry['main'], dict):
                            logger.warning("Missing or invalid 'main' data in forecast entry")
                        if 'clouds' not in entry or not isinstance(entry['clouds'], dict):
                            logger.warning("Missing or invalid cloud cover data in forecast entry")

                    # Update cache with new data
                    self._weather_cache[cache_key] = data
                    self._last_cache_time[cache_key] = current_time

                    return data

                except requests.exceptions.RequestException as e:
                    logger.warning(f"Weather API request failed (attempt {retry + 1}): {str(e)}")
                    if retry < self._max_retries - 1:
                        time.sleep(self._exponential_backoff(retry))
                except (ValueError, KeyError) as e:
                    logger.error(f"Invalid API response format: {str(e)}")
                    return None

            raise Exception("Failed to fetch weather data after all retries")

        except Exception as e:
            logger.error(f"Error in get_weather_data: {str(e)}")
            return None

    def get_location_from_ip(self) -> Tuple[float, float]:
        """Get location with Netherlands as default"""
        logger.info(f"Using default location (Netherlands): {self._default_location}")
        self._save_cached_location(self._default_location)
        return self._default_location

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
                            logger.info(f"Loaded valid cached location: {self._location_cache}")
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
