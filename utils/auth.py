# Location => ./utils/auth.py

import sys
sys.dont_write_bytecode = True

import streamlit as st


def is_admin() -> bool:
    return st.session_state.get("role") == "admin"


def login_sidebar() -> None:
    if is_admin():
        st.sidebar.caption("👤 Admin")
        if st.sidebar.button("🚪 Logout", use_container_width=True, key="auth_logout"):
            st.session_state.pop("role", None)
            st.rerun()
    else:
        with st.sidebar.expander("🔐 Admin Login"):
            pwd = st.text_input("Password", type="password", key="auth_pwd")
            if st.button("Login", use_container_width=True, key="auth_login"):
                expected = st.secrets.get("auth", {}).get("admin_password", "")
                if pwd and pwd == expected:
                    st.session_state["role"] = "admin"
                    st.rerun()
                else:
                    st.error("❌ Λάθος password")
