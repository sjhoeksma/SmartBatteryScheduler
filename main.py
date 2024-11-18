import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
import os

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

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Streamlit with optimized settings
st.set_page_config(
    page_title="Energy Management Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Verify required environment variables
required_env_vars = ['OPENWEATHERMAP_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error(f"Missing environment variables: {missing_vars}")

# Initialize weather service with enhanced error handling
if 'weather_service' not in st.session_state:
    try:
        st.session_state.weather_service = WeatherService()
        logger.info("Weather service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing weather service: {str(e)}")
        st.error("""
            ⚠️ Weather service initialization failed. This will affect PV production forecasts. 
            Please check your OpenWeatherMap API key configuration.
        """)
        st.session_state.weather_service = None

def get_max_forecast_hours():
    """Calculate maximum available forecast hours based on current time"""
    now = datetime.now()
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    if now >= publication_time:
        return 36
    else:
        remaining_hours = 24 - now.hour
        return remaining_hours

# Cache price data with TTL based on forecast hours
@st.cache_data(ttl=900)  # 15 minutes cache
def get_cached_prices(forecast_hours):
    """Get cached price data with extended forecast support"""
    try:
        return get_day_ahead_prices(forecast_hours=forecast_hours)
    except Exception as e:
        logger.error(f"Error fetching price data: {str(e)}")
        return None

def main():
    try:
        # Add language selector to sidebar
        add_language_selector()

        st.title(get_text("app_title"))

        # Initialize session state with error handling
        if 'store' not in st.session_state:
            try:
                st.session_state.store = ObjectStore()
                logger.info("Object store initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing object store: {str(e)}")
                st.error("Failed to initialize storage. Please refresh the page.")
                return

        # Initialize battery configuration
        if 'battery' not in st.session_state:
            try:
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
                    logger.info("Battery initialized with default profile")
            except Exception as e:
                logger.error(f"Error initializing battery: {str(e)}")
                st.error("Failed to initialize battery configuration")
                return

        # Initialize forecast hours
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
                logger.info("Successfully optimized schedule")
        except Exception as e:
            logger.error(f"Error updating price data: {str(e)}")
            st.error("Error updating price data. Please try refreshing the page.")

        # Layout
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            get_text("real_time_dashboard"),
            get_text("manual_control"),
            get_text("power_flow"),
            get_text("historical_analysis"),
            get_text("cost_calculator")
        ])

        with tab1:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Energy Price and Charging Schedule")

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
                render_historical_analysis(historical_prices,
                                        st.session_state.battery)
            else:
                st.warning("Please configure battery settings first")

        with tab5:
            if st.session_state.battery and historical_prices is not None:
                render_cost_calculator(historical_prices, st.session_state.battery)
            else:
                st.warning("Please configure battery settings first")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An unexpected error occurred. Please try refreshing the page.")

if __name__ == "__main__":
    main()
