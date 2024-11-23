"""
Core battery management and state tracking functionality
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Union, Any

class Battery:
    """Battery energy storage system simulation and management"""
    
    def __init__(
        self,
        capacity: float,
        empty_soc: float,
        min_soc: float,
        max_soc: float,
        charge_rate: float,
        profile_name: Optional[str] = None,
        daily_consumption: float = 15.0,
        usage_pattern: str = "Flat",
        yearly_consumption: float = 5475.0,
        monthly_distribution: Optional[Dict[int, float]] = None,
        surcharge_rate: float = 0.050,
        max_daily_cycles: float = 1.5,
        max_watt_peak: float = 0.0,
        look_ahead_hours: int = 12,
        current_soc: float = 0.5,
        pv_efficiency: float = 0.15
    ):
        """Initialize battery with given parameters"""
        self.capacity = capacity
        self.empty_soc = empty_soc
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.charge_rate = charge_rate
        self.profile_name = profile_name
        self.daily_consumption = daily_consumption
        self.usage_pattern = usage_pattern
        self.yearly_consumption = yearly_consumption
        self.monthly_distribution = monthly_distribution or {
            1: 1.2, 2: 1.15, 3: 1.0, 4: 0.9, 5: 0.8,
            6: 0.7, 7: 0.7, 8: 0.7, 9: 0.8, 10: 0.9,
            11: 1.0, 12: 1.15
        }
        self.surcharge_rate = round(float(surcharge_rate), 3)
        self.max_daily_cycles = max_daily_cycles
        self.max_watt_peak = float(max_watt_peak)
        self.look_ahead_hours = look_ahead_hours
        self.pv_efficiency = pv_efficiency
        self.current_soc = current_soc
        self._current_power = 0.0
        self._daily_cycles = 0.0
        self._last_reset = datetime.now().date()

    def _reset_daily_counters_if_needed(self) -> None:
        """Reset daily counters if it's a new day"""
        current_date = datetime.now().date()
        if current_date > self._last_reset:
            self._daily_cycles = 0.0
            self._last_reset = current_date

    def get_available_capacity(self) -> float:
        """Get available capacity for charging"""
        return self.capacity * (self.max_soc - self.current_soc)

    def get_current_energy(self) -> float:
        """Get current stored energy"""
        return self.capacity * self.current_soc

    def can_charge(self, amount: float) -> bool:
        """Check if battery can be charged with given amount"""
        return (self.current_soc + (amount / self.capacity)) <= self.max_soc

    def can_discharge(self, amount: float) -> bool:
        """Check if battery can be discharged with given amount"""
        return (self.current_soc - (amount / self.capacity)) >= self.min_soc

    def get_seasonal_factor(self, month: int) -> float:
        """Get seasonal adjustment factor for given month"""
        return self.monthly_distribution.get(month, 1.0)

    def get_daily_consumption_for_date(self, date: Optional[datetime] = None) -> float:
        """Calculate daily consumption for specific date considering seasonal patterns"""
        if date is None:
            date = datetime.now()
        yearly_daily_avg = self.yearly_consumption / 365.0
        seasonal_factor = self.get_seasonal_factor(date.month)
        return yearly_daily_avg * seasonal_factor

    def get_hourly_consumption(self, hour: int, date: Optional[datetime] = None) -> float:
        """Calculate hourly consumption based on usage pattern"""
        if date is None:
            date = datetime.now()

        if hour > 24:
            date = date + timedelta(days=int(hour / 24))
            hour = hour % 24

        daily = self.get_daily_consumption_for_date(date) / 24.0
        is_weekend = date.weekday() >= 5

        if not is_weekend:
            if 7 <= hour <= 9:
                return daily * 2.0
            elif 17 <= hour <= 22:
                return daily * 2.5
            elif 0 <= hour <= 6:
                return daily * 0.3
            else:
                return daily * 0.8
        else:
            if 9 <= hour <= 12:
                return daily * 1.8
            elif 13 <= hour <= 22:
                return daily * 1.5
            else:
                return daily * 0.4

    def get_current_power(self) -> float:
        """Get current power flow (positive for charging, negative for discharging)"""
        hour = datetime.now().hour
        consumption = self.get_hourly_consumption(hour)
        
        if self.current_soc <= self.min_soc:
            return 0.0
        elif self.current_soc < 0.3:  # Low SOC condition
            return min(self.charge_rate, self.get_available_capacity())
        elif self.current_soc > 0.8:  # High SOC condition
            return -min(self.charge_rate, consumption)
        else:
            if 0 <= hour < 6:  # Night charging
                return min(self.charge_rate * 0.8, self.get_available_capacity())
            elif 10 <= hour < 16:  # Day discharge
                return -min(self.charge_rate * 0.6, consumption)
            else:  # Evening/morning
                return -min(self.charge_rate * 0.3, consumption)

    def get_effective_price(self, base_price: float, hour: int) -> float:
        """Calculate effective price including surcharge"""
        return round(base_price + self.surcharge_rate, 3)

    def get_consumption_confidence_intervals(self, date: Optional[datetime] = None) -> Dict[str, float]:
        """Calculate confidence intervals for consumption prediction"""
        if date is None:
            date = datetime.now()

        base_consumption = self.get_daily_consumption_for_date(date)
        std_dev = base_consumption * 0.15
        
        return {
            'mean': base_consumption,
            'lower_95': base_consumption - (1.96 * std_dev),
            'upper_95': base_consumption + (1.96 * std_dev)
        }
