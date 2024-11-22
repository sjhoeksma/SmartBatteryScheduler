import json
from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class BatteryProfile:
    name: str
    capacity: float
    empty_soc: float
    min_soc: float
    max_soc: float
    charge_rate: float
    daily_consumption: float = 15.0  # Default daily consumption in kWh
    usage_pattern: str = "Flat"  # Default usage pattern
    yearly_consumption: float = 5475.0  # Default yearly consumption (15 kWh * 365)
    monthly_distribution: Dict[
        int, float] = None  # Monthly consumption distribution factors
    surcharge_rate: float = 0.05  # Default surcharge rate in €/kWh
    max_daily_cycles: float = 1.5  # Default maximum daily cycles
    max_charge_events: int = 2  # Default max charging events per day
    max_discharge_events: int = 1  # Default max discharging events per day
    max_watt_peak: float = 0.0  # Default PV installation size in Wp
    look_ahead_hours: int = 12
    current_soc: float = 0.6
    pv_efficiency: float = 0.15

    def __post_init__(self):
        if self.monthly_distribution is None:
            # Initialize with default seasonal distribution
            self.monthly_distribution = {
                1: 1.2,  # Winter
                2: 1.15,
                3: 1.0,
                4: 0.9,
                5: 0.5,
                6: 0.4,  # Summer
                7: 0.5,
                8: 0.7,
                9: 0.8,
                10: 0.9,
                11: 1.0,
                12: 1.15  # Winter
            }

    def get_seasonal_factor(self, month: int) -> float:
        """Get seasonal adjustment factor for given month"""
        return self.monthly_distribution.get(month, 1.0)

    def get_daily_consumption_for_month(self, month: int) -> float:
        """Calculate daily consumption for specific month considering seasonal patterns"""
        yearly_daily_avg = self.yearly_consumption / 365.0
        seasonal_factor = self.get_seasonal_factor(month)
        return yearly_daily_avg * seasonal_factor


class BatteryProfileManager:

    def __init__(self):
        self.profiles: Dict[str, BatteryProfile] = {}
        self._load_default_profiles()

    def _load_default_profiles(self):
        """Load default battery profiles"""
        defaults = {
            "Home Battery":
            BatteryProfile(name="Home Battery",
                           capacity=20,
                           empty_soc=0.1,
                           min_soc=0.2,
                           max_soc=0.9,
                           charge_rate=12.0,
                           daily_consumption=9.0,
                           usage_pattern="Day-heavy",
                           yearly_consumption=3475.0,
                           surcharge_rate=0.030,
                           max_daily_cycles=1.5,
                           max_watt_peak=5000.0,
                           look_ahead_hours=12,
                           current_soc=0.6,
                           pv_efficiency=0.15),  # 5kWp default PV installation
            "EV Battery":
            BatteryProfile(name="EV Battery",
                           capacity=75.0,
                           empty_soc=0.1,
                           min_soc=0.2,
                           max_soc=0.8,
                           charge_rate=11.0,
                           daily_consumption=20.0,
                           usage_pattern="Night-heavy",
                           yearly_consumption=7300.0,
                           surcharge_rate=0.03,
                           max_daily_cycles=2.0,
                           max_watt_peak=3000.0,
                           look_ahead_hours=12,
                           current_soc=0.6,
                           pv_efficiency=0.15),  # 3kWp default PV installation
            "Small Battery":
            BatteryProfile(name="Small Battery",
                           capacity=5.0,
                           empty_soc=0.1,
                           min_soc=0.15,
                           max_soc=0.85,
                           charge_rate=3.3,
                           daily_consumption=8.0,
                           usage_pattern="Flat",
                           yearly_consumption=2920.0,
                           surcharge_rate=0.03,
                           max_daily_cycles=2.0,
                           max_watt_peak=2000.0,
                           look_ahead_hours=12,
                           current_soc=0.6,
                           pv_efficiency=0.15)  # 2kWp default PV installation
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
        if name in self.profiles and name not in [
                "Home Battery", "EV Battery", "Small Battery"
        ]:
            del self.profiles[name]
            return True
        return False
