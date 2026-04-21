# Location => ./utils/sidebar.py

import sys
sys.dont_write_bytecode = True

import streamlit as st
from utils.navigation    import hide_default_nav_bar, nav_bar
from utils.header_footer import app_title, copy_right, logo
from utils.buttons       import refresh_button
from utils.auth          import logout_button


def sidebar() -> None:
    # Header
    logo()
    app_title()
    st.sidebar.markdown("---")
    
    # Navigation
    hide_default_nav_bar()
    nav_bar()
    st.sidebar.markdown("---")
    
    # Buttons
    refresh_button()
    logout_button()
    st.sidebar.markdown("---")

    # Footer
    copy_right()
