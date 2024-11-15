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
    """
    Calculate dynamic price thresholds using rolling window comparison
    
    Args:
        _effective_prices: Series of prices with confidence weighting
        _date: Target date for threshold calculation
        
    Returns:
        Dictionary containing charge and discharge thresholds based on rolling analysis
    """
    # Convert _date to datetime.date if it isn't already
    target_date = _date.date() if hasattr(_date, 'date') else _date
    
    # Use datetime index properly
    mask = pd.to_datetime(_effective_prices.index).date == target_date
    daily_prices = _effective_prices[mask]
    
    # Calculate rolling statistics with adaptive window for extended timelines
    window_size = min(24, len(daily_prices))
    rolling_mean = daily_prices.rolling(window=window_size, min_periods=1, center=True).mean()
    rolling_std = daily_prices.rolling(window=window_size, min_periods=1, center=True).std()
    
    # Calculate dynamic thresholds
    charge_threshold = rolling_mean - 0.3 * rolling_std
    discharge_threshold = rolling_mean + 0.3 * rolling_std
    
    return {
        'charge': charge_threshold.mean(),
        'discharge': discharge_threshold.mean(),
        'rolling_mean': rolling_mean.mean()
    }

def optimize_schedule(_prices, _battery):
    """
    Optimize charging schedule based on prices and battery constraints
    Returns charging power for each time period and predicted SOC values
    with immediate changes for charging/discharging
    
    Strategy:
    1. Calculate effective prices considering confidence weighting
    2. Use rolling window analysis for price thresholds
    3. Compare future prices with less restrictive thresholds
    4. Maintain cycle and event limits while maximizing profitability
    5. Apply immediate SOC changes for charging/discharging events
    """
    periods = len(_prices)
    schedule = np.zeros(periods)
    predicted_soc = np.zeros(periods * 4)  # Removed the +1 to fix alignment
    consumption_stats = analyze_consumption_patterns(_battery, _prices.index)
    
    # Calculate effective prices with reduced confidence weighting impact
    effective_prices = pd.Series(
        [_battery.get_effective_price(price, date.hour) * (0.9 + 0.1 * get_price_forecast_confidence(date))
         for price, date in zip(_prices.values, _prices.index)],
        index=_prices.index
    )
    
    # Pre-calculate daily thresholds with extended timeline support
    daily_thresholds = {}
    for date in set(_prices.index.date):
        daily_thresholds[date] = calculate_price_thresholds(effective_prices, date)
    
    # Start with current battery SOC
    current_soc = _battery.current_soc
    predicted_soc[0] = current_soc
    
    # Track charge/discharge events per day
    daily_events = {}
    
    # Process each period with look-ahead price comparison
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
        
        # Get daily thresholds
        thresholds = daily_thresholds[current_date]
        
        # Calculate home consumption for this hour
        home_consumption = _battery.get_hourly_consumption(hour, current_datetime)
        
        # Calculate remaining cycles for current day
        remaining_cycles = _battery.max_daily_cycles - daily_events[current_date]['cycles']
        
        # Initialize schedule value for this period
        schedule[i] = 0
        
        # Look ahead for better prices with adaptive window for extended timelines
        look_ahead_window = min(8, periods - i - 1)  # Increased look-ahead window
        look_ahead_end = min(i + look_ahead_window, periods)
        future_prices = effective_prices.iloc[i+1:look_ahead_end]
        future_max_price = future_prices.mean() + 0.2 * future_prices.std() if len(future_prices) > 0 else 0
        
        # Calculate consumption impact
        consumption_impact = min(
            home_consumption / _battery.capacity,
            current_soc - _battery.min_soc
        ) if current_soc > _battery.min_soc else 0
        
        # Optimize charging/discharging decision with bounds checking
        available_capacity = _battery.capacity * (_battery.max_soc - current_soc)
        available_discharge = _battery.capacity * (current_soc - _battery.min_soc)
        
        if remaining_cycles > 0:
            # Charging decision with relative threshold
            relative_charge_threshold = thresholds['rolling_mean'] * 1.05
            if (current_price <= relative_charge_threshold and 
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
            
            # Discharging decision with relative threshold and future price comparison
            elif (current_price >= thresholds['rolling_mean'] * 0.95 and
                  current_price > future_max_price * 0.9 and
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
        
        # Calculate SOC change immediately when charging/discharging occurs
        strategic_change = schedule[i] / _battery.capacity
        total_change = strategic_change - consumption_impact

        # Update intermediate points for the current hour
        for j in range(4):
            point_index = i * 4 + j
            if schedule[i] != 0:
                # For charging/discharging, apply changes immediately at the start
                if j == 0:
                    # Immediate full change at start of period
                    predicted_soc[point_index] = current_soc + total_change
                else:
                    # Maintain the changed level for rest of period
                    predicted_soc[point_index] = predicted_soc[point_index - 1]
            else:
                # For consumption-only periods, keep gradual change
                alpha = (j + 1) / 4
                predicted_soc[point_index] = current_soc + (total_change * alpha)
            
            # Ensure SOC stays within battery limits
            predicted_soc[point_index] = np.clip(
                predicted_soc[point_index],
                _battery.min_soc,
                _battery.max_soc
            )
        
        # Update current SOC for next hour
        current_soc += total_change
        
        # Ensure SOC stays within limits
        current_soc = np.clip(current_soc, _battery.min_soc, _battery.max_soc)
    
    return schedule, predicted_soc, consumption_stats
