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
