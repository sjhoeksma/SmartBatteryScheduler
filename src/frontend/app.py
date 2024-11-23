import streamlit as st
from frontend.main import main
from frontend.translations import add_language_selector
from backend.app import create_app

# Initialize services first
create_app()

# Then set page config
st.set_page_config(page_title="Energy Management Dashboard",
                  page_icon="⚡",
                  layout="wide",
                  initial_sidebar_state="collapsed")

# Add language selector to sidebar
add_language_selector()

# Run main application
if __name__ == "__main__":
    main()
