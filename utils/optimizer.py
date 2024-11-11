import numpy as np
import pandas as pd
from datetime import datetime

def analyze_consumption_patterns(battery, dates):
    """Analyze consumption patterns and return statistical metrics"""
    consumptions = []
    for date in dates:
        daily_consumption = battery.get_daily_consumption_for_date(date)
        consumptions.append({
            'date': date,
            'consumption': daily_consumption
        })
    return pd.DataFrame(consumptions)

def optimize_schedule(prices, battery):
    """
    Optimize charging schedule based on prices and battery constraints
    Returns charging power for each time period and predicted SOC values
    """
    periods = len(prices)
    schedule = np.zeros(periods)
    predicted_soc = np.zeros(periods)
    consumption_stats = analyze_consumption_patterns(battery, prices.index)
    
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
        current_date = prices.index[i] if isinstance(prices, pd.Series) else datetime.now()
        hour = current_date.hour
        
        # Calculate home consumption for this hour with seasonal adjustment
        home_consumption = battery.get_hourly_consumption(hour, current_date)
        
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
    
    return schedule, predicted_soc, consumption_stats
