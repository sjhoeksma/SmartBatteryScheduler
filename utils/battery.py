import numpy as np
from datetime import datetime

class Battery:
    def __init__(self, capacity, min_soc, max_soc, charge_rate, profile_name=None, 
                 daily_consumption=15.0, usage_pattern="Flat", yearly_consumption=5475.0,
                 monthly_distribution=None):
        self.capacity = capacity
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.charge_rate = charge_rate
        self.current_soc = 0.5  # Start at 50%
        self.profile_name = profile_name
        self.daily_consumption = daily_consumption
        self.usage_pattern = usage_pattern
        self.yearly_consumption = yearly_consumption
        self.monthly_distribution = monthly_distribution or {
            1: 1.2, 2: 1.15, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7,
            7: 0.7, 8: 0.7, 9: 0.8, 10: 0.9, 11: 1.0, 12: 1.15
        }
        self._current_power = 0.0  # Initialize current power flow
    
    def get_available_capacity(self):
        return self.capacity * (self.max_soc - self.current_soc)
    
    def get_current_energy(self):
        return self.capacity * self.current_soc

    def get_current_power(self):
        """Get current power flow (positive for charging, negative for discharging)"""
        hour = datetime.now().hour
        consumption = self.get_hourly_consumption(hour)
        
        # Simulate charging/discharging based on time of day and SOC
        if self.current_soc < 0.3:  # Low battery, prioritize charging
            return min(self.charge_rate, self.get_available_capacity())
        elif self.current_soc > 0.8:  # High battery, prioritize discharging
            return -min(self.charge_rate, consumption)
        else:  # Normal operation
            if 0 <= hour < 6:  # Night charging
                return min(self.charge_rate * 0.8, self.get_available_capacity())
            elif 10 <= hour < 16:  # Day discharging
                return -min(self.charge_rate * 0.6, consumption)
            else:  # Mixed operation
                return -min(self.charge_rate * 0.3, consumption)
    
    def can_charge(self, amount):
        return (self.current_soc + (amount / self.capacity)) <= self.max_soc
    
    def can_discharge(self, amount):
        return (self.current_soc - (amount / self.capacity)) >= self.min_soc
    
    def charge(self, amount):
        if self.can_charge(amount):
            self.current_soc += amount / self.capacity
            self._current_power = amount
            return True
        return False
    
    def discharge(self, amount):
        if self.can_discharge(amount):
            self.current_soc -= amount / self.capacity
            self._current_power = -amount
            return True
        return False

    def get_seasonal_factor(self, month):
        """Get seasonal adjustment factor for given month"""
        return self.monthly_distribution.get(month, 1.0)

    def get_daily_consumption_for_date(self, date=None):
        """Calculate daily consumption for specific date considering seasonal patterns"""
        if date is None:
            date = datetime.now()
        
        yearly_daily_avg = self.yearly_consumption / 365.0
        seasonal_factor = self.get_seasonal_factor(date.month)
        return yearly_daily_avg * seasonal_factor

    def get_hourly_consumption(self, hour, date=None):
        """Calculate hourly consumption based on usage pattern and seasonal factors"""
        if date is None:
            date = datetime.now()
            
        daily = self.get_daily_consumption_for_date(date) / 24.0  # Base hourly consumption
        
        # Apply hourly pattern adjustments
        if self.usage_pattern == "Flat":
            return daily
        elif self.usage_pattern == "Day-heavy":
            if 7 <= hour < 23:  # Daytime hours
                return daily * 1.5
            return daily * 0.5
        elif self.usage_pattern == "Night-heavy":
            if 7 <= hour < 23:  # Daytime hours
                return daily * 0.5
            return daily * 1.5
        return daily

    def get_consumption_confidence_intervals(self, date=None):
        """Calculate confidence intervals for consumption prediction"""
        if date is None:
            date = datetime.now()
            
        base_consumption = self.get_daily_consumption_for_date(date)
        
        # Calculate confidence intervals (assuming 15% variation)
        std_dev = base_consumption * 0.15
        return {
            'mean': base_consumption,
            'lower_95': base_consumption - (1.96 * std_dev),
            'upper_95': base_consumption + (1.96 * std_dev)
        }
