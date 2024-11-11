from typing import Dict, Optional
import streamlit as st
from dataclasses import dataclass

@dataclass
class Translation:
    en: str
    nl: str

# Dictionary of translations
TRANSLATIONS: Dict[str, Translation] = {
    # Main interface translations
    "app_title": Translation(
        en="⚡ Energy Management Dashboard",
        nl="⚡ Energiebeheer Dashboard"
    ),
    "real_time_dashboard": Translation(
        en="Real-time Dashboard",
        nl="Real-time Dashboard"
    ),
    "historical_analysis": Translation(
        en="Historical Analysis",
        nl="Historische Analyse"
    ),
    "cost_calculator": Translation(
        en="Cost Calculator",
        nl="Kostenberekening"
    ),
    "power_flow": Translation(
        en="Power Flow",
        nl="Energiestroom"
    ),
    "power_flow_status": Translation(
        en="Power Flow Status",
        nl="Energiestroom Status"
    ),
    "energy_balance": Translation(
        en="Energy Balance",
        nl="Energiebalans"
    ),
    "surplus": Translation(
        en="Surplus",
        nl="Overschot"
    ),
    "deficit": Translation(
        en="Deficit",
        nl="Tekort"
    ),
    
    # Power flow translations
    "power_flow_title": Translation(
        en="Real-time Power Flow",
        nl="Real-time Energiestroom"
    ),
    "power_flow_visualization": Translation(
        en="Power Flow Visualization",
        nl="Energiestroom Visualisatie"
    ),
    "grid_power": Translation(
        en="Grid Power",
        nl="Netvermogen"
    ),
    "battery_power": Translation(
        en="Battery Power",
        nl="Batterijvermogen"
    ),
    "home_consumption": Translation(
        en="Home Consumption",
        nl="Thuisverbruik"
    ),
    
    # Battery configuration translations
    "battery_config": Translation(
        en="Battery Configuration",
        nl="Batterij Configuratie"
    ),
    "battery_capacity": Translation(
        en="Battery Capacity (kWh)",
        nl="Batterijcapaciteit (kWh)"
    ),
    "min_soc": Translation(
        en="Minimum State of Charge",
        nl="Minimale Laadtoestand"
    ),
    "max_soc": Translation(
        en="Maximum State of Charge",
        nl="Maximale Laadtoestand"
    ),
    "charge_rate": Translation(
        en="Maximum Charge Rate (kW)",
        nl="Maximaal Laadvermogen (kW)"
    ),
    "yearly_consumption": Translation(
        en="Yearly Consumption (kWh)",
        nl="Jaarlijks Verbruik (kWh)"
    ),
    "daily_consumption": Translation(
        en="Average Daily Consumption (kWh)",
        nl="Gemiddeld Dagelijks Verbruik (kWh)"
    ),
    "usage_pattern": Translation(
        en="Usage Pattern",
        nl="Gebruikspatroon"
    ),
    
    # Battery status translations
    "battery_status": Translation(
        en="Battery Status",
        nl="Batterijstatus"
    ),
    "current_soc": Translation(
        en="Current State of Charge",
        nl="Huidige Laadtoestand"
    ),
    "available_capacity": Translation(
        en="Available Capacity",
        nl="Beschikbare Capaciteit"
    ),
    "current_energy": Translation(
        en="Current Energy",
        nl="Huidige Energie"
    ),
    "charging_status": Translation(
        en="Charging Status",
        nl="Oplaadstatus"
    ),
    "available": Translation(
        en="Available",
        nl="Beschikbaar"
    ),
    "unavailable": Translation(
        en="Unavailable",
        nl="Niet Beschikbaar"
    ),
    "last_updated": Translation(
        en="Last updated",
        nl="Laatst bijgewerkt"
    ),

    # Historical analysis translations
    "price_trend": Translation(
        en="Price Trend",
        nl="Prijstrend"
    ),
    "peak_hours": Translation(
        en="Peak Hours",
        nl="Piekuren"
    ),
    "off_peak_hours": Translation(
        en="Off-peak Hours",
        nl="Daluren"
    ),
    "savings_opportunities": Translation(
        en="Savings Opportunities",
        nl="Besparingsmogelijkheden"
    ),
    "avg_daily_savings": Translation(
        en="Average Daily Savings",
        nl="Gemiddelde Dagelijkse Besparing"
    ),
    "per_day": Translation(
        en="per day",
        nl="per dag"
    ),
    "weekly_savings_pattern": Translation(
        en="Weekly Savings Pattern",
        nl="Wekelijks Besparingspatroon"
    ),
    "day_of_week": Translation(
        en="Day of Week",
        nl="Dag van de Week"
    ),
    "avg_potential_savings": Translation(
        en="Average Potential Savings",
        nl="Gemiddelde Potentiële Besparing"
    ),
    "optimization_recommendations": Translation(
        en="Optimization Recommendations",
        nl="Optimalisatie Aanbevelingen"
    ),
    "charge_below": Translation(
        en="Charge when price is below {}",
        nl="Opladen wanneer prijs onder {}"
    ),
    "discharge_above": Translation(
        en="Discharge when price is above {}",
        nl="Ontladen wanneer prijs boven {}"
    ),
    "best_charging_times": Translation(
        en="Best charging times are typically during night hours",
        nl="Beste oplaadtijden zijn meestal tijdens nachtelijke uren"
    ),
    "consider_weekly_patterns": Translation(
        en="Consider weekly patterns for optimal scheduling",
        nl="Houd rekening met wekelijkse patronen voor optimale planning"
    ),

    # Cost calculator translations
    "cost_savings_calculator": Translation(
        en="Cost Savings Calculator",
        nl="Kostenbesparingsberekening"
    ),
    "daily_savings": Translation(
        en="Daily Savings",
        nl="Dagelijkse Besparing"
    ),
    "monthly_savings": Translation(
        en="Monthly Savings",
        nl="Maandelijkse Besparing"
    ),
    "roi_period": Translation(
        en="ROI Period",
        nl="Terugverdientijd"
    ),
    "investment": Translation(
        en="investment",
        nl="investering"
    ),
    "cycles": Translation(
        en="cycles",
        nl="cycli"
    ),
    "energy_shifted": Translation(
        en="kWh shifted",
        nl="kWh verschoven"
    ),
    "price_spread": Translation(
        en="Price Spread (€/kWh)",
        nl="Prijsverschil (€/kWh)"
    ),
    "cost_breakdown": Translation(
        en="Cost Breakdown",
        nl="Kostenverdeling"
    ),
    "peak_price": Translation(
        en="Peak Price",
        nl="Piekprijs"
    ),
    "off_peak_price": Translation(
        en="Off-Peak Price",
        nl="Dalprijs"
    ),
    "monthly_statistics": Translation(
        en="Monthly Statistics",
        nl="Maandelijkse Statistieken"
    ),
    "investment_analysis": Translation(
        en="Investment Analysis",
        nl="Investeringsanalyse"
    ),
    "annual_savings": Translation(
        en="Annual Savings",
        nl="Jaarlijkse Besparing"
    ),
    "return_on_investment": Translation(
        en="Return on Investment",
        nl="Rendement op Investering"
    ),
    "years": Translation(
        en="years",
        nl="jaren"
    ),
}

def get_browser_language() -> str:
    """Get the browser's language preference."""
    # Default to English if not set
    if 'language' not in st.session_state:
        st.session_state.language = 'en'
    return st.session_state.language

def set_language(lang: str) -> None:
    """Set the application language."""
    if lang in ['en', 'nl']:
        st.session_state.language = lang

def get_text(key: str) -> str:
    """Get translated text for the current language."""
    lang = get_browser_language()
    translation = TRANSLATIONS.get(key)
    if translation is None:
        return f"Missing translation: {key}"
    return getattr(translation, lang)

def add_language_selector():
    """Add a language selector widget to the sidebar."""
    st.sidebar.selectbox(
        "🌐 Language / Taal",
        options=['en', 'nl'],
        format_func=lambda x: "English" if x == "en" else "Nederlands",
        key="language_selector",
        on_change=lambda: set_language(st.session_state.language_selector)
    )
