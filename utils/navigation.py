# Location => ./utils/navigation.py

import sys
sys.dont_write_bytecode = True

import streamlit as st
from utils.auth import is_admin


def hide_default_nav_bar() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"],
            [data-testid="stSidebarHeader"] {
                display: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def nav_bar() -> None:
    st.markdown(
        """
        <style>
            div[data-testid="stButton"] button {
                display: flex;
                justify-content: flex-start;
                text-align: left;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("📋 Register Event", type="primary", use_container_width=True, key="nav_form"):
        st.switch_page("app.py")

    if st.sidebar.button("📊 Dashboard", type="primary", use_container_width=True, key="nav_dashboard"):
        st.switch_page("pages/1_dashboard.py")

    if is_admin():
        if st.sidebar.button("⚙️ Settings", use_container_width=True, key="nav_settings"):
            st.switch_page("pages/2_settings.py")
