import numpy as np
import pandas as pd

def optimize_schedule(prices, battery):
    """
    Optimize charging schedule based on prices and battery constraints
    Returns charging power for each time period
    """
    periods = len(prices)
    schedule = np.zeros(periods)
    
    # Find lowest price periods
    price_periods = list(enumerate(prices))
    price_periods.sort(key=lambda x: x[1])
    
    remaining_capacity = battery.get_available_capacity()
    
    for idx, price in price_periods:
        if remaining_capacity <= 0:
            break
            
        # Calculate maximum charge for this period
        max_charge = min(
            battery.charge_rate,
            remaining_capacity
        )
        
        schedule[idx] = max_charge
        remaining_capacity -= max_charge
    
    return schedule
