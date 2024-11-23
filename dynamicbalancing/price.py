"""
Energy price data management and forecasting
"""
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Optional

class PriceService:
    """Energy price data service"""
    
    def __init__(self):
        """Initialize price service"""
        self._cache = {}
        
    def get_day_ahead_prices(
        self,
        forecast_hours: Optional[int] = None
    ) -> pd.Series:
        """
        Get day-ahead energy prices
        
        Args:
            forecast_hours: Number of hours to forecast
            
        Returns:
            Time series of energy prices
        """
        if forecast_hours is None:
            forecast_hours = 24
            
        now = datetime.now()
        dates = pd.date_range(start=now, periods=forecast_hours, freq='h')
        
        # Create realistic daily price pattern
        base_price = 0.10  # Base price €0.10/kWh
        prices = []
        
        for date in dates:
            hour = date.hour
            # Early morning valley
            if 0 <= hour < 6:
                price = base_price * (0.7 + 0.1 * np.sin(hour))
            # Morning peak
            elif 6 <= hour < 10:
                price = base_price * (1.3 + 0.2 * np.sin(hour))
            # Midday moderate
            elif 10 <= hour < 16:
                price = base_price * (1.1 + 0.1 * np.sin(hour))
            # Evening peak
            elif 16 <= hour < 22:
                price = base_price * (1.4 + 0.2 * np.sin(hour))
            # Late evening decline
            else:
                price = base_price * (0.9 + 0.1 * np.sin(hour))
                
            # Add some random variation
            price *= (1 + 0.1 * np.random.randn())
            prices.append(max(0.05, price))  # Ensure minimum price
            
        return pd.Series(prices, index=dates)
        
    def get_price_forecast_confidence(self, date: datetime) -> float:
        """Calculate confidence factor for price forecasts"""
        hours_ahead = (date - datetime.now()).total_seconds() / 3600
        return max(0.5, 1 - (hours_ahead / 48))
