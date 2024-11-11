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
    
    # Add price trace (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        line=dict(color="blue", width=2),
        yaxis="y2"
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
            # Calculate seasonal baseline
            seasonal_factor = battery.monthly_distribution[date.month]
            baseline = battery.daily_consumption / 24.0 * seasonal_factor
            seasonal_trend.append(baseline)
        
        # Add actual consumption line
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=home_usage,
            name="Home Usage",
            line=dict(color="black", width=2)
        ))
        
        # Add seasonal baseline
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=seasonal_trend,
            name="Seasonal Baseline",
            line=dict(color="red", width=2, dash="dot"),
            opacity=0.7
        ))

    # Combined load strategy trace (primary y-axis)
    if schedule is not None:
        schedule = np.where(np.abs(schedule) < 1e-6, 0, schedule)
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=schedule,
            name="Load Strategy",
            line=dict(color="purple", width=2)
        ))
    
    # SOC prediction trace (third y-axis)
    if predicted_soc is not None:
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=predicted_soc * 100,  # Convert to percentage
            name="Predicted SOC",
            line=dict(color="orange", width=2, dash="dot"),
            yaxis="y3"
        ))
    
    # Calculate average price
    avg_price = prices.mean()
    
    # Add next update time annotation if before 13:00
    if not is_prices_available_for_tomorrow():
        next_update = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
        if next_update < datetime.now():
            next_update = next_update + timedelta(days=1)
        fig.add_annotation(
            x=prices.index[-1],
            y=avg_price,
            xref="x",
            yref="y2",
            text=f"Next update at 13:00 CET",
            showarrow=False,
            xanchor="right",
            yanchor="top",
            xshift=-10,
            yshift=20,
            font=dict(color="red")
        )
    
    # Update layout with triple y-axes
    fig.update_layout(
        title="Energy Prices and Usage Patterns",
        xaxis_title="Time",
        yaxis=dict(
            title="Power (kW)",
            titlefont=dict(color="purple"),
            tickfont=dict(color="purple")
        ),
        yaxis2=dict(
            title="Price (€/kWh)",
            titlefont=dict(color="blue"),
            tickfont=dict(color="blue"),
            anchor="free",
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
            position=1.0,
            range=[0, 100]
        ),
        shapes=[
            dict(
                type="line",
                yref="y2",
                y0=avg_price,
                y1=avg_price,
                x0=prices.index[0],
                x1=prices.index[-1],
                line=dict(
                    color="gray",
                    dash="dash",
                )
            )
        ],
        annotations=[
            dict(
                x=prices.index[-1],
                y=avg_price,
                xref="x",
                yref="y2",
                text=f"Avg: €{avg_price:.2f}/kWh",
                showarrow=False,
                xanchor="left",
                yanchor="bottom",
                xshift=10,
                font=dict(color="gray")
            )
        ],
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add seasonal pattern explanation
    st.info("""
    📈 **Usage Pattern Information**
    - The black line shows actual home usage including hourly variations
    - The red dotted line shows the seasonal baseline consumption
    - Seasonal factors adjust consumption based on the month (higher in winter, lower in summer)
    """)
