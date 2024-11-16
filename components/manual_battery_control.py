import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from utils.translations import get_text
from utils.object_store import ObjectStore

def render_schedule_timeline(schedules):
    """Render a visual timeline of scheduled operations"""
    if not schedules:
        st.info("No scheduled operations")
        return

    # Create figure
    fig = go.Figure()

    # Sort schedules by start time
    schedules = sorted(schedules, key=lambda x: x['start_time'])

    # Add bars for each schedule
    for schedule in schedules:
        start_time = schedule['start_time']
        end_time = start_time + timedelta(hours=schedule['duration'])
        operation = schedule['operation']
        power = schedule['power']
        status = schedule.get('status', 'scheduled')

        # Set color and opacity based on operation type and status
        if operation == 'charge':
            color = 'rgba(52, 152, 219, {})'  # Blue
        else:
            color = 'rgba(231, 76, 60, {})'  # Red

        # Set opacity based on status
        if status == 'completed':
            opacity = 0.4
        elif status == 'in_progress':
            opacity = 0.7
        else:  # scheduled
            opacity = 1.0

        # Add bar
        fig.add_trace(go.Bar(
            x=[start_time],
            y=[abs(power)],
            width=[schedule['duration'] * 3600000],  # Convert hours to milliseconds
            name=f"{operation.title()} ({status})",
            marker_color=color.format(opacity),
            hovertemplate=(
                f"Operation: {operation.title()}<br>"
                f"Power: {abs(power):.1f} kW<br>"
                f"Start: %{x}<br>"
                f"Duration: {schedule['duration']} hours<br>"
                f"Status: {status.title()}"
            )
        ))

    # Update layout
    fig.update_layout(
        title="Scheduled Operations Timeline",
        xaxis_title="Time",
        yaxis_title="Power (kW)",
        barmode='overlay',
        showlegend=True,
        height=400,
        xaxis=dict(
            type='date',
            tickformat='%H:%M\n%Y-%m-%d',
            tickangle=-45
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def render_manual_battery_control(battery, prices=None, schedule=None, predicted_soc=None, consumption_stats=None):
    """Render manual battery control interface with schedule management"""
    st.subheader(get_text("manual_control"))
    
    # Initialize object store
    store = ObjectStore()
    
    # Create tabs for immediate control and schedule management
    tab1, tab2 = st.tabs([get_text("immediate_control"), get_text("schedule_control")])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            charge_power = st.number_input(
                get_text("charge_power_kw"),
                min_value=0.0,
                max_value=battery.charge_rate,
                value=battery.charge_rate / 2,
                step=0.1
            )
            
            if st.button(get_text("start_charging")):
                if battery.charge(charge_power):
                    st.success(get_text("charging_started"))
                else:
                    if not battery.can_charge(charge_power):
                        st.error(get_text("capacity_limit_reached"))
                    else:
                        st.error(get_text("charge_failed"))
        
        with col2:
            discharge_power = st.number_input(
                get_text("discharge_power_kw"),
                min_value=0.0,
                max_value=battery.charge_rate,
                value=battery.charge_rate / 2,
                step=0.1
            )
            
            if st.button(get_text("start_discharging")):
                if battery.discharge(discharge_power):
                    st.success("Discharging started successfully")
                else:
                    if not battery.can_discharge(discharge_power):
                        st.error(get_text("minimum_soc_reached"))
                    else:
                        st.error(get_text("discharge_failed"))
    
    with tab2:
        # Schedule Form
        with st.form("schedule_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                operation = st.selectbox(
                    get_text("operation"),
                    ['charge', 'discharge'],
                    format_func=lambda x: get_text(f"operation_{x}")
                )
            
            with col2:
                power = st.number_input(
                    get_text("power_kw"),
                    min_value=0.1,
                    max_value=battery.charge_rate,
                    value=battery.charge_rate / 2,
                    step=0.1
                )
            
            with col3:
                start_time = st.time_input(
                    get_text("start_time"),
                    value=datetime.now().time()
                )
            
            duration = st.slider(
                get_text("duration_hours"),
                min_value=1,
                max_value=12,
                value=2
            )
            
            if st.form_submit_button(get_text("add_schedule")):
                # Convert time to datetime
                now = datetime.now()
                start_datetime = datetime.combine(now.date(), start_time)
                
                # If the time is earlier than now, schedule for tomorrow
                if start_datetime < now:
                    start_datetime += timedelta(days=1)
                
                # Create schedule
                schedule_entry = {
                    'operation': operation,
                    'power': power if operation == 'charge' else -power,
                    'start_time': start_datetime.replace(tzinfo=pytz.UTC),
                    'duration': duration,
                    'status': 'scheduled'
                }
                
                try:
                    store.save_schedule(schedule_entry)
                    st.success(f"Added {operation} schedule starting at {start_time}")
                except Exception as e:
                    st.error(f"Failed to save schedule: {str(e)}")
        
        # Display current schedules
        st.subheader(get_text("scheduled_operations"))
        schedules = store.load_schedules()
        
        # Render timeline visualization
        render_schedule_timeline(schedules)
        
        # Add clear schedules button
        if st.button(get_text("clear_all_schedules")):
            store.clear_schedules()
            st.success(get_text("schedules_cleared"))
            st.rerun()
