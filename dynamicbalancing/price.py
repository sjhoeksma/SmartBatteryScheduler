"""
Energy price data management and forecasting
"""
from datetime import datetime, timedelta
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
        dates = pd.date_range(
            start=now,
            periods=forecast_hours,
            freq='H'
        )
        
        # Simple simulation for now
        prices = pd.Series(
            [0.10 + 0.05 * (i % 24 / 12) for i in range(len(dates))],
            index=dates
        )
        return prices
        
    def get_price_forecast_confidence(self, date: datetime) -> float:
        """Calculate confidence factor for price forecasts"""
        hours_ahead = (date - datetime.now()).total_seconds() / 3600
        return max(0.5, 1 - (hours_ahead / 48))
