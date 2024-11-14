import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from utils.price_data import is_prices_available_for_tomorrow

# Cache the base figure layout
@st.cache_data(ttl=3600)
def get_base_figure_layout():
    return {
        'title': {
            'text': "Energy Prices and Usage Patterns",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=20)
        },
        'xaxis': dict(
            title="Time",
            gridcolor="rgba(128, 128, 128, 0.2)",
            tickformat="%H:%M",
            tickangle=-45,
            domain=[0, 0.85]
        ),
        'yaxis': dict(
            title="Power (kW)",
            titlefont=dict(color="rgba(52, 73, 94, 1.0)"),
            tickfont=dict(color="rgba(52, 73, 94, 1.0)"),
            gridcolor="rgba(128, 128, 128, 0.2)",
            zerolinecolor="rgba(128, 128, 128, 0.2)"
        ),
        'yaxis2': dict(
            title="Price (€/kWh)",
            titlefont=dict(color="rgba(41, 128, 185, 1.0)"),
            tickfont=dict(color="rgba(41, 128, 185, 1.0)"),
            anchor="x",
            overlaying="y",
            side="right",
            position=0.85
        ),
        'yaxis3': dict(
            title="State of Charge (%)",
            titlefont=dict(color="rgba(155, 89, 182, 1.0)"),
            tickfont=dict(color="rgba(155, 89, 182, 1.0)"),
            anchor="free",
            overlaying="y",
            side="right",
            position=0.95,
            range=[0, 100]
        ),
        'plot_bgcolor': "white",
        'paper_bgcolor': "white",
        'showlegend': True,
        'legend': dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.05,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(128, 128, 128, 0.2)",
            borderwidth=1
        ),
        'margin': dict(l=50, r=150, t=50, b=50),
        'height': 600
    }

@st.cache_data(ttl=300)  # Cache color calculations for 5 minutes
def get_price_colors(dates):
    """Calculate and cache price period colors"""
    colors = []
    for date in dates:
        hour = date.hour
        if hour in [7, 8, 9, 17, 18, 19, 20]:
            colors.append("rgba(255, 99, 71, 0.3)")  # Peak
        elif hour in [10, 11, 12, 13, 14, 15, 16]:
            colors.append("rgba(255, 165, 0, 0.3)")  # Shoulder
        else:
            colors.append("rgba(34, 139, 34, 0.3)")  # Off-peak
    return colors

def render_price_chart(prices, schedule=None, predicted_soc=None, consumption_stats=None):
    """Render interactive price chart with charging schedule and SOC prediction"""
    # Add data availability notice
    if not is_prices_available_for_tomorrow():
        st.warning("⚠️ Day-ahead prices for tomorrow will be available after 13:00 CET")
    
    # Create figure with cached base layout
    fig = go.Figure(layout=get_base_figure_layout())
    
    # Get cached price period colors
    colors = get_price_colors(prices.index)
    
    # Add price bars with progressive loading for longer time periods
    chunk_size = 12  # Hours per chunk
    for i in range(0, len(prices), chunk_size):
        chunk_slice = slice(i, i + chunk_size)
        chunk_prices = prices.iloc[chunk_slice]
        chunk_colors = colors[i:i + chunk_size]
        chunk_dates = prices.index[chunk_slice]
        
        fig.add_trace(go.Bar(
            x=chunk_dates,
            y=chunk_prices.values,
            name="Energy Price" if i == 0 else None,  # Only show in legend once
            marker_color=chunk_colors,
            marker_opacity=[get_price_forecast_confidence(date) for date in chunk_dates],
            yaxis="y2",
            width=3600000,  # 1 hour in milliseconds
            hovertemplate="Time: %{x}<br>Price: €%{y:.3f}/kWh<br>Confidence: %{marker.opacity:.0%}<extra></extra>",
            showlegend=(i == 0)  # Only show in legend for first chunk
        ))
    
    # Add charging/discharging visualization if schedule exists
    if schedule is not None:
        charge_mask = schedule > 0
        discharge_mask = schedule < 0
        
        if any(charge_mask):
            fig.add_trace(go.Bar(
                x=prices.index[charge_mask],
                y=schedule[charge_mask],
                name="Charging",
                marker_color="rgba(52, 152, 219, 0.9)",
                width=3600000,
                hovertemplate="Time: %{x}<br>Charging: %{y:.2f} kW<extra></extra>"
            ))
        
        if any(discharge_mask):
            fig.add_trace(go.Bar(
                x=prices.index[discharge_mask],
                y=schedule[discharge_mask],
                name="Discharging",
                marker_color="rgba(41, 128, 185, 0.9)",
                width=3600000,
                hovertemplate="Time: %{x}<br>Discharging: %{y:.2f} kW<extra></extra>"
            ))
    
    # Add home usage line if battery is in session state
    if 'battery' in st.session_state:
        battery = st.session_state.battery
        home_usage = [battery.get_hourly_consumption(date.hour, date) 
                     for date in prices.index]
        
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=home_usage,
            name="Home Usage",
            line=dict(color="rgba(52, 73, 94, 0.9)", width=2),
            mode='lines',
            hovertemplate="Time: %{x}<br>Usage: %{y:.2f} kW<extra></extra>"
        ))
    
    # Add SOC prediction with optimized point calculation
    if predicted_soc is not None:
        timestamps = []
        soc_values = []
        
        # Use fewer interpolation points for longer time periods
        points_per_hour = 4 if len(prices) <= 24 else 2
        
        for i, ts in enumerate(prices.index[:-1]):
            base_soc = predicted_soc[i * points_per_hour]
            next_soc = predicted_soc[(i + 1) * points_per_hour]
            
            for j in range(points_per_hour):
                point_time = ts + timedelta(minutes=(60 // points_per_hour) * j)
                alpha = j / points_per_hour
                interpolated_soc = base_soc + (next_soc - base_soc) * alpha
                
                timestamps.append(point_time)
                soc_values.append(interpolated_soc * 100)
        
        # Add final point
        timestamps.append(prices.index[-1])
        soc_values.append(predicted_soc[-1] * 100)
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=soc_values,
            name="Predicted SOC",
            line=dict(
                color="rgba(155, 89, 182, 0.9)",
                width=3,
                shape='spline',
                smoothing=0.3
            ),
            mode='lines',
            yaxis="y3",
            hovertemplate="Time: %{x}<br>SOC: %{y:.1f}%<extra></extra>"
        ))
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add cached legends
    st.markdown("""
    ### Price Period Legend
    - 🔴 **Peak Hours** (07:00-09:00, 17:00-20:00): Typically highest prices
    - 🟠 **Shoulder Hours** (10:00-16:00): Moderate prices
    - 🟢 **Off-peak Hours** (21:00-06:00): Usually lowest prices
    """)
    
    st.info("""
    📈 **Usage Pattern Information**
    - The black line shows actual home usage including hourly variations
    - Light blue bars indicate charging periods (buying energy)
    - Dark blue bars indicate discharging periods (using stored energy)
    - Energy prices are shown as hourly blocks with reduced opacity to highlight charging patterns
    - Purple line shows predicted battery State of Charge (SOC) with smooth transitions
    """)

def get_price_forecast_confidence(date):
    """Get confidence level for price forecasts"""
    current_time = datetime.now()
    time_diff = (date - current_time).total_seconds() / 3600
    confidence = 1 - abs(time_diff) / 24
    return max(0, min(1, confidence))
