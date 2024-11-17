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
        self._cache_duration = timedelta(hours=12)
        self._last_cache_time = None
        self._cache_file = Path('.DB/location_cache.pkl')
        self._last_api_call = 0
        self._base_delay = 1.0
        self._max_retries = 3
        self._timezone_cache = {}
        self._load_cached_location()

    def _exponential_backoff(self, retry: int) -> float:
        """Calculate exponential backoff delay"""
        return min(300, self._base_delay * (2 ** retry))

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
                            logger.info(f"Loaded valid cached location: {self._location_cache}")
                            return
                    logger.info("Cache expired or invalid")
        except Exception as e:
            logger.warning(f"Failed to load cached location: {str(e)}")

    def _save_cached_location(self, location: Tuple[float, float]):
        """Save location to cache file"""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                'location': location,
                'timestamp': datetime.now()
            }
            with open(self._cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            self._location_cache = location
            logger.info(f"Saved location to cache: {location}")
        except Exception as e:
            logger.warning(f"Failed to save location to cache: {str(e)}")

    def get_location_from_ip(self) -> Tuple[float, float]:
        """Get location with fallback mechanisms"""
        # Return cached location if available
        if self._location_cache:
            return self._location_cache

        # Try IP-based geolocation services
        geolocation_services = [
            ('https://ipapi.co/json/', lambda x: (x.get('latitude'), x.get('longitude'))),
            ('https://ip-api.com/json/', lambda x: (x.get('lat'), x.get('lon'))),
            ('https://ipinfo.io/json', lambda x: tuple(map(float, x.get('loc', '0,0').split(','))))
        ]

        for retry in range(self._max_retries):
            self._wait_for_rate_limit(retry)
            
            # Shuffle services to distribute load
            np.random.shuffle(geolocation_services)
            
            for service_url, extract_coords in geolocation_services:
                try:
                    response = requests.get(service_url, timeout=5)
                    if response.status_code == 429:
                        logger.warning(f"Rate limit reached for {service_url}")
                        continue
                    
                    response.raise_for_status()
                    data = response.json()

                    if not isinstance(data, dict):
                        raise ValueError("Invalid response format")

                    lat, lon = extract_coords(data)
                    if lat is None or lon is None:
                        raise ValueError("Missing coordinates in response")

                    if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
                        raise ValueError("Invalid coordinate values")

                    location = (float(lat), float(lon))
                    self._save_cached_location(location)
                    return location

                except Exception as e:
                    logger.warning(f"Error with {service_url}: {str(e)}")
                
                if retry < self._max_retries - 1:
                    time.sleep(self._exponential_backoff(retry))

        # Fallback to Netherlands coordinates
        default_location = (52.3025, 4.6889)  # Netherlands coordinates
        logger.warning(f"Using default location (Netherlands): {default_location}")
        self._save_cached_location(default_location)
        return default_location

    def _get_timezone(self, lat: float, lon: float) -> str:
        """Get timezone string for given coordinates"""
        try:
            import timezonefinder
            tf = timezonefinder.TimezoneFinder()
            timezone_str = tf.timezone_at(lat=lat, lng=lon)
            if timezone_str:
                return timezone_str
        except Exception as e:
            logger.warning(f"TimezoneFinder failed: {str(e)}")

        # Fallback to region-based approximation
        if lat >= 35 and lat <= 70:  # Europe
            if lon >= -10 and lon <= 40:
                return 'Europe/Amsterdam'
        elif lat >= 25 and lat <= 50:  # North America
            if lon >= -130 and lon <= -60:
                return 'America/New_York'
        
        logger.warning("Using UTC timezone as fallback")
        return 'UTC'

    def calculate_solar_production(self, weather_data: Dict, max_watt_peak: float,
                                 lat: float, lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data"""
        try:
            if not isinstance(weather_data, dict) or 'list' not in weather_data:
                raise ValueError("Invalid weather data format")

            location = Location(latitude=lat, longitude=lon)
            tz_name = self._get_timezone(lat, lon)
            timezone = pytz.timezone(tz_name)
            production = {}

            for forecast in weather_data['list']:
                try:
                    if not isinstance(forecast, dict):
                        continue

                    # Convert timestamp to timezone-aware datetime
                    timestamp = datetime.fromtimestamp(forecast['dt'])
                    if timestamp.tzinfo is None:
                        timestamp = pytz.utc.localize(timestamp).astimezone(timezone)

                    # Get solar position
                    solar_position = location.get_solarposition(timestamp)
                    
                    # Calculate clearness index from cloud cover
                    clouds = forecast.get('clouds', {}).get('all', 100) / 100.0
                    clearness_index = 1 - (clouds * 0.75)

                    # Determine if it's daytime
                    zenith = float(solar_position['apparent_zenith'].iloc[0])
                    is_day = zenith < 90

                    if is_day:
                        # Calculate clear sky radiation
                        clearsky = location.get_clearsky(timestamp)
                        if not clearsky.empty:
                            ghi = float(clearsky['ghi'].iloc[0]) * clearness_index

                            # Apply weather conditions
                            weather_condition = forecast.get('weather', [{}])[0].get('main', '').lower()
                            condition_factors = {
                                'clear': 1.0,
                                'clouds': 0.8,
                                'rain': 0.4,
                                'snow': 0.3,
                                'mist': 0.6,
                                'fog': 0.5
                            }
                            weather_factor = condition_factors.get(weather_condition, 0.7)
                            ghi *= weather_factor

                            # Calculate irradiance components
                            disc_output = pvlib.irradiance.disc(
                                ghi=ghi,
                                solar_zenith=zenith,
                                datetime_or_doy=timestamp
                            )

                            dni = disc_output['dni']
                            dhi = ghi - (dni * np.cos(np.radians(zenith)))

                            # Calculate total irradiance
                            total_irrad = pvlib.irradiance.get_total_irradiance(
                                surface_tilt=30,  # Assuming 30-degree tilt for panels
                                surface_azimuth=180,  # Assuming south-facing
                                dni=dni,
                                ghi=ghi,
                                dhi=dhi,
                                solar_zenith=zenith,
                                solar_azimuth=float(solar_position['azimuth'].iloc[0])
                            )

                            # Apply system efficiency and temperature derating
                            system_efficiency = 0.75  # Standard system efficiency
                            temperature_coefficient = -0.0040  # Temperature coefficient for power

                            # Temperature correction
                            ambient_temp = forecast.get('main', {}).get('temp', 25)
                            cell_temperature = ambient_temp + (total_irrad['poa_global'] / 800.0) * 30
                            temperature_factor = 1 + temperature_coefficient * (cell_temperature - 25)

                            # Calculate final power output
                            dc_power = (
                                total_irrad['poa_global'] * max_watt_peak / 1000.0  # Convert to kW
                                * system_efficiency * temperature_factor * weather_factor
                            )

                            production[timestamp] = max(0, dc_power)
                        else:
                            # Simplified calculation for missing clearsky data
                            daytime_factor = np.cos(np.radians(zenith)) if zenith < 90 else 0
                            production[timestamp] = max_watt_peak * 0.2 * clearness_index * daytime_factor / 1000.0
                    else:
                        production[timestamp] = 0.0

                except Exception as e:
                    logger.warning(f"Error processing forecast at {timestamp}: {str(e)}")
                    continue

            return production

        except Exception as e:
            logger.error(f"Error calculating solar production: {str(e)}")
            return {}

    def get_pv_forecast(self, max_watt_peak: float) -> Dict[datetime, float]:
        """Get PV production forecast with error handling"""
        try:
            if not isinstance(max_watt_peak, (int, float)) or max_watt_peak <= 0:
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
                    logger.warning(f"Weather data fetch attempt {retry + 1} failed: {str(e)}")
                    if retry < self._max_retries - 1:
                        time.sleep(self._exponential_backoff(retry))

            if not weather_data:
                return {}

            return self.calculate_solar_production(weather_data, max_watt_peak, lat, lon)

        except Exception as e:
            logger.error(f"Error in PV forecast: {str(e)}")
            return {}

    def get_weather_data(self, lat: float, lon: float) -> Dict:
        """Get weather data with improved caching and rate limiting"""
        cache_key = f"{lat},{lon}"
        current_time = datetime.now()

        if (self._last_cache_time and 
            cache_key in self._weather_cache and
            current_time - self._last_cache_time < self._cache_duration):
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

                if not isinstance(data, dict) or 'list' not in data:
                    raise ValueError("Invalid API response format")

                self._weather_cache[cache_key] = data
                self._last_cache_time = current_time

                return data

            except Exception as e:
                logger.warning(f"Weather API request failed (attempt {retry + 1}): {str(e)}")
                if retry < self._max_retries - 1:
                    time.sleep(self._exponential_backoff(retry))

        raise Exception("Failed to fetch weather data after all retries")
