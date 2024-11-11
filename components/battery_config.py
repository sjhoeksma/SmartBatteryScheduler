import streamlit as st
from utils.battery_profiles import BatteryProfile, BatteryProfileManager
from utils.battery import Battery

def render_battery_config():
    """Render battery configuration controls"""
    # Initialize profile manager in session state if not exists
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = BatteryProfileManager()
    
    # Profile selection
    profiles = st.session_state.profile_manager.list_profiles()
    current_profile = st.selectbox(
        "Battery Profile",
        profiles,
        index=profiles.index(getattr(st.session_state.battery, 'profile_name', profiles[0]))
    )
    
    # Load selected profile
    profile = st.session_state.profile_manager.get_profile(current_profile)
    
    with st.form("battery_config"):
        capacity = st.number_input(
            "Battery Capacity (kWh)",
            min_value=1.0,
            max_value=100.0,
            value=float(profile.capacity if profile else st.session_state.battery.capacity)
        )
        
        min_soc = st.slider(
            "Minimum State of Charge",
            min_value=0.0,
            max_value=0.5,
            value=float(profile.min_soc if profile else st.session_state.battery.min_soc)
        )
        
        max_soc = st.slider(
            "Maximum State of Charge",
            min_value=0.5,
            max_value=1.0,
            value=float(profile.max_soc if profile else st.session_state.battery.max_soc)
        )
        
        charge_rate = st.number_input(
            "Maximum Charge Rate (kW)",
            min_value=1.0,
            max_value=22.0,
            value=float(profile.charge_rate if profile else st.session_state.battery.charge_rate)
        )
        
        # Add home usage settings
        daily_consumption = st.number_input(
            "Daily Consumption (kWh)",
            min_value=1.0,
            max_value=100.0,
            value=float(profile.daily_consumption if profile else st.session_state.battery.daily_consumption)
        )
        
        usage_pattern = st.selectbox(
            "Usage Pattern",
            ["Flat", "Day-heavy", "Night-heavy"],
            index=["Flat", "Day-heavy", "Night-heavy"].index(
                profile.usage_pattern if profile else st.session_state.battery.usage_pattern
            )
        )
        
        if st.form_submit_button("Update Configuration"):
            # Update battery with new configuration
            st.session_state.battery = Battery(
                capacity=capacity,
                min_soc=min_soc,
                max_soc=max_soc,
                charge_rate=charge_rate,
                profile_name=current_profile,
                daily_consumption=daily_consumption,
                usage_pattern=usage_pattern
            )
            st.success("Battery configuration updated!")
    
    # New profile creation
    st.markdown("### Create New Profile")
    with st.form("new_profile"):
        new_name = st.text_input("Profile Name")
        if st.form_submit_button("Create Profile"):
            if new_name and new_name not in profiles:
                new_profile = BatteryProfile(
                    name=new_name,
                    capacity=st.session_state.battery.capacity,
                    min_soc=st.session_state.battery.min_soc,
                    max_soc=st.session_state.battery.max_soc,
                    charge_rate=st.session_state.battery.charge_rate,
                    daily_consumption=st.session_state.battery.daily_consumption,
                    usage_pattern=st.session_state.battery.usage_pattern
                )
                st.session_state.profile_manager.add_profile(new_profile)
                st.success(f"Created new profile: {new_name}")
            else:
                st.error("Please provide a unique profile name")
