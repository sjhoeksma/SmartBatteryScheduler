import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd  # Added missing pandas import

def render_price_chart(prices, schedule=None):
    """Render interactive price chart with charging schedule"""
    fig = go.Figure()
    
    # Add price trace on secondary y-axis
    fig.add_trace(go.Scatter(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        line=dict(color="blue", width=2),
        yaxis="y2"
    ))
    
    if schedule is not None:
        # Ensure schedule values are exactly 0 when no activity
        schedule = np.where(pd.isna(schedule), 0, schedule)
        
        # Add single trace for battery power (both charging and discharging)
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=schedule,
            name="Battery Power",
            line=dict(
                color=["red" if val < 0 else "green" if val > 0 else "gray" for val in schedule],
                width=2
            ),
            mode='lines'
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