class Battery:
    def __init__(self, capacity, min_soc, max_soc, charge_rate):
        self.capacity = capacity
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.charge_rate = charge_rate
        self.current_soc = 0.5  # Start at 50%
    
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