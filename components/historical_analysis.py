import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from datetime import datetime, timedelta
from utils.formatting import format_currency, format_percentage, format_number
from utils.translations import get_text

def render_historical_analysis(prices, battery):
    """Render historical price analysis charts and insights"""
    from utils.historical_data import analyze_price_patterns, calculate_savings_opportunity, analyze_historical_pv_production
    
    # Get price analysis and savings opportunities
    analysis = analyze_price_patterns(prices)
    savings = calculate_savings_opportunity(prices, battery)
    
    # Get PV production analysis if PV is configured
    pv_analysis = None
    progress_bar = None
    partial_results = None
    daily_chart = None
    hourly_chart = None
    monthly_chart = None

    try:
        if battery.max_watt_peak > 0:
            logger.info("Analyzing PV production data...")
            
            # Create progress bar and placeholder for partial results
            progress_bar = st.progress(0)
            partial_results = st.empty()
            
            # Initialize container for charts
            daily_chart = st.empty()
            hourly_chart = st.empty()
            monthly_chart = st.empty()
            
            # Process data with progress tracking
            for result in analyze_historical_pv_production(prices.index, battery, st.session_state.weather_service, progress_bar):
                if not result['complete']:
                    # Show partial results
                    partial_df = result['partial_data']
                    processed = result['processed_entries']
                    total = result['total_entries']
                    
                    # Update progress message
                    partial_results.info(f"Processing data: {processed}/{total} entries ({int(processed/total*100)}% complete)")
                    
                    # Show partial visualizations if enough data is available
                    if len(partial_df) > 24:  # At least a day's worth of data
                        with daily_chart:
                            partial_daily = partial_df.groupby(partial_df['datetime'].dt.date)['production'].sum()
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=partial_daily.index, y=partial_daily.values,
                                                    name="Daily Production (Partial)",
                                                    line=dict(color="rgba(241, 196, 15, 0.5)")))
                            fig.update_layout(title="Daily Production (Processing...)")
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    # Clear progress indicators
                    progress_bar.empty()
                    partial_results.empty()
                    
                    if result['data']:
                        pv_analysis = result['data']
                        logger.info(f"Production data points: {len(pv_analysis['production_data'])}")
                    else:
                        st.error("Error processing PV production data")
    except Exception as e:
        logger.error(f"Error in PV analysis: {str(e)}")
        st.error(f"Error analyzing PV production: {str(e)}")
        return
                
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs([
        get_text("price_trends_tab"),
        get_text("daily_patterns_tab"),
        get_text("savings_analysis_tab"),
        "PV Production Analysis"
    ])
    
    with tab1:
        st.subheader(get_text("historical_price_trends"))
        
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
        
        fig.update_layout(
            height=600,
            showlegend=True,
            modebar={'remove': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']}
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        
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
        
        pattern_fig.update_layout(
            height=400,
            showlegend=True,
            modebar={'remove': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']}
        )
        st.plotly_chart(pattern_fig, use_container_width=True, config={'displayModeBar': True})
        
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
        savings_fig.update_layout(
            modebar={'remove': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']}
        )
        st.plotly_chart(savings_fig, use_container_width=True, config={'displayModeBar': True})
        
        # Display optimization recommendations
        st.info(f"""
        💰 **{get_text('optimization_recommendations')}:**
        1. {get_text('charge_below').format(format_currency(savings['price_thresholds'][0.25]))}
        2. {get_text('discharge_above').format(format_currency(savings['price_thresholds'][0.75]))}
        3. {get_text('best_charging_times')}
        4. {get_text('consider_weekly_patterns')}
        """)
            
    with tab4:
        if pv_analysis and 'daily_production' in pv_analysis:
            st.subheader("Solar Production Analysis")
            
            # Daily production trend
            daily_fig = go.Figure()
            daily_fig.add_trace(
                go.Scatter(x=pv_analysis['daily_production'].index,
                          y=pv_analysis['daily_production'].values,
                          name="Daily Production",
                          line=dict(color="rgba(241, 196, 15, 1.0)", width=2))
            )
            daily_fig.update_layout(
                title="Daily Solar Production",
                xaxis_title="Date",
                yaxis_title="Production (kWh)",
                showlegend=True
            )
            daily_fig.update_layout(
                modebar={'remove': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']}
            )
            st.plotly_chart(daily_fig, use_container_width=True, config={'displayModeBar': True})
            
            # Hourly production pattern
            hourly_fig = go.Figure()
            hourly_fig.add_trace(
                go.Bar(x=pv_analysis['hourly_production'].index,
                      y=pv_analysis['hourly_production'].values,
                      name="Average Hourly Production",
                      marker_color="rgba(241, 196, 15, 0.8)")
            )
            hourly_fig.update_layout(
                title="Average Hourly Production Pattern",
                xaxis_title="Hour of Day",
                yaxis_title="Average Production (kW)",
                showlegend=True
            )
            hourly_fig.update_layout(
                modebar={'remove': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']}
            )
            st.plotly_chart(hourly_fig, use_container_width=True, config={'displayModeBar': True})
            
            # Monthly production trend
            monthly_fig = go.Figure()
            monthly_fig.add_trace(
                go.Bar(x=pv_analysis['monthly_production'].index,
                      y=pv_analysis['monthly_production'].values,
                      name="Average Monthly Production",
                      marker_color="rgba(241, 196, 15, 0.8)")
            )
            monthly_fig.update_layout(
                title="Monthly Production Pattern",
                xaxis_title="Month",
                yaxis_title="Average Production (kW)",
                showlegend=True
            )
            monthly_fig.update_layout(
                modebar={'remove': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']}
            )
            st.plotly_chart(monthly_fig, use_container_width=True, config={'displayModeBar': True})
            
            # Production statistics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Production", f"{pv_analysis['total_production']:.2f} kWh")
                st.metric("System Efficiency", f"{pv_analysis['efficiency_ratio']*100:.1f}%")
            
            with col2:
                st.markdown("### Peak Production Hours")
                peak_hours_str = ", ".join([f"{hour:02d}:00" for hour in sorted(pv_analysis['peak_hours'])])
                st.info(f"Best production hours: {peak_hours_str}")
        else:
            st.info("No PV installation configured. Add PV capacity in the battery configuration to see production analysis.")
