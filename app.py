# Location => ./app.py  (κύρια σελίδα — Register Event)

import sys
sys.dont_write_bytecode = True

import streamlit as st
from shared import render_event_form
from utils.sidebar import sidebar
from utils.auth import require_login

st.set_page_config(
    page_title="Register Event",
    page_icon="📋",
    layout="wide",
)

require_login()
sidebar()

st.title("📋 Register Event")

success = render_event_form(prefix="form_", submit_label="💾 Save Event")
if success:
    st.success("✅ Το event αποθηκεύτηκε επιτυχώς!")
    st.balloons()
