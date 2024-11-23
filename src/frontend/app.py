import streamlit as st
from frontend.main import main
from frontend.translations import add_language_selector
from backend.app import create_app

# Set page config first - must be the first Streamlit command
st.set_page_config(page_title="Energy Management Dashboard",
                  page_icon="⚡",
                  layout="wide",
                  initial_sidebar_state="collapsed")

# Initialize services
if not create_app():
    st.error("Failed to initialize application services")
    st.stop()

# Add language selector to sidebar
add_language_selector()

# Run main application
if __name__ == "__main__":
    main()
