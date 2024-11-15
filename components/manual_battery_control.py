import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.translations import get_text

def render_manual_battery_control(battery):
    """Render manual battery control interface with scheduling"""
    st.subheader(get_text("manual_control"))
    
    # Display current battery status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current SOC", f"{battery.current_soc*100:.1f}%")
    with col2:
        st.metric("Available Capacity", f"{battery.get_available_capacity():.1f} kWh")
    with col3:
        current_power = battery.get_current_power()
        st.metric("Current Power", 
                 f"{abs(current_power):.1f} kW",
                 delta="Charging" if current_power > 0 else "Discharging" if current_power < 0 else "Idle")

    # Immediate control section
    st.markdown("### " + get_text("immediate_control"))
    
    col1, col2 = st.columns(2)
    with col1:
        charge_power = st.number_input(
            "Charge Power (kW)",
            min_value=0.0,
            max_value=battery.charge_rate,
            value=battery.charge_rate/2,
            step=0.1
        )
        if st.button("Start Charging"):
            if battery.can_charge(charge_power):
                if battery.charge(charge_power):
                    st.success("Charging started")
                else:
                    st.error("Failed to start charging")
            else:
                st.error("Cannot charge: Battery capacity limit reached")
    
    with col2:
        discharge_power = st.number_input(
            "Discharge Power (kW)",
            min_value=0.0,
            max_value=battery.charge_rate,
            value=battery.charge_rate/2,
            step=0.1
        )
        if st.button("Start Discharging"):
            if battery.can_discharge(discharge_power):
                if battery.discharge(discharge_power):
                    st.success("Discharging started")
                else:
                    st.error("Failed to start discharging")
            else:
                st.error("Cannot discharge: Minimum SOC reached")
    
    # Schedule section
    st.markdown("### " + get_text("schedule_control"))
    
    # Initialize session state for schedules if not exists
    if 'battery_schedules' not in st.session_state:
        st.session_state.battery_schedules = []
    
    # Add new schedule
    with st.form("add_schedule"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            operation = st.selectbox(
                "Operation",
                ["Charge", "Discharge"]
            )
        
        with col2:
            power = st.number_input(
                "Power (kW)",
                min_value=0.0,
                max_value=battery.charge_rate,
                value=battery.charge_rate/2,
                step=0.1
            )
        
        with col3:
            start_time = st.time_input(
                "Start Time",
                value=datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            )
        
        duration = st.slider(
            "Duration (hours)",
            min_value=1,
            max_value=12,
            value=2
        )
        
        if st.form_submit_button("Add Schedule"):
            new_schedule = {
                'operation': operation,
                'power': power,
                'start_time': start_time,
                'duration': duration,
                'status': 'Scheduled'
            }
            st.session_state.battery_schedules.append(new_schedule)
            st.success("Schedule added successfully")
    
    # Display schedules
    if st.session_state.battery_schedules:
        st.markdown("### " + get_text("scheduled_operations"))
        
        # Convert schedules to DataFrame for display
        schedule_data = []
        current_time = datetime.now().time()
        
        for schedule in st.session_state.battery_schedules:
            # Calculate end time
            start_datetime = datetime.combine(datetime.today(), schedule['start_time'])
            end_time = (start_datetime + timedelta(hours=schedule['duration'])).time()
            
            # Update status based on time
            if current_time < schedule['start_time']:
                status = 'Scheduled'
            elif schedule['start_time'] <= current_time <= end_time:
                status = 'In Progress'
            else:
                status = 'Completed'
            
            schedule_data.append({
                'Operation': schedule['operation'],
                'Power (kW)': schedule['power'],
                'Start Time': schedule['start_time'].strftime('%H:%M'),
                'Duration (h)': schedule['duration'],
                'End Time': end_time.strftime('%H:%M'),
                'Status': status
            })
        
        schedule_df = pd.DataFrame(schedule_data)
        st.dataframe(schedule_df, use_container_width=True)
        
        if st.button("Clear All Schedules"):
            st.session_state.battery_schedules = []
            st.success("All schedules cleared")
