# Location => ./pages/2_settings.py  (admin only)

import sys
sys.dont_write_bytecode = True

import streamlit as st
import pandas as pd

from utils.sidebar import sidebar
from utils.auth import require_login, is_admin
from utils.mappings import load_list, save_list
from paths.paths import (
    ROOM_TYPES_JSON, RATE_PLANS_JSON, CANCELLATION_JSON,
    SPACE_NAMES_JSON, SERVICES_JSON, EVENT_TYPES_JSON, PRICE_COMBOS_JSON,
)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

require_login()
sidebar()

if not is_admin():
    st.error("⛔ Μόνο ο admin έχει πρόσβαση σε αυτή τη σελίδα.")
    st.stop()

st.title("⚙️ Settings")
st.caption("Επεξεργασία λιστών επιλογών — οι αλλαγές αποθηκεύονται στα αντίστοιχα JSON αρχεία.")

SECTIONS = [
    ("🏨 Room Types",            ROOM_TYPES_JSON,  "room_types",  False),
    ("🍽️ Rate Plans",            RATE_PLANS_JSON,  "rate_plans",  False),
    ("📜 Cancellation Policies", CANCELLATION_JSON,"cancellation",False),
    ("🏛️ Space Names",           SPACE_NAMES_JSON, "space_names", False),
    ("☕ Services",               SERVICES_JSON,    "services",    False),
    ("📅 Event Types",           EVENT_TYPES_JSON, "event_types", False),
    ("💰 Price Combos",          PRICE_COMBOS_JSON,"price_combos",True),
]

tabs = st.tabs([s[0] for s in SECTIONS])

for tab, (label, path, key, is_sensitive) in zip(tabs, SECTIONS):
    with tab:
        if is_sensitive:
            st.warning(
                "⚠️ Τα Price Combos συνδέονται άμεσα με τις στήλες δεδομένων στο Google Sheets "
                "(ROOMS_HEADER στο shared.py). Αν προσθέσεις ή αφαιρέσεις τιμές, "
                "πρέπει να ενημερώσεις και το `ROOMS_HEADER` χειροκίνητα."
            )

        items = load_list(path)
        df = pd.DataFrame({"Τιμή": items})

        edited = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Τιμή": st.column_config.TextColumn(
                    label,
                    help="Κάνε double-click για επεξεργασία · ➕ κάτω για προσθήκη · ☑ + Delete για διαγραφή",
                    required=True,
                )
            },
            key=f"editor_{key}",
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("💾 Αποθήκευση", key=f"save_{key}", type="primary", use_container_width=True):
                new_items = [
                    str(v).strip()
                    for v in edited["Τιμή"].tolist()
                    if v is not None and str(v).strip()
                ]
                if not new_items:
                    st.error("❌ Η λίστα δεν μπορεί να είναι κενή.")
                else:
                    save_list(path, new_items)
                    st.success(f"✅ Αποθηκεύτηκε — {len(new_items)} τιμές.")
                    st.rerun()
        with col2:
            st.caption(f"📄 `maps/{path.name}`  ·  {len(items)} τιμές")
