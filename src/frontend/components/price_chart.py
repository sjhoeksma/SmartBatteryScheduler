import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from core.price_data import get_price_forecast_confidence, is_prices_available_for_tomorrow
from core.weather import WeatherService
import logging
from frontend.translations import get_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Cache the base figure layout
@st.cache_data(ttl=3600)
def get_base_figure_layout():
    return {
        'xaxis':
        dict(title=get_text("time"),
             gridcolor="rgba(128, 128, 128, 0.2)",
             tickformat="%H:%M",
             tickangle=-45,
             domain=[0, 0.85]),
        'yaxis':
        dict(title=get_text("power_kw"),
             titlefont=dict(color="rgba(52, 73, 94, 1.0)"),
             tickfont=dict(color="rgba(52, 73, 94, 1.0)"),
             gridcolor="rgba(128, 128, 128, 0.2)",
             zerolinecolor="rgba(128, 128, 128, 0.2)"),
        'yaxis2':
        dict(title=get_text("price_per_kwh"),
             titlefont=dict(color="rgba(41, 128, 185, 1.0)"),
             tickfont=dict(color="rgba(41, 128, 185, 1.0)"),
             anchor="x",
             overlaying="y",
             side="right",
             position=0.85),
        'yaxis3':
        dict(title=get_text("state_of_charge_percent"),
             titlefont=dict(color="rgba(155, 89, 182, 1.0)"),
             tickfont=dict(color="rgba(155, 89, 182, 1.0)"),
             anchor="free",
             overlaying="y",
             side="right",
             position=0.90,
             range=[0, 100]),
        'plot_bgcolor':
        "white",
        'paper_bgcolor':
        "white",
        'showlegend':
        True,
        'legend':
        dict(orientation="v",
             yanchor="top",
             y=1,
             xanchor="left",
             x=1.05,
             bgcolor="rgba(255, 255, 255, 0.8)",
             bordercolor="rgba(128, 128, 128, 0.2)",
             borderwidth=1),
        'margin':
        dict(l=50, r=150, t=50, b=50),
        'height':
        600
    }


@st.cache_data(ttl=300)  # Cache color calculations for 5 minutes
def get_price_colors(_dates, _prices):
    """Calculate and cache price period colors with extended timeline support"""
    colors = []

    # Calculate price percentiles for dynamic thresholds
    price_75th = np.percentile(_prices, 75)
    price_25th = np.percentile(_prices, 25)

    for date, price in zip(_dates, _prices):
        hour = date.hour
        confidence = get_price_forecast_confidence(date)

        # Dynamic color assignment based on both time and price
        if price >= price_75th:
            base_color = "rgba(255, 99, 71, {opacity})"  # Peak (red)
        elif price <= price_25th:
            base_color = "rgba(34, 139, 34, {opacity})"  # Off-peak (green)
        else:
            base_color = "rgba(255, 165, 0, {opacity})"  # Shoulder (orange)

        # Updated opacity settings for better visualization
        confidence = np.clip(confidence, 0,
                             1.0)  # Ensure confidence is in [0,1]
        if hour in [7, 8, 9, 17, 18, 19, 20]:
            opacity = np.clip(confidence * 0.4, 0.15, 1.0)  # Peak hours
        elif hour in [10, 11, 12, 13, 14, 15, 16]:
            opacity = np.clip(confidence * 0.3, 0.1, 1.0)  # Shoulder hours
        else:
            opacity = np.clip(confidence * 0.25, 0.08, 1.0)  # Off-peak hours

        colors.append(base_color.format(opacity=opacity))

    return colors


def render_price_chart(prices,
                       schedule=None,
                       predicted_soc=None,
                       consumption_stats=None):
    """Render interactive price chart with charging schedule and SOC prediction"""
    try:
        # Add data availability notice
        if not is_prices_available_for_tomorrow():
            st.warning(
                "⚠️ Day-ahead prices for tomorrow will be available after 13:00 CET"
            )

        # Validate price data
        if prices is None or len(prices) == 0:
            st.error("No price data available for visualization")
            return

        # Create figure with cached base layout
        fig = go.Figure(layout=get_base_figure_layout())

        # Get cached price period colors with price-sensitive coloring
        colors = get_price_colors(prices.index, prices.values)

        # Add price bars first (for proper rendering order)
        chunk_size = 12  # Hours per chunk
        for i in range(0, len(prices), chunk_size):
            chunk_slice = slice(i, i + chunk_size)
            chunk_prices = prices.iloc[chunk_slice]
            chunk_colors = colors[i:i + chunk_size]
            chunk_dates = prices.index[chunk_slice]

            # Calculate confidence levels for each point and clip them to [0,1] range
            confidence_levels = [
                np.clip(get_price_forecast_confidence(date), 0, 1.0)
                for date in chunk_dates
            ]

            fig.add_trace(
                go.Bar(
                    x=chunk_dates,
                    y=chunk_prices.values,
                    name=get_text("energy_price") if i == 0 else None,
                    marker_color=chunk_colors,
                    marker_opacity=confidence_levels,
                    yaxis="y2",
                    width=3600000,  # 1 hour in milliseconds
                    hovertemplate=
                    "Time: %{x}<br>Price: €%{y:.3f}/kWh<br>Confidence: %{marker.opacity:.0%}<extra></extra>",
                    showlegend=(i == 0)))

        # Add PV production forecast if battery has PV configured
        if 'battery' in st.session_state and st.session_state.battery.max_watt_peak > 0:
            # Get all forecasts at once
            weather_service = st.session_state.weather_service
            pv_production = []
            dates = prices.index

            for date in dates:
                production = weather_service.get_pv_forecast(
                    st.session_state.battery.max_watt_peak,
                    st.session_state.battery.pv_efficiency,
                    date=date) / 1000  # Convert to kWh
                pv_production.append(float(production))

            # Add debug logging
            logger.debug(f"PV production values: {pv_production}")

            # Only add trace if we have production values
            if any(v > 0 for v in pv_production):
                fig.add_trace(
                    go.Scatter(
                        x=dates,
                        y=pv_production,
                        name=get_text("solar_production"),
                        line=dict(color="rgba(241, 196, 15, 1.0)",
                                  width=3,
                                  shape='spline',
                                  smoothing=1.3),
                        mode='lines',
                        hovertemplate=
                        "Time: %{x}<br>PV Production: %{y:.2f} kW<extra></extra>"
                    ))

        # Add home usage line if battery is in session state
        if 'battery' in st.session_state:
            battery = st.session_state.battery
            home_usage = [
                battery.get_hourly_consumption(date.hour, date)
                for date in prices.index
            ]

            fig.add_trace(
                go.Scatter(x=prices.index,
                           y=home_usage,
                           name=get_text("home_usage"),
                           line=dict(color="rgba(52, 73, 94, 0.9)",
                                     width=3,
                                     shape='spline',
                                     smoothing=1.3),
                           mode='lines',
                           hovertemplate=
                           "Time: %{x}<br>Usage: %{y:.2f} kW<extra></extra>"))

        # Add SOC prediction with proper point visualization
        if predicted_soc is not None and isinstance(
                predicted_soc,
            (list, np.ndarray
             )) and len(predicted_soc) > 0 and 'battery' in st.session_state:
            # Create full timeline of points
            timestamps = []
            soc_values = []
            points_per_hour = 4

            # Convert predicted_soc to numpy array if it's a list
            soc_array = np.array(predicted_soc) if isinstance(
                predicted_soc, list) else predicted_soc

            for i in range(len(prices)):
                # Add points for each interval within the hour
                for j in range(points_per_hour):
                    point_index = i * points_per_hour + j
                    if point_index < len(soc_array):
                        timestamps.append(prices.index[i] +
                                          timedelta(minutes=15 * j))
                        # Convert SOC from decimal to percentage (0-100 range)
                        soc_values.append(float(soc_array[point_index] * 100))

            # Add SOC prediction trace if we have valid points
            if timestamps and soc_values:
                fig.add_trace(
                    go.Scatter(x=timestamps,
                               y=soc_values,
                               name=get_text("predicted_soc"),
                               line=dict(color="rgba(155, 89, 182, 0.9)",
                                         width=3,
                                         shape='spline',
                                         smoothing=1.3),
                               mode='lines',
                               yaxis="y3",
                               hovertemplate=
                               "Time: %{x}<br>SOC: %{y:.1f}%<extra></extra>"))

        # Add charging/discharging visualization with increased opacity
        if schedule is not None and isinstance(
                schedule, (list, np.ndarray)) and len(schedule) > 0:
            # Convert schedule to numpy array if it's a list
            schedule_array = np.array(schedule) if isinstance(
                schedule, list) else schedule
            charge_mask = np.greater(schedule_array, 0)
            discharge_mask = np.less(schedule_array, 0)

            if np.any(charge_mask):
                fig.add_trace(
                    go.Bar(
                        x=prices.index[charge_mask],
                        y=schedule_array[charge_mask],
                        name="Charging",
                        marker_color="rgba(0, 154, 0, 0.98)",
                        width=3600000,
                        hovertemplate=
                        "Time: %{x}<br>Charging: %{y:.2f} kW<extra></extra>"))

            if np.any(discharge_mask):
                fig.add_trace(
                    go.Bar(
                        x=prices.index[discharge_mask],
                        y=schedule_array[discharge_mask],
                        name="Discharging",
                        marker_color="rgba(255, 0, 0, 0.98)",
                        width=3600000,
                        hovertemplate=
                        "Time: %{x}<br>Discharging: %{y:.2f} kW<extra></extra>"
                    ))

        # Add unique key to plotly chart to fix StreamlitDuplicateElementId error
        fig.update_layout(modebar={
            'remove':
            ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle']
        })
        st.plotly_chart(fig,
                        use_container_width=True,
                        config={'displayModeBar': True},
                        key=f"price_chart_{datetime.now().timestamp()}")

        st.info(f'''
        📈 **{get_text("usage_pattern_info_title")}**
        - {get_text("usage_pattern_info_usage")}
        - {get_text("usage_pattern_info_solar")}
        - {get_text("usage_pattern_info_charging")}
        - {get_text("usage_pattern_info_discharging")}
        - {get_text("usage_pattern_info_prices")}
        - {get_text("usage_pattern_info_soc")}
        ''')
    except Exception as e:
        st.error(f"Error rendering price chart: {str(e)}")
