"""
Backend application factory
"""
from core import Battery, Optimizer, PriceService, WeatherService


def create_app():
    """Create and configure application"""
    from streamlit import session_state

    # Initialize services
    if 'price_service' not in session_state:
        session_state.price_service = PriceService()

    if 'weather_service' not in session_state:
        session_state.weather_service = WeatherService()

    return True
