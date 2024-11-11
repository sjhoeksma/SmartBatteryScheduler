class Battery:
    def __init__(self, capacity, min_soc, max_soc, charge_rate, profile_name=None, daily_consumption=15.0, usage_pattern="Flat"):
        self.capacity = capacity
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.charge_rate = charge_rate
        self.current_soc = 0.5  # Start at 50%
        self.profile_name = profile_name
        self.daily_consumption = daily_consumption
        self.usage_pattern = usage_pattern
    
    def get_available_capacity(self):
        return self.capacity * (self.max_soc - self.current_soc)
    
    def get_current_energy(self):
        return self.capacity * self.current_soc
    
    def can_charge(self, amount):
        return (self.current_soc + (amount / self.capacity)) <= self.max_soc
    
    def can_discharge(self, amount):
        return (self.current_soc - (amount / self.capacity)) >= self.min_soc
    
    def charge(self, amount):
        if self.can_charge(amount):
            self.current_soc += amount / self.capacity
            return True
        return False
    
    def discharge(self, amount):
        if self.can_discharge(amount):
            self.current_soc -= amount / self.capacity
            return True
        return False

    def get_hourly_consumption(self, hour):
        """Calculate hourly consumption based on usage pattern"""
        daily = self.daily_consumption / 24.0  # Base hourly consumption
        
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
