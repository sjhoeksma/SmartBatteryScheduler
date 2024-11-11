import streamlit as st
import plotly.graph_objects as go

def render_price_chart(prices):
    """Render interactive price chart"""
    fig = go.Figure()
    
    # Add price trace
    fig.add_trace(go.Scatter(
        x=prices.index,
        y=prices.values,
        name="Energy Price",
        line=dict(color="#0366d6", width=2)
    ))
    
    # Calculate average price
    avg_price = prices.mean()
    fig.add_hline(
        y=avg_price,
        line_dash="dash",
        annotation_text=f"Avg: €{avg_price:.2f}/kWh",
        line_color="gray"
    )
    
    # Update layout
    fig.update_layout(
        title="Day-Ahead Energy Prices",
        xaxis_title="Time",
        yaxis_title="Price (€/kWh)",
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
