import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd

def render_price_chart(prices, schedule=None):
    """Render interactive price chart with charging schedule"""
    fig = go.Figure()
    
    # Add price trace
    fig.add_trace(go.Scatter(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        line=dict(color="blue", width=2),
        yaxis="y2"
    ))
    
    if schedule is not None:
        schedule = np.where(np.abs(schedule) < 1e-6, 0, schedule)
        
        # Create masks for different states
        charging_mask = schedule > 0
        discharging_mask = schedule < 0
        
        # Add charging trace (positive values)
        charging_values = np.where(charging_mask, schedule, None)
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=charging_values,
            name="Charging",
            line=dict(color="green", width=2)
        ))
        
        # Add discharging trace (negative values)
        discharging_values = np.where(discharging_mask, schedule, None)
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=discharging_values,
            name="Discharging",
            line=dict(color="red", width=2)
        ))
        
        # Add idle trace (zero values)
        idle_mask = np.abs(schedule) < 1e-6
        idle_values = np.where(idle_mask, 0, None)
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=idle_values,
            name="Idle",
            line=dict(color="gray", width=2)
        ))
    
    # Calculate average price
    avg_price = prices.mean()
    
    # Update layout with dual y-axes
    fig.update_layout(
        title="Energy Prices and Battery Schedule",
        xaxis_title="Time",
        yaxis=dict(
            title="Power (kW)",
            titlefont=dict(color="black"),
            tickfont=dict(color="black")
        ),
        yaxis2=dict(
            title="Price (€/kWh)",
            titlefont=dict(color="blue"),
            tickfont=dict(color="blue"),
            anchor="free",
            overlaying="y",
            side="right",
            position=0.95
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
