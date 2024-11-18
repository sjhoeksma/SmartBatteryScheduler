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
from scipy.interpolate import CubicSpline

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

    def calculate_solar_production(self, weather_data: Dict, max_watt_peak: float, lat: float, lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data with smooth transitions"""
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

        # Process each forecast period
        for forecast in weather_data['list']:
            try:
                timestamp = datetime.fromtimestamp(forecast['dt']).replace(tzinfo=pytz.UTC)
                local_timestamp = timestamp.astimezone(timezone)

                # Get sunrise/sunset times for the day
                date = local_timestamp.date()
                day_times = pd.date_range(start=f"{date} 00:00:00", end=f"{date} 23:59:59", freq="H", tz=location.tz)
                sun_times = location.get_sun_rise_set_transit(day_times[0])
                sunrise = sun_times['sunrise'].iloc[0]
                sunset = sun_times['sunset'].iloc[0]

                # Skip if outside daylight hours
                if local_timestamp.hour < sunrise.hour or local_timestamp.hour > sunset.hour:
                    production[timestamp] = 0.0
                    continue

                # Calculate relative position in daylight hours
                day_progress = (local_timestamp - sunrise).total_seconds() / (sunset - sunrise).total_seconds()
                
                # Create smooth production curve base using sine function
                base_production_factor = np.sin(day_progress * np.pi)

                # Calculate solar position
                solar_position = location.get_solarposition(pd.DatetimeIndex([local_timestamp]))
                apparent_elevation = float(solar_position['apparent_elevation'].iloc[0])

                # Calculate clear sky radiation
                clearsky = location.get_clearsky(pd.DatetimeIndex([local_timestamp]), model='ineichen')
                
                # Get cloud cover and calculate clearness index
                clouds = min(max(0, forecast.get('clouds', {}).get('all', 100)), 100) / 100.0
                day_of_year = local_timestamp.timetuple().tm_yday
                seasonal_factor = 1.0 + 0.03 * np.sin(2 * np.pi * (day_of_year - 81) / 365)
                clearness_index = max(0.1, (1.0 - (clouds * 0.75)) * seasonal_factor)

                # Calculate radiation components
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

                # Calculate total irradiance
                surface_tilt = 30  # Typical tilt for Netherlands
                surface_azimuth = 180  # South-facing
                
                total_irrad = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=surface_tilt,
                    surface_azimuth=surface_azimuth,
                    dni=dni,
                    ghi=ghi,
                    dhi=dhi,
                    solar_zenith=float(solar_position['apparent_zenith'].iloc[0]),
                    solar_azimuth=float(solar_position['azimuth'].iloc[0]),
                    dni_extra=pvlib.irradiance.get_extra_radiation(local_timestamp.dayofyear),
                    model='haydavies'
                )

                # Calculate temperature effects
                wind_speed = float(forecast.get('wind', {}).get('speed', 1.0))
                temp_air = float(forecast.get('main', {}).get('temp', 25.0))
                
                poa_global = float(total_irrad['poa_global'])
                temp_cell = float(pvlib.temperature.pvsyst_cell(
                    poa_global=poa_global,
                    temp_air=temp_air,
                    wind_speed=wind_speed,
                    u_c=29.0,
                    u_v=0
                ))

                # Calculate efficiency factors
                temp_coefficient = -0.0040
                temp_factor = 1 + temp_coefficient * (temp_cell - 25)
                system_efficiency = 0.75
                soiling_factor = 0.98
                mismatch_factor = 0.98
                wiring_factor = 0.98
                inverter_efficiency = 0.96

                # Calculate final power output with smooth curve integration
                dc_power = (
                    poa_global 
                    * max_watt_peak / 1000.0  # Convert to kW
                    * base_production_factor  # Apply smooth curve
                    * system_efficiency
                    * temp_factor
                    * weather_factor
                    * soiling_factor
                    * mismatch_factor
                    * wiring_factor
                    * inverter_efficiency
                )

                production[timestamp] = max(0.0, dc_power)
                logger.info(f"Calculated production for {local_timestamp}: {dc_power:.2f} kW "
                          f"(clearness: {clearness_index:.2f}, weather: {weather_condition})")

            except Exception as e:
                logger.error(f"Error processing forecast at {timestamp}: {str(e)}")
                production[timestamp] = 0.0

        return production

    def get_pv_forecast(self, max_watt_peak: float) -> float:
        """Get PV production forecast with improved daily curve"""
        try:
            if not isinstance(max_watt_peak, (int, float)) or max_watt_peak <= 0:
                return 0.0

            lat, lon = self.get_location_from_ip()
            current_hour = datetime.now(pytz.UTC).replace(minute=0, second=0, microsecond=0)
            
            # Get location object for solar calculations
            location = Location(latitude=lat, longitude=lon, tz=self._get_timezone(lat, lon))
            
            # Calculate sun position for the day
            date = current_hour.date()
            times = pd.date_range(start=f"{date} 00:00:00", end=f"{date} 23:59:59", freq="H", tz=location.tz)
            solar_position = location.get_solarposition(times)
            
            # Get sunrise/sunset times
            sun_times = location.get_sun_rise_set_transit(times[0])
            sunrise = sun_times['sunrise'].iloc[0]
            sunset = sun_times['sunset'].iloc[0]
            
            # Generate smooth production curve
            production = 0.0
            if sunrise <= current_hour <= sunset:
                # Calculate relative position in daylight hours
                day_progress = (current_hour - sunrise).total_seconds() / (sunset - sunrise).total_seconds()
                
                # Create bell curve peaking at solar noon
                production_factor = np.sin(day_progress * np.pi)
                
                # Get weather data and apply factors
                weather_data = self.get_weather_data(lat, lon)
                if weather_data:
                    clouds = min(max(0, weather_data['list'][0].get('clouds', {}).get('all', 100)), 100) / 100.0
                    clearness = 1.0 - (clouds * 0.75)
                    production = max_watt_peak * production_factor * clearness / 1000.0  # Convert to kW
            
            return max(0.0, production)
            
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
