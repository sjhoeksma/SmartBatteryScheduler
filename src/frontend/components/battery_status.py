import streamlit as st
from datetime import datetime
from frontend.translations import get_text
from frontend.formatting import format_percentage, format_number, format_date


def render_battery_status(battery):
    """Render battery status indicators"""
    # Add auto-refresh using st.empty()
    status_container = st.empty()

    with status_container.container():
        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                get_text("current_soc"),
                format_percentage(battery.current_soc * 100),
            )

            st.metric(
                get_text("available_capacity"),
                f"{format_number(battery.get_available_capacity())} kWh")

        with col2:
            st.metric(get_text("current_energy"),
                      f"{format_number(battery.get_current_energy())} kWh")

            st.metric(get_text("charge_rate"),
                      f"{format_number(battery.charge_rate)} kW")

        # Charging status indicator
        status_color = "green" if battery.can_charge(1.0) else "red"
        status_text = get_text(
            "available") if status_color == "green" else get_text(
                "unavailable")
        st.markdown(
            f"{get_text('charging_status')}: 🔋 <span style='color:{status_color}'>{status_text}</span>",
            unsafe_allow_html=True)

        # Last updated timestamp
        current_time = datetime.now()
        st.markdown(
            f"*{get_text('last_updated')}: {format_date(current_time, include_time=True)}*"
        )
