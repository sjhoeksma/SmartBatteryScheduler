import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from utils.price_data import get_price_forecast_confidence
import streamlit as st


@st.cache_data(ttl=300)  # Cache consumption patterns for 5 minutes
def analyze_consumption_patterns(_battery, _dates):
    """Analyze consumption patterns and return statistical metrics"""
    consumptions = []
    for date in _dates:
        daily_consumption = _battery.get_daily_consumption_for_date(date)
        consumptions.append({'date': date, 'consumption': daily_consumption})
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
    window_size = min(36, len(daily_prices))
    rolling_mean = daily_prices.rolling(window=window_size,
                                        min_periods=1,
                                        center=True).mean()
    rolling_std = daily_prices.rolling(window=window_size,
                                       min_periods=1,
                                       center=True).std()

    # Calculate dynamic thresholds with updated factors for better statistical significance
    charge_threshold = rolling_mean - 0.7 * rolling_std  # Changed from 0.5 to 0.7
    discharge_threshold = rolling_mean + 0.7 * rolling_std  # Changed from 0.5 to 0.7

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
    effective_prices = pd.Series([
        _battery.get_effective_price(price, date.hour) *
        (0.9 + 0.1 * get_price_forecast_confidence(date))
        for price, date in zip(_prices.values, _prices.index)
    ],
                                 index=_prices.index)

    # Pre-calculate daily thresholds with extended timeline support
    daily_thresholds = {}
    for date in set(_prices.index.date):
        daily_thresholds[date] = calculate_price_thresholds(
            effective_prices, date)

    # Start with current battery SOC
    current_soc = _battery.current_soc
    predicted_soc[0] = current_soc

    # Track charge/discharge events per day
    daily_events = {}

    # Process each period with look-ahead price comparison
    for i in range(periods):
        current_datetime = _prices.index[i]
        current_date = current_datetime.date()
        current_hour = current_datetime.hour
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

        # Calculate remaining cycles for current day
        remaining_cycles = _battery.max_daily_cycles - daily_events[
            current_date]['cycles']

        # Initialize schedule value for this period
        schedule[i] = 0

        # Look ahead for better prices with extended window
        look_ahead_window = min(36, periods - i - 1)
        look_ahead_end = min(i + look_ahead_window, periods)
        future_prices = effective_prices.iloc[i + 1:look_ahead_end]
        future_max_price = future_prices.max() if len(future_prices) > 0 else 0

        # Add strict peak detection with higher threshold
        is_peak = current_price >= future_prices.quantile(0.95) if len(
            future_prices) > 0 else True  

        is_valley = current_price <=future_prices.quantile(0.10) if len(
             future_prices) > 0 else True  
      
        # Optimize charging/discharging decision with bounds checking
        available_capacity = _battery.capacity * (_battery.max_soc -
                                                  current_soc)
        available_discharge = _battery.capacity * (current_soc -
                                                   _battery.min_soc)

        # Calculate home consumption for this hour
        current_hour_consumption = _battery.get_hourly_consumption(
            current_hour, current_datetime)

        if remaining_cycles > 0:
            # Charging decision with relative threshold
           # relative_charge_threshold = thresholds['rolling_mean'] * 0.98
            if (is_valley #and current_price <= relative_charge_threshold
                    and daily_events[current_date]['charge_events']
                    < _battery.max_charge_events and available_capacity > 0):
                max_allowed_charge = min(
                    available_capacity,  # Remove hardcoded value
                    _battery.charge_rate,  # Use battery's actual charge rate
                    remaining_cycles * _battery.capacity)
                if max_allowed_charge > 0:
                    schedule[i] = max_allowed_charge
                    daily_events[current_date]['charge_events'] += 1
                    daily_events[current_date][
                        'cycles'] += max_allowed_charge / _battery.capacity

            # Add peak price preservation check with more sensitive threshold
            elif not is_peak and future_prices.max(
            ) > current_price * 1.05:  # Changed from 1.1 to 1.05
                pass  # Skip discharge, better prices coming, but calcuated SOC

            # Discharging decision with peak detection and relative threshold
            elif (is_peak and future_max_price!=0 and current_price >= future_max_price * 0.98
                  and  # Changed from 0.95 to 0.98
                  daily_events[current_date]['discharge_events']
                  < _battery.max_discharge_events and
                  available_discharge - current_hour_consumption > 0):
                max_allowed_discharge = min(
                    _battery.charge_rate,
                    available_discharge - current_hour_consumption,
                    remaining_cycles * _battery.capacity)
                if max_allowed_discharge > 0:
                    schedule[i] = -max_allowed_discharge
                    daily_events[current_date]['discharge_events'] += 1
                    daily_events[current_date][
                        'cycles'] += max_allowed_discharge / _battery.capacity

        # Calculate SOC change for current hour with proper scaling
        try:

            # Calculate SOC impacts for this hour
            consumption_soc_impact = current_hour_consumption / _battery.capacity  # Hourly consumption impact
            soc_impact = (schedule[i] / _battery.capacity)  # soc impact

            # Calculate net SOC change for this hour
            net_soc_change = soc_impact - consumption_soc_impact

            # Update SOC for each 15-minute interval in this hour
            for j in range(4):
                point_index = i * 4 + j
                if point_index < len(predicted_soc):
                    # Apply proportional change for each 15-minute period
                    interval_soc = current_soc + (net_soc_change * (j + 1) / 4)

                    # Ensure SOC stays within battery limits
                    predicted_soc[point_index] = np.clip(
                        interval_soc, _battery.empty_soc, _battery.max_soc)

            # Update current SOC for next hour
            current_soc = current_soc + net_soc_change
            current_soc = np.clip(current_soc, _battery.empty_soc,
                                  _battery.max_soc)

        except (IndexError, KeyError, ValueError) as e:
            # If there's an error, maintain current SOC
            print(f"Error in SOC calculation: {str(e)}")
            for j in range(4):
                point_index = i * 4 + j
                if point_index < len(predicted_soc):
                    predicted_soc[point_index] = current_soc

        # Ensure SOC stays within limits
        current_soc = np.clip(current_soc, _battery.empty_soc,
                              _battery.max_soc)
    #print("Consumption for {} {} {}".format(schedule,predicted_soc,
    #                                        consumption_stats))

    return schedule, predicted_soc, consumption_stats
