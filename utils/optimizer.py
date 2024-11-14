import numpy as np
import pandas as pd
from datetime import datetime
from utils.price_data import get_price_forecast_confidence
import streamlit as st

@st.cache_data(ttl=300)  # Cache consumption patterns for 5 minutes
def analyze_consumption_patterns(_battery, _dates):
    """Analyze consumption patterns and return statistical metrics"""
    consumptions = []
    for date in _dates:
        daily_consumption = _battery.get_daily_consumption_for_date(date)
        consumptions.append({
            'date': date,
            'consumption': daily_consumption
        })
    return pd.DataFrame(consumptions)

@st.cache_data(ttl=300)  # Cache price thresholds for 5 minutes
def calculate_price_thresholds(_effective_prices, _date):
    """Calculate price thresholds for a specific date"""
    # Convert _date to datetime.date if it isn't already
    target_date = _date.date() if hasattr(_date, 'date') else _date
    # Use datetime index properly
    mask = pd.to_datetime(_effective_prices.index).date == target_date
    daily_prices = _effective_prices[mask]
    return {
        'median': np.median(daily_prices),
        'std': np.std(daily_prices)
    }

def optimize_schedule(_prices, _battery):
    """
    Optimize charging schedule based on prices and battery constraints
    Returns charging power for each time period and predicted SOC values
    with averaged transitions
    """
    periods = len(_prices)
    schedule = np.zeros(periods)
    predicted_soc = np.zeros(periods * 4 + 1)
    consumption_stats = analyze_consumption_patterns(_battery, _prices.index)
    
    # Calculate effective prices with confidence weighting and preserve datetime index
    effective_prices = pd.Series(
        [_battery.get_effective_price(price, date.hour) * get_price_forecast_confidence(date)
         for price, date in zip(_prices.values, _prices.index)],
        index=_prices.index  # Preserve the datetime index
    )
    
    # Pre-calculate daily thresholds
    daily_thresholds = {}
    for date in set(_prices.index.date):
        daily_thresholds[date] = calculate_price_thresholds(effective_prices, date)
    
    # Start with current battery SOC
    current_soc = _battery.current_soc
    predicted_soc[0] = current_soc
    
    # Track charge/discharge events per day
    daily_events = {}
    
    # Process each period with vectorized operations where possible
    for i in range(periods):
        current_datetime = _prices.index[i]
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
        home_consumption = _battery.get_hourly_consumption(hour, current_datetime)
        
        # Calculate remaining cycles for current day
        remaining_cycles = _battery.max_daily_cycles - daily_events[current_date]['cycles']
        
        # Initialize schedule value for this period
        schedule[i] = 0
        
        # Calculate consumption impact
        consumption_impact = min(
            home_consumption / _battery.capacity,
            current_soc - _battery.min_soc
        ) if current_soc > _battery.min_soc else 0
        
        # Optimize charging/discharging decision with bounds checking
        available_capacity = _battery.capacity * (_battery.max_soc - current_soc)
        available_discharge = _battery.capacity * (current_soc - _battery.min_soc)
        
        if remaining_cycles > 0:
            if (current_price <= charge_threshold and 
                daily_events[current_date]['charge_events'] < _battery.max_charge_events and
                available_capacity > 0):
                max_allowed_charge = min(
                    _battery.charge_rate,
                    available_capacity,
                    remaining_cycles * _battery.capacity
                )
                if max_allowed_charge > 0:
                    schedule[i] = max_allowed_charge
                    daily_events[current_date]['charge_events'] += 1
                    daily_events[current_date]['cycles'] += max_allowed_charge / _battery.capacity
            elif (current_price >= discharge_threshold and 
                  daily_events[current_date]['discharge_events'] < _battery.max_discharge_events and
                  available_discharge > 0):
                max_allowed_discharge = min(
                    _battery.charge_rate,
                    available_discharge,
                    remaining_cycles * _battery.capacity
                )
                if max_allowed_discharge > 0:
                    schedule[i] = -max_allowed_discharge
                    daily_events[current_date]['discharge_events'] += 1
                    daily_events[current_date]['cycles'] += max_allowed_discharge / _battery.capacity
        
        # Calculate SOC change with bounds checking
        strategic_change = schedule[i] / _battery.capacity
        total_change = strategic_change - consumption_impact
        
        # Validate SOC bounds
        next_soc = current_soc + total_change
        if next_soc < _battery.min_soc:
            # Adjust change to maintain minimum SOC
            total_change = _battery.min_soc - current_soc
            schedule[i] = (total_change + consumption_impact) * _battery.capacity
        elif next_soc > _battery.max_soc:
            # Adjust change to maintain maximum SOC
            total_change = _battery.max_soc - current_soc
            schedule[i] = (total_change + consumption_impact) * _battery.capacity
        
        # Calculate intermediate points with averaged transitions
        for j in range(4):
            point_index = i * 4 + j + 1
            alpha = (j + 1) / 4
            predicted_soc[point_index] = current_soc + (total_change * alpha)
            # Ensure intermediate points are within bounds
            predicted_soc[point_index] = np.clip(
                predicted_soc[point_index],
                _battery.min_soc,
                _battery.max_soc
            )
        
        # Update current SOC for next hour
        current_soc += total_change
        
        # Ensure final SOC is within bounds
        current_soc = np.clip(current_soc, _battery.min_soc, _battery.max_soc)
    
    return schedule, predicted_soc, consumption_stats
