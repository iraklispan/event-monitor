# Location => ./utils/auth.py

import sys
sys.dont_write_bytecode = True

import streamlit as st


def is_logged_in() -> bool:
    return st.session_state.get("role") in ("user", "admin")


def is_admin() -> bool:
    return st.session_state.get("role") == "admin"


def require_login() -> None:
    """
    Αν ο χρήστης δεν είναι logged in, εμφανίζει τη φόρμα login
    στο κεντρικό περιεχόμενο και σταματά την εκτέλεση της σελίδας.
    """
    if is_logged_in():
        return

    st.markdown("<br>" * 3, unsafe_allow_html=True)
    _, col, _ = st.columns([1.2, 1, 1.2])
    with col:
        st.markdown("### 🔐 Event Monitor")
        st.markdown("Παρακαλώ εισάγετε τον κωδικό πρόσβασης.")
        pwd = st.text_input("Password", type="password", key="login_pwd", label_visibility="collapsed",
                            placeholder="Password...")
        if st.button("Login", type="primary", use_container_width=True, key="login_btn"):
            _check_login(pwd)
        if st.session_state.get("_login_error"):
            st.error("❌ Λάθος password. Δοκίμασε ξανά.")

    st.stop()


def _check_login(pwd: str) -> None:
    admin_pwd = st.secrets.get("auth", {}).get("admin_password", "")
    user_pwd  = st.secrets.get("auth", {}).get("user_password", "")

    if pwd and pwd == admin_pwd:
        st.session_state["role"] = "admin"
        st.session_state.pop("_login_error", None)
        st.rerun()
    elif pwd and pwd == user_pwd:
        st.session_state["role"] = "user"
        st.session_state.pop("_login_error", None)
        st.rerun()
    else:
        st.session_state["_login_error"] = True
        st.rerun()


def logout_button() -> None:
    role  = st.session_state.get("role", "")
    label = "👤 Admin" if role == "admin" else "👤 User"
    #sst.sidebar.caption(label)
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="auth_logout"):
        st.session_state.pop("role", None)
        st.rerun()
    st.sidebar.caption(label)
