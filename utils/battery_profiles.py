import json
from dataclasses import dataclass, asdict
from typing import Dict, Optional
import numpy as np

@dataclass
class BatteryProfile:
    name: str
    capacity: float
    min_soc: float
    max_soc: float
    charge_rate: float
    daily_consumption: float = 15.0  # Default daily consumption in kWh
    usage_pattern: str = "Flat"  # Default usage pattern
    yearly_consumption: float = 5475.0  # Default yearly consumption (15 kWh * 365)
    monthly_distribution: Dict[int, float] = None  # Monthly consumption distribution factors
    surcharge_rate: float = 0.05  # Default surcharge rate in €/kWh
    surcharge_hours: Dict[int, bool] = None  # Hours when surcharge applies
    
    def __post_init__(self):
        if self.monthly_distribution is None:
            # Initialize with default seasonal distribution
            self.monthly_distribution = {
                1: 1.2,  # Winter
                2: 1.15,
                3: 1.0,
                4: 0.9,
                5: 0.8,
                6: 0.7,  # Summer
                7: 0.7,
                8: 0.7,
                9: 0.8,
                10: 0.9,
                11: 1.0,
                12: 1.15  # Winter
            }
        if self.surcharge_hours is None:
            # Initialize with default surcharge hours (peak hours)
            self.surcharge_hours = {
                hour: hour in [7, 8, 9, 17, 18, 19, 20]
                for hour in range(24)
            }

    def get_seasonal_factor(self, month: int) -> float:
        """Get seasonal adjustment factor for given month"""
        return self.monthly_distribution.get(month, 1.0)

    def get_daily_consumption_for_month(self, month: int) -> float:
        """Calculate daily consumption for specific month considering seasonal patterns"""
        yearly_daily_avg = self.yearly_consumption / 365.0
        seasonal_factor = self.get_seasonal_factor(month)
        return yearly_daily_avg * seasonal_factor

    def is_surcharge_hour(self, hour: int) -> bool:
        """Check if surcharge applies for given hour"""
        return self.surcharge_hours.get(hour, False)

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
                usage_pattern="Day-heavy",
                yearly_consumption=5475.0,
                surcharge_rate=0.05
            ),
            "EV Battery": BatteryProfile(
                name="EV Battery",
                capacity=75.0,
                min_soc=0.2,
                max_soc=0.8,
                charge_rate=11.0,
                daily_consumption=20.0,
                usage_pattern="Night-heavy",
                yearly_consumption=7300.0,
                surcharge_rate=0.08
            ),
            "Small Battery": BatteryProfile(
                name="Small Battery",
                capacity=5.0,
                min_soc=0.15,
                max_soc=0.85,
                charge_rate=3.3,
                daily_consumption=8.0,
                usage_pattern="Flat",
                yearly_consumption=2920.0,
                surcharge_rate=0.05
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
