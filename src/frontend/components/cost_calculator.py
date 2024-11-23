import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from frontend.translations import get_text


def calculate_monthly_savings(prices, battery, usage_pattern='optimize'):
    """Calculate monthly savings based on battery usage pattern"""
    daily_cycles = 1.0 if usage_pattern == 'conservative' else 1.5
    usable_capacity = battery.capacity * (battery.max_soc - battery.min_soc)

    # Calculate average price difference between peak and off-peak
    sorted_prices = prices.sort_values()
    off_peak_avg = sorted_prices[:int(len(prices) * 0.25)].mean()
    peak_avg = sorted_prices[-int(len(prices) * 0.25):].mean()
    price_spread = peak_avg - off_peak_avg

    # Calculate daily savings
    daily_energy_shifted = usable_capacity * daily_cycles
    daily_savings = daily_energy_shifted * price_spread

    # Monthly calculations
    monthly_savings = daily_savings * 30
    monthly_cycles = daily_cycles * 30

    # ROI calculations (assuming battery cost of €400/kWh)
    battery_cost = battery.capacity * 400
    roi_years = battery_cost / (monthly_savings * 12)

    return {
        'daily_energy_shifted': daily_energy_shifted,
        'daily_savings': daily_savings,
        'monthly_savings': monthly_savings,
        'monthly_cycles': monthly_cycles,
        'battery_cost': battery_cost,
        'roi_years': roi_years,
        'price_spread': price_spread,
        'peak_price': peak_avg,
        'off_peak_price': off_peak_avg
    }


def render_cost_calculator(prices, battery):
    """Render the cost savings calculator interface"""
    st.subheader(get_text("cost_savings_calculator"))

    col1, col2 = st.columns(2)

    with col1:
        usage_pattern = st.selectbox(
            get_text("usage_pattern"),
            ['optimize', 'conservative'],
            format_func=lambda x: get_text(f"usage_pattern_{x.lower()}"),
            help=get_text("usage_pattern_help"))

    # Calculate savings
    savings = calculate_monthly_savings(prices, battery, usage_pattern)

    # Display key metrics
    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

    with metrics_col1:
        st.metric(get_text("daily_savings"),
                  f"€{savings['daily_savings']:.2f}",
                  f"{savings['daily_energy_shifted']:.1f} kWh shifted")

    with metrics_col2:
        st.metric(get_text("monthly_savings"),
                  f"€{savings['monthly_savings']:.2f}",
                  f"{savings['monthly_cycles']:.0f} cycles")

    with metrics_col3:
        st.metric(get_text("roi_period"), f"{savings['roi_years']:.1f} years",
                  f"€{savings['battery_cost']:.0f} investment")

    # Create price spread visualization
    fig = go.Figure()

    fig.add_trace(
        go.Indicator(mode="gauge+number+delta",
                     value=savings['price_spread'],
                     title={'text': get_text("price_spread")},
                     delta={'reference': 0.1},
                     gauge={
                         'axis': {
                             'range': [0, 0.3]
                         },
                         'bar': {
                             'color': "darkblue"
                         },
                         'steps': [{
                             'range': [0, 0.1],
                             'color': "lightgray"
                         }, {
                             'range': [0.1, 0.2],
                             'color': "gray"
                         }, {
                             'range': [0.2, 0.3],
                             'color': "darkgray"
                         }],
                         'threshold': {
                             'line': {
                                 'color': "red",
                                 'width': 4
                             },
                             'thickness': 0.75,
                             'value': 0.1
                         }
                     }))

    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)

    # Display detailed breakdown
    st.markdown(f"### {get_text('cost_breakdown')}")
    st.markdown(f"""
    - {get_text('peak_price')}: €{savings['peak_price']:.3f}/kWh
    - {get_text('off_peak_price')}: €{savings['off_peak_price']:.3f}/kWh
    - {get_text('price_spread')}: €{savings['price_spread']:.3f}/kWh
    
    **{get_text('monthly_statistics')}:**
    - {get_text('energy_shifted')}: {savings['daily_energy_shifted'] * 30:.1f} kWh
    - {get_text('cycles')}: {savings['monthly_cycles']:.0f}
    - {get_text('monthly_savings')}: €{savings['monthly_savings']:.2f}
    
    **{get_text('investment_analysis')}:**
    - {get_text('investment')}: €{savings['battery_cost']:.2f}
    - {get_text('annual_savings')}: €{savings['monthly_savings'] * 12:.2f}
    - {get_text('return_on_investment')}: {savings['roi_years']:.1f} {get_text('years')}
    """)
