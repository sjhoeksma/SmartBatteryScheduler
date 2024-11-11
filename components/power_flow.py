import streamlit as st
import streamlit.components.v1 as components
from utils.translations import get_text
from datetime import datetime
import numpy as np

def create_power_flow_svg(battery, grid_power, home_consumption):
    """Create SVG-based power flow visualization"""
    battery_power = battery.get_current_power()
    battery_percentage = (battery.current_soc - battery.min_soc) / (battery.max_soc - battery.min_soc) * 100
    
    # Create HTML wrapper with SVG content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            .svg-container {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                height: 100%;
            }
            @keyframes flowAnimation {
                0% { stroke-dashoffset: 20; }
                100% { stroke-dashoffset: 0; }
            }
            .flow-line {
                stroke-dasharray: 4 2;
                animation: flowAnimation 1s linear infinite;
            }
            .power-value { 
                font-family: Arial; 
                font-size: 14px; 
                fill: white;
                text-anchor: middle;
                dominant-baseline: middle;
            }
            .icon-label { 
                font-family: Arial; 
                font-size: 14px; 
                fill: #333;
                text-anchor: middle;
            }
            .icon-circle {
                stroke-width: 2;
                stroke: rgba(0,0,0,0.1);
            }
            .value-circle {
                fill-opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="svg-container">
            <svg width="800" height="400" xmlns="http://www.w3.org/2000/svg">
    """
    
    # Add Grid Icon (left)
    html_content += f"""
                <g transform="translate(200,200)">
                    <circle class="icon-circle" cx="0" cy="0" r="40" fill="#3366cc"/>
                    <path d="M-15,-25 L15,-25 M0,-25 L0,25 M-15,0 L15,0 M-15,25 L15,25" 
                          stroke="white" stroke-width="3"/>
                    <text class="icon-label" y="70">{get_text("grid_power")}</text>
                    <circle class="value-circle" cx="0" cy="90" r="25" fill="#3366cc"/>
                    <text class="power-value" y="90">{abs(grid_power):.1f}</text>
                    <text class="power-value" y="90" dx="35" fill="#666">kW</text>
                </g>
    """

    # Add House Icon (center)
    html_content += f"""
                <g transform="translate(400,200)">
                    <circle class="icon-circle" cx="0" cy="0" r="40" fill="#ff9900"/>
                    <path d="M-20,15 L-20,-5 L0,-25 L20,-5 L20,15 Z M-10,15 L-10,5 L10,5 L10,15" 
                          fill="white"/>
                    <text class="icon-label" y="70">{get_text("home_consumption")}</text>
                    <circle class="value-circle" cx="0" cy="90" r="25" fill="#ff9900"/>
                    <text class="power-value" y="90">{home_consumption:.1f}</text>
                    <text class="power-value" y="90" dx="35" fill="#666">kW</text>
                </g>
    """

    # Add Battery Icon (right)
    html_content += f"""
                <g transform="translate(600,200)">
                    <circle class="icon-circle" cx="0" cy="0" r="40" fill="#00cc66"/>
                    <rect x="-15" y="-20" width="30" height="40" fill="white" rx="2"/>
                    <rect x="-10" y="-25" width="20" height="5" fill="white"/>
                    <rect x="-12" y="-17" width="24" height="{34 * (100 - battery_percentage) / 100}" 
                          fill="#00cc66"/>
                    <text class="icon-label" y="70">{get_text("battery_power")}</text>
                    <circle class="value-circle" cx="0" cy="90" r="25" fill="#00cc66"/>
                    <text class="power-value" y="90">{abs(battery_power):.1f}</text>
                    <text class="power-value" y="90" dx="35" fill="#666">kW</text>
                </g>

                <!-- Flow Lines -->
    """

    # Add Flow Lines based on power flow direction
    if battery_power > 0:  # Charging battery
        html_content += """
                <path class="flow-line" d="M240,200 C320,200 380,200 560,200" 
                      stroke="#3366cc" stroke-width="3"/>
                <path d="M540,195 L560,200 L540,205" fill="#3366cc" stroke="#3366cc" stroke-width="2"/>
        """
    elif battery_power < 0:  # Discharging battery
        html_content += """
                <path class="flow-line" d="M560,200 C480,200 420,200 440,200" 
                      stroke="#00cc66" stroke-width="3"/>
                <path d="M420,195 L440,200 L420,205" fill="#00cc66" stroke="#00cc66" stroke-width="2"/>
        """

    if grid_power > 0:  # Grid supplying power
        html_content += """
                <path class="flow-line" d="M240,200 C320,200 320,200 360,200" 
                      stroke="#3366cc" stroke-width="3"/>
                <path d="M340,195 L360,200 L340,205" fill="#3366cc" stroke="#3366cc" stroke-width="2"/>
        """

    # Close SVG and HTML
    html_content += """
            </svg>
        </div>
    </body>
    </html>
    """
    
    return html_content

def render_power_flow(battery):
    """Main function to render power flow visualization"""
    try:
        st.subheader(get_text("power_flow_visualization"))
        
        # Create containers for the visualization and metrics
        viz_container = st.container()
        metrics_container = st.container()
        
        with viz_container:
            # Simulate real-time values for demonstration
            grid_power = np.sin(datetime.now().timestamp() / 10) * 2 + 3
            home_consumption = abs(np.sin(datetime.now().timestamp() / 10 + 1)) * 1.5 + 1
            
            # Create and display HTML visualization
            html_content = create_power_flow_svg(battery, grid_power, home_consumption)
            components.html(html_content, height=450, scrolling=False)
        
        with metrics_container:
            # Add metrics below the visualization
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(get_text("grid_power"), f"{grid_power:.1f} kW")
            with col2:
                st.metric(get_text("home_consumption"), f"{home_consumption:.1f} kW")
            with col3:
                st.metric(get_text("battery_power"), f"{battery.get_current_power():.1f} kW")
        
        # Add auto-refresh using empty placeholder
        st.empty()
        
    except Exception as e:
        st.error(f"Error rendering power flow visualization: {str(e)}")
        raise e  # Re-raise the exception for debugging
