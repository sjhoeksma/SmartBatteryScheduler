import os
import time
import json
import logging
import pickle
import requests
import numpy as np
import pandas as pd
import pvlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import pytz
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


class WeatherService:

    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 3600):
        """Initialize WeatherService with API key and cache settings"""
        self.api_key = api_key or os.environ.get('OPENWEATHERMAP_API_KEY')
        if not self.api_key:
            logger.error("OpenWeatherMap API key is missing")
            raise ValueError("OpenWeatherMap API key is required")
        self._base_url = "http://api.openweathermap.org/data/2.5/weather"
        self._weather_cache = {}
        self._pv_forecast_cache = {}
        self._location_cache = None
        self._cache_ttl = timedelta(seconds=cache_ttl)
        self._last_cache_time = {}
        self._cache_file = Path('.DB/location_cache.pkl')
        self._last_api_call = 0
        self._wait_time = 1.0  # Initial wait time between API calls
        self._base_delay = 1.0
        self._max_retries = 3
        self._timezone_cache = {}
        self._load_cached_location()

    def _wait_for_rate_limit(self, retry: int = 0):
        """Implement rate limiting with exponential backoff"""
        current_time = time.time()
        delay = self._exponential_backoff(retry)
        time_since_last_call = current_time - self._last_api_call
        if time_since_last_call < delay:
            time.sleep(delay - time_since_last_call)
        self._last_api_call = time.time()

    def _exponential_backoff(self, retry: int) -> float:
        """Calculate exponential backoff delay"""
        return min(300, self._base_delay * (2**retry))

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

    def _load_cached_location(self):
        """Load location from cache file"""
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
            cache_data = {
                'location': location,
                'timestamp': datetime.now(pytz.UTC)
            }
            with open(self._cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to save location to cache: {str(e)}")

    def get_location(self) -> Tuple[float, float]:
        """Get location coordinates (latitude, longitude)"""
        if self._location_cache is None:
            # Default to Netherlands coordinates if no location is set
            self._location_cache = (52.3676, 4.9041)  # Amsterdam coordinates
            self._save_cached_location(self._location_cache)
        return self._location_cache

    def get_timezone(self) -> str:
        """Get timezone string for current location"""
        lat, lon = self.get_location()
        cache_key = f"{lat},{lon}"

        if cache_key not in self._timezone_cache:
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lat=lat, lng=lon)
            self._timezone_cache[
                cache_key] = timezone_str or 'Europe/Amsterdam'

        return self._timezone_cache[cache_key]

    def calculate_solar_production(self, date, max_watt_peak,
                                   system_efficiency):
        try:
            # Get location data
            lat, lon = self.get_location()
            timezone = self.get_timezone()
            location = pvlib.location.Location(latitude=lat,
                                               longitude=lon,
                                               tz=timezone)

            # Get solar position
            times = pd.DatetimeIndex([date])
            solar_position = location.get_solarposition(times)

            # Check if sun is up and get elevation angle
            elevation = solar_position['apparent_elevation']
            if isinstance(elevation, pd.Series):
                elevation = elevation.iloc[0]

            # No production before sunrise or after sunset
            if elevation <= 0:
                return 0.0

            # Get weather data
            weather = self.get_weather_data(date)
            cloud_cover = weather.get('clouds', {}).get('all', 0) / 100.0

            # Calculate clear sky radiation using proper solar model
            clearsky = location.get_clearsky(times, model='ineichen')
            ghi = clearsky['ghi']
            if isinstance(ghi, pd.Series):
                ghi = ghi.iloc[0]  # Global horizontal irradiance

            # Calculate actual radiation considering cloud cover
            actual_ghi = ghi * (1.0 - (0.75 * cloud_cover))

            # Calculate PV production using realistic system efficiency
            angle_factor = np.sin(np.radians(elevation))  # Sun angle impact

            # Calculate final production in kW
            production = (max_watt_peak /
                          1000.0) * system_efficiency * angle_factor * (
                              actual_ghi / 1000.0)

            return max(0.0, production)  # Ensure no negative values

        except Exception as e:
            logger.error(f"Error calculating solar production: {str(e)}")
            return 0.0

    def get_weather_data(self, timestamp: datetime) -> Dict:
        """Get weather data for specified timestamp"""
        self._clean_cache()

        # Convert timestamp to UTC for consistent caching
        if timestamp.tzinfo is None:
            timestamp = pytz.UTC.localize(timestamp)
        cache_key = timestamp.strftime('%Y-%m-%d-%H')

        # Return cached data if available
        if cache_key in self._weather_cache:
            if datetime.now(
                    pytz.UTC
            ) - self._last_cache_time[cache_key] < self._cache_ttl:
                return self._weather_cache[cache_key]

        # Get fresh weather data
        lat, lon = self.get_location()
        retry_count = 0

        while retry_count <= self._max_retries:
            try:
                self._wait_for_rate_limit(retry_count)
                response = requests.get(self._base_url,
                                        params={
                                            'lat': lat,
                                            'lon': lon,
                                            'appid': self.api_key,
                                            'units': 'metric'
                                        },
                                        timeout=10)

                if response.status_code == 200:
                    weather_data = response.json()
                    self._weather_cache[cache_key] = weather_data
                    self._last_cache_time[cache_key] = datetime.now(pytz.UTC)
                    return weather_data

            except requests.RequestException as e:
                logger.error(f"Weather API request failed: {str(e)}")
                retry_count += 1
                if retry_count > self._max_retries:
                    raise

        raise RuntimeError(
            "Failed to fetch weather data after multiple retries")

    def get_pv_forecast(self,
                        max_watt_peak: float,
                        system_efficiency: float,
                        date: Optional[datetime] = None) -> float:
        if max_watt_peak <= 0:
            return 0.0

        if date is None:
            date = datetime.now(pytz.UTC)

        # Ensure date is timezone-aware
        if date.tzinfo is None:
            timezone = pytz.timezone(self.get_timezone())
            date = timezone.localize(date)

        # Create cache key
        cache_key = f"{date.strftime('%Y-%m-%d-%H')}-{max_watt_peak}"

        # Check cache
        if cache_key in self._pv_forecast_cache:
            cache_entry = self._pv_forecast_cache[cache_key]
            if datetime.now(
                    pytz.UTC) - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['production']

        # Calculate new forecast
        production = self.calculate_solar_production(date, max_watt_peak,
                                                     system_efficiency)

        # Cache the result
        self._pv_forecast_cache[cache_key] = {
            'production': production,
            'timestamp': datetime.now(pytz.UTC)
        }

        return production

    @property
    def location(self):
        """Get pvlib location object for current coordinates"""
        lat, lon = self.get_location()
        timezone = self.get_timezone()
        return pvlib.location.Location(latitude=lat,
                                       longitude=lon,
                                       tz=timezone)
