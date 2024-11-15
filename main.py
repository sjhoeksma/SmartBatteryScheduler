import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.battery_config import render_battery_config
from components.price_chart import render_price_chart
from components.battery_status import render_battery_status
from components.historical_analysis import render_historical_analysis
from components.cost_calculator import render_cost_calculator
from components.power_flow import render_power_flow
from utils.price_data import get_day_ahead_prices, get_price_forecast_confidence
from utils.historical_data import generate_historical_prices
from utils.optimizer import optimize_schedule
from utils.battery import Battery
from utils.battery_profiles import BatteryProfileManager
from utils.translations import get_text, add_language_selector

st.set_page_config(
    page_title="Energy Management Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_max_forecast_hours():
    """Calculate maximum available forecast hours based on current time"""
    now = datetime.now()
    publication_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    if now >= publication_time:
        # After 13:00 CET, we have tomorrow's prices plus additional forecast
        return 48  # Extended to 48 hours
    else:
        # Before 13:00 CET, calculate remaining hours plus next day
        remaining_hours = 24 - now.hour
        return max(24, remaining_hours + 24)  # Ensure at least 24 hours

# Cache price data with TTL based on forecast hours
@st.cache_data(ttl=900)  # 15 minutes cache
def get_cached_prices(forecast_hours):
    """Get cached price data with extended forecast support"""
    return get_day_ahead_prices(forecast_hours=forecast_hours)

# Cache optimization results
@st.cache_data(ttl=600)  # 10 minutes cache
def get_cached_optimization(_prices, _battery):
    """Get cached optimization results"""
    return optimize_schedule(_prices, _battery)

def main():
    # Add language selector to sidebar
    add_language_selector()
    
    st.title(get_text("app_title"))
    
    # Initialize session state
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = BatteryProfileManager()
    
    if 'battery' not in st.session_state:
        default_profile = st.session_state.profile_manager.get_profile("Home Battery")
        if default_profile:
            st.session_state.battery = Battery(
                capacity=default_profile.capacity,
                min_soc=default_profile.min_soc,
                max_soc=default_profile.max_soc,
                charge_rate=default_profile.charge_rate,
                profile_name="Home Battery",
                daily_consumption=default_profile.daily_consumption,
                usage_pattern=default_profile.usage_pattern,
                yearly_consumption=default_profile.yearly_consumption,
                monthly_distribution=default_profile.monthly_distribution
            )
    
    # Initialize forecast hours with default value
    if 'forecast_hours' not in st.session_state:
        st.session_state.forecast_hours = 24
    
    # Layout
    tab1, tab2, tab3, tab4 = st.tabs([
        get_text("real_time_dashboard"),
        get_text("power_flow"),
        get_text("historical_analysis"),
        get_text("cost_calculator")
    ])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Energy Price and Charging Schedule")
            
            # Add forecast hours selector with dynamic maximum
            max_hours = get_max_forecast_hours()
            forecast_hours = st.slider(
                "Forecast Hours",
                min_value=12,
                max_value=max_hours,
                value=min(st.session_state.forecast_hours, max_hours),
                step=1,
                help=f"Select number of hours to forecast (12-{max_hours} hours)"
            )
            
            if forecast_hours != st.session_state.forecast_hours:
                st.session_state.forecast_hours = forecast_hours
                st.cache_data.clear()
            
            try:
                # Get cached price forecast and optimization results
                prices = get_cached_prices(forecast_hours)
                if st.session_state.battery:
                    schedule, predicted_soc, consumption_stats = get_cached_optimization(
                        prices,
                        st.session_state.battery
                    )
                    render_price_chart(prices, schedule, predicted_soc, consumption_stats)
                else:
                    render_price_chart(prices)
            except Exception as e:
                st.error(f"Error updating price data: {str(e)}")
                st.info("Please try adjusting the forecast hours or refresh the page.")

        with col2:
            st.subheader(get_text("battery_config"))
            render_battery_config()
            
            if st.session_state.battery:
                st.subheader(get_text("battery_status"))
                render_battery_status(st.session_state.battery)
    
    with tab2:
        if st.session_state.battery:
            render_power_flow(st.session_state.battery)
    
    with tab3:
        st.subheader(get_text("historical_analysis"))
        historical_prices = generate_historical_prices(days=30)
        if st.session_state.battery:
            render_historical_analysis(historical_prices, st.session_state.battery)
        
    with tab4:
        if st.session_state.battery:
            historical_prices = generate_historical_prices(days=30)
            render_cost_calculator(historical_prices, st.session_state.battery)

if __name__ == "__main__":
    main()
