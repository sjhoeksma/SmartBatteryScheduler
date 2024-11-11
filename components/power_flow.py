import streamlit as st
import streamlit.components.v1 as components
from utils.translations import get_text
from datetime import datetime
import numpy as np

def create_power_flow_svg(battery, grid_power, home_consumption):
    """Create SVG-based power flow visualization"""
    battery_power = battery.get_current_power()
    battery_percentage = (battery.current_soc - battery.min_soc) / (battery.max_soc - battery.min_soc) * 100
    
    # Create HTML wrapper with SVG
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @keyframes flowAnimation {{
                0% {{ stroke-dashoffset: 20; }}
                100% {{ stroke-dashoffset: 0; }}
            }}
            .flow-line {{
                stroke-dasharray: 4 2;
                animation: flowAnimation 1s linear infinite;
            }}
            .power-value {{
                font-family: Arial;
                font-size: 12px;
                fill: #666;
            }}
            .icon-label {{
                font-family: Arial;
                font-size: 14px;
                fill: #333;
                text-anchor: middle;
            }}
        </style>
    </head>
    <body>
        <svg width="800" height="400" xmlns="http://www.w3.org/2000/svg">
            <!-- Grid Icon -->
            <g transform="translate(100,200)">
                <rect x="-30" y="-30" width="60" height="60" fill="#3366cc" rx="5"/>
                <path d="M-15,-15 L15,15 M-15,15 L15,-15" stroke="white" stroke-width="3"/>
                <text class="icon-label" y="50">{get_text("grid_power")}</text>
                <text class="power-value" y="70">{abs(grid_power):.1f} kW</text>
            </g>
            
            <!-- Battery Icon -->
            <g transform="translate(400,200)">
                <rect x="-40" y="-60" width="80" height="120" fill="#dc3912" rx="5"/>
                <rect x="-35" y="-55" width="70" height="{110 * (100 - battery_percentage) / 100}" fill="white"/>
                <rect x="-15" y="-70" width="30" height="10" fill="#dc3912"/>
                <text class="icon-label" y="50">{get_text("battery_power")}</text>
                <text class="power-value" y="70">{abs(battery_power):.1f} kW</text>
                <text class="power-value" y="90">{battery_percentage:.0f}%</text>
            </g>
            
            <!-- House Icon -->
            <g transform="translate(700,200)">
                <path d="M-40,30 L0,-30 L40,30 Z" fill="#ff9900"/>
                <rect x="-30" y="30" width="60" height="40" fill="#ff9900"/>
                <rect x="-15" y="40" width="30" height="30" fill="white"/>
                <text class="icon-label" y="50">{get_text("home_consumption")}</text>
                <text class="power-value" y="70">{home_consumption:.1f} kW</text>
            </g>
            
            <!-- Flow Lines -->
            {
            f'''
            <path class="flow-line" d="M130,200 L360,200" stroke="#3366cc" stroke-width="3"/>
            <path d="M340,195 L360,200 L340,205" fill="none" stroke="#3366cc" stroke-width="3"/>
            <path class="flow-line" d="M130,200 C300,200 500,150 660,200" stroke="#ff9900" stroke-width="3"/>
            <path d="M640,195 L660,200 L640,205" fill="none" stroke="#ff9900" stroke-width="3"/>
            ''' if battery_power > 0 else f'''
            <path class="flow-line" d="M440,200 L660,200" stroke="#dc3912" stroke-width="3"/>
            <path d="M640,195 L660,200 L640,205" fill="none" stroke="#dc3912" stroke-width="3"/>
            {
            f"""
            <path class="flow-line" d="M130,200 C300,200 500,150 660,200" stroke="#3366cc" stroke-width="3"/>
            <path d="M640,195 L660,200 L640,205" fill="none" stroke="#3366cc" stroke-width="3"/>
            """ if grid_power > 0 else ""
            }
            '''
            }
        </svg>
    </body>
    </html>
    """
    return html_content

def render_power_flow(battery):
    """Main function to render power flow visualization"""
    st.subheader(get_text("power_flow_visualization"))
    
    # Create a container for the visualization
    viz_container = st.empty()
    
    # Simulate real-time values for demonstration
    grid_power = np.sin(datetime.now().timestamp() / 10) * 2 + 3
    home_consumption = abs(np.sin(datetime.now().timestamp() / 10 + 1)) * 1.5 + 1
    
    # Create and display HTML visualization using components.html
    html_content = create_power_flow_svg(battery, grid_power, home_consumption)
    components.html(html_content, height=450)
    
    # Add auto-refresh using empty placeholder
    st.empty()