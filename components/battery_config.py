import streamlit as st

def render_battery_config():
    """Render battery configuration controls"""
    with st.form("battery_config"):
        capacity = st.number_input(
            "Battery Capacity (kWh)",
            min_value=1.0,
            max_value=100.0,
            value=st.session_state.battery.capacity
        )
        
        min_soc = st.slider(
            "Minimum State of Charge",
            min_value=0.0,
            max_value=0.5,
            value=st.session_state.battery.min_soc
        )
        
        max_soc = st.slider(
            "Maximum State of Charge",
            min_value=0.5,
            max_value=1.0,
            value=st.session_state.battery.max_soc
        )
        
        charge_rate = st.number_input(
            "Maximum Charge Rate (kW)",
            min_value=1.0,
            max_value=22.0,
            value=st.session_state.battery.charge_rate
        )
        
        if st.form_submit_button("Update Configuration"):
            st.session_state.battery.capacity = capacity
            st.session_state.battery.min_soc = min_soc
            st.session_state.battery.max_soc = max_soc
            st.session_state.battery.charge_rate = charge_rate
            st.success("Battery configuration updated!")
