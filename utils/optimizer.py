import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from pandas.core.series import missing
from utils.battery import Battery
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
def calculate_price_thresholds(_battery, _effective_prices, _date):
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
    window_size = min(_battery.look_ahead_hours, len(daily_prices))
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
    Optimize charging schedule based on prices, battery constraints, and PV production
    Returns charging power for each time period and predicted SOC values
    with immediate changes for charging/discharging
    
    Strategy:
    1. Calculate effective prices considering confidence weighting
    2. Use rolling window analysis for price thresholds
    3. Include PV production in optimization
    4. Compare future prices with less restrictive thresholds
    5. Maintain cycle and event limits while maximizing profitability
    6. Apply immediate SOC changes for charging/discharging events
    """
    periods = len(_prices)
    schedule = np.zeros(periods)
    predicted_soc = np.zeros(periods * 4)  # Removed the +1 to fix alignment
    consumption_stats = analyze_consumption_patterns(_battery, _prices.index)
    weather_service = st.session_state.weather_service

    # Get PV production forecast for optimization period
    pv_forecast = {}
    if _battery.max_watt_peak > 0:
        for date in _prices.index:
            try:
                pv_forecast[date] = weather_service.get_pv_forecast(
                    _battery.max_watt_peak, _battery.pv_efficiency, date=date)
            except Exception as e:
                print(f"Error getting PV forecast: {str(e)}")
                pv_forecast[date] = 0.0

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
            _battery, effective_prices, date)

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
        current_pv = pv_forecast.get(current_datetime, 0.0)

        # Initialize daily tracking if needed
        if current_date not in daily_events:
            daily_events[current_date] = {'cycles': 0.0}

        # Get daily thresholds
        thresholds = daily_thresholds[current_date]

        # Calculate remaining cycles for current day
        remaining_cycles = _battery.max_daily_cycles - daily_events[
            current_date]['cycles']

        # Initialize schedule value for this period
        schedule[i] = 0

        # Look ahead for better prices with extended window
        look_ahead_window = min(_battery.look_ahead_hours, periods - i)
        look_ahead_end = min(i + look_ahead_window, periods)
        future_prices = effective_prices.iloc[i + 1:look_ahead_end]
        future_max_price = future_prices.max() if len(future_prices) > 0 else 0
        future_min_price = future_prices.min() if len(
            future_prices) > 0 else future_max_price

        # Add strict peak detection with higher threshold
        is_peak = current_price >= future_prices.quantile(0.95) if len(
            future_prices) > 0 else True

        # How lower the soc how wider the quantile
        soc_quantile = 0.05 + (0.10 * (1 - (current_soc / 100)))
        is_valley = current_price <= future_prices.quantile(
            soc_quantile) if len(future_prices) > 0 else True

        # Optimize charging/discharging decision with bounds checking
        available_capacity = _battery.capacity * (_battery.max_soc -
                                                  current_soc)
        available_discharge = _battery.capacity * (current_soc -
                                                   _battery.min_soc)

        # Calculate home consumption for this hour
        current_hour_consumption = _battery.get_hourly_consumption(
            current_hour, current_datetime)

        # Include PV production in decision making
        net_consumption = max(0, current_hour_consumption - current_pv)
        excess_pv = max(0, current_pv - current_hour_consumption)

        # Prioritize storing excess PV production
        if excess_pv > 0 and available_capacity > 0:
            max_pv_charge = min(excess_pv, _battery.charge_rate,
                                available_capacity,
                                remaining_cycles * _battery.capacity)
            if max_pv_charge > 0:
                schedule[i] = max_pv_charge
                daily_events[current_date][
                    'cycles'] += max_pv_charge / _battery.capacity
                available_capacity -= max_pv_charge

        if remaining_cycles > 0:
            # Regular price-based optimization
            relative_charge_threshold = thresholds['rolling_mean'] * 0.98
            if (is_valley and current_soc <= _battery.max_soc * 0.95
                    and (current_price <= relative_charge_threshold or
                         (current_soc <= _battery.min_soc
                          and current_price <= future_prices.min() * 1.02))
                    and future_min_price != future_max_price
                    and available_capacity > 0):
                max_allowed_charge = min(
                    available_capacity,
                    _battery.charge_rate -
                    max(0, schedule[i]),  # Consider existing PV charging
                    remaining_cycles * _battery.capacity)

                if max_allowed_charge > 0:
                    schedule[i] += max_allowed_charge
                    daily_events[current_date][
                        'cycles'] += max_allowed_charge / _battery.capacity

            # Add peak price preservation check with more sensitive threshold or battery full
            elif not is_peak and future_prices.max() > current_price * 1.05:
                pass  # Skip discharge, better prices coming, but calculated SOC

            # Discharging decision with peak detection and relative threshold
            elif (is_peak and future_max_price != 0
                  and current_price >= future_max_price * 0.98
                  and available_discharge - net_consumption > 0):
                max_allowed_discharge = min(
                    _battery.charge_rate,
                    available_discharge - net_consumption,
                    remaining_cycles * _battery.capacity)

                if max_allowed_discharge > 0:
                    schedule[i] = -max_allowed_discharge
                    daily_events[current_date][
                        'cycles'] += max_allowed_discharge / _battery.capacity

        # Calculate SOC change for current hour with proper scaling
        try:
            # Calculate SOC impacts for this hour including PV and grid charging
            consumption_soc_impact = net_consumption / _battery.capacity  # Net consumption after PV
            charge_soc_impact = max(
                0, schedule[i]) / _battery.capacity  # Grid charging impact
            discharge_soc_impact = abs(min(
                0, schedule[i])) / _battery.capacity  # Grid discharging impact
            pv_charge_soc_impact = min(
                excess_pv, available_capacity
            ) / _battery.capacity  # Direct PV charging impact

            # Calculate net SOC change considering all factors
            net_soc_change = (charge_soc_impact + pv_charge_soc_impact -
                              discharge_soc_impact - consumption_soc_impact)

            # Check if the current soc drops below the minimum SOC
            if current_soc + net_soc_change <= _battery.empty_soc and i > 0:
                # Find last discharge event and adjust discharge event to keep SOC above minimum level
                missing_consumption_soc = (_battery.empty_soc -
                                           (current_soc + net_soc_change))
                missing_consumption_soc_impact = missing_consumption_soc * _battery.capacity
                for j in reversed(range(i)):
                    if schedule[j] < 0:
                        if abs(schedule[j]) >= missing_consumption_soc_impact:
                            schedule[j] += missing_consumption_soc_impact
                            #Adjust the predicted soc array
                            _missing_consumption_soc = missing_consumption_soc / (
                                i - j) * 4
                            for point_index in range((i - j) * 4):
                                predicted_soc[
                                    j * 4 +
                                    point_index] += _missing_consumption_soc
                            break
                        missing_consumption_soc_impact += schedule[j]
                        _missing_consumption_soc = abs(
                            schedule[j]) / _battery.capacity / (i - j) * 4
                        for point_index in range((i - j) * 4):
                            predicted_soc[
                                j * 4 +
                                point_index] += _missing_consumption_soc
                        schedule[j] = 0

            # Update SOC for each 15-minute interval with smoother transitions
            for j in range(4):
                point_index = i * 4 + j
                if point_index < len(predicted_soc):
                    # Progressive SOC change over 15-minute intervals
                    progress_factor = (j + 1) / 4
                    interval_soc = current_soc + (net_soc_change *
                                                  progress_factor)

                    # Apply battery constraints
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

    return schedule, predicted_soc, consumption_stats
