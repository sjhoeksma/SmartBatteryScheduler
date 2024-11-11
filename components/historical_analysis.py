import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def render_historical_analysis(prices, battery):
    """Render historical price analysis charts and insights"""
    from utils.historical_data import analyze_price_patterns, calculate_savings_opportunity
    
    # Get price analysis and savings opportunities
    analysis = analyze_price_patterns(prices)
    savings = calculate_savings_opportunity(prices, battery)
    
    # Create tabs for different analyses
    tab1, tab2, tab3 = st.tabs(["Price Trends", "Daily Patterns", "Savings Analysis"])
    
    with tab1:
        st.subheader("Historical Price Trends")
        
        # Create figure with secondary y-axis
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           subplot_titles=("Price Trend", "Price Volatility"))
        
        # Add price trend with rolling average
        fig.add_trace(
            go.Scatter(x=analysis['daily_avg'].index, y=analysis['daily_avg'].values,
                      name="Daily Average", line=dict(color="blue")),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=analysis['rolling_mean'].index, y=analysis['rolling_mean'].values,
                      name="7-Day Average", line=dict(color="red", dash="dash")),
            row=1, col=1
        )
        
        # Add volatility
        fig.add_trace(
            go.Scatter(x=analysis['price_volatility'].index, y=analysis['price_volatility'].values,
                      name="Daily Volatility", line=dict(color="orange")),
            row=2, col=1
        )
        
        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # Display trend insights
        st.info(f"📈 Price Trend: {analysis['trend_direction']}")
    
    with tab2:
        st.subheader("Price Patterns")
        
        # Create subplots for hourly and weekly patterns
        pattern_fig = make_subplots(rows=1, cols=2, subplot_titles=("Hourly Pattern", "Weekly Pattern"))
        
        # Hourly pattern
        pattern_fig.add_trace(
            go.Scatter(x=list(range(24)), y=analysis['hourly_avg'].values,
                      name="Hourly Average", line=dict(color="green")),
            row=1, col=1
        )
        
        # Weekly pattern
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        pattern_fig.add_trace(
            go.Scatter(x=days, y=analysis['weekly_avg'].values,
                      name="Weekly Average", line=dict(color="purple")),
            row=1, col=2
        )
        
        pattern_fig.update_layout(height=400, showlegend=True)
        st.plotly_chart(pattern_fig, use_container_width=True)
        
        # Display pattern insights
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"⚡ Peak Price Hours: {', '.join(f'{h:02d}:00' for h in analysis['peak_hours'])}")
        with col2:
            st.info(f"💡 Lowest Price Hours: {', '.join(f'{h:02d}:00' for h in analysis['off_peak_hours'])}")
    
    with tab3:
        st.subheader("Savings Opportunities")
        
        # Display daily savings potential
        st.metric(
            "Average Daily Savings Potential",
            f"€{savings['daily_savings']:.2f}",
            delta="per day"
        )
        
        # Create weekly savings pattern chart
        savings_fig = go.Figure()
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        savings_fig.add_trace(go.Bar(
            x=days,
            y=savings['weekly_pattern'].values,
            name="Weekly Savings Pattern",
            marker_color="green"
        ))
        
        savings_fig.update_layout(
            title="Weekly Savings Pattern",
            xaxis_title="Day of Week",
            yaxis_title="Average Potential Savings (€)"
        )
        st.plotly_chart(savings_fig, use_container_width=True)
        
        # Display optimization recommendations
        st.info("""
        💰 **Optimization Recommendations:**
        1. Charge when prices are below €{:.3f}/kWh
        2. Discharge when prices are above €{:.3f}/kWh
        3. Best charging times are typically during off-peak hours
        4. Consider weekly patterns for optimal scheduling
        """.format(savings['price_thresholds'][0.25], savings['price_thresholds'][0.75]))
