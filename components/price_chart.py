import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd

def render_price_chart(prices, schedule=None, predicted_soc=None):
    """Render interactive price chart with charging schedule and SOC prediction"""
    fig = go.Figure()
    
    # Add price trace (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        line=dict(color="blue", width=2),
        yaxis="y2"
    ))
    
    # Add home usage line
    if 'battery' in st.session_state:
        battery = st.session_state.battery
        home_usage = [battery.get_hourly_consumption(h.hour) for h in prices.index]
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=home_usage,
            name="Home Usage",
            line=dict(color="black", width=2, dash="dash")
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
    
    # Update layout with triple y-axes
    fig.update_layout(
        title="Energy Prices and Battery Schedule",
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
