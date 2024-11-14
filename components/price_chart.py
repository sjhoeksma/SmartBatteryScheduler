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
    peak_color = "rgba(255, 99, 71, 0.7)"  # Tomato red
    shoulder_color = "rgba(255, 165, 0, 0.7)"  # Orange
    offpeak_color = "rgba(60, 179, 113, 0.7)"  # Medium sea green
    
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
    
    # Add price bars (secondary y-axis)
    fig.add_trace(go.Bar(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        marker_color=colors,
        yaxis="y2",
        width=3600000,  # 1 hour in milliseconds for block width
        hovertemplate="Time: %{x}<br>Price: €%{y:.3f}/kWh<extra></extra>"
    ))
    
    # Add home usage line with enhanced seasonal pattern visualization
    if 'battery' in st.session_state:
        battery = st.session_state.battery
        
        # Calculate home usage with seasonal factors
        home_usage = []
        seasonal_trend = []
        for date in prices.index:
            hourly_usage = battery.get_hourly_consumption(date.hour, date)
            home_usage.append(hourly_usage)
            seasonal_factor = battery.monthly_distribution[date.month]
            baseline = battery.daily_consumption / 24.0 * seasonal_factor
            seasonal_trend.append(baseline)
        
        # Add actual consumption line
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=home_usage,
            name="Home Usage",
            line=dict(color="black", width=2),
            mode='lines',
            hovertemplate="Time: %{x}<br>Usage: %{y:.2f} kW<extra></extra>"
        ))
        
        # Add seasonal baseline
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=seasonal_trend,
            name="Seasonal Baseline",
            line=dict(color="red", width=2, dash="dot"),
            mode='lines',
            opacity=0.7,
            hovertemplate="Time: %{x}<br>Baseline: %{y:.2f} kW<extra></extra>"
        ))

    # Combined load strategy trace (primary y-axis)
    if schedule is not None:
        schedule = np.where(np.abs(schedule) < 1e-6, 0, schedule)
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=schedule,
            name="Load Strategy",
            line=dict(color="purple", width=2),
            mode='lines',
            hovertemplate="Time: %{x}<br>Load: %{y:.2f} kW<extra></extra>"
        ))
    
    # SOC prediction trace (third y-axis)
    if predicted_soc is not None:
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=predicted_soc * 100,  # Convert to percentage
            name="Predicted SOC",
            line=dict(color="orange", width=2, dash="dot"),
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
            domain=[0, 0.85]  # Adjust plot width to accommodate legend
        ),
        yaxis=dict(
            title="Power (kW)",
            titlefont=dict(color="purple"),
            tickfont=dict(color="purple"),
            gridcolor="rgba(128, 128, 128, 0.2)",
            zerolinecolor="rgba(128, 128, 128, 0.2)"
        ),
        yaxis2=dict(
            title="Price (€/kWh)",
            titlefont=dict(color="blue"),
            tickfont=dict(color="blue"),
            anchor="x",
            overlaying="y",
            side="right",
            position=0.85
        ),
        yaxis3=dict(
            title="State of Charge (%)",
            titlefont=dict(color="orange"),
            tickfont=dict(color="orange"),
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
        margin=dict(l=50, r=150, t=50, b=50),  # Increased right margin for legend
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
    
    # Add seasonal pattern explanation
    st.info("""
    📈 **Usage Pattern Information**
    - The black line shows actual home usage including hourly variations
    - The red dotted line shows the seasonal baseline consumption
    - Seasonal factors adjust consumption based on the month (higher in winter, lower in summer)
    - Energy prices are shown as hourly blocks to reflect actual market trading periods
    """)
