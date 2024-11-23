"""
Backend application factory
"""
import streamlit as st
from core import Battery, Optimizer, PriceService, WeatherService
from core.object_store import ObjectStore


def create_app():
    """Create and configure application"""
    try:
        # Initialize store first
        if 'store' not in st.session_state:
            st.session_state.store = ObjectStore()

        # Initialize price service before battery
        if 'price_service' not in st.session_state:
            try:
                st.session_state.price_service = PriceService()
            except Exception as e:
                st.error(f"Failed to initialize price service: {str(e)}")
                return False

        # Initialize weather service
        if 'weather_service' not in st.session_state:
            try:
                st.session_state.weather_service = WeatherService()
            except Exception as e:
                st.error(f"Failed to initialize weather service: {str(e)}")
                return False

        # Initialize battery after required services
        if 'battery' not in st.session_state:
            if not hasattr(st.session_state, 'store'):
                st.error("Object store must be initialized before battery")
                return False
            st.session_state.battery = None

        # Initialize default language
        if 'language' not in st.session_state:
            st.session_state.language = 'en'

        return True
    except Exception as e:
        st.error(f"Error initializing application: {str(e)}")
        return False
