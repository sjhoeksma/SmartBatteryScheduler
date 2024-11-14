import streamlit as st
import plotly.graph_objects as go
from utils.battery_profiles import BatteryProfile, BatteryProfileManager
from utils.battery import Battery
from utils.translations import get_text

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
    # Initialize profile manager in session state if not exists
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = BatteryProfileManager()
    
    # Profile selection
    profiles = st.session_state.profile_manager.list_profiles()
    current_profile = st.selectbox(
        get_text("battery_profile"),
        profiles,
        index=profiles.index(getattr(st.session_state.battery, 'profile_name', profiles[0]))
    )
    
    # Load selected profile
    profile = st.session_state.profile_manager.get_profile(current_profile)
    
    with st.form("battery_config"):
        col1, col2 = st.columns(2)
        
        with col1:
            capacity = st.number_input(
                get_text("battery_capacity"),
                min_value=1.0,
                max_value=100.0,
                value=float(profile.capacity if profile else st.session_state.battery.capacity)
            )
            
            min_soc = st.slider(
                get_text("min_soc"),
                min_value=0.0,
                max_value=0.5,
                value=float(profile.min_soc if profile else st.session_state.battery.min_soc)
            )
            
            max_soc = st.slider(
                get_text("max_soc"),
                min_value=0.5,
                max_value=1.0,
                value=float(profile.max_soc if profile else st.session_state.battery.max_soc)
            )
            
            charge_rate = st.number_input(
                get_text("charge_rate"),
                min_value=1.0,
                max_value=22.0,
                value=float(profile.charge_rate if profile else st.session_state.battery.charge_rate)
            )
        
        with col2:
            yearly_consumption = st.number_input(
                get_text("yearly_consumption"),
                min_value=1000.0,
                max_value=20000.0,
                value=float(profile.yearly_consumption if profile else st.session_state.battery.yearly_consumption),
                help=get_text("total_yearly_consumption")
            )
            
            daily_consumption = st.number_input(
                get_text("daily_consumption"),
                min_value=1.0,
                max_value=100.0,
                value=float(profile.daily_consumption if profile else st.session_state.battery.daily_consumption),
                help=get_text("consumption_help")
            )
            
            usage_pattern = st.selectbox(
                get_text("usage_pattern"),
                ["Flat", "Day-heavy", "Night-heavy"],
                index=["Flat", "Day-heavy", "Night-heavy"].index(
                    profile.usage_pattern if profile else st.session_state.battery.usage_pattern
                )
            )
            
            surcharge_rate = st.number_input(
                "Surcharge Rate (€/kWh)",
                min_value=0.0,
                max_value=0.5,
                value=float(profile.surcharge_rate if profile else st.session_state.battery.surcharge_rate),
                step=0.01,
                help="Additional cost applied to energy prices"
            )
        
        # Show monthly distribution visualization
        st.plotly_chart(render_monthly_distribution(
            profile.monthly_distribution if profile else st.session_state.battery.monthly_distribution
        ), use_container_width=True)
        
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
                monthly_distribution=profile.monthly_distribution if profile else None,
                surcharge_rate=surcharge_rate
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
                    surcharge_rate=st.session_state.battery.surcharge_rate
                )
                st.session_state.profile_manager.add_profile(new_profile)
                st.success(get_text("profile_created").format(new_name))
            else:
                st.error(get_text("provide_unique_name"))