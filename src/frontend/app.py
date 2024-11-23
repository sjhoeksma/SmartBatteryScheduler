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
create_app()

# Initialize language in session state if not present
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Add language selector to sidebar
add_language_selector()

# Run main application
if __name__ == "__main__":
    main()
