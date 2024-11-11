import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def render_historical_analysis(prices, battery):
    """Render historical price analysis charts and insights"""
    from utils.historical_data import analyze_price_patterns, calculate_savings_opportunity
    
    # Get price analysis
    analysis = analyze_price_patterns(prices)
    
    # Create tabs for different analyses
    tab1, tab2, tab3 = st.tabs(["Price Trends", "Daily Patterns", "Savings Analysis"])
    
    with tab1:
        st.subheader("Historical Price Trends")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        
        # Daily average prices
        fig.add_trace(
            go.Scatter(x=analysis['daily_avg'].index, y=analysis['daily_avg'].values,
                      name="Daily Average", line=dict(color="blue")),
            row=1, col=1
        )
        
        # Price volatility
        fig.add_trace(
            go.Scatter(x=analysis['avg_daily_swing'].index, y=analysis['avg_daily_swing'].values,
                      name="Daily Price Swing", line=dict(color="red")),
            row=2, col=1
        )
        
        fig.update_layout(height=500, title_text="Price Trends and Volatility")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Hourly Price Patterns")
        hourly_fig = go.Figure()
        
        hourly_fig.add_trace(go.Scatter(
            x=list(range(24)), y=analysis['hourly_avg'].values,
            name="Average Price", line=dict(color="green")
        ))
        
        hourly_fig.update_layout(
            title="Average Price by Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Price (€/kWh)"
        )
        st.plotly_chart(hourly_fig, use_container_width=True)
        
        # Display insights
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"Peak Price Hours: {', '.join(f'{h:02d}:00' for h in analysis['peak_hours'])}")
        with col2:
            st.info(f"Lowest Price Hours: {', '.join(f'{h:02d}:00' for h in analysis['off_peak_hours'])}")
    
    with tab3:
        st.subheader("Savings Analysis")
        savings = calculate_savings_opportunity(prices, battery)
        
        st.metric(
            "Average Daily Savings Opportunity",
            f"€{savings:.2f}",
            delta="per day"
        )
        
        st.info("""
        💡 **Optimization Tips:**
        - Charge during off-peak hours (shown above)
        - Discharge during peak price periods
        - Maintain battery health by staying within optimal charge levels
        """)
