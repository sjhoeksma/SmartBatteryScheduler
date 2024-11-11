import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.battery_config import render_battery_config
from components.price_chart import render_price_chart
from components.battery_status import render_battery_status
from components.historical_analysis import render_historical_analysis
from utils.price_data import get_day_ahead_prices
from utils.historical_data import generate_historical_prices
from utils.optimizer import optimize_schedule
from utils.battery import Battery

st.set_page_config(
    page_title="Energy Management Dashboard",
    page_icon="⚡",
    layout="wide"
)

def main():
    st.title("⚡ Energy Management Dashboard")
    
    # Initialize session state
    if 'battery' not in st.session_state:
        st.session_state.battery = Battery(
            capacity=40.0,
            min_soc=0.1,
            max_soc=0.9,
            charge_rate=7.4
        )

    # Layout
    tab1, tab2 = st.tabs(["Real-time Dashboard", "Historical Analysis"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Energy Price and Charging Schedule")
            prices = get_day_ahead_prices()
            schedule, predicted_soc = optimize_schedule(
                prices,
                st.session_state.battery
            )
            render_price_chart(prices, schedule, predicted_soc)

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

if __name__ == "__main__":
    main()
