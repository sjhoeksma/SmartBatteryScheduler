"""Stub implementation of ecactus-ecos-client for testing and development."""

class EcactusClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        
    def get_battery_status(self):
        """Stub implementation of battery status"""
        return {
            'soc': 0.65,  # 65% charge
            'power': 2.5,  # 2.5 kW charging
            'temperature': 25.0,  # 25°C
            'voltage': 230.0  # 230V
        }
    
    def get_power_consumption(self):
        """Stub implementation of power consumption"""
        return {
            'grid_power': 3.0,  # 3.0 kW from grid
            'home_consumption': 2.0,  # 2.0 kW home usage
            'battery_power': 1.0  # 1.0 kW battery charging
        }
    
    def update_battery_settings(self, settings):
        """Stub implementation of battery settings update"""
        return True  # Always succeed in stub mode
