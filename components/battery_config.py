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
        
        if st.form_submit_button("Update Configuration"):
            # Update battery with new configuration
            st.session_state.battery = Battery(
                capacity=capacity,
                min_soc=min_soc,
                max_soc=max_soc,
                charge_rate=charge_rate
            )
            # Store profile name in battery instance
            setattr(st.session_state.battery, 'profile_name', current_profile)
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
                    charge_rate=st.session_state.battery.charge_rate
                )
                st.session_state.profile_manager.add_profile(new_profile)
                st.success(f"Created new profile: {new_name}")
            else:
                st.error("Please provide a unique profile name")
