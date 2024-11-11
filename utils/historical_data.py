import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_historical_prices(days=30):
    """Generate historical price data for analysis"""
    end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Base parameters for price generation
    base_price = 0.22
    yearly_factor = dates.dayofyear / 365.0
    hourly_factor = dates.hour / 24.0
    
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
    
    daily_avg = prices.resample('D').mean()
    hourly_avg = prices.groupby(prices.index.hour).mean()
    peak_hours = hourly_avg.nlargest(3).index.tolist()
    off_peak_hours = hourly_avg.nsmallest(3).index.tolist()
    
    return {
        'daily_avg': daily_avg,
        'hourly_avg': hourly_avg,
        'peak_hours': peak_hours,
        'off_peak_hours': off_peak_hours,
        'price_volatility': prices.std(),
        'avg_daily_swing': prices.resample('D').agg(lambda x: x.max() - x.min())
    }

def calculate_savings_opportunity(prices, battery):
    """Calculate potential savings based on historical prices"""
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)
    
    daily_swings = prices.resample('D').agg(lambda x: x.max() - x.min())
    max_daily_charge = battery.charge_rate * 1  # Assuming 1 hour of charging
    potential_savings = daily_swings * max_daily_charge
    return potential_savings.mean()
