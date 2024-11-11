import json
from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class BatteryProfile:
    name: str
    capacity: float
    min_soc: float
    max_soc: float
    charge_rate: float
    daily_consumption: float = 15.0  # Default daily consumption in kWh
    usage_pattern: str = "Flat"  # Default usage pattern

class BatteryProfileManager:
    def __init__(self):
        self.profiles: Dict[str, BatteryProfile] = {}
        self._load_default_profiles()
    
    def _load_default_profiles(self):
        """Load default battery profiles"""
        defaults = {
            "Home Battery": BatteryProfile(
                name="Home Battery",
                capacity=13.5,
                min_soc=0.1,
                max_soc=0.9,
                charge_rate=5.0,
                daily_consumption=15.0,
                usage_pattern="Day-heavy"
            ),
            "EV Battery": BatteryProfile(
                name="EV Battery",
                capacity=75.0,
                min_soc=0.2,
                max_soc=0.8,
                charge_rate=11.0,
                daily_consumption=20.0,
                usage_pattern="Night-heavy"
            ),
            "Small Battery": BatteryProfile(
                name="Small Battery",
                capacity=5.0,
                min_soc=0.15,
                max_soc=0.85,
                charge_rate=3.3,
                daily_consumption=8.0,
                usage_pattern="Flat"
            )
        }
        self.profiles.update(defaults)
    
    def add_profile(self, profile: BatteryProfile) -> None:
        """Add or update a battery profile"""
        self.profiles[profile.name] = profile
    
    def get_profile(self, name: str) -> Optional[BatteryProfile]:
        """Get a battery profile by name"""
        return self.profiles.get(name)
    
    def list_profiles(self) -> list[str]:
        """List all available profile names"""
        return list(self.profiles.keys())
    
    def delete_profile(self, name: str) -> bool:
        """Delete a battery profile"""
        if name in self.profiles and name not in ["Home Battery", "EV Battery", "Small Battery"]:
            del self.profiles[name]
            return True
        return False
