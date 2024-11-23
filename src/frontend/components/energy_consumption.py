import streamlit as st
from frontend.translations import get_text

def render_energy_consumption_summary(consumption, consumption_cost, optimize_consumption, optimize_cost):
    """
    Render energy consumption summary component
    
    Args:
        consumption: Total consumption in kWh
        consumption_cost: Total cost without optimization
        optimize_consumption: Optimized consumption in kWh
        optimize_cost: Optimized cost
    """
    if consumption and consumption_cost and optimize_consumption and optimize_cost:
        avg_price = consumption_cost / consumption if consumption > 0 else 0
        avg_opt_price = optimize_cost / optimize_consumption if optimize_consumption > 0 else 0
        savings = consumption_cost - optimize_cost
        st.markdown(f'''
            ### {get_text("energy_consumption_summary")}
            - 📊 {get_text("total_predicted_consumption")}: {consumption:.2f} kWh
            - 💰 {get_text("total_estimated_cost")}: €{consumption_cost:.2f}
            - 💵 {get_text("average_price")}: €{avg_price:.3f}/kWh
            - 📊 {get_text("optimization_consumption")}: {optimize_consumption:.2f} kWh
            - 💰 {get_text("optimization_cost")}: €{optimize_cost:.2f}
            - 💵 {get_text("average_optimization_price")}: €{avg_opt_price:.3f}/kWh
            - 💰 {get_text("savings")}: €{savings:.2f}
            ''')
