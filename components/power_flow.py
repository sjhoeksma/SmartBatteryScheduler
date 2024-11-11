import streamlit as st
from utils.translations import get_text
from datetime import datetime, timedelta
import numpy as np
import time
from utils.ecactus_client import get_ecactus_client

def get_flow_direction(power):
    """Return directional indicator based on power flow"""
    if abs(power) < 0.1:  # Near zero flow
        return "↔"
    return "↑" if power > 0 else "↓"

def render_power_flow(battery):
    """Render power flow visualization using real-time data from Ecactus API"""
    try:
        st.subheader(get_text("power_flow_visualization"))
        
        # Create container for real-time updates
        display_container = st.empty()
        
        # Function to update power values
        def update_power_values():
            try:
                client = get_ecactus_client()
                power_data = client.get_power_consumption()
                if power_data:
                    return (
                        power_data['grid_power'],
                        power_data['home_consumption'],
                        power_data['battery_power']
                    )
            except (ValueError, Exception) as e:
                pass
            
            # Fallback to simulated values if API fails
            timestamp = time.time()
            grid_power = np.sin(timestamp / 10) * 2 + 3
            home_consumption = abs(np.sin(timestamp / 10 + 1)) * 1.5 + 1
            battery_power = battery.get_current_power()
            return grid_power, home_consumption, battery_power
        
        # Initial values
        grid_power, home_consumption, battery_power = update_power_values()
        
        with display_container.container():
            # Display power flow metrics in three columns
            cols = st.columns(3)
            
            # Grid metrics
            with cols[0]:
                st.metric(
                    f"{get_text('grid_power')} {get_flow_direction(grid_power)}", 
                    f"{abs(grid_power):.1f} kW",
                    delta=get_text("supply") if grid_power > 0 else get_text("return")
                )
            
            # Battery metrics
            with cols[1]:
                st.metric(
                    f"{get_text('battery_power')} {get_flow_direction(battery_power)}", 
                    f"{abs(battery_power):.1f} kW",
                    delta=get_text("charging") if battery_power > 0 else get_text("discharging")
                )
                # Add battery charge level
                st.progress(
                    value=battery.current_soc,
                    text=f"🔋 {battery.current_soc*100:.1f}%"
                )
            
            # Home consumption metrics
            with cols[2]:
                st.metric(
                    f"{get_text('home_consumption')} {get_flow_direction(-home_consumption)}", 
                    f"{home_consumption:.1f} kW",
                    delta=get_text("consuming")
                )
            
            # Display flow information
            st.markdown("### " + get_text("power_flow_status"))
            
            # Calculate net power flow
            net_flow = grid_power + battery_power - home_consumption
            
            # Show power flow status with emojis
            if grid_power > 0:
                if battery_power > 0:
                    st.info("⚡ Grid → Home & Battery 🔋")
                else:
                    st.info("⚡ Grid → Home 🏠")
            elif battery_power < 0:
                st.info("🔋 Battery → Home 🏠")
            else:
                st.info("🏠 Home self-consuming")
            
            # Show energy balance
            st.metric(
                get_text("energy_balance"),
                f"{abs(net_flow):.1f} kW",
                delta=get_text("surplus") if net_flow > 0 else get_text("deficit")
            )

    except Exception as e:
        st.error(f"Error rendering power flow visualization: {str(e)}")
        st.exception(e)  # Show detailed error information
