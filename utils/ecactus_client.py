import os
from utils.ecactus_stub import EcactusClient
from typing import Dict, Optional
from datetime import datetime

class EcactusEnergyClient:
    def __init__(self):
        self.username = os.getenv('ECACTUS_USERNAME')
        self.password = os.getenv('ECACTUS_PASSWORD')
        if not self.username or not self.password:
            raise ValueError("ECACTUS_USERNAME and ECACTUS_PASSWORD environment variables not set")
        self.client = EcactusClient(
            username=self.username,
            password=self.password
        )
    
    def get_battery_status(self) -> Optional[Dict]:
        """Get real-time battery status"""
        try:
            status = self.client.get_battery_status()
            return {
                'current_soc': status.get('soc', 0.5),
                'current_power': status.get('power', 0.0),
                'temperature': status.get('temperature', 20.0),
                'voltage': status.get('voltage', 230.0),
                'last_updated': datetime.now()
            }
        except Exception as e:
            if 'authentication' in str(e).lower():
                print("Authentication error: Please check your credentials")
            else:
                print(f"Error fetching battery status: {e}")
            return None
    
    def get_power_consumption(self) -> Optional[Dict]:
        """Get real-time power consumption data"""
        try:
            consumption = self.client.get_power_consumption()
            return {
                'grid_power': consumption.get('grid_power', 0.0),
                'home_consumption': consumption.get('home_consumption', 0.0),
                'battery_power': consumption.get('battery_power', 0.0),
                'last_updated': datetime.now()
            }
        except Exception as e:
            if 'authentication' in str(e).lower():
                print("Authentication error: Please check your credentials")
            else:
                print(f"Error fetching power consumption: {e}")
            return None
    
    def update_battery_settings(self, settings: Dict) -> bool:
        """Update battery settings"""
        try:
            return self.client.update_battery_settings(settings)
        except Exception as e:
            if 'authentication' in str(e).lower():
                print("Authentication error: Please check your credentials")
            else:
                print(f"Error updating battery settings: {e}")
            return False

_client_instance = None
_last_username = None
_last_password = None

def get_ecactus_client() -> EcactusEnergyClient:
    """Get singleton instance of EcactusEnergyClient"""
    global _client_instance, _last_username, _last_password
    
    current_username = os.getenv('ECACTUS_USERNAME')
    current_password = os.getenv('ECACTUS_PASSWORD')
    
    # Reinitialize if credentials changed or instance doesn't exist
    if (_client_instance is None or 
        current_username != _last_username or 
        current_password != _last_password):
        _client_instance = EcactusEnergyClient()
        _last_username = current_username
        _last_password = current_password
    
    return _client_instance
