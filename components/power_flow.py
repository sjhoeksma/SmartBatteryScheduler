import streamlit as st
import plotly.graph_objects as go
from utils.translations import get_text
import numpy as np

def create_power_flow_sankey(battery, grid_power, home_consumption):
    """Create a Sankey diagram showing power flow between grid, battery, and home"""
    # Calculate power flows
    battery_power = battery.get_current_power()  # Positive for charging, negative for discharging
    
    # Define node labels and colors
    nodes = ["Grid", "Battery", "Home"]
    node_colors = ["#3366cc", "#dc3912", "#ff9900"]
    
    # Initialize links
    source = []
    target = []
    value = []
    color = []
    
    # Grid to Battery flow (charging)
    if battery_power > 0:
        source.append(0)  # Grid
        target.append(1)  # Battery
        value.append(abs(battery_power))
        color.append("#3366cc")
    
    # Battery to Home flow (discharging)
    if battery_power < 0:
        source.append(1)  # Battery
        target.append(2)  # Home
        value.append(abs(battery_power))
        color.append("#dc3912")
    
    # Grid to Home flow (direct consumption)
    grid_to_home = max(0, home_consumption - abs(min(0, battery_power)))
    if grid_to_home > 0:
        source.append(0)  # Grid
        target.append(2)  # Home
        value.append(grid_to_home)
        color.append("#ff9900")
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=color
        )
    )])
    
    fig.update_layout(
        title=get_text("power_flow_title"),
        font_size=12,
        height=400
    )
    
    return fig

def render_power_flow_metrics(battery, grid_power, home_consumption):
    """Render key metrics for power flow"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            get_text("grid_power"),
            f"{grid_power:.2f} kW",
            delta=f"{grid_power - home_consumption:.2f} kW"
        )
    
    with col2:
        battery_power = battery.get_current_power()
        st.metric(
            get_text("battery_power"),
            f"{battery_power:.2f} kW",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            get_text("home_consumption"),
            f"{home_consumption:.2f} kW",
            delta=None
        )

def render_power_flow(battery):
    """Main function to render power flow visualization"""
    st.subheader(get_text("power_flow_visualization"))
    
    # Simulate some real-time values for demonstration
    # In a real implementation, these would come from actual measurements
    grid_power = np.sin(np.datetime64('now').astype(float) / 1e11) * 2 + 3  # Simulated grid power
    home_consumption = abs(np.sin(np.datetime64('now').astype(float) / 1e11 + 1)) * 1.5 + 1  # Simulated consumption
    
    # Create and display Sankey diagram
    fig = create_power_flow_sankey(battery, grid_power, home_consumption)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display metrics
    render_power_flow_metrics(battery, grid_power, home_consumption)
    
    # Add auto-refresh
    st.empty()  # This will trigger a refresh of the component
