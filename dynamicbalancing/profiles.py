"""
Battery configuration profiles management
"""
from dataclasses import dataclass
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
    daily_consumption: float
    usage_pattern: str
    yearly_consumption: float
    monthly_distribution: Dict[int, float]
    surcharge_rate: float
    max_daily_cycles: float
    max_watt_peak: float = 0.0
    look_ahead_hours: int = 12
    current_soc: float = 0.5
    pv_efficiency: float = 0.15

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
            'max_watt_peak': self.max_watt_peak,
            'look_ahead_hours': self.look_ahead_hours,
            'current_soc': self.current_soc,
            'pv_efficiency': self.pv_efficiency
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BatteryProfile':
        """Create profile from dictionary"""
        return cls(**data)
