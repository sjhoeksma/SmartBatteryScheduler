import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.battery_config import render_battery_config
from components.price_chart import render_price_chart
from components.battery_status import render_battery_status
from components.historical_analysis import render_historical_analysis
from components.cost_calculator import render_cost_calculator
from components.power_flow import render_power_flow
from components.manual_battery_control import render_manual_battery_control
from utils.price_data import get_day_ahead_prices, get_price_forecast_confidence
from utils.historical_data import generate_historical_prices
from utils.optimizer import optimize_schedule
from utils.battery import Battery
from utils.translations import get_text, add_language_selector
from utils.object_store import ObjectStore
from utils.weather_service import WeatherService

st.set_page_config(page_title="Energy Management Dashboard",
                   page_icon="⚡",
                   layout="wide",
                   initial_sidebar_state="collapsed")


def get_max_forecast_hours():
    """Calculate maximum available forecast hours based on current time"""
    now = datetime.now()
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    if now >= publication_time:
        # After 13:00 CET, we have tomorrow's prices
        return 36  # Changed from 48 to 36 hours
    else:
        # Before 13:00 CET, calculate remaining hours
        remaining_hours = 24 - now.hour
        return remaining_hours  # Only return remaining hours of current day


# Cache price data with TTL based on forecast hours
@st.cache_data(ttl=900)  # 15 minutes cache
def get_cached_prices(forecast_hours):
    """Get cached price data with extended forecast support"""
    return get_day_ahead_prices(forecast_hours=forecast_hours)


def main():
    # Add custom CSS to reduce padding
    st.markdown('''
        <style>
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 0rem;
            }
            .stApp {
                overflow-x: hidden;
            }
            .css-18e3th9 {
                padding-top: 0rem;
            }
            header {
                visibility: hidden;
            }
        </style>
    ''',
                unsafe_allow_html=True)

    # Add language selector to sidebar
    add_language_selector()

    # Initialize session state
    if 'store' not in st.session_state:
        st.session_state.store = ObjectStore()

    # Initialize WeatherService
    if 'weather_service' not in st.session_state:
        try:
            st.session_state.weather_service = WeatherService()
            st.session_state.weather_service_initialized = True
        except Exception as e:
            st.error(f"Error initializing weather service: {str(e)}")
            st.session_state.weather_service_initialized = False

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
                max_watt_peak=default_profile.max_watt_peak)

    # Initialize forecast hours with default value
    if 'forecast_hours' not in st.session_state:
        st.session_state.forecast_hours = get_max_forecast_hours()

    # Initialize variables
    prices = None
    schedule = None
    predicted_soc = None
    consumption_stats = None

    # Get cached price forecast and optimization results
    try:
        # Update forecast hours if needed
        forecast_hours = get_max_forecast_hours()
        if forecast_hours != st.session_state.forecast_hours:
            st.session_state.forecast_hours = forecast_hours
            st.cache_data.clear()

        # Get prices and optimization results
        prices = get_cached_prices(st.session_state.forecast_hours)
        if prices is not None and st.session_state.battery:
            schedule, predicted_soc, consumption_stats = optimize_schedule(
                prices, st.session_state.battery)
    except Exception as e:
        st.error(f"Error updating price data: {str(e)}")

        # Layout
        # tab1, tab2, tab3, tab4, tab5 = st.tabs([
        #     get_text("real_time_dashboard"),
        #     get_text("manual_control"),
        #     get_text("power_flow"),
        #     get_text("historical_analysis"),
        #     get_text("cost_calculator")
        # ])

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        get_text("real_time_dashboard"),
        get_text("manual_control"),
        get_text("power_flow"),
        get_text("historical_analysis"),
        get_text("cost_calculator")
    ])

    with tab1:
        st.markdown(
            f"<h1 style='font-size: 1.8rem; margin: 0; padding: 0;'>{get_text('app_title')}</h1>",
            unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])

        with col1:
            if prices is not None and st.session_state.battery:
                render_price_chart(prices, schedule, predicted_soc,
                                   consumption_stats)
            else:
                st.warning("No price data available")

        with col2:
            st.subheader(get_text("battery_config"))
            render_battery_config()

            if st.session_state.battery:
                st.subheader(get_text("battery_status"))
                render_battery_status(st.session_state.battery)

    with tab2:
        if st.session_state.battery:
            render_manual_battery_control(st.session_state.battery,
                                      prices=prices,
                                      schedule=schedule,
                                      predicted_soc=predicted_soc,
                                      consumption_stats=consumption_stats)
        else:
            st.warning("Please configure battery settings first")

    with tab3:
        if st.session_state.battery:
            render_power_flow(st.session_state.battery)
        else:
            st.warning("Please configure battery settings first")

    with tab4:
        st.subheader(get_text("historical_analysis"))
        historical_prices = generate_historical_prices(days=30)
        if st.session_state.battery:
            render_historical_analysis(historical_prices, st.session_state.battery)
        else:
            st.warning("Please configure battery settings first")

    with tab5:
        if st.session_state.battery and historical_prices is not None:
            render_cost_calculator(historical_prices, st.session_state.battery)
        else:
            st.warning("Please configure battery settings first")


if __name__ == "__main__":
    main()
