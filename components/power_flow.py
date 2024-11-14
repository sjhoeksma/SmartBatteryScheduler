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
        
        # When battery is at minimum SOC, show all home consumption as grid usage
        if battery.current_soc <= battery.min_soc:
            net_grid_consumption = home_consumption  # All consumption comes from grid
            home_discharge = 0
            grid_discharge = 0
            
            with display_container.container():
                # Grid metrics
                cols = st.columns(3)
                
                with cols[0]:
                    # Always show the grid power metric when at min SOC
                    st.metric(
                        f"{get_text('grid_power')} {get_flow_direction(net_grid_consumption)}", 
                        f"{net_grid_consumption:.1f} kW",
                        delta=get_text("supply")
                    )
                
                # Battery metrics
                with cols[1]:
                    # Show battery status with min SOC indicator
                    st.progress(
                        value=battery.current_soc,
                        text=f"🔋 {battery.current_soc*100:.1f}% (Min SOC)"
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
                status_messages = ["⚡ Grid → 🏠 Home (Direct Supply)"]
                
                # Display status message
                st.info(status_messages[0])
                
                # Show energy balance
                st.metric(
                    get_text("energy_balance"),
                    f"{abs(net_grid_consumption - home_consumption):.1f} kW",
                    delta=get_text("balanced")
                )
        else:
            # Calculate separated discharge values
            total_discharge = abs(min(battery_power, 0))
            home_discharge = min(total_discharge, home_consumption)
            grid_discharge = max(0, total_discharge - home_consumption)
            # Calculate actual grid consumption (excluding battery discharge to grid)
            net_grid_consumption = max(0, home_consumption - home_discharge)
            
            with display_container.container():
                # Display power flow metrics in three columns
                cols = st.columns(3)
                
                # Grid metrics
                with cols[0]:
                    if net_grid_consumption > 0:
                        st.metric(
                            f"{get_text('grid_power')} {get_flow_direction(net_grid_consumption)}", 
                            f"{net_grid_consumption:.1f} kW",
                            delta=get_text("supply")
                        )
                    if grid_discharge > 0:
                        st.metric(
                            f"{get_text('grid_discharge')} {get_flow_direction(-grid_discharge)}", 
                            f"{grid_discharge:.1f} kW",
                            delta=get_text("discharge_to_grid")
                        )
                
                # Battery metrics
                with cols[1]:
                    st.progress(
                        value=battery.current_soc,
                        text=f"🔋 {battery.current_soc*100:.1f}%"
                    )
                    
                    if battery_power > 0:
                        st.metric(
                            f"{get_text('battery_power')} {get_flow_direction(battery_power)}", 
                            f"{battery_power:.1f} kW",
                            delta=get_text("charging")
                        )
                    elif battery_power < 0:
                        if home_discharge > 0:
                            st.metric(
                                f"{get_text('home_discharge')} {get_flow_direction(-home_discharge)}", 
                                f"{home_discharge:.1f} kW",
                                delta=get_text("discharge_to_home")
                            )
                        if grid_discharge > 0:
                            st.metric(
                                f"{get_text('grid_discharge')} {get_flow_direction(-grid_discharge)}", 
                                f"{grid_discharge:.1f} kW",
                                delta=get_text("discharge_to_grid")
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
                
                # Show power flow status with emojis
                status_messages = []
                
                if net_grid_consumption > 0:
                    status_messages.append("⚡ Grid → 🏠 Home")
                
                if battery_power > 0:
                    status_messages.append("⚡ Grid → 🔋 Battery")
                elif battery_power < 0:
                    if home_discharge > 0:
                        status_messages.append("🔋 Battery → 🏠 Home")
                    if grid_discharge > 0:
                        status_messages.append("🔋 Battery → ⚡ Grid")
                
                # Default message if no active flows
                if not status_messages:
                    status_messages.append("🏠 Home self-consuming")
                
                # Display all active power flows
                for message in status_messages:
                    st.info(message)
                
                # Show detailed energy balance
                total_input = net_grid_consumption + (battery_power if battery_power > 0 else 0)
                total_output = home_consumption + (abs(battery_power) if battery_power < 0 else 0)
                energy_balance = total_input - total_output
                
                st.metric(
                    get_text("energy_balance"),
                    f"{abs(energy_balance):.1f} kW",
                    delta=get_text("surplus") if energy_balance > 0 else get_text("deficit")
                )
    
    except Exception as e:
        st.error(f"Error rendering power flow visualization: {str(e)}")
