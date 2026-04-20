# Location => ./utils/header_footer.py

import sys
sys.dont_write_bytecode = True

import streamlit as st

APP_NAME = "Event Monitor"
VERSION  = "1.1.2"


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


def copy_right() -> None:
    st.sidebar.caption(f"{APP_NAME} v{VERSION}")
    st.sidebar.caption("© 2026 | iP-Labs.gr | All rights reserved.")
