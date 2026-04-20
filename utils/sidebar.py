# Location => ./utils/sidebar.py

import sys
sys.dont_write_bytecode = True

import streamlit as st
from utils.navigation    import hide_default_nav_bar, nav_bar
from utils.header_footer import app_title, copy_right
from utils.buttons       import refresh_button
from utils.auth          import logout_button


def sidebar() -> None:
    app_title()
    st.sidebar.markdown("---")
    hide_default_nav_bar()
    nav_bar()
    st.sidebar.markdown("---")
    refresh_button()
    logout_button()
    st.sidebar.markdown("---")
    copy_right()
