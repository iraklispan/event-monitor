# Location => ./utils/header_footer.py

import sys
sys.dont_write_bytecode = True

import streamlit as st
from paths.paths import LOGO, APP_NAME, VERSION


def app_title() -> None:
    st.sidebar.markdown(
        f"""
        <style>
        .em-sidebar-title {{
            text-align: center;
            font-weight: 700;
            font-size: 1rem;
            letter-spacing: 0.05em;
            font-family: "Courier New", Courier, monospace;
            margin-bottom: 6px;
        }}
        </style>
        <div class="em-sidebar-title">{APP_NAME}</div>
        """,
        unsafe_allow_html=True,
    )


def logo() -> None:
    """Εμφανίζει το λογότυπο στο sidebar."""
    try:
        _, col2, _ = st.sidebar.columns([1, 2, 1])
        with col2:
            st.image(str(LOGO), width=100)
    except Exception:
        pass  # Αν δεν υπάρχει logo, παράλειψε χωρίς error
    st.sidebar.markdown(
        f"""
        <style>
        .em-sidebar-title {{
            text-align: center;
            font-weight: 700;
            font-size: 1rem;
            letter-spacing: 0.05em;
            font-family: "Courier New", Courier, monospace;
            margin-bottom: 6px;
        }}
        </style>
        <div class="em-sidebar-title">{APP_NAME}</div>
        """,
        unsafe_allow_html=True,
    )

def copy_right() -> None:
    st.sidebar.caption(f"{APP_NAME} v{VERSION}")
    st.sidebar.caption("© 2026 | iP-Labs.gr | All rights reserved.")
