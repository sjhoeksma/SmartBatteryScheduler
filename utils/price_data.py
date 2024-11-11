import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_day_ahead_prices():
    """
    Get day-ahead energy prices for the Netherlands
    Returns hourly prices for the available hours
    
    The day-ahead prices are published daily around 13:00 CET for the next day
    """
    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    
    # Determine if tomorrow's prices are available
    if now >= publication_time:
        # After 13:00, we have tomorrow's prices
        start_date = current_hour
        end_date = (now + timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
    else:
        # Before 13:00, we only have today's remaining prices
        start_date = current_hour
        end_date = now.replace(hour=23, minute=0, second=0, microsecond=0)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Simulate realistic Dutch energy prices (€/kWh)
    base_price = 0.22
    peak_hours = [7, 8, 9, 17, 18, 19, 20]
    
    prices = []
    for date in dates:
        hour = date.hour
        if hour in peak_hours:
            price = base_price * (1 + np.random.uniform(0.3, 0.5))
        else:
            price = base_price * (1 + np.random.uniform(-0.3, 0.1))
        prices.append(price)
    
    return pd.Series(prices, index=dates)

def is_prices_available_for_tomorrow():
    """Check if tomorrow's prices are available"""
    now = datetime.now()
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    return now >= publication_time
