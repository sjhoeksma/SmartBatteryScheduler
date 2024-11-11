import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from utils.formatting import format_currency, format_percentage, format_number
from utils.translations import get_text

def render_historical_analysis(prices, battery):
    """Render historical price analysis charts and insights"""
    from utils.historical_data import analyze_price_patterns, calculate_savings_opportunity
    
    # Get price analysis and savings opportunities
    analysis = analyze_price_patterns(prices)
    savings = calculate_savings_opportunity(prices, battery)
    
    # Create tabs for different analyses
    tab1, tab2, tab3 = st.tabs([
        get_text("price_trends_tab"),
        get_text("daily_patterns_tab"),
        get_text("savings_analysis_tab")
    ])
    
    with tab1:
        st.subheader("Historical Price Trends")
        
        # Create figure with secondary y-axis
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           subplot_titles=(get_text("price_trend_title"),
                                         get_text("price_volatility_title")))
        
        # Add price trend with rolling average
        fig.add_trace(
            go.Scatter(x=analysis['daily_avg'].index, y=analysis['daily_avg'].values,
                      name=get_text("daily_savings"), line=dict(color="blue")),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=analysis['rolling_mean'].index, y=analysis['rolling_mean'].values,
                      name=get_text("weekly_average_label"), line=dict(color="red", dash="dash")),
            row=1, col=1
        )
        
        # Add volatility
        fig.add_trace(
            go.Scatter(x=analysis['price_volatility'].index, y=analysis['price_volatility'].values,
                      name=get_text("price_volatility_title"), line=dict(color="orange")),
            row=2, col=1
        )
        
        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # Display trend insights
        st.info(f"📈 {get_text('price_trend')}: {analysis['trend_direction']}")
    
    with tab2:
        st.subheader(get_text("daily_patterns_tab"))
        
        # Create subplots for hourly and weekly patterns
        pattern_fig = make_subplots(rows=1, cols=2, 
                                  subplot_titles=(get_text("hourly_pattern_title"),
                                                get_text("weekly_pattern_title")))
        
        # Hourly pattern
        pattern_fig.add_trace(
            go.Scatter(x=list(range(24)), y=analysis['hourly_avg'].values,
                      name=get_text("hourly_average_label"), line=dict(color="green")),
            row=1, col=1
        )
        
        # Weekly pattern
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        pattern_fig.add_trace(
            go.Scatter(x=days, y=analysis['weekly_avg'].values,
                      name=get_text("weekly_average_label"), line=dict(color="purple")),
            row=1, col=2
        )
        
        pattern_fig.update_layout(height=400, showlegend=True)
        st.plotly_chart(pattern_fig, use_container_width=True)
        
        # Display pattern insights
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"⚡ {get_text('peak_hours')}: {', '.join(f'{h:02d}:00' for h in analysis['peak_hours'])}")
        with col2:
            st.info(f"💡 {get_text('off_peak_hours')}: {', '.join(f'{h:02d}:00' for h in analysis['off_peak_hours'])}")
    
    with tab3:
        st.subheader(get_text("savings_opportunities"))
        
        # Display daily savings potential
        st.metric(
            get_text("avg_daily_savings"),
            format_currency(savings['daily_savings']),
            delta=get_text("per_day")
        )
        
        # Create weekly savings pattern chart
        savings_fig = go.Figure()
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        savings_fig.add_trace(go.Bar(
            x=days,
            y=savings['weekly_pattern'].values,
            name=get_text("weekly_savings_pattern"),
            marker_color="green"
        ))
        
        savings_fig.update_layout(
            title=get_text("weekly_savings_pattern"),
            xaxis_title=get_text("day_of_week"),
            yaxis_title=get_text("avg_potential_savings")
        )
        st.plotly_chart(savings_fig, use_container_width=True)
        
        # Display optimization recommendations
        st.info(f"""
        💰 **{get_text('optimization_recommendations')}:**
        1. {get_text('charge_below').format(format_currency(savings['price_thresholds'][0.25]))}
        2. {get_text('discharge_above').format(format_currency(savings['price_thresholds'][0.75]))}
        3. {get_text('best_charging_times')}
        4. {get_text('consider_weekly_patterns')}
        """)
