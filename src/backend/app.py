"""
Backend application factory
"""
import streamlit as st
from core import Battery, Optimizer, PriceService, WeatherService
from core.object_store import ObjectStore


def create_app():
    """Create and configure application"""
    try:
        # Initialize services with proper error handling
        if 'price_service' not in st.session_state:
            st.session_state.price_service = PriceService()
            
        if 'weather_service' not in st.session_state:
            st.session_state.weather_service = WeatherService()
            
        if 'battery' not in st.session_state:
            st.session_state.battery = None
            
        if 'store' not in st.session_state:
            st.session_state.store = ObjectStore()
            
        if 'language' not in st.session_state:
            st.session_state.language = 'en'
            
        return True
    except Exception as e:
        st.error(f"Error initializing application: {str(e)}")
        return False
