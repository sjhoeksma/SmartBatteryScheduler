import streamlit as st
from utils.translations import get_text
from datetime import datetime
import numpy as np
from utils.ecactus_client import get_ecactus_client
from utils.weather_service import WeatherService

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
        
        # Initialize weather service for PV production
        weather_service = WeatherService()
        
        def update_power_values():
            """Get power values from API or simulation"""
            try:
                client = get_ecactus_client()
                power_data = client.get_power_consumption()
                
                # Get PV production forecast
                pv_forecast = weather_service.get_pv_forecast(battery.max_watt_peak)
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                current_pv_production = pv_forecast.get(current_hour, 0.0)
                
                if power_data:
                    return (
                        power_data['grid_power'],
                        power_data['home_consumption'],
                        power_data['battery_power'],
                        current_pv_production
                    )
            except Exception:
                pass
            
            # Fallback to simulated values if API fails
            current_time = datetime.now().timestamp()
            grid_power = np.sin(current_time / 10) * 2 + 3
            home_consumption = abs(np.sin(current_time / 10 + 1)) * 1.5 + 1
            battery_power = battery.get_current_power()
            
            # Simulate PV production based on time of day
            hour = datetime.now().hour
            if 6 <= hour <= 20:  # Daylight hours
                pv_production = abs(np.sin((hour - 6) * np.pi / 14)) * (battery.max_watt_peak / 1000.0) * 0.7
            else:
                pv_production = 0.0
            
            return grid_power, home_consumption, battery_power, pv_production
        
        # Get initial power values
        grid_power, home_consumption, battery_power, pv_production = update_power_values()
        
        # Pre-calculate all power flows
        grid_consumption = max(0, grid_power)  # Power from grid
        grid_discharge = abs(min(0, grid_power))  # Power to grid
        
        # Calculate battery discharge flows
        battery_discharge = abs(min(0, battery_power))  # Total battery discharge
        battery_to_home = min(battery_discharge, home_consumption)  # Battery power used by home
        battery_to_grid = battery_discharge - battery_to_home  # Remaining battery power to grid
        
        # Calculate PV flows
        pv_to_home = min(pv_production, home_consumption)  # PV power used by home
        pv_to_battery = min(
            max(0, pv_production - pv_to_home),  # Remaining PV power
            battery.get_available_capacity()  # Available battery capacity
        )
        pv_to_grid = max(0, pv_production - pv_to_home - pv_to_battery)  # Excess PV to grid
        
        # Calculate home consumption sources
        home_from_battery = battery_to_home  # Home consumption from battery
        home_from_pv = pv_to_home  # Home consumption from PV
        home_from_grid = max(0, home_consumption - home_from_battery - home_from_pv)  # Home consumption from grid
        
        with display_container.container():
            cols = st.columns(4)  # Added one more column for PV
            
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
            
            # PV metrics (new)
            with cols[1]:
                st.markdown("### Solar Production")
                if pv_production > 0:
                    st.metric(
                        "Total PV Production ☀️",
                        f"{pv_production:.1f} kW",
                        delta="Generating"
                    )
                    if pv_to_home > 0:
                        st.metric(
                            f"PV to Home {get_flow_direction(-pv_to_home)}",
                            f"{pv_to_home:.1f} kW",
                            delta="Self-consumption"
                        )
                    if pv_to_battery > 0:
                        st.metric(
                            f"PV to Battery {get_flow_direction(pv_to_battery)}",
                            f"{pv_to_battery:.1f} kW",
                            delta="Charging"
                        )
                    if pv_to_grid > 0:
                        st.metric(
                            f"PV to Grid {get_flow_direction(-pv_to_grid)}",
                            f"{pv_to_grid:.1f} kW",
                            delta="Export"
                        )
            
            # Battery metrics
            with cols[2]:
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
            with cols[3]:
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
                if home_from_pv > 0:
                    st.metric(
                        f"{get_text('home_consumption')} (PV) {get_flow_direction(-home_from_pv)}", 
                        f"{home_from_pv:.1f} kW",
                        delta="Solar Power"
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
            if pv_production > 0:
                if pv_to_home > 0:
                    status_messages.append("☀️ PV → 🏠 Home")
                if pv_to_battery > 0:
                    status_messages.append("☀️ PV → 🔋 Battery")
                if pv_to_grid > 0:
                    status_messages.append("☀️ PV → ⚡ Grid")
            
            # Default message if no active flows
            if not status_messages:
                status_messages.append("🏠 Home self-consuming")
            
            # Display all active power flows
            for message in status_messages:
                st.info(message)
            
            # Show energy balance
            total_input = grid_consumption + pv_production + (battery_power if battery_power > 0 else 0)
            total_output = home_consumption + battery_to_grid + pv_to_grid
            energy_balance = total_input - total_output
            
            st.metric(
                get_text("energy_balance"),
                f"{abs(energy_balance):.1f} kW",
                delta=get_text("surplus") if energy_balance > 0 else get_text("deficit")
            )
    
    except Exception as e:
        st.error(f"Error rendering power flow visualization: {str(e)}")
