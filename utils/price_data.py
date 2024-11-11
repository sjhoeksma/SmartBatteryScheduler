import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_day_ahead_prices():
    """
    Simulate day-ahead energy prices for the Netherlands
    Returns hourly prices for the next 24 hours
    """
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    dates = pd.date_range(start=now, periods=24, freq='h')
    
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
