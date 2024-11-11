import numpy as np
import pandas as pd

def optimize_schedule(prices, battery):
    """
    Optimize charging schedule based on prices and battery constraints
    Returns charging power for each time period (positive for charging, negative for discharging)
    """
    periods = len(prices)
    schedule = np.zeros(periods)
    
    # Find periods sorted by price
    price_periods = list(enumerate(prices))
    sorted_periods = sorted(price_periods, key=lambda x: x[1])
    
    # Identify cheap and expensive periods
    num_periods = len(sorted_periods)
    cheap_periods = sorted_periods[:num_periods//3]  # Cheapest third
    expensive_periods = sorted_periods[-num_periods//3:]  # Most expensive third
    
    current_soc = battery.current_soc
    
    # Charge during cheap periods
    for idx, price in cheap_periods:
        available_capacity = battery.capacity * (battery.max_soc - current_soc)
        if available_capacity > 0:
            charge_amount = min(battery.charge_rate, available_capacity)
            schedule[idx] = charge_amount
            current_soc += charge_amount / battery.capacity
    
    # Discharge during expensive periods
    for idx, price in expensive_periods:
        available_discharge = battery.capacity * (current_soc - battery.min_soc)
        if available_discharge > 0:
            discharge_amount = min(battery.charge_rate, available_discharge)
            schedule[idx] = -discharge_amount  # Negative value for discharging
            current_soc -= discharge_amount / battery.capacity
    
    return schedule
