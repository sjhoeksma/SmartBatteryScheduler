import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.battery_config import render_battery_config
from components.price_chart import render_price_chart
from components.battery_status import render_battery_status
from components.historical_analysis import render_historical_analysis
from components.cost_calculator import render_cost_calculator
from components.power_flow import render_power_flow
from utils.price_data import get_day_ahead_prices
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

def main():
    # Add language selector to sidebar
    add_language_selector()
    
    st.title(get_text("app_title"))
    
    # Initialize session state
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = BatteryProfileManager()
    
    if 'battery' not in st.session_state:
        default_profile = st.session_state.profile_manager.get_profile("Home Battery")
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
            prices = get_day_ahead_prices()
            schedule, predicted_soc, consumption_stats = optimize_schedule(
                prices,
                st.session_state.battery
            )
            render_price_chart(prices, schedule, predicted_soc, consumption_stats)

        with col2:
            st.subheader(get_text("battery_config"))
            render_battery_config()
            
            st.subheader(get_text("battery_status"))
            render_battery_status(st.session_state.battery)
    
    with tab2:
        render_power_flow(st.session_state.battery)
    
    with tab3:
        st.subheader(get_text("historical_analysis"))
        # Generate 30 days of historical data
        historical_prices = generate_historical_prices(days=30)
        render_historical_analysis(historical_prices, st.session_state.battery)
        
    with tab4:
        # Generate 30 days of historical data for cost calculations
        historical_prices = generate_historical_prices(days=30)
        render_cost_calculator(historical_prices, st.session_state.battery)

if __name__ == "__main__":
    main()
