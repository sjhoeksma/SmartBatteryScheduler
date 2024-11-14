import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from utils.price_data import is_prices_available_for_tomorrow

def render_price_chart(prices, schedule=None, predicted_soc=None, consumption_stats=None):
    """Render interactive price chart with charging schedule and SOC prediction"""
    # Add data availability notice
    if not is_prices_available_for_tomorrow():
        st.warning("⚠️ Day-ahead prices for tomorrow will be available after 13:00 CET")
    
    fig = go.Figure()
    
    # Define colors for different price periods
    peak_color = "rgba(255, 99, 71, 0.3)"  # Tomato red with lower opacity
    shoulder_color = "rgba(255, 165, 0, 0.3)"  # Orange with lower opacity
    offpeak_color = "rgba(34, 139, 34, 0.3)"  # Forest green with lower opacity
    
    # Define updated colors for charging/discharging using blue shades
    charging_color = "rgba(52, 152, 219, 0.9)"  # Peter River blue with high opacity
    discharging_color = "rgba(41, 128, 185, 0.9)"  # Belize Hole blue with high opacity
    
    # Determine price period colors
    colors = []
    for idx in prices.index:
        hour = idx.hour
        if hour in [7, 8, 9, 17, 18, 19, 20]:  # Peak hours
            colors.append(peak_color)
        elif hour in [10, 11, 12, 13, 14, 15, 16]:  # Shoulder hours
            colors.append(shoulder_color)
        else:  # Off-peak hours
            colors.append(offpeak_color)
    
    # Add price bars first (bottom layer)
    fig.add_trace(go.Bar(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        marker_color=colors,
        yaxis="y2",
        width=3600000,  # 1 hour in milliseconds for block width
        hovertemplate="Time: %{x}<br>Price: €%{y:.3f}/kWh<extra></extra>"
    ))
    
    # Load strategy visualization (middle layer)
    if schedule is not None:
        # Convert schedule to discrete states
        charge_mask = schedule > 0
        discharge_mask = schedule < 0
        
        # Add charging bars
        if any(charge_mask):
            fig.add_trace(go.Bar(
                x=prices.index[charge_mask],
                y=schedule[charge_mask],
                name="Charging",
                marker_color=charging_color,
                width=3600000,  # 1 hour in milliseconds
                hovertemplate="Time: %{x}<br>Charging: %{y:.2f} kW<extra></extra>"
            ))
        
        # Add discharging bars
        if any(discharge_mask):
            fig.add_trace(go.Bar(
                x=prices.index[discharge_mask],
                y=schedule[discharge_mask],
                name="Discharging",
                marker_color=discharging_color,
                width=3600000,  # 1 hour in milliseconds
                hovertemplate="Time: %{x}<br>Discharging: %{y:.2f} kW<extra></extra>"
            ))
    
    # Add home usage line (top layer)
    if 'battery' in st.session_state:
        battery = st.session_state.battery
        
        # Calculate home usage
        home_usage = []
        for date in prices.index:
            hourly_usage = battery.get_hourly_consumption(date.hour, date)
            home_usage.append(hourly_usage)
        
        # Add actual consumption line
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=home_usage,
            name="Home Usage",
            line=dict(color="rgba(52, 73, 94, 0.9)", width=2),
            mode='lines',
            hovertemplate="Time: %{x}<br>Usage: %{y:.2f} kW<extra></extra>"
        ))
    
    # SOC prediction trace (top layer)
    if predicted_soc is not None:
        # Create timestamps for intermediate points (4 points per hour)
        base_timestamps = list(prices.index)
        timestamps = []
        for ts in base_timestamps:
            # Add main hour point and three 15-minute interval points
            timestamps.extend([
                ts,
                ts + pd.Timedelta(minutes=15),
                ts + pd.Timedelta(minutes=30),
                ts + pd.Timedelta(minutes=45)
            ])
        # Add final point
        if len(base_timestamps) > 0:
            timestamps.append(base_timestamps[-1] + pd.Timedelta(hours=1))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=predicted_soc * 100,  # Convert to percentage
            name="Predicted SOC",
            line=dict(
                color="rgba(155, 89, 182, 0.9)",  # Purple with higher opacity
                width=3,
                shape='spline',  # Use spline interpolation for smooth transitions
                smoothing=0.3  # Adjust smoothing factor for natural curves
            ),
            mode='lines',
            yaxis="y3",
            hovertemplate="Time: %{x}<br>SOC: %{y:.1f}%<extra></extra>"
        ))
    
    # Update layout with enhanced settings
    fig.update_layout(
        title={
            'text': "Energy Prices and Usage Patterns",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=20)
        },
        xaxis=dict(
            title="Time",
            gridcolor="rgba(128, 128, 128, 0.2)",
            tickformat="%H:%M",
            tickangle=-45,
            domain=[0, 0.85]
        ),
        yaxis=dict(
            title="Power (kW)",
            titlefont=dict(color="rgba(52, 73, 94, 1.0)"),
            tickfont=dict(color="rgba(52, 73, 94, 1.0)"),
            gridcolor="rgba(128, 128, 128, 0.2)",
            zerolinecolor="rgba(128, 128, 128, 0.2)"
        ),
        yaxis2=dict(
            title="Price (€/kWh)",
            titlefont=dict(color="rgba(41, 128, 185, 1.0)"),
            tickfont=dict(color="rgba(41, 128, 185, 1.0)"),
            anchor="x",
            overlaying="y",
            side="right",
            position=0.85
        ),
        yaxis3=dict(
            title="State of Charge (%)",
            titlefont=dict(color="rgba(155, 89, 182, 1.0)"),
            tickfont=dict(color="rgba(155, 89, 182, 1.0)"),
            anchor="free",
            overlaying="y",
            side="right",
            position=0.95,
            range=[0, 100]
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.05,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(128, 128, 128, 0.2)",
            borderwidth=1
        ),
        margin=dict(l=50, r=150, t=50, b=50),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add legend explaining price periods
    st.markdown("""
    ### Price Period Legend
    - 🔴 **Peak Hours** (07:00-09:00, 17:00-20:00): Typically highest prices
    - 🟠 **Shoulder Hours** (10:00-16:00): Moderate prices
    - 🟢 **Off-peak Hours** (21:00-06:00): Usually lowest prices
    """)
    
    # Add usage pattern explanation with updated color description
    st.info("""
    📈 **Usage Pattern Information**
    - The black line shows actual home usage including hourly variations
    - Light blue bars indicate charging periods (buying energy)
    - Dark blue bars indicate discharging periods (using stored energy)
    - Energy prices are shown as hourly blocks with reduced opacity to highlight charging patterns
    - Purple line shows predicted battery State of Charge (SOC) with smooth transitions
    """)
