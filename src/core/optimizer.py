"""
Battery charging schedule optimization and energy management
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List, Any, Union
from datetime import datetime

from .battery import Battery
from .optimize_result import OptimizeResult

class Optimizer:
    """Battery charge/discharge schedule optimizer"""
    
    def __init__(self, battery: Battery):
        """Initialize optimizer with battery instance"""
        self.battery = battery

    def optimize_schedule(
        self,
        prices: pd.Series,
        pv_forecast: Optional[Dict[Union[datetime, pd.Timestamp], float]] = None
    ) -> OptimizeResult:
        """
        Optimize charging schedule based on prices, battery constraints, and PV production
        
        Args:
            prices: Time series of energy prices
            pv_forecast: Optional dictionary of PV production forecast by datetime
            
        Returns:
            OptimizeResult containing optimization results including:
            - Optimized charging schedule
            - Predicted state of charge
            - Consumption statistics
            - Cost and consumption metrics
        """
        periods = len(prices)
        schedule = np.zeros(periods)
        predicted_soc = np.zeros(periods * 4)
        consumption_stats = self._analyze_consumption_patterns(list(prices.index))
        
        consumption = 0
        consumption_cost = 0.0
        optimize_consumption = 0
        optimize_cost = 0.0

        # Calculate effective prices with confidence weighting
        def calculate_effective_price(price: float, date: Any) -> float:
            try:
                # Handle different date input types
                if isinstance(date, (str, int, float)):
                    date_ts = pd.to_datetime(date)
                else:
                    date_ts = pd.Timestamp(date)
                
                if isinstance(date_ts, pd.Timestamp):
                    if pd.isna(date_ts):
                        return float(price)
                    confidence = self._get_price_forecast_confidence(date_ts.to_pydatetime())
                    effective_price = self.battery.get_effective_price(float(price), date_ts.hour)
                    return float(effective_price) * (0.9 + 0.1 * confidence)
                return float(price)
            except Exception as e:
                print(f"Error calculating effective price: {str(e)}")
                return float(price)
            
        effective_prices = pd.Series([
            calculate_effective_price(price, date)
            for price, date in zip(prices.values, prices.index)
        ], index=prices.index)

        # Calculate daily thresholds
        # Calculate daily thresholds with proper date handling
        unique_dates = set(pd.to_datetime(prices.index).map(lambda x: x.date()))
        daily_thresholds = {
            date: self._calculate_price_thresholds(effective_prices, date)
            for date in unique_dates
        }

        current_soc = self.battery.current_soc
        predicted_soc[0] = current_soc
        daily_events = {}

        # Process each period
        for i in range(periods):
            try:
                current_datetime = prices.index[i]
                if isinstance(current_datetime, (str, int, float)):
                    current_datetime = pd.to_datetime(current_datetime)
                
                if not isinstance(current_datetime, pd.Timestamp):
                    raise ValueError(f"Invalid datetime type: {type(current_datetime)}")
                    
                if pd.isna(current_datetime):
                    continue
                    
                current_date = current_datetime.date()
                current_hour = current_datetime.hour
            except Exception as e:
                print(f"Error processing datetime at index {i}: {str(e)}")
                continue
            current_price = effective_prices.iloc[i]
            # Convert to Python datetime for PV forecast lookup
            current_pv_time = current_datetime.to_pydatetime()
            current_pv = pv_forecast.get(current_pv_time, 0.0) if pv_forecast else 0.0

            if current_date not in daily_events:
                daily_events[current_date] = {'cycles': 0.0}

            thresholds = daily_thresholds[current_date]
            remaining_cycles = self.battery.max_daily_cycles - daily_events[current_date]['cycles']

            schedule[i] = self._optimize_period(
                current_soc, current_price, current_pv,
                effective_prices.iloc[i:i+self.battery.look_ahead_hours],
                remaining_cycles, thresholds
            )

            # Update statistics and state
            consumption_datetime = current_datetime.to_pydatetime() if isinstance(current_datetime, pd.Timestamp) else current_datetime
            current_hour_consumption = self.battery.get_hourly_consumption(
                current_hour,
                consumption_datetime
            )
            net_consumption = max(0, current_hour_consumption - current_pv)
            consumption += net_consumption
            consumption_cost += prices.iloc[i] * net_consumption

            current_soc = self._update_soc(
                current_soc, schedule[i], net_consumption, current_pv,
                predicted_soc, i
            )

        # Calculate optimization results
        for i in range(periods):
            optimize_consumption += schedule[i]
            optimize_cost += prices.iloc[i] * schedule[i]

        return OptimizeResult(
            schedule=schedule,
            predicted_soc=predicted_soc,
            consumption_stats=consumption_stats,
            consumption=consumption,
            consumption_cost=consumption_cost,
            optimize_consumption=optimize_consumption,
            optimize_cost=optimize_cost
        )

    def _analyze_consumption_patterns(self, dates: List[datetime]) -> pd.DataFrame:
        """Analyze consumption patterns and return statistical metrics"""
        consumptions = []
        for date in dates:
            daily_consumption = self.battery.get_daily_consumption_for_date(date)
            consumptions.append({'date': date, 'consumption': daily_consumption})
        return pd.DataFrame(consumptions)

    def _get_price_forecast_confidence(self, date: datetime) -> float:
        """Calculate confidence factor for price forecasts"""
        # Simple confidence calculation - can be extended
        hours_ahead = (date - datetime.now()).total_seconds() / 3600
        return max(0.5, 1 - (hours_ahead / 48))

    def _calculate_price_thresholds(
        self,
        effective_prices: pd.Series,
        date: datetime
    ) -> Dict[str, float]:
        """Calculate dynamic price thresholds using rolling window comparison"""
        target_date = pd.Timestamp(date).date()
        mask = pd.to_datetime(effective_prices.index).map(lambda x: x.date()) == target_date
        daily_prices = effective_prices[mask]

        window_size = min(self.battery.look_ahead_hours, len(daily_prices))
        daily_prices_series = pd.Series(daily_prices)
        rolling_mean = daily_prices_series.rolling(window=window_size, min_periods=1, center=True).mean()
        rolling_std = daily_prices_series.rolling(window=window_size, min_periods=1, center=True).std()

        charge_threshold = rolling_mean - 0.7 * rolling_std
        discharge_threshold = rolling_mean + 0.7 * rolling_std

        return {
            'charge': charge_threshold.mean(),
            'discharge': discharge_threshold.mean(),
            'rolling_mean': float(rolling_mean.mean())
        }

    def _optimize_period(
        self,
        current_soc: float,
        current_price: float,
        current_pv: float,
        future_prices: pd.Series,
        remaining_cycles: float,
        thresholds: Dict[str, float]
    ) -> float:
        """Optimize single period charging decision"""
        if remaining_cycles <= 0:
            return 0.0

        available_capacity = self.battery.capacity * (self.battery.max_soc - current_soc)
        available_discharge = self.battery.capacity * (current_soc - self.battery.min_soc)

        # Handle PV charging first
        if current_pv > 0 and available_capacity > 0:
            return min(current_pv, self.battery.charge_rate, available_capacity)

        # Price-based optimization
        future_max = future_prices.max() if len(future_prices) > 0 else current_price
        future_min = future_prices.min() if len(future_prices) > 0 else current_price

        if current_price <= thresholds['charge'] and available_capacity > 0:
            return min(self.battery.charge_rate, available_capacity, remaining_cycles * self.battery.capacity)
        elif current_price >= thresholds['discharge'] and available_discharge > 0:
            return -min(self.battery.charge_rate, available_discharge, remaining_cycles * self.battery.capacity)

        return 0.0

    def _update_soc(
        self,
        current_soc: float,
        schedule_value: float,
        net_consumption: float,
        current_pv: float,
        predicted_soc: np.ndarray,
        period: int
    ) -> float:
        """Update state of charge and predicted values"""
        consumption_soc_impact = net_consumption / self.battery.capacity
        charge_soc_impact = max(0, schedule_value) / self.battery.capacity
        discharge_soc_impact = abs(min(0, schedule_value)) / self.battery.capacity
        pv_charge_soc_impact = min(current_pv, self.battery.get_available_capacity()) / self.battery.capacity

        net_soc_change = (charge_soc_impact + pv_charge_soc_impact - 
                         discharge_soc_impact - consumption_soc_impact)

        new_soc = current_soc + net_soc_change
        new_soc = np.clip(new_soc, self.battery.empty_soc, self.battery.max_soc)

        # Update predicted SOC for visualization
        for j in range(4):
            point_index = period * 4 + j
            if point_index < len(predicted_soc):
                progress_factor = (j + 1) / 4
                interval_soc = current_soc + (net_soc_change * progress_factor)
                predicted_soc[point_index] = np.clip(
                    interval_soc, self.battery.empty_soc, self.battery.max_soc
                )

        return new_soc
