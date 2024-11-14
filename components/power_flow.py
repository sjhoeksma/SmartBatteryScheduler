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
        
        # Initial values
        grid_power, home_consumption, battery_power = update_power_values()
        
        with display_container.container():
            cols = st.columns(3)
            
            # Grid metrics
            with cols[0]:
                # Calculate grid consumption and discharge separately
                grid_consumption = max(0, grid_power)
                grid_discharge = abs(min(0, grid_power))
                
                # Show grid consumption if present
                if grid_consumption > 0:
                    st.metric(
                        f"{get_text('grid_power')} {get_flow_direction(grid_consumption)}", 
                        f"{grid_consumption:.1f} kW",
                        delta=get_text("supply")
                    )
                
                # Show grid discharge if present
                if grid_discharge > 0:
                    st.metric(
                        f"{get_text('grid_discharge')} {get_flow_direction(-grid_discharge)}", 
                        f"{grid_discharge:.1f} kW",
                        delta=get_text("discharge_to_grid")
                    )
            
            # Battery metrics
            with cols[1]:
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
                    # Separate home and grid discharge
                    battery_to_home = min(abs(battery_power), home_consumption)
                    battery_to_grid = abs(battery_power) - battery_to_home
                    
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
                # Calculate home consumption sources
                home_from_battery = min(abs(min(0, battery_power)), home_consumption)
                home_from_grid = max(0, home_consumption - home_from_battery)
                
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
            total_output = home_consumption + (battery_to_grid if 'battery_to_grid' in locals() else 0)
            energy_balance = total_input - total_output
            
            st.metric(
                get_text("energy_balance"),
                f"{abs(energy_balance):.1f} kW",
                delta=get_text("surplus") if energy_balance > 0 else get_text("deficit")
            )
    
    except Exception as e:
        st.error(f"Error rendering power flow visualization: {str(e)}")