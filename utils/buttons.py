# Location => ./utils/buttons.py

import sys
sys.dont_write_bytecode = True

import streamlit as st


def refresh_button() -> None:
    if st.sidebar.button("🔄 Refresh", type="secondary", use_container_width=True, key="btn_refresh"):
        st.cache_data.clear()
        st.rerun()
