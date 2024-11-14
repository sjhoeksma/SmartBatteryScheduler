import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_day_ahead_prices(forecast_days=7):
    """
    Get day-ahead energy prices for the Netherlands with extended forecast
    Returns hourly block prices for the available hours
    
    The day-ahead prices are published daily around 13:00 CET for the next day
    For days beyond tomorrow, prices are forecasted based on historical patterns
    
    Args:
        forecast_days (int): Number of days to forecast prices for (default: 7)
    """
    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    
    # Determine if tomorrow's prices are available
    if now >= publication_time:
        # After 13:00, we have tomorrow's prices
        start_date = current_hour
        end_date = (now + timedelta(days=forecast_days)).replace(hour=23, minute=0, second=0, microsecond=0)
    else:
        # Before 13:00, we only have today's remaining prices plus forecast
        start_date = current_hour
        end_date = (now + timedelta(days=forecast_days-1)).replace(hour=23, minute=0, second=0, microsecond=0)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Simulate realistic Dutch energy prices (€/kWh)
    base_price = 0.22
    peak_hours = [7, 8, 9, 17, 18, 19, 20]
    shoulder_hours = [10, 11, 12, 13, 14, 15, 16]
    
    prices = []
    for date in dates:
        hour = date.hour
        days_ahead = (date.date() - now.date()).days
        
        # Add increasing uncertainty for future days
        uncertainty_factor = min(0.2 * (days_ahead / forecast_days), 0.2)
        
        # Add weekly pattern
        weekly_factor = 1.0 + (0.05 if date.weekday() < 5 else -0.05)
        
        if hour in peak_hours:
            # Peak hours have higher prices
            price = base_price * weekly_factor * (1 + np.random.uniform(0.3, 0.5))
        elif hour in shoulder_hours:
            # Shoulder hours have moderate prices
            price = base_price * weekly_factor * (1 + np.random.uniform(0.1, 0.3))
        else:
            # Off-peak hours have lower prices
            price = base_price * weekly_factor * (1 + np.random.uniform(-0.3, 0.0))
        
        # Add uncertainty based on forecast distance
        price *= (1 + np.random.uniform(-uncertainty_factor, uncertainty_factor))
        prices.append(price)
    
    return pd.Series(prices, index=dates)

def is_prices_available_for_tomorrow():
    """Check if tomorrow's prices are available"""
    now = datetime.now()
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    return now >= publication_time

def get_price_forecast_confidence(date):
    """
    Get confidence level for price forecasts based on how far in the future they are
    Returns a value between 0 and 1, where 1 is highest confidence
    """
    now = datetime.now()
    days_ahead = (date.date() - now.date()).days
    
    if days_ahead <= 1 and is_prices_available_for_tomorrow():
        return 1.0  # Actual day-ahead prices
    else:
        # Confidence decreases with forecast distance
        return max(0.2, 1.0 - (days_ahead * 0.15))  # Minimum 20% confidence
