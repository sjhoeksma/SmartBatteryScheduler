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
    with averaged transitions
    """
    periods = len(prices)
    schedule = np.zeros(periods)
    # Create array for intermediate points (4 points per hour)
    predicted_soc = np.zeros(periods * 4 + 1)
    consumption_stats = analyze_consumption_patterns(battery, prices.index)
    
    # Calculate price thresholds for decision making
    effective_prices = pd.Series([
        battery.get_effective_price(price, date.hour)
        for price, date in zip(prices.values, prices.index)
    ])
    median_price = np.median(effective_prices)
    price_std = np.std(effective_prices)
    charge_threshold = median_price - 0.5 * price_std
    discharge_threshold = median_price + 0.5 * price_std
    
    # Start with current battery SOC
    current_soc = battery.current_soc
    predicted_soc[0] = current_soc
    
    # Process each period
    for i in range(periods):
        current_price = effective_prices.iloc[i]
        current_datetime = prices.index[i]
        hour = current_datetime.hour if isinstance(current_datetime, pd.Timestamp) else datetime.now().hour
        
        # Calculate home consumption for this hour with seasonal adjustment
        home_consumption = battery.get_hourly_consumption(hour, current_datetime)
        
        # Calculate available capacity and energy at period start
        available_capacity = battery.capacity * (battery.max_soc - current_soc)
        available_energy = battery.capacity * (current_soc - battery.min_soc)
        
        # First, handle home consumption
        if available_energy >= home_consumption:
            # Can supply home consumption from battery
            schedule[i] = -home_consumption
            consumption_change = home_consumption / battery.capacity
        else:
            # Need to charge to meet home consumption
            needed_charge = home_consumption - available_energy
            if battery.can_charge(needed_charge):
                schedule[i] = needed_charge
                consumption_change = -needed_charge / battery.capacity
            else:
                consumption_change = 0

        # Then optimize based on prices
        if current_price <= charge_threshold and available_capacity > 0:
            # Charge during low price periods
            charge_amount = min(battery.charge_rate, available_capacity)
            schedule[i] += charge_amount
            charge_change = charge_amount / battery.capacity
        elif current_price >= discharge_threshold and available_energy > 0:
            # Discharge during high price periods
            discharge_amount = min(battery.charge_rate, available_energy)
            schedule[i] -= discharge_amount
            charge_change = -discharge_amount / battery.capacity
        else:
            charge_change = 0

        # Calculate total SOC change for this hour
        total_change = charge_change - consumption_change
        
        # Calculate intermediate points with averaged transitions
        for j in range(4):
            point_index = i * 4 + j + 1
            # Use exponential smoothing for transitions
            alpha = (j + 1) / 4  # Smoothing factor increases through the hour
            predicted_soc[point_index] = current_soc + (total_change * alpha)
        
        # Update current SOC for next hour
        current_soc += total_change
    
    return schedule, predicted_soc, consumption_stats
