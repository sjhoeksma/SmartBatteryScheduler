import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from utils.translations import get_text
from components.price_chart import render_price_chart
from utils.object_store import ObjectStore

def render_schedule_timeline(schedule_df):
    """Render a visual timeline of scheduled operations"""
    if schedule_df.empty:
        return None
        
    fig = go.Figure()
    
    # Define colors for different operations and status
    colors = {
        'charge': {
            'scheduled': 'rgb(52, 152, 219)',
            'in_progress': 'rgb(41, 128, 185)',
            'completed': 'rgb(33, 97, 140)',
            'optimized': 'rgb(52, 152, 219)'  # Added optimized status
        },
        'discharge': {
            'scheduled': 'rgb(231, 76, 60)',
            'in_progress': 'rgb(192, 57, 43)',
            'completed': 'rgb(146, 43, 33)',
            'optimized': 'rgb(231, 76, 60)'  # Added optimized status
        }
    }
    
    # Convert operation names to standardized format
    operation_map = {
        get_text('operation_charge'): 'charge',
        get_text('operation_discharge'): 'discharge'
    }
    
    for idx, row in schedule_df.iterrows():
        operation = operation_map.get(row[get_text('operation')], 'charge')
        start_time = pd.to_datetime(row[get_text('start_time')])
        duration = row[get_text('duration_hours')]
        end_time = start_time + pd.Timedelta(hours=duration)
        status = row['Status'].lower()
        power = row[get_text('power_kw')]
        
        color = colors[operation][status]
        
        # Create hover text
        hover_text = (
            f"Operation: {row[get_text('operation')]}<br>"
            f"Power: {power:.1f} kW<br>"
            f"Start: {start_time.strftime('%Y-%m-%d %H:%M')}<br>"
            f"Duration: {duration}h<br>"
            f"Status: {row['Status']}<br>"
            f"Type: {row['Type']}"
        )
        
        fig.add_trace(go.Bar(
            name=row[get_text('operation')],
            x=[start_time],
            y=[power],
            width=duration * 3600000,  # Convert hours to milliseconds
            marker_color=color,
            text=f"{power:.1f}kW",
            textposition='auto',
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))
    
    # Update layout
    fig.update_layout(
        title=get_text("scheduled_operations"),
        xaxis=dict(
            title="Time",
            type='date',
            tickformat="%Y-%m-%d %H:%M",
            tickangle=-45
        ),
        yaxis=dict(
            title="Power (kW)",
            range=[
                -max(abs(schedule_df[get_text('power_kw')])) * 1.1,
                max(abs(schedule_df[get_text('power_kw')])) * 1.1
            ]
        ),
        barmode='overlay',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Add legend for status colors
    for operation in ['charge', 'discharge']:
        for status in ['scheduled', 'in_progress', 'completed', 'optimized']:
            fig.add_trace(go.Bar(
                x=[None],
                y=[None],
                name=f"{operation.title()} - {status.title()}",
                marker_color=colors[operation][status],
                showlegend=True
            ))
    
    return fig

def render_manual_battery_control(battery, prices=None, schedule=None, predicted_soc=None, consumption_stats=None):
    """Render manual battery control interface with scheduling"""
    st.subheader(get_text("manual_control"))
    
    # Initialize store if not exists
    if 'store' not in st.session_state:
        st.session_state.store = ObjectStore()
    
    # Initialize session state for schedules if not exists
    if 'battery_schedules' not in st.session_state:
        st.session_state.battery_schedules = st.session_state.store.load_schedules()
    
    # Display prediction chart if data is available
    if prices is not None:
        st.markdown("### " + get_text("price_and_prediction"))
        render_price_chart(prices, schedule, predicted_soc, consumption_stats)
    
    # Display current battery status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(get_text("current_soc"), f"{battery.current_soc*100:.1f}%")
    with col2:
        st.metric(get_text("available_capacity"), f"{battery.get_available_capacity():.1f} kWh")
    with col3:
        current_power = battery.get_current_power()
        st.metric(get_text("battery_power"), 
                 f"{abs(current_power):.1f} kW",
                 delta=get_text("charging") if current_power > 0 else get_text("discharging") if current_power < 0 else "Idle")
    
    # Immediate control section
    st.markdown("### " + get_text("immediate_control"))
    
    col1, col2 = st.columns(2)
    with col1:
        charge_power = st.number_input(
            get_text("charge_power_kw"),
            min_value=0.0,
            max_value=battery.charge_rate,
            value=battery.charge_rate/2,
            step=0.1
        )
        if st.button(get_text("start_charging")):
            if battery.can_charge(charge_power):
                if battery.charge(charge_power):
                    st.success(get_text("charging_started"))
                else:
                    st.error(get_text("charge_failed"))
            else:
                st.error(get_text("capacity_limit_reached"))
    
    with col2:
        discharge_power = st.number_input(
            get_text("discharge_power_kw"),
            min_value=0.0,
            max_value=battery.charge_rate,
            value=battery.charge_rate/2,
            step=0.1
        )
        if st.button(get_text("start_discharging")):
            if battery.can_discharge(discharge_power):
                if battery.discharge(discharge_power):
                    st.success(get_text("discharging_started"))
                else:
                    st.error(get_text("discharge_failed"))
            else:
                st.error(get_text("minimum_soc_reached"))
    
    # Schedule section
    st.markdown("### " + get_text("schedule_control"))
    
    # Add new schedule
    with st.form("add_schedule"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            operation = st.selectbox(
                get_text("operation"),
                [get_text("operation_charge"), get_text("operation_discharge")]
            )
        
        with col2:
            power = st.number_input(
                get_text("power_kw"),
                min_value=0.0,
                max_value=battery.charge_rate,
                value=battery.charge_rate/2,
                step=0.1
            )
        
        with col3:
            start_time = st.time_input(
                get_text("start_time"),
                value=datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            )
        
        duration = st.slider(
            get_text("duration_hours"),
            min_value=1,
            max_value=12,
            value=2
        )
        
        if st.form_submit_button(get_text("add_schedule")):
            # Create datetime with proper timezone
            today = datetime.now(timezone.utc).date()
            start_datetime = datetime.combine(today, start_time).replace(tzinfo=timezone.utc)
            
            # If start time is earlier than current time, schedule for tomorrow
            current_time = datetime.now(timezone.utc)
            if start_datetime <= current_time:
                start_datetime += timedelta(days=1)
            
            new_schedule = {
                'operation': operation,
                'power': power,
                'start_time': start_datetime,
                'duration': duration,
                'status': 'Manual'
            }
            st.session_state.store.save_schedule(new_schedule)
            st.session_state.battery_schedules = st.session_state.store.load_schedules()
            st.success("Schedule added successfully!")
    
    # Process all schedules (manual and optimized)
    schedule_data = []
    current_time = datetime.now(timezone.utc)
    
    # Process manual schedules
    manual_schedules = st.session_state.battery_schedules
    for idx, schedule_entry in enumerate(manual_schedules):
        start_datetime = schedule_entry['start_time']
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        end_datetime = start_datetime + timedelta(hours=schedule_entry['duration'])
        
        status = get_text("scheduled")
        if current_time > end_datetime:
            status = get_text("completed")
        elif current_time >= start_datetime:
            status = get_text("in_progress")
        
        schedule_data.append({
            'idx': idx,  # Store original index for deletion
            get_text("operation"): schedule_entry['operation'],
            get_text("power_kw"): schedule_entry['power'],
            get_text("start_time"): start_datetime.strftime('%Y-%m-%d %H:%M'),
            get_text("duration_hours"): schedule_entry['duration'],
            'End Time': end_datetime.strftime('%Y-%m-%d %H:%M'),
            'Status': status,
            'Type': 'Manual'
        })
    
    # Process optimization schedule if available
    if schedule is not None and prices is not None:
        current_operation = None
        start_idx = 0
        power_threshold = 0.1  # Increased threshold for more accurate detection
        min_duration = 1  # Minimum duration to consider as an operation
        
        for i, power in enumerate(schedule):
            if abs(power) > power_threshold:
                # Start new operation or update existing
                if current_operation is None:
                    current_operation = {'power': power, 'start_idx': i}
                elif (power > 0) != (current_operation['power'] > 0):
                    # Different operation type, add previous and start new
                    duration = i - current_operation['start_idx']
                    if duration >= min_duration:
                        start_time = prices.index[current_operation['start_idx']]
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)
                        
                        schedule_data.append({
                            'idx': None,
                            get_text('operation'): get_text('operation_charge') if current_operation['power'] > 0 
                                        else get_text('operation_discharge'),
                            get_text('power_kw'): abs(current_operation['power']),
                            get_text('start_time'): start_time.strftime('%Y-%m-%d %H:%M'),
                            get_text('duration_hours'): duration,
                            'End Time': (start_time + timedelta(hours=duration)).strftime('%Y-%m-%d %H:%M'),
                            'Status': 'Optimized',
                            'Type': 'Optimized'
                        })
                    current_operation = {'power': power, 'start_idx': i}
                else:
                    # Same operation type, update average power
                    current_operation['power'] = (current_operation['power'] * (i - current_operation['start_idx']) + power) / (i - current_operation['start_idx'] + 1)
            elif current_operation is not None:
                # Power below threshold, end current operation
                duration = i - current_operation['start_idx']
                if duration >= min_duration:
                    start_time = prices.index[current_operation['start_idx']]
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    
                    schedule_data.append({
                        'idx': None,
                        get_text('operation'): get_text('operation_charge') if current_operation['power'] > 0 
                                    else get_text('operation_discharge'),
                        get_text('power_kw'): abs(current_operation['power']),
                        get_text('start_time'): start_time.strftime('%Y-%m-%d %H:%M'),
                        get_text('duration_hours'): duration,
                        'End Time': (start_time + timedelta(hours=duration)).strftime('%Y-%m-%d %H:%M'),
                        'Status': 'Optimized',
                        'Type': 'Optimized'
                    })
                current_operation = None
                
        # Handle last operation if exists
        if current_operation is not None:
            duration = len(schedule) - current_operation['start_idx']
            if duration >= min_duration:
                start_time = prices.index[current_operation['start_idx']]
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                
                schedule_data.append({
                    'idx': None,
                    get_text('operation'): get_text('operation_charge') if current_operation['power'] > 0 
                                else get_text('operation_discharge'),
                    get_text('power_kw'): abs(current_operation['power']),
                    get_text('start_time'): start_time.strftime('%Y-%m-%d %H:%M'),
                    get_text('duration_hours'): duration,
                    'End Time': (start_time + timedelta(hours=duration)).strftime('%Y-%m-%d %H:%M'),
                    'Status': 'Optimized',
                    'Type': 'Optimized'
                })
    
    # Create DataFrame and sort schedules
    if schedule_data:
        schedule_df = pd.DataFrame(schedule_data)
        schedule_df['start_time_dt'] = pd.to_datetime(schedule_df[get_text('start_time')])
        schedule_df = schedule_df.sort_values('start_time_dt')
        
        # Render timeline visualization
        timeline_fig = render_schedule_timeline(schedule_df)
        if timeline_fig:
            st.plotly_chart(timeline_fig, use_container_width=True)
        
        # Display schedules in a table
        display_df = schedule_df[[
            get_text('operation'),
            get_text('power_kw'),
            get_text('start_time'),
            get_text('duration_hours'),
            'End Time',
            'Status',
            'Type'
        ]].copy()
        
        st.dataframe(display_df, hide_index=True)
        
        # Add delete buttons for manual schedules
        manual_schedules = schedule_df[schedule_df['Type'] == 'Manual']
        if not manual_schedules.empty:
            st.markdown("#### Manage Manual Schedules")
            for _, row in manual_schedules.iterrows():
                col1, col2 = st.columns([0.9, 0.1])
                with col1:
                    st.write(f"{row[get_text('operation')]} - {row[get_text('power_kw')]}kW - {row[get_text('start_time')]} ({row[get_text('duration_hours')]}h)")
                with col2:
                    if st.button('🗑️', key=f'delete_{row["idx"]}'):
                        st.session_state.store.remove_schedule(int(row['idx']))
                        st.session_state.battery_schedules = st.session_state.store.load_schedules()
                        st.rerun()
            
            if st.button(get_text("clear_all_schedules")):
                st.session_state.store.clear_schedules()
                st.session_state.battery_schedules = []
                st.success(get_text("schedules_cleared"))
                st.rerun()