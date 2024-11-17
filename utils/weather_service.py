import os
import requests
import json
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, Optional, Tuple
import pvlib
from pvlib.location import Location
import pytz


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

    def get_location_from_ip(self) -> Tuple[float, float]:
        """Get location coordinates using IP geolocation"""
        if self._location_cache:
            return self._location_cache

        try:
            response = requests.get('https://ipapi.co/json/')
            data = response.json()
            self._location_cache = (float(data['latitude']), float(data['longitude']))
            return self._location_cache
        except Exception as e:
            # Default to Amsterdam coordinates if location detection fails
            default_location = (52.3676, 4.9041)
            self._location_cache = default_location
            return default_location

    def get_weather_data(self, lat: float, lon: float) -> Dict:
        """Get weather data from OpenWeatherMap API"""
        cache_key = f"{lat},{lon}"
        current_time = datetime.now()

        # Check cache
        if (self._last_cache_time and
            cache_key in self._weather_cache and
            current_time - self._last_cache_time < self._cache_duration):
            return self._weather_cache[cache_key]

        # Fetch new data
        try:
            response = requests.get(
                f"{self.base_url}/forecast",
                params={
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric'
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            self._weather_cache[cache_key] = data
            self._last_cache_time = current_time
            
            return data
        except Exception as e:
            raise Exception(f"Error fetching weather data: {str(e)}")

    def calculate_solar_production(self, 
                                 weather_data: Dict, 
                                 max_watt_peak: float,
                                 lat: float,
                                 lon: float) -> Dict[datetime, float]:
        """Calculate expected solar production based on weather data"""
        try:
            # Create location object
            location = Location(latitude=lat, longitude=lon)
            
            # Initialize results dictionary
            production = {}
            
            # Get timezone for the location
            timezone = pytz.timezone(self._get_timezone(lat, lon))
            
            for forecast in weather_data['list']:
                timestamp = datetime.fromtimestamp(forecast['dt'])
                timestamp = timezone.localize(timestamp)
                
                # Get solar position
                solar_position = location.get_solarposition(timestamp)
                
                # Get cloud cover and convert to clearness index
                clouds = forecast['clouds']['all'] / 100.0
                clearness_index = 1 - (clouds * 0.75)  # Simple conversion
                
                # Calculate irradiance
                dni = pvlib.irradiance.disc(
                    ghi=forecast['main']['temp'],  # Using temp as a simple approximation
                    solar_zenith=solar_position['apparent_zenith'],
                    datetime_or_doy=timestamp
                )['dni']
                
                # Calculate total irradiance on tilted surface (assuming 30° tilt)
                total_irrad = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=30,
                    surface_azimuth=180,  # Assuming south-facing
                    dni=dni,
                    ghi=forecast['main']['temp'],  # Simple approximation
                    dhi=dni * 0.2,  # Simple approximation
                    solar_zenith=solar_position['apparent_zenith'],
                    solar_azimuth=solar_position['azimuth']
                )
                
                # Calculate power output
                dc_power = (total_irrad['poa_global'] * max_watt_peak / 1000.0  # Convert to kW
                          * clearness_index  # Account for cloud cover
                          * 0.75)  # System efficiency factor
                
                # Store hourly production
                production[timestamp] = max(0, dc_power)  # Ensure non-negative
            
            return production
        except Exception as e:
            print(f"Error calculating solar production: {str(e)}")
            return {}

    def _get_timezone(self, lat: float, lon: float) -> str:
        """Get timezone string for given coordinates"""
        try:
            response = requests.get(
                f"http://api.timezonedb.com/v2.1/get-time-zone",
                params={
                    'key': os.getenv('TIMEZONEDB_API_KEY', 'dummy'),
                    'format': 'json',
                    'by': 'position',
                    'lat': lat,
                    'lng': lon
                }
            )
            data = response.json()
            return data.get('zoneName', 'Europe/Amsterdam')  # Default to Amsterdam
        except Exception:
            return 'Europe/Amsterdam'  # Default timezone

    def get_pv_forecast(self, max_watt_peak: float) -> Dict[datetime, float]:
        """Get PV production forecast for the next 36 hours"""
        try:
            # Get location
            lat, lon = self.get_location_from_ip()
            
            # Get weather data
            weather_data = self.get_weather_data(lat, lon)
            
            # Calculate production
            production = self.calculate_solar_production(
                weather_data, max_watt_peak, lat, lon)
            
            return production
        except Exception as e:
            print(f"Error getting PV forecast: {str(e)}")
            return {}
