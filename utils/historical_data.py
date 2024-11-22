import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_historical_prices(days=30):
    """Generate historical price data for analysis"""
    end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='h')

    # Base parameters for price generation
    base_price = 0.22
    yearly_factor = pd.Series(dates).dt.dayofyear / 365.0
    hourly_factor = pd.Series(dates).dt.hour / 24.0

    # Generate prices with seasonality and random variation
    yearly_seasonality = np.sin(2 * np.pi * yearly_factor) * 0.05
    daily_seasonality = np.sin(2 * np.pi * hourly_factor) * 0.1

    prices = base_price + yearly_seasonality + daily_seasonality
    prices += np.random.normal(0, 0.02, len(dates))

    return pd.Series(prices, index=dates)


def analyze_price_patterns(prices):
    """Analyze price patterns and return key statistics"""
    # Ensure prices is a pandas Series with datetime index
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)

    # Basic statistics
    daily_avg = prices.resample('D').mean()
    hourly_avg = prices.groupby(pd.Series(prices.index).dt.hour).mean()
    peak_hours = hourly_avg.nlargest(3).index.tolist()
    off_peak_hours = hourly_avg.nsmallest(3).index.tolist()

    # Weekly patterns
    weekly_avg = prices.groupby(pd.Series(prices.index).dt.dayofweek).mean()
    weekly_volatility = prices.groupby(pd.Series(
        prices.index).dt.dayofweek).std()

    # Price trend analysis
    rolling_mean = daily_avg.rolling(window=7).mean()
    trend_direction = "Increasing" if rolling_mean.iloc[
        -1] > rolling_mean.iloc[-7] else "Decreasing"

    # Volatility analysis
    daily_volatility = prices.resample('D').std()
    avg_daily_swing = prices.resample('D').agg(lambda x: x.max() - x.min())

    return {
        'daily_avg': daily_avg,
        'hourly_avg': hourly_avg,
        'peak_hours': peak_hours,
        'off_peak_hours': off_peak_hours,
        'weekly_avg': weekly_avg,
        'weekly_volatility': weekly_volatility,
        'price_volatility': daily_volatility,
        'avg_daily_swing': avg_daily_swing,
        'trend_direction': trend_direction,
        'rolling_mean': rolling_mean
    }


@st.cache_data(ttl=3600)
def analyze_historical_pv_production(_dates,
                                     _battery,
                                     _weather_service,
                                     _progress_bar=None):
    """Analyze historical PV production with serializable return values"""
    # Initialize data structures
    production_data = []
    total_entries = len(_dates)
    successful_entries = 0

    try:
        # Process all entries
        for date in _dates:
            try:
                production = _weather_service.get_pv_forecast(
                    _battery.max_watt_peak, _battery.pv_efficiency, date)
                if production is not None:
                    production_data.append({
                        'datetime': date,
                        'production': float(production),
                        'hour': int(date.hour),
                        'day': int(date.day),
                        'month': int(date.month),
                        'dayofweek': int(date.weekday())
                    })
                    successful_entries += 1

                    # Update progress
                    if _progress_bar is not None:
                        _progress_bar.progress(successful_entries /
                                               total_entries)
            except Exception as e:
                logger.warning(
                    f"Error processing PV data for {date}: {str(e)}")
                continue

        # Create DataFrame and calculate patterns
        df = pd.DataFrame(production_data)

        # Calculate all metrics at once
        daily_production = df.groupby(pd.to_datetime(
            df['datetime']).dt.date)['production'].sum()
        hourly_production = df.groupby('hour')['production'].mean()
        monthly_production = df.groupby('month')['production'].mean()

        # Get peak hours using proper sorting
        hour_means = df.groupby('hour')['production'].mean()
        peak_hours = hour_means.sort_values(
            ascending=False).head(5).index.tolist()

        # Calculate efficiency
        total_capacity = float(_battery.max_watt_peak * len(_dates) * 24)
        actual_production = float(df['production'].sum())
        efficiency_ratio = float((actual_production /
                                  total_capacity) if total_capacity > 0 else 0)

        # Convert Series to lists/dicts for better serialization
        result = {
            'daily_production':
            dict(
                zip(daily_production.index.astype(str),
                    daily_production.values.tolist())),
            'hourly_production':
            dict(
                zip(hourly_production.index.astype(str),
                    hourly_production.values.tolist())),
            'monthly_production':
            dict(
                zip(monthly_production.index.astype(str),
                    monthly_production.values.tolist())),
            'peak_hours': [int(h) for h in peak_hours],
            'total_production':
            actual_production,
            'efficiency_ratio':
            efficiency_ratio
        }

        return result

    except Exception as e:
        logger.error(f"Error in PV production analysis: {str(e)}")
        return None


def calculate_savings_opportunity(prices, battery):
    """Calculate potential savings based on historical prices"""
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)

    # Calculate daily potential savings
    daily_swings = prices.resample('D').agg(lambda x: x.max() - x.min())
    max_daily_charge = battery.charge_rate * 1  # Assuming 1 hour of charging
    potential_savings = daily_swings * max_daily_charge

    # Calculate weekly savings pattern
    weekly_savings = potential_savings.groupby(
        potential_savings.index.dayofweek).mean()

    # Calculate optimal charging windows
    price_percentiles = prices.quantile([0.25, 0.75])
    optimal_charge_mask = prices <= price_percentiles[0.25]
    optimal_discharge_mask = prices >= price_percentiles[0.75]

    return {
        'daily_savings': potential_savings.mean(),
        'weekly_pattern': weekly_savings,
        'optimal_charge_times': optimal_charge_mask,
        'optimal_discharge_times': optimal_discharge_mask,
        'price_thresholds': price_percentiles
    }
