import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from utils.weather_service import WeatherService
from utils.translations import get_text

def render_historical_analysis(battery):
    """Render historical PV production analysis"""
    st.subheader(get_text("historical_pv_analysis"))

    if battery.max_watt_peak <= 0:
        st.warning(get_text("no_pv_configured"))
        return

    # Initialize weather service
    weather_service = st.session_state.weather_service

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            get_text("start_date"),
            value=datetime.now().date() - timedelta(days=7),
            max_value=datetime.now().date()
        )
    with col2:
        end_date = st.date_input(
            get_text("end_date"),
            value=datetime.now().date(),
            max_value=datetime.now().date()
        )

    if start_date and end_date:
        if start_date > end_date:
            st.error(get_text("date_range_error"))
            return

        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq='h')
        
        # Get PV production data
        pv_data = []
        daily_totals = {}
        
        for date in dates:
            production = weather_service.get_pv_forecast(
                battery.max_watt_peak,
                battery.pv_efficiency,
                date=date
            )
            pv_data.append({
                'datetime': date,
                'production': float(production),
                'date': date.date(),
                'hour': date.hour
            })
            
            # Calculate daily totals
            if date.date() not in daily_totals:
                daily_totals[date.date()] = 0
            daily_totals[date.date()] += float(production)

        # Convert to DataFrame
        df = pd.DataFrame(pv_data)

        # Create daily production chart
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=list(daily_totals.keys()),
            y=list(daily_totals.values()),
            name=get_text("daily_production"),
            marker_color="rgba(241, 196, 15, 0.8)"
        ))
        
        fig1.update_layout(
            title=get_text("daily_pv_production"),
            xaxis_title=get_text("date"),
            yaxis_title=get_text("energy_kwh"),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        
        st.plotly_chart(fig1, use_container_width=True)

        # Create hourly heatmap
        pivot_df = df.pivot(index='date', columns='hour', values='production')
        
        fig2 = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale='YlOrRd',
            name=get_text("hourly_production")
        ))
        
        fig2.update_layout(
            title=get_text("hourly_pv_production"),
            xaxis_title=get_text("hour_of_day"),
            yaxis_title=get_text("date"),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        
        st.plotly_chart(fig2, use_container_width=True)

        # Calculate statistics
        total_production = sum(daily_totals.values())
        avg_daily_production = total_production / len(daily_totals)
        peak_production = df['production'].max()
        peak_time = df.loc[df['production'].idxmax(), 'datetime']

        # Display statistics
        st.markdown("### " + get_text("production_statistics"))
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                get_text("total_production"),
                f"{total_production:.2f} kWh"
            )
        
        with col2:
            st.metric(
                get_text("average_daily"),
                f"{avg_daily_production:.2f} kWh/day"
            )
        
        with col3:
            st.metric(
                get_text("peak_production"),
                f"{peak_production:.2f} kW",
                delta=f"at {peak_time.strftime('%Y-%m-%d %H:%M')}"
            )
