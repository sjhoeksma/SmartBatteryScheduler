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
        self._pv_forecast_cache = {}  # Cache for PV forecasts
        self._cache_ttl = timedelta(seconds=cache_ttl)
        self._last_cache_time = {}
        self._cache_file = Path('.DB/location_cache.pkl')
        self._last_api_call = 0
        self._base_delay = 1.0
        self._max_retries = 3
        self._timezone_cache = {}
        self._default_location = (52.3025, 4.6889)  # Netherlands coordinates
        self._load_cached_location()
        
        # Clean old cache entries periodically
        self._clean_cache()

    def calculate_solar_production(self, weather_data: Dict, max_watt_peak: float, lat: float, lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data"""
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
                timestamp = datetime.fromtimestamp(forecast['dt']).replace(tzinfo=pytz.UTC)
                local_timestamp = timestamp.astimezone(timezone)

                # Create times DataFrame
                times = pd.date_range(start=local_timestamp, periods=1, freq='h')

                # Calculate solar position
                solar_position = location.get_solarposition(times)
                apparent_elevation = float(solar_position['apparent_elevation'].iloc[0])

                # Check if sun is below horizon
                if apparent_elevation <= 0:
                    production[timestamp] = 0.0
                    continue

                # Calculate extra terrestrial DNI
                dni_extra = float(pvlib.irradiance.get_extra_radiation(times.dayofyear[0]))

                # Get cloud cover and calculate clearness index
                clouds = min(max(0, forecast.get('clouds', {}).get('all', 100)), 100) / 100.0
                day_of_year = local_timestamp.timetuple().tm_yday
                seasonal_factor = 1.0 + 0.03 * np.sin(2 * np.pi * (day_of_year - 81) / 365)
                clearness_index = max(0.1, (1.0 - (clouds * 0.75)) * seasonal_factor)

                # Calculate clear sky radiation
                clearsky = location.get_clearsky(times, model='ineichen')

                # Calculate DNI and DHI with proper DataFrame handling
                dni = float(clearsky['dni'].iloc[0]) * clearness_index
                ghi = float(clearsky['ghi'].iloc[0]) * clearness_index
                dhi = float(clearsky['dhi'].iloc[0]) * clearness_index

                # Apply weather condition factors
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

                # Calculate total irradiance with proper DataFrame handling
                surface_tilt = 30  # Typical tilt for Netherlands
                surface_azimuth = 180  # South-facing

                solar_zenith = float(solar_position['apparent_zenith'].iloc[0])
                solar_azimuth = float(solar_position['azimuth'].iloc[0])

                total_irrad = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=surface_tilt,
                    surface_azimuth=surface_azimuth,
                    dni=dni,
                    ghi=ghi,
                    dhi=dhi,
                    solar_zenith=solar_zenith,
                    solar_azimuth=solar_azimuth,
                    dni_extra=dni_extra,
                    model='haydavies'
                )

                # Calculate cell temperature
                wind_speed = float(forecast.get('wind', {}).get('speed', 1.0))
                temp_air = float(forecast.get('main', {}).get('temp', 25.0))

                # Calculate cell temperature using pvsyst model with proper float handling
                poa_global = float(total_irrad['poa_global'])
                temp_cell = float(pvlib.temperature.pvsyst_cell(
                    poa_global=poa_global,
                    temp_air=temp_air,
                    wind_speed=wind_speed,
                    u_c=29.0,  # Heat transfer coefficient
                    u_v=0  # Wind speed coefficient
                ))

                # Calculate efficiency factors
                temp_coefficient = -0.0040
                temp_factor = 1 + temp_coefficient * (temp_cell - 25)
                system_efficiency = 0.75
                soiling_factor = 0.98
                mismatch_factor = 0.98
                wiring_factor = 0.98
                inverter_efficiency = 0.96

                # Calculate final power output
                dc_power = (
                    poa_global 
                    * max_watt_peak / 1000.0
                    * system_efficiency
                    * temp_factor
                    * weather_factor
                    * soiling_factor
                    * mismatch_factor
                    * wiring_factor
                    * inverter_efficiency
                )

                production[timestamp] = max(0, dc_power)
                logger.info(f"Calculated production for {local_timestamp}: {dc_power:.2f} kW "
                          f"(clearness: {clearness_index:.2f}, weather: {weather_condition})")

            except Exception as e:
                logger.error(f"Error processing forecast at {timestamp}: {str(e)}")
                production[timestamp] = 0.0

        return production

    def get_pv_forecast(self, max_watt_peak: float) -> float:
        """Get PV production forecast with caching"""
        try:
            if not isinstance(max_watt_peak, (int, float)) or max_watt_peak <= 0:
                return 0.0

            current_hour = datetime.now(pytz.UTC).replace(minute=0, second=0, microsecond=0)
            cache_key = f"{current_hour}_{max_watt_peak}"

            # Check cache first
            if cache_key in self._pv_forecast_cache:
                cache_entry = self._pv_forecast_cache[cache_key]
                if datetime.now(pytz.UTC) - cache_entry['timestamp'] < self._cache_ttl:
                    return cache_entry['value']

            lat, lon = self.get_location_from_ip()
            
            # Get weather data
            weather_data = self.get_weather_data(lat, lon)
            if not weather_data:
                return 0.0

            # Calculate production for all hours
            pv_forecast = self.calculate_solar_production(weather_data, max_watt_peak, lat, lon)
            
            # Find the closest forecast time
            if not pv_forecast:
                return 0.0
                
            closest_time = min(pv_forecast.keys(), key=lambda x: abs(x - current_hour))
            time_diff = abs((closest_time - current_hour).total_seconds())
            
            if time_diff <= 3600:  # Within 1 hour
                forecast_value = pv_forecast[closest_time]
                # Cache the result
                self._pv_forecast_cache[cache_key] = {
                    'value': forecast_value,
                    'timestamp': datetime.now(pytz.UTC)
                }
                return forecast_value
            
            logger.warning(f"No production data available for current hour: {current_hour}")
            return 0.0

        except Exception as e:
            logger.error(f"Error in PV forecast: {str(e)}")
            return 0.0

    def get_weather_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Get weather data with caching"""
        try:
            cache_key = f"{lat},{lon}"
            current_time = datetime.now(pytz.UTC)

            # Check cache
            if (cache_key in self._weather_cache
                    and cache_key in self._last_cache_time
                    and current_time - self._last_cache_time[cache_key] < self._cache_ttl):
                return self._weather_cache[cache_key]

            # Fetch new data
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
                        logger.warning("API rate limit reached")
                        time.sleep(self._exponential_backoff(retry))
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Update cache
                    self._weather_cache[cache_key] = data
                    self._last_cache_time[cache_key] = current_time
                    return data

                except requests.exceptions.RequestException as e:
                    logger.warning(f"API request failed (attempt {retry + 1}): {str(e)}")
                    if retry < self._max_retries - 1:
                        time.sleep(self._exponential_backoff(retry))

            return None

        except Exception as e:
            logger.error(f"Error in get_weather_data: {str(e)}")
            return None

    def get_location_from_ip(self) -> Tuple[float, float]:
        """Get location with Netherlands as default"""
        logger.info(f"Using default location (Netherlands): {self._default_location}")
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

    def _load_cached_location(self):
        """Load cached location from file"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    if isinstance(cache_data, dict):
                        self._location_cache = cache_data.get('location')
        except Exception as e:
            logger.warning(f"Failed to load location cache: {str(e)}")

    def _save_cached_location(self, location: Tuple[float, float]):
        """Save location to cache file"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            cache_data = {'location': location, 'timestamp': datetime.now(pytz.UTC)}
            with open(self._cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to save location to cache: {str(e)}")

    def _clean_cache(self):
        """Clean expired cache entries"""
        current_time = datetime.now(pytz.UTC)
        # Clean weather cache
        expired_weather = [
            key for key, timestamp in self._last_cache_time.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_weather:
            self._weather_cache.pop(key, None)
            self._last_cache_time.pop(key, None)

        # Clean PV forecast cache
        expired_pv = [
            key for key, entry in self._pv_forecast_cache.items()
            if current_time - entry['timestamp'] >= self._cache_ttl
        ]
        for key in expired_pv:
            self._pv_forecast_cache.pop(key)

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
