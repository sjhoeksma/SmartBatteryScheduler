import streamlit as st
from frontend.main import main

if __name__ == "__main__":
    st.set_page_config(page_title="Energy Management Dashboard",
                      page_icon="⚡",
                      layout="wide",
                      initial_sidebar_state="collapsed")
    main()


def main():
    # Add custom CSS to reduce padding
    st.markdown('''
        <style>
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 0rem;
            }
            .stApp {
                overflow-x: hidden;
            }
            .css-18e3th9 {
                padding-top: 0rem;
            }
            header {
                visibility: hidden;
            }
        </style>
    ''',
                unsafe_allow_html=True)

    # Add language selector to sidebar
    add_language_selector()

    # Initialize session state
    if 'store' not in st.session_state:
        st.session_state.store = ObjectStore()

    # Initialize WeatherService
    if 'weather_service' not in st.session_state:
        try:
            st.session_state.weather_service = WeatherService()
            st.session_state.weather_service_initialized = True
        except Exception as e:
            st.error(f"Error initializing weather service: {str(e)}")
            st.session_state.weather_service_initialized = False

    if 'battery' not in st.session_state:
        default_profile = st.session_state.store.get_profile("Home Battery")
        if default_profile:
            st.session_state.battery = Battery(
                capacity=default_profile.capacity,
                empty_soc=default_profile.empty_soc,
                min_soc=default_profile.min_soc,
                max_soc=default_profile.max_soc,
                charge_rate=default_profile.charge_rate,
                profile_name="Home Battery",
                daily_consumption=default_profile.daily_consumption,
                usage_pattern=default_profile.usage_pattern,
                yearly_consumption=default_profile.yearly_consumption,
                monthly_distribution=default_profile.monthly_distribution,
                max_daily_cycles=default_profile.max_daily_cycles,
                surcharge_rate=default_profile.surcharge_rate,
                max_watt_peak=default_profile.max_watt_peak,
                look_ahead_hours=default_profile.look_ahead_hours,
                current_soc=default_profile.current_soc,
                pv_efficiency=default_profile.pv_efficiency)

    # Initialize forecast hours with default value
    if 'forecast_hours' not in st.session_state:
        st.session_state.forecast_hours = get_max_forecast_hours()

    # Initialize variables
    prices = None
    schedule = None
    predicted_soc = None
    consumption_stats = None
    consumption = None
    consumption_cost = None
    optimize_consumption = None
    optimize_cost = None

    # Get cached price forecast and optimization results
    try:
        # Update forecast hours if needed
        forecast_hours = get_max_forecast_hours()
        if forecast_hours != st.session_state.forecast_hours:
            st.session_state.forecast_hours = forecast_hours
            st.cache_data.clear()

        # Get prices and optimization results
        prices = get_cached_prices(st.session_state.forecast_hours)
        if prices is not None and st.session_state.battery:
            optimizer = Optimizer(st.session_state.battery)
            schedule, predicted_soc, consumption_stats, consumption, consumption_cost, optimize_consumption, optimize_cost = optimizer.optimize_schedule(
                prices)
    except Exception as e:
        st.error(f"Error updating price data: {str(e)}")

    # Layout
    tab1, tab2, tab3, tab4 = st.tabs([
        get_text("real_time_dashboard"),
        get_text("manual_control"),
        get_text("cost_calculator"),
        get_text("historical_analysis")
    ])

    with tab1:
        st.markdown(
            f"<h1 style='font-size: 1.8rem; margin: 0; padding: 0;'>{get_text('app_title')}</h1>",
            unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])

        with col1:
            if prices is not None and st.session_state.battery:
                render_price_chart(prices, schedule, predicted_soc,
                                   consumption_stats)
            else:
                st.warning("No price data available")

            # Format consumption summary with proper null handling
            if consumption and consumption_cost and optimize_consumption and optimize_cost:
                avg_price = consumption_cost / consumption if consumption > 0 else 0
                avg_opt_price = optimize_cost / optimize_consumption if optimize_consumption > 0 else 0
                savings = consumption_cost - optimize_cost
                st.markdown(f'''
                    ### Energy Consumption Summary
                    - 📊 Total Predicted Consumption: {consumption:.2f} kWh
                    - 💰 Total Estimated Cost: €{consumption_cost:.2f}
                    - 💵 Average Price: €{avg_price:.3f}/kWh
                    - 📊 Optimization Consumption: {optimize_consumption:.2f} kWh
                    - 💰 Optimization Cost: €{optimize_cost:.2f}
                    - 💵 Average Optimization Price: €{avg_opt_price:.3f}/kWh
                    - 💰 Saving: €{savings:.2f}
                    ''')

        with col2:
            st.subheader(get_text("battery_config"))
            render_battery_config()

            if st.session_state.battery:
                st.subheader(get_text("battery_status"))
                render_battery_status(st.session_state.battery)

    with tab2:
        if st.session_state.battery:
            render_manual_battery_control(st.session_state.battery,
                                          prices=prices,
                                          schedule=schedule,
                                          predicted_soc=predicted_soc,
                                          consumption_stats=consumption_stats)
        else:
            st.warning("Please configure battery settings first")

    with tab3:
        if st.session_state.battery and prices is not None:
            render_cost_calculator(prices, st.session_state.battery)
        else:
            st.warning(
                "Please configure battery settings and wait for price data")
    with tab4:
        if st.session_state.battery:
            render_historical_analysis(st.session_state.battery)
        else:
            st.warning("Please configure battery settings first")


if __name__ == "__main__":
    main()
