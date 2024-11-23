"""
Backend application factory
"""
import streamlit as st
from core import Battery, Optimizer, PriceService, WeatherService


def create_app():
    """Create and configure application"""
    # Initialize services
    if 'price_service' not in st.session_state:
        st.session_state.price_service = PriceService()
    if 'weather_service' not in st.session_state:
        st.session_state.weather_service = WeatherService()
    return True
