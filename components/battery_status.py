import streamlit as st
from datetime import datetime
from utils.translations import get_text

def render_battery_status(battery):
    """Render battery status indicators"""
    # Add auto-refresh using st.empty()
    status_container = st.empty()
    
    with status_container.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                get_text("current_soc"),
                f"{battery.current_soc*100:.1f}%",
                delta=f"{(battery.current_soc-0.5)*100:.1f}%"
            )
            
            st.metric(
                get_text("available_capacity"),
                f"{battery.get_available_capacity():.1f} kWh"
            )
        
        with col2:
            st.metric(
                get_text("current_energy"),
                f"{battery.get_current_energy():.1f} kWh"
            )
            
            st.metric(
                get_text("charge_rate"),
                f"{battery.charge_rate:.1f} kW"
            )
        
        # Battery level visualization
        st.progress(battery.current_soc)
        
        # Charging status indicator
        status_color = "green" if battery.can_charge(1.0) else "red"
        status_text = get_text("available") if status_color == "green" else get_text("unavailable")
        st.markdown(
            f"{get_text('charging_status')}: 🔋 <span style='color:{status_color}'>{status_text}</span>",
            unsafe_allow_html=True
        )
        
        # Last updated timestamp
        st.markdown(f"*{get_text('last_updated')}: {datetime.now().strftime('%H:%M:%S')}*")
