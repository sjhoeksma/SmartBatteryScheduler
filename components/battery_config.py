import streamlit as st
import plotly.graph_objects as go
from utils.battery_profiles import BatteryProfile
from utils.battery import Battery
from utils.translations import get_text
from utils.object_store import ObjectStore

def render_monthly_distribution(monthly_distribution):
    """Render monthly distribution visualization"""
    months = list(range(1, 13))
    factors = [monthly_distribution[m] for m in months]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months,
        y=factors,
        name=get_text("monthly_distribution_title"),
        marker_color="blue"
    ))
    
    fig.update_layout(
        title=get_text("monthly_distribution_title"),
        xaxis_title=get_text("month"),
        yaxis_title=get_text("consumption_factor"),
        xaxis=dict(tickmode='array', ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                  tickvals=months)
    )
    return fig

def render_battery_config():
    """Render battery configuration controls"""
    # Initialize object store in session state if not exists
    if 'store' not in st.session_state:
        st.session_state.store = ObjectStore()
    
    # Profile selection
    profiles = st.session_state.store.list_profiles()
    if not profiles:
        st.warning("No battery profiles found. Creating default profile...")
        st.rerun()
        return
    
    # Get current profile name or use "Home Battery" as default
    current_profile_name = getattr(st.session_state.battery, 'profile_name', "Home Battery")
    if current_profile_name not in profiles:
        current_profile_name = "Home Battery"
    
    # Profile selection with delete button
    col1, col2 = st.columns([3, 1])
    with col1:
        current_profile = st.selectbox(
            get_text("battery_profile"),
            profiles,
            index=profiles.index(current_profile_name)
        )
    with col2:
        if st.button("🗑️ Delete Profile", key="delete_profile"):
            if current_profile != "Home Battery":  # Prevent deletion of default profile
                st.session_state.store.remove_profile(current_profile)
                st.rerun()
    
    # Load selected profile
    profile = st.session_state.store.get_profile(current_profile)
    if not profile:
        st.error("Selected profile not found")
        return
    
    with st.form("battery_config"):
        col1, col2 = st.columns(2)
        
        with col1:
            capacity = st.number_input(
                get_text("battery_capacity"),
                min_value=1.0,
                max_value=100.0,
                value=float(profile.capacity)
            )
            
            min_soc = st.slider(
                get_text("min_soc"),
                min_value=0.0,
                max_value=0.5,
                value=float(profile.min_soc)
            )
            
            max_soc = st.slider(
                get_text("max_soc"),
                min_value=0.5,
                max_value=1.0,
                value=float(profile.max_soc)
            )
            
            charge_rate = st.number_input(
                get_text("charge_rate"),
                min_value=1.0,
                max_value=22.0,
                value=float(profile.charge_rate)
            )
        
        with col2:
            yearly_consumption = st.number_input(
                get_text("yearly_consumption"),
                min_value=1000.0,
                max_value=20000.0,
                value=float(profile.yearly_consumption),
                help=get_text("total_yearly_consumption")
            )
            
            daily_consumption = st.number_input(
                get_text("daily_consumption"),
                min_value=1.0,
                max_value=100.0,
                value=float(profile.daily_consumption),
                help=get_text("consumption_help")
            )
            
            usage_pattern = st.selectbox(
                get_text("usage_pattern"),
                ["Flat", "Day-heavy", "Night-heavy"],
                index=["Flat", "Day-heavy", "Night-heavy"].index(profile.usage_pattern)
            )
            
            surcharge_rate = st.number_input(
                "Surcharge Rate (€/kWh)",
                min_value=0.0,
                max_value=0.5,
                value=float(profile.surcharge_rate),
                step=0.001,
                format="%.3f",
                help="Additional cost applied to energy prices"
            )
        
        # Cycle and Event Limits Section
        st.markdown("### Event Limits")
        st.info(get_text('cycle_limits_help'))
        
        # Add maximum daily cycles input
        max_daily_cycles = st.number_input(
            get_text("max_daily_cycles"),
            min_value=0.1,
            max_value=5.0,
            value=float(profile.max_daily_cycles),
            step=0.1,
            format="%.1f"
        )
        
        # Add event limits inputs sequentially
        max_charge_events = st.number_input(
            "Maximum Daily Charge Events",
            min_value=1,
            max_value=10,
            value=int(profile.max_charge_events),
            help="Maximum number of times the battery can start charging per day"
        )
        
        max_discharge_events = st.number_input(
            "Maximum Daily Discharge Events",
            min_value=1,
            max_value=10,
            value=int(profile.max_discharge_events),
            help="Maximum number of times the battery can start discharging per day"
        )
        
        # Show monthly distribution visualization
        st.plotly_chart(render_monthly_distribution(profile.monthly_distribution), use_container_width=True)
        
        if st.form_submit_button("Update Configuration"):
            # Update battery with new configuration
            st.session_state.battery = Battery(
                capacity=capacity,
                min_soc=min_soc,
                max_soc=max_soc,
                charge_rate=charge_rate,
                profile_name=current_profile,
                daily_consumption=daily_consumption,
                usage_pattern=usage_pattern,
                yearly_consumption=yearly_consumption,
                monthly_distribution=profile.monthly_distribution,
                surcharge_rate=round(surcharge_rate, 3),
                max_daily_cycles=max_daily_cycles,
                max_charge_events=max_charge_events,
                max_discharge_events=max_discharge_events
            )
            st.success(get_text("config_updated"))
    
    # New profile creation
    st.markdown(f"### {get_text('create_new_profile')}")
    with st.form("new_profile"):
        new_name = st.text_input(get_text("profile_name"))
        if st.form_submit_button("Create Profile"):
            if new_name and new_name not in profiles:
                new_profile = BatteryProfile(
                    name=new_name,
                    capacity=st.session_state.battery.capacity,
                    min_soc=st.session_state.battery.min_soc,
                    max_soc=st.session_state.battery.max_soc,
                    charge_rate=st.session_state.battery.charge_rate,
                    daily_consumption=st.session_state.battery.daily_consumption,
                    usage_pattern=st.session_state.battery.usage_pattern,
                    yearly_consumption=st.session_state.battery.yearly_consumption,
                    monthly_distribution=st.session_state.battery.monthly_distribution,
                    surcharge_rate=round(st.session_state.battery.surcharge_rate, 3),
                    max_daily_cycles=st.session_state.battery.max_daily_cycles,
                    max_charge_events=st.session_state.battery.max_charge_events,
                    max_discharge_events=st.session_state.battery.max_discharge_events
                )
                st.session_state.store.save_profile(new_profile)
                st.success(get_text("profile_created").format(new_name))
            else:
                st.error(get_text("provide_unique_name"))
