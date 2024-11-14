import numpy as np
import pandas as pd
from datetime import datetime
from utils.price_data import get_price_forecast_confidence
import streamlit as st

@st.cache_data(ttl=300)  # Cache consumption patterns for 5 minutes
def analyze_consumption_patterns(_battery, dates):
    """Analyze consumption patterns and return statistical metrics"""
    consumptions = []
    for date in dates:
        daily_consumption = _battery.get_daily_consumption_for_date(date)
        consumptions.append({
            'date': date,
            'consumption': daily_consumption
        })
    return pd.DataFrame(consumptions)

@st.cache_data(ttl=300)  # Cache price thresholds for 5 minutes
def calculate_price_thresholds(effective_prices, date):
    """Calculate price thresholds for a specific date"""
    mask = effective_prices.index.date == date
    daily_prices = effective_prices[mask]
    return {
        'median': np.median(daily_prices),
        'std': np.std(daily_prices)
    }

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
    
    # Calculate effective prices with confidence weighting
    effective_prices = pd.Series([
        battery.get_effective_price(price, date.hour) * get_price_forecast_confidence(date)
        for price, date in zip(prices.values, prices.index)
    ])
    
    # Pre-calculate daily thresholds
    daily_thresholds = {}
    for date in set(prices.index.date):
        daily_thresholds[date] = calculate_price_thresholds(effective_prices, date)
    
    # Start with current battery SOC
    current_soc = battery.current_soc
    predicted_soc[0] = current_soc
    
    # Track charge/discharge events per day
    daily_events = {}
    
    # Process each period with vectorized operations where possible
    for i in range(periods):
        current_datetime = prices.index[i]
        current_date = current_datetime.date()
        hour = current_datetime.hour
        current_price = effective_prices.iloc[i]
        
        # Initialize daily tracking if needed
        if current_date not in daily_events:
            daily_events[current_date] = {
                'charge_events': 0,
                'discharge_events': 0,
                'cycles': 0.0
            }
        
        # Get daily price thresholds
        thresholds = daily_thresholds[current_date]
        charge_threshold = thresholds['median'] - 0.25 * thresholds['std']
        discharge_threshold = thresholds['median'] + 0.25 * thresholds['std']
        
        # Calculate home consumption for this hour
        home_consumption = battery.get_hourly_consumption(hour, current_datetime)
        
        # Calculate remaining cycles for current day
        remaining_cycles = battery.max_daily_cycles - daily_events[current_date]['cycles']
        
        # Optimize charging/discharging decision
        if current_soc <= battery.min_soc:
            if (current_price <= charge_threshold and 
                daily_events[current_date]['charge_events'] < battery.max_charge_events):
                max_charge = min(
                    battery.charge_rate,
                    battery.capacity * (battery.max_soc - current_soc),
                    remaining_cycles * battery.capacity
                )
                schedule[i] = max_charge
                daily_events[current_date]['charge_events'] += 1
                daily_events[current_date]['cycles'] += max_charge / battery.capacity
                consumption_impact = 0
            else:
                schedule[i] = 0
                consumption_impact = 0
        else:
            consumption_impact = min(
                home_consumption / battery.capacity,
                current_soc - battery.min_soc
            ) if current_soc > battery.min_soc else 0
        
        # Optimize based on prices if possible
        available_capacity = battery.capacity * (battery.max_soc - current_soc)
        
        if remaining_cycles > 0 and available_capacity > 0:
            if (current_price <= charge_threshold and 
                daily_events[current_date]['charge_events'] < battery.max_charge_events):
                max_allowed_charge = min(
                    battery.charge_rate,
                    available_capacity,
                    remaining_cycles * battery.capacity
                )
                if max_allowed_charge > 0:
                    schedule[i] += max_allowed_charge
                    daily_events[current_date]['charge_events'] += 1
                    daily_events[current_date]['cycles'] += max_allowed_charge / battery.capacity
            elif (current_price >= discharge_threshold and 
                  current_soc > battery.min_soc and 
                  daily_events[current_date]['discharge_events'] < battery.max_discharge_events):
                max_allowed_discharge = min(
                    battery.charge_rate,
                    battery.capacity * (current_soc - battery.min_soc),
                    remaining_cycles * battery.capacity
                )
                if max_allowed_discharge > 0:
                    schedule[i] -= max_allowed_discharge
                    daily_events[current_date]['discharge_events'] += 1
                    daily_events[current_date]['cycles'] += max_allowed_discharge / battery.capacity
        
        strategic_change = (schedule[i] / battery.capacity)
        total_change = strategic_change - consumption_impact
        
        # Ensure we never go below min_soc
        if current_soc + total_change < battery.min_soc:
            total_change = battery.min_soc - current_soc
            schedule[i] = (battery.min_soc - current_soc + consumption_impact) * battery.capacity
        
        # Calculate intermediate points with averaged transitions
        for j in range(4):
            point_index = i * 4 + j + 1
            alpha = (j + 1) / 4
            predicted_soc[point_index] = current_soc + (total_change * alpha)
        
        # Update current SOC for next hour
        current_soc += total_change
    
    return schedule, predicted_soc, consumption_stats
