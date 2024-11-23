"""
core - A library for battery energy optimization and scheduling

This library provides components for:
- Battery state management and simulation
- Charging schedule optimization
- Battery profile configuration
- Price-based optimization strategies
- Weather and PV production forecasting
- Price data management and forecasting
"""

from .battery import Battery
from .optimizer import Optimizer
from .profiles import BatteryProfile
from .weather import WeatherService
from .price import PriceService
from . import price_data
from .client import Client
from .exceptions import (
    EcactusEcosConnectionException,
    EcactusEcosException,
    EcactusEcosUnauthenticatedException,
    EcactusEcosDataException,
)

__version__ = "0.1.0"
__all__ = [
    'Battery', 'Optimizer', 'BatteryProfile', 'WeatherService', 'PriceService',
    'price_data', "Client", 'EcactusEcosConnectionException',
    "EcactusEcosException", "EcactusEcosUnauthenticatedException",
    "EcactusEcosDataException"
]
