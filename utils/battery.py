import numpy as np
from datetime import datetime, timedelta
from utils.ecactus_client import get_ecactus_client


class Battery:

    def __init__(self,
                 capacity,
                 empty_soc,
                 min_soc,
                 max_soc,
                 charge_rate,
                 profile_name=None,
                 daily_consumption=15.0,
                 usage_pattern="Flat",
                 yearly_consumption=5475.0,
                 monthly_distribution=None,
                 surcharge_rate=0.050,
                 max_daily_cycles=1.5,
                 max_charge_events=2,
                 max_discharge_events=1,
                 max_watt_peak=0.0):
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
            1: 1.2,
            2: 1.15,
            3: 1.0,
            4: 0.9,
            5: 0.8,
            6: 0.7,
            7: 0.7,
            8: 0.7,
            9: 0.8,
            10: 0.9,
            11: 1.0,
            12: 1.15
        }
        self.surcharge_rate = round(float(surcharge_rate), 3)
        self.max_daily_cycles = max_daily_cycles
        self.max_charge_events = max_charge_events
        self.max_discharge_events = max_discharge_events
        self.max_watt_peak = max_watt_peak
        self._current_power = 0.0
        self._daily_cycles = 0.0
        self._charge_events = 0
        self._discharge_events = 0
        self._last_reset = datetime.now().date()
        try:
            self.ecactus_client = get_ecactus_client()
            self.current_soc = self.ecactus_client.get_current_soc()
        except ValueError:
            self.ecactus_client = None
            self.current_soc = 0.6

    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if it's a new day"""
        current_date = datetime.now().date()
        if current_date > self._last_reset:
            self._daily_cycles = 0.0
            self._charge_events = 0
            self._discharge_events = 0
            self._last_reset = current_date

    def _can_add_charge_event(self):
        """Check if another charge event can be added"""
        self._reset_daily_counters_if_needed()
        return self._charge_events < self.max_charge_events

    def _can_add_discharge_event(self):
        """Check if another discharge event can be added"""
        self._reset_daily_counters_if_needed()
        return self._discharge_events < self.max_discharge_events

    def _update_cycles_and_events(self, energy_amount):
        """Update cycles and events counters"""
        self._reset_daily_counters_if_needed()
        cycle_fraction = abs(energy_amount) / self.capacity
        self._daily_cycles += cycle_fraction

        if energy_amount > 0:
            self._charge_events += 1
        elif energy_amount < 0:
            self._discharge_events += 1

    def can_complete_operation(self, energy_amount):
        """Check if the operation would exceed any limits"""
        self._reset_daily_counters_if_needed()
        new_cycles = self._daily_cycles + (abs(energy_amount) / self.capacity)

        if energy_amount > 0:
            return new_cycles <= self.max_daily_cycles and self._can_add_charge_event(
            )
        elif energy_amount < 0:
            return new_cycles <= self.max_daily_cycles and self._can_add_discharge_event(
            )
        return True

    def get_remaining_events(self):
        """Get remaining available events for the day"""
        self._reset_daily_counters_if_needed()
        return {
            'charge_events': self.max_charge_events - self._charge_events,
            'discharge_events':
            self.max_discharge_events - self._discharge_events,
            'cycles': self.max_daily_cycles - self._daily_cycles
        }

    def charge(self, amount):
        if self.can_charge(amount) and self.can_complete_operation(amount):
            if self.ecactus_client:
                success = self.ecactus_client.update_battery_settings({
                    'charge_power':
                    amount,
                    'mode':
                    'charge'
                })
                if success:
                    self._update_cycles_and_events(amount)
                    self._update_from_api()
                    return True
            else:
                self.current_soc += amount / self.capacity
                self._current_power = amount
                self._update_cycles_and_events(amount)
                return True
        return False

    def discharge(self, amount):
        if self.can_discharge(amount) and self.can_complete_operation(-amount):
            if self.ecactus_client:
                success = self.ecactus_client.update_battery_settings({
                    'discharge_power':
                    amount,
                    'mode':
                    'discharge'
                })
                if success:
                    self._update_cycles_and_events(-amount)
                    self._update_from_api()
                    return True
            else:
                self.current_soc -= amount / self.capacity
                self._current_power = -amount
                self._update_cycles_and_events(-amount)
                return True
        return False

    def _update_from_api(self):
        """Update battery status from Ecactus API"""
        if self.ecactus_client:
            status = self.ecactus_client.get_battery_status()
            if status:
                self.current_soc = status['current_soc']
                self._current_power = status['current_power']

    def get_available_capacity(self):
        self._update_from_api()
        return self.capacity * (self.max_soc - self.current_soc)

    def get_current_energy(self):
        self._update_from_api()
        return self.capacity * self.current_soc

    def get_current_power(self):
        """Get current power flow (positive for charging, negative for discharging)"""
        if self.ecactus_client:
            status = self.ecactus_client.get_battery_status()
            if status:
                return status['current_power']

        # Fallback to simulated behavior
        hour = datetime.now().hour
        consumption = self.get_hourly_consumption(hour)

        # Return 0 power when at minimum SOC
        if self.current_soc <= self.min_soc:
            return 0.0
        elif self.current_soc < 0.3:  # Low SOC condition
            return min(self.charge_rate, self.get_available_capacity())
        elif self.current_soc > 0.8:
            return -min(self.charge_rate, consumption)
        else:
            if 0 <= hour < 6:
                return min(self.charge_rate * 0.8,
                         self.get_available_capacity())
            elif 10 <= hour < 16:
                return -min(self.charge_rate * 0.6, consumption)
            else:
                return -min(self.charge_rate * 0.3, consumption)

    def can_charge(self, amount):
        self._update_from_api()
        return (self.current_soc + (amount / self.capacity)) <= self.max_soc

    def can_discharge(self, amount):
        self._update_from_api()
        return (self.current_soc - (amount / self.capacity)) >= self.min_soc

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
        """Calculate hourly consumption based on usage pattern"""
        if date is None:
            date = datetime.now()

        if hour > 24:
            date = date + timedelta(days=int(hour / 24))
            hour = hour % 24

        daily = self.get_daily_consumption_for_date(date) / 24.0  # Base hourly
        is_weekend = date.weekday() >= 5

        # Weekday patterns
        if not is_weekend:
            # Morning peak (7-9 AM)
            if 7 <= hour <= 9:
                return daily * 2.0
            # Evening peak (17-22)
            elif 17 <= hour <= 22:
                return daily * 2.5
            # Night/work hours
            elif 0 <= hour <= 6:
                return daily * 0.3
            else:
                return daily * 0.8

        # Weekend patterns
        else:
            # Late morning peak (9-12)
            if 9 <= hour <= 12:
                return daily * 1.8
            # Afternoon/evening (13-22)
            elif 13 <= hour <= 22:
                return daily * 1.5
            # Night hours
            else:
                return daily * 0.4

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

    def get_effective_price(self, base_price: float, hour: int) -> float:
        """Calculate effective price including surcharge"""
        return round(base_price + self.surcharge_rate, 3)
