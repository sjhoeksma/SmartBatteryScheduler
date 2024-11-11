import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.battery_config import render_battery_config
from components.price_chart import render_price_chart
from components.battery_status import render_battery_status
from utils.price_data import get_day_ahead_prices
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
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Energy Price Overview")
        prices = get_day_ahead_prices()
        render_price_chart(prices)
        
        st.subheader("Charging Schedule")
        schedule = optimize_schedule(
            prices,
            st.session_state.battery
        )
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=schedule,
            name="Charging Schedule",
            fill='tozeroy'
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Battery Configuration")
        render_battery_config()
        
        st.subheader("Battery Status")
        render_battery_status(st.session_state.battery)

if __name__ == "__main__":
    main()
