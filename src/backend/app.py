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
                st.session_state.price_service_initialized = True
            except Exception as e:
                st.error(f"Failed to initialize price service: {str(e)}")
                st.session_state.price_service_initialized = False
                return False

        # Initialize weather service
        if 'weather_service' not in st.session_state:
            try:
                st.session_state.weather_service = WeatherService()
                st.session_state.weather_service_initialized = True
            except Exception as e:
                st.error(f"Failed to initialize weather service: {str(e)}")
                st.session_state.weather_service_initialized = False
                return False

        # Initialize battery after required services
        if 'battery' not in st.session_state:
            default_profile = st.session_state.store.get_profile("Home Battery")
            if default_profile:
                st.session_state.battery = Battery(
                    capacity=default_profile.capacity,
                    empty_soc=default_profile.empty_soc,
                    min_soc=default_profile.min_soc,
                    max_soc=default_profile.max_soc,
                    charge_rate=default_profile.charge_rate,
                    profile_name="Home Battery",
                    daily_consumption=default_profile.daily_consumption,
                    usage_pattern=default_profile.usage_pattern,
                    yearly_consumption=default_profile.yearly_consumption,
                    monthly_distribution=default_profile.monthly_distribution,
                    max_daily_cycles=default_profile.max_daily_cycles,
                    surcharge_rate=default_profile.surcharge_rate,
                    max_watt_peak=default_profile.max_watt_peak,
                    look_ahead_hours=36
                )

        # Initialize default language
        if 'language' not in st.session_state:
            st.session_state.language = 'en'

        return True
    except Exception as e:
        st.error(f"Error initializing application: {str(e)}")
        return False
