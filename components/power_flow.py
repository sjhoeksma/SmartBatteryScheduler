import streamlit as st
from utils.translations import get_text
from datetime import datetime
import numpy as np
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
        
        def update_power_values():
            """Get power values from API or simulation"""
            try:
                client = get_ecactus_client()
                power_data = client.get_power_consumption()
                if power_data:
                    return (
                        power_data['grid_power'],
                        power_data['home_consumption'],
                        power_data['battery_power']
                    )
            except Exception:
                pass
            
            # Fallback to simulated values if API fails
            current_time = datetime.now().timestamp()
            grid_power = np.sin(current_time / 10) * 2 + 3
            home_consumption = abs(np.sin(current_time / 10 + 1)) * 1.5 + 1
            battery_power = battery.get_current_power()
            return grid_power, home_consumption, battery_power
        
        # Get initial power values
        grid_power, home_consumption, battery_power = update_power_values()
        
        # Pre-calculate all power flows
        grid_consumption = max(0, grid_power)  # Power from grid
        grid_discharge = abs(min(0, grid_power))  # Power to grid
        
        # Calculate battery discharge flows
        battery_discharge = abs(min(0, battery_power))  # Total battery discharge
        battery_to_home = min(battery_discharge, home_consumption)  # Battery power used by home
        battery_to_grid = battery_discharge - battery_to_home  # Remaining battery power to grid
        
        # Calculate home consumption sources
        home_from_battery = battery_to_home  # Home consumption from battery
        home_from_grid = max(0, home_consumption - home_from_battery)  # Home consumption from grid
        
        with display_container.container():
            cols = st.columns(3)
            
            # Grid metrics
            with cols[0]:
                st.markdown("### " + get_text("grid_power"))
                if grid_consumption > 0:
                    st.metric(
                        f"{get_text('grid_power')} {get_flow_direction(grid_consumption)}", 
                        f"{grid_consumption:.1f} kW",
                        delta=get_text("supply")
                    )
                
                if grid_discharge > 0:
                    st.metric(
                        f"{get_text('grid_discharge')} {get_flow_direction(-grid_discharge)}", 
                        f"{grid_discharge:.1f} kW",
                        delta=get_text("return")
                    )
            
            # Battery metrics
            with cols[1]:
                st.markdown("### " + get_text("battery_power"))
                # Battery SOC indicator
                soc_text = (
                    f"🔋 {battery.current_soc*100:.1f}% (Min SOC)"
                    if battery.current_soc <= battery.min_soc
                    else f"🔋 {battery.current_soc*100:.1f}%"
                )
                st.progress(
                    value=battery.current_soc,
                    text=soc_text
                )
                
                # Battery power flow metrics
                if battery_power > 0:
                    st.metric(
                        f"{get_text('battery_power')} {get_flow_direction(battery_power)}", 
                        f"{battery_power:.1f} kW",
                        delta=get_text("charging")
                    )
                elif battery_power < 0:
                    if battery_to_home > 0:
                        st.metric(
                            f"{get_text('home_discharge')} {get_flow_direction(-battery_to_home)}", 
                            f"{battery_to_home:.1f} kW",
                            delta=get_text("discharge_to_home")
                        )
                    if battery_to_grid > 0:
                        st.metric(
                            f"{get_text('grid_discharge')} {get_flow_direction(-battery_to_grid)}", 
                            f"{battery_to_grid:.1f} kW",
                            delta=get_text("discharge_to_grid")
                        )
            
            # Home consumption metrics
            with cols[2]:
                st.markdown("### " + get_text("home_consumption"))
                if home_from_grid > 0:
                    st.metric(
                        f"{get_text('home_consumption')} (Grid) {get_flow_direction(-home_from_grid)}", 
                        f"{home_from_grid:.1f} kW",
                        delta=get_text("consuming")
                    )
                if home_from_battery > 0:
                    st.metric(
                        f"{get_text('home_consumption')} (Battery) {get_flow_direction(-home_from_battery)}", 
                        f"{home_from_battery:.1f} kW",
                        delta=get_text("consuming")
                    )
            
            # Display flow information
            st.markdown("### " + get_text("power_flow_status"))
            status_messages = []
            
            # Build status messages based on actual flows
            if home_from_grid > 0:
                status_messages.append("⚡ Grid → 🏠 Home")
            if battery_power > 0:
                status_messages.append("⚡ Grid → 🔋 Battery")
            if home_from_battery > 0:
                status_messages.append("🔋 Battery → 🏠 Home")
            if battery_to_grid > 0:
                status_messages.append("🔋 Battery → ⚡ Grid")
            
            # Default message if no active flows
            if not status_messages:
                status_messages.append("🏠 Home self-consuming")
            
            # Display all active power flows
            for message in status_messages:
                st.info(message)
            
            # Show energy balance
            total_input = grid_consumption + (battery_power if battery_power > 0 else 0)
            total_output = home_consumption + battery_to_grid
            energy_balance = total_input - total_output
            
            st.metric(
                get_text("energy_balance"),
                f"{abs(energy_balance):.1f} kW",
                delta=get_text("surplus") if energy_balance > 0 else get_text("deficit")
            )
    
    except Exception as e:
        st.error(f"Error rendering power flow visualization: {str(e)}")
