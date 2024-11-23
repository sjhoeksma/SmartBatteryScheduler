"""
OptimizeResult class for encapsulating battery optimization results
"""
from typing import Optional
import numpy as np
import pandas as pd

class OptimizeResult:
    """Container for battery optimization results"""
    
    def __init__(self,
                 schedule: np.ndarray,
                 predicted_soc: np.ndarray,
                 consumption_stats: pd.DataFrame,
                 consumption: float,
                 consumption_cost: float,
                 optimize_consumption: float,
                 optimize_cost: float):
        """
        Initialize OptimizeResult with optimization outputs
        
        Args:
            schedule: Optimized charging schedule array
            predicted_soc: Predicted state of charge array
            consumption_stats: DataFrame with consumption statistics
            consumption: Total consumption in kWh
            consumption_cost: Total cost without optimization
            optimize_consumption: Optimized consumption in kWh
            optimize_cost: Optimized cost
        """
        self.schedule = schedule
        self.predicted_soc = predicted_soc
        self.consumption_stats = consumption_stats
        self.consumption = consumption
        self.consumption_cost = consumption_cost
        self.optimize_consumption = optimize_consumption
        self.optimize_cost = optimize_cost
        
    @property
    def savings(self) -> float:
        """Calculate total cost savings from optimization"""
        return self.consumption_cost - self.optimize_cost
    
    @property
    def avg_price(self) -> float:
        """Calculate average price per kWh before optimization"""
        return self.consumption_cost / self.consumption if self.consumption > 0 else 0
        
    @property
    def avg_optimized_price(self) -> float:
        """Calculate average price per kWh after optimization"""
        return self.optimize_cost / self.optimize_consumption if self.optimize_consumption > 0 else 0

    def to_dict(self) -> dict:
        """Convert results to dictionary format"""
        return {
            'schedule': self.schedule,
            'predicted_soc': self.predicted_soc,
            'consumption_stats': self.consumption_stats,
            'consumption': self.consumption,
            'consumption_cost': self.consumption_cost,
            'optimize_consumption': self.optimize_consumption,
            'optimize_cost': self.optimize_cost,
            'savings': self.savings,
            'avg_price': self.avg_price,
            'avg_optimized_price': self.avg_optimized_price
        }
