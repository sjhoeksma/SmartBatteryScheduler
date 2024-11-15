import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.translations import get_text
from components.price_chart import render_price_chart
from utils.object_store import ObjectStore

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
            new_schedule = {
                'operation': operation,
                'power': power,
                'start_time': start_time,
                'duration': duration,
                'status': 'Manual'
            }
            st.session_state.store.save_schedule(new_schedule)
            st.session_state.battery_schedules = st.session_state.store.load_schedules()
            st.success(get_text("schedule_added"))
    
    # Display schedules
    if st.session_state.battery_schedules or (schedule is not None and prices is not None):
        st.markdown("### " + get_text("scheduled_operations"))
        
        schedule_data = []
        current_time = datetime.now()
        
        # Process manual schedules
        for schedule_entry in st.session_state.battery_schedules:
            start_datetime = schedule_entry['start_time']
            end_datetime = start_datetime + timedelta(hours=schedule_entry['duration'])
            
            status = get_text("scheduled")
            if current_time > end_datetime:
                status = get_text("completed")
            elif current_time >= start_datetime:
                status = get_text("in_progress")
            
            schedule_data.append({
                get_text("operation"): schedule_entry['operation'],
                get_text("power_kw"): schedule_entry['power'],
                get_text("start_time"): start_datetime.strftime('%H:%M'),
                get_text("duration_hours"): schedule_entry['duration'],
                'End Time': end_datetime.strftime('%H:%M'),
                'Status': status,
                'Type': 'Manual'
            })
        
        # Process optimization schedule if available
        if schedule is not None and prices is not None:
            current_operation = None
            start_idx = 0
            power_threshold = 0.1  # Minimum power threshold (kW)
            
            for i, power in enumerate(schedule):
                if abs(power) > power_threshold:
                    # New operation starts or operation type changes
                    if current_operation is None or (power > 0) != (current_operation['power'] > 0):
                        # Add previous operation if exists and power is significant
                        if current_operation is not None and abs(current_operation['power']) > power_threshold:
                            duration = i - start_idx
                            if duration > 0:  # Only add if duration is positive
                                start_time = prices.index[start_idx]
                                end_time = prices.index[min(start_idx + duration - 1, len(prices.index) - 1)]
                                
                                schedule_data.append({
                                    get_text("operation"): get_text("operation_charge") if power > 0 
                                                      else get_text("operation_discharge"),
                                    get_text("power_kw"): abs(current_operation['power']),
                                    get_text("start_time"): start_time.strftime('%H:%M'),
                                    get_text("duration_hours"): duration,
                                    'End Time': end_time.strftime('%H:%M'),
                                    'Status': 'Optimized',
                                    'Type': 'Optimized'
                                })
                        
                        # Start new operation
                        current_operation = {'power': power}
                        start_idx = i
                elif current_operation is not None:
                    # End current operation if power drops below threshold
                    duration = i - start_idx
                    if duration > 0 and abs(current_operation['power']) > power_threshold:
                        start_time = prices.index[start_idx]
                        end_time = prices.index[min(start_idx + duration - 1, len(prices.index) - 1)]
                        
                        schedule_data.append({
                            get_text("operation"): get_text("operation_charge") if current_operation['power'] > 0 
                                              else get_text("operation_discharge"),
                            get_text("power_kw"): abs(current_operation['power']),
                            get_text("start_time"): start_time.strftime('%H:%M'),
                            get_text("duration_hours"): duration,
                            'End Time': end_time.strftime('%H:%M'),
                            'Status': 'Optimized',
                            'Type': 'Optimized'
                        })
                    current_operation = None
            
            # Add last operation if exists and power is significant
            if current_operation is not None and abs(current_operation['power']) > power_threshold:
                duration = len(schedule) - start_idx
                if duration > 0:  # Only add if duration is positive
                    start_time = prices.index[start_idx]
                    end_time = prices.index[min(start_idx + duration - 1, len(prices.index) - 1)]
                    
                    schedule_data.append({
                        get_text("operation"): get_text("operation_charge") if current_operation['power'] > 0 
                                          else get_text("operation_discharge"),
                        get_text("power_kw"): abs(current_operation['power']),
                        get_text("start_time"): start_time.strftime('%H:%M'),
                        get_text("duration_hours"): duration,
                        'End Time': end_time.strftime('%H:%M'),
                        'Status': 'Optimized',
                        'Type': 'Optimized'
                    })
        
        if schedule_data:
            schedule_df = pd.DataFrame(schedule_data)
            st.dataframe(schedule_df, use_container_width=True)
            
            if st.button(get_text("clear_all_schedules")):
                st.session_state.store.clear_schedules()
                st.session_state.battery_schedules = []
                st.success(get_text("schedules_cleared"))