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
    
    # Track charge/discharge events
    charge_events = 0
    discharge_events = 0
    daily_cycles = 0.0
    last_date = None
    
    # Process each period
    for i in range(periods):
        current_price = effective_prices.iloc[i]
        current_datetime = prices.index[i]
        hour = current_datetime.hour if isinstance(current_datetime, pd.Timestamp) else datetime.now().hour
        
        # Reset counters on new day
        if last_date is None or current_datetime.date() > last_date:
            charge_events = 0
            discharge_events = 0
            daily_cycles = 0.0
        last_date = current_datetime.date()
        
        # Calculate home consumption for this hour with seasonal adjustment
        home_consumption = battery.get_hourly_consumption(hour, current_datetime)
        
        # Handle home consumption with proper min_soc check
        if current_soc - (home_consumption / battery.capacity) >= battery.min_soc:
            # Can safely supply home consumption from battery
            schedule[i] = -home_consumption
            consumption_change = home_consumption / battery.capacity
        else:
            # Can only discharge until min_soc, need to get rest from grid
            available_discharge = (current_soc - battery.min_soc) * battery.capacity
            if available_discharge > 0:
                schedule[i] = -available_discharge
                consumption_change = available_discharge / battery.capacity
            else:
                schedule[i] = 0
                consumption_change = 0
        
        # Track cycles from consumption
        daily_cycles += abs(consumption_change)
        
        # Calculate available capacity for charging
        available_capacity = battery.capacity * (battery.max_soc - current_soc)
        
        # Then optimize based on prices if we haven't exceeded event limits
        remaining_cycles = battery.max_daily_cycles - daily_cycles
        if remaining_cycles > 0:
            if current_price <= charge_threshold and available_capacity > 0 and charge_events < battery.max_charge_events:
                # Charge during low price periods
                max_allowed_charge = min(
                    battery.charge_rate,
                    available_capacity,
                    remaining_cycles * battery.capacity
                )
                if max_allowed_charge > 0:
                    schedule[i] += max_allowed_charge
                    charge_events += 1
                    daily_cycles += max_allowed_charge / battery.capacity
                    
            elif current_price >= discharge_threshold and current_soc > battery.min_soc and discharge_events < battery.max_discharge_events:
                # Discharge during high price periods with min_soc constraint
                max_allowed_discharge = min(
                    battery.charge_rate,
                    battery.capacity * (current_soc - battery.min_soc),
                    remaining_cycles * battery.capacity
                )
                if max_allowed_discharge > 0:
                    schedule[i] -= max_allowed_discharge
                    discharge_events += 1
                    daily_cycles += max_allowed_discharge / battery.capacity
        
        # Calculate total SOC change for this hour with min_soc protection
        consumption_impact = min(
            home_consumption / battery.capacity,
            current_soc - battery.min_soc  # Limit consumption to available capacity above min_soc
        )
        strategic_change = (schedule[i] / battery.capacity)
        total_change = strategic_change - consumption_impact

        # Ensure we never go below min_soc
        if current_soc + total_change < battery.min_soc:
            total_change = battery.min_soc - current_soc
        
        # Calculate intermediate points with averaged transitions
        for j in range(4):
            point_index = i * 4 + j + 1
            alpha = (j + 1) / 4
            predicted_soc[point_index] = current_soc + (total_change * alpha)
        
        # Update current SOC for next hour
        current_soc += total_change
    
    return schedule, predicted_soc, consumption_stats
