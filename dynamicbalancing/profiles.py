"""
Battery configuration profiles management
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class BatteryProfile:
    """Battery configuration profile"""
    name: str
    capacity: float
    empty_soc: float
    min_soc: float
    max_soc: float
    charge_rate: float
    daily_consumption: float = 15.0  # Default daily consumption in kWh
    usage_pattern: str = "Flat"  # Default usage pattern
    yearly_consumption: float = 5475.0  # Default yearly consumption
    monthly_distribution: Dict[int, float] = field(default_factory=lambda: {
        1: 1.2,   # Winter
        2: 1.15,
        3: 1.0,
        4: 0.9,
        5: 0.5,
        6: 0.4,   # Summer
        7: 0.5,
        8: 0.7,
        9: 0.8,
        10: 0.9,
        11: 1.0,
        12: 1.15  # Winter
    })
    surcharge_rate: float = 0.05  # Default surcharge rate in €/kWh
    max_daily_cycles: float = 1.5  # Default maximum daily cycles
    max_charge_events: int = 2  # Default max charging events per day
    max_discharge_events: int = 1  # Default max discharging events per day
    max_watt_peak: float = 0.0  # Default PV installation size in Wp
    look_ahead_hours: int = 12
    current_soc: float = 0.6
    pv_efficiency: float = 0.15

    def get_seasonal_factor(self, month: int) -> float:
        """Get seasonal adjustment factor for given month"""
        return self.monthly_distribution.get(month, 1.0)

    def get_daily_consumption_for_month(self, month: int) -> float:
        """Calculate daily consumption for specific month considering seasonal patterns"""
        yearly_daily_avg = self.yearly_consumption / 365.0
        seasonal_factor = self.get_seasonal_factor(month)
        return yearly_daily_avg * seasonal_factor

    def to_dict(self) -> Dict:
        """Convert profile to dictionary"""
        return {
            'name': self.name,
            'capacity': self.capacity,
            'empty_soc': self.empty_soc,
            'min_soc': self.min_soc,
            'max_soc': self.max_soc,
            'charge_rate': self.charge_rate,
            'daily_consumption': self.daily_consumption,
            'usage_pattern': self.usage_pattern,
            'yearly_consumption': self.yearly_consumption,
            'monthly_distribution': self.monthly_distribution,
            'surcharge_rate': self.surcharge_rate,
            'max_daily_cycles': self.max_daily_cycles,
            'max_charge_events': self.max_charge_events,
            'max_discharge_events': self.max_discharge_events,
            'max_watt_peak': self.max_watt_peak,
            'look_ahead_hours': self.look_ahead_hours,
            'current_soc': self.current_soc,
            'pv_efficiency': self.pv_efficiency
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BatteryProfile':
        """Create profile from dictionary"""
        return cls(**data)
