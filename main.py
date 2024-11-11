import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.battery_config import render_battery_config
from components.price_chart import render_price_chart
from components.battery_status import render_battery_status
from components.historical_analysis import render_historical_analysis
from components.cost_calculator import render_cost_calculator
from utils.price_data import get_day_ahead_prices
from utils.historical_data import generate_historical_prices
from utils.optimizer import optimize_schedule
from utils.battery import Battery
from utils.battery_profiles import BatteryProfileManager

st.set_page_config(
    page_title="Energy Management Dashboard",
    page_icon="⚡",
    layout="wide"
)

def main():
    st.title("⚡ Energy Management Dashboard")
    
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
    tab1, tab2, tab3 = st.tabs(["Real-time Dashboard", "Historical Analysis", "Cost Calculator"])
    
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
            st.subheader("Battery Configuration")
            render_battery_config()
            
            st.subheader("Battery Status")
            render_battery_status(st.session_state.battery)
    
    with tab2:
        st.subheader("Historical Price Analysis")
        # Generate 30 days of historical data
        historical_prices = generate_historical_prices(days=30)
        render_historical_analysis(historical_prices, st.session_state.battery)
        
    with tab3:
        # Generate 30 days of historical data for cost calculations
        historical_prices = generate_historical_prices(days=30)
        render_cost_calculator(historical_prices, st.session_state.battery)

if __name__ == "__main__":
    main()
