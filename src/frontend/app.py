import streamlit as st
from frontend.main import main
from frontend.translations import add_language_selector
from backend.app import create_app
import sys
import os

# Add src directory to Python path if not already present
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if src_path not in sys.path:
    sys.path.append(src_path)

# Set page config first - must be the first Streamlit command
st.set_page_config(page_title="Energy Management Dashboard",
                  page_icon="⚡",
                  layout="wide",
                  initial_sidebar_state="collapsed")

# Initialize services and run main application
if create_app():
    # Add language selector to sidebar
    add_language_selector()
    
    # Run main application
    main()
else:
    st.error("Failed to initialize application services")
