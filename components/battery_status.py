import streamlit as st

def render_battery_status(battery):
    """Render battery status indicators"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Current State of Charge",
            f"{battery.current_soc*100:.1f}%",
            delta=f"{(battery.current_soc-0.5)*100:.1f}%"
        )
        
        st.metric(
            "Available Capacity",
            f"{battery.get_available_capacity():.1f} kWh"
        )
    
    with col2:
        st.metric(
            "Current Energy",
            f"{battery.get_current_energy():.1f} kWh"
        )
        
        st.metric(
            "Max Charge Rate",
            f"{battery.charge_rate:.1f} kW"
        )
    
    # Battery level visualization
    st.progress(battery.current_soc)
    
    # Status indicators
    status_color = "green" if battery.can_charge(1.0) else "red"
    st.markdown(f"Charging Status: 🔋 <span style='color:{status_color}'>{'Available' if status_color == 'green' else 'Unavailable'}</span>", unsafe_allow_html=True)
