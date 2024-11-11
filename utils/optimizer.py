import numpy as np
import pandas as pd

def optimize_schedule(prices, battery):
    """
    Optimize charging schedule based on prices and battery constraints
    Returns charging power for each time period and predicted SOC values
    """
    periods = len(prices)
    schedule = np.zeros(periods)
    predicted_soc = np.zeros(periods)
    
    # Calculate price thresholds for decision making
    median_price = np.median(prices)
    price_std = np.std(prices)
    charge_threshold = median_price - 0.5 * price_std
    discharge_threshold = median_price + 0.5 * price_std
    
    # Track battery state through schedule
    current_soc = battery.current_soc
    predicted_soc[0] = current_soc
    
    # Process periods sequentially
    for i in range(periods):
        current_price = prices.values[i] if isinstance(prices, pd.Series) else prices[i]
        hour = prices.index[i].hour if isinstance(prices, pd.Series) else i % 24
        
        # Calculate home consumption for this hour
        home_consumption = battery.get_hourly_consumption(hour)
        
        # Calculate available capacity and energy
        available_capacity = battery.capacity * (battery.max_soc - current_soc)
        available_energy = battery.capacity * (current_soc - battery.min_soc)
        
        # First, handle home consumption
        if available_energy >= home_consumption:
            # Can supply home consumption from battery
            schedule[i] = -home_consumption
            current_soc -= home_consumption / battery.capacity
        else:
            # Need to charge to meet home consumption
            needed_charge = home_consumption - available_energy
            if battery.can_charge(needed_charge):
                schedule[i] = needed_charge
                current_soc += needed_charge / battery.capacity
        
        # Then optimize based on prices
        if current_price <= charge_threshold and available_capacity > 0:
            # Charge during low price periods
            charge_amount = min(battery.charge_rate, available_capacity)
            schedule[i] += charge_amount
            current_soc += charge_amount / battery.capacity
            
        elif current_price >= discharge_threshold and available_energy > 0:
            # Discharge during high price periods
            discharge_amount = min(battery.charge_rate, available_energy)
            schedule[i] -= discharge_amount
            current_soc -= discharge_amount / battery.capacity
            
        # Store predicted SOC for this period
        if i < periods - 1:
            predicted_soc[i + 1] = current_soc
    
    return schedule, predicted_soc
