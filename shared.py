"""
shared.py — Κοινός κώδικας για όλες τις σελίδες
Normalized schema: events / rooms / spaces / services
"""

import sys
sys.dont_write_bytecode = True

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import hashlib
import uuid

from utils.mappings import (
    get_room_types, get_rate_plans, get_cancellation_policies,
    get_space_names, get_services, get_event_types, get_price_combos,
)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
SHEET_NAME = "Groups & Conferences Data"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLOR_PALETTE = [
    "#4C9BE8", "#F28C38", "#5DBB8A", "#E8637A", "#A78BFA",
    "#F59E0B", "#34D399", "#60A5FA", "#F472B6", "#38BDF8",
    "#FB923C", "#A3E635", "#E879F9", "#2DD4BF", "#FCA5A5",
    "#93C5FD", "#6EE7B7", "#FCD34D", "#C4B5FD", "#86EFAC",
]

# Sheet headers — ROOMS_HEADER price columns must match maps/price_combos.json
EVENTS_HEADER = [
    "event_id", "submitted_at", "submitted_by",
    "event_name", "event_type", "event_start", "event_end", "attendees",
    "includes_accommodation", "acc_start", "acc_end",
    "booking_code", "cut_off_date",
    "cancellation_policy", "cancellation_days", "deposit_days",
    "minimum_stay", "includes_meeting_spaces",
]

ROOMS_HEADER = [
    "event_id", "room_type", "room_count", "rate_plan",
    "price_1_0", "price_2_0", "price_2_1", "price_2_2",
    "price_3_0", "price_3_1", "price_4_0",
]

SPACES_HEADER   = ["space_id", "event_id", "space_name"]
SERVICES_HEADER = ["space_id", "event_id", "service_type", "service_pax"]


# ─────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────────
def get_workbook():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)


def get_or_create_sheet(wb, title, header):
    try:
        ws = wb.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = wb.add_worksheet(title=title, rows=2000, cols=len(header))
        ws.update("A1", [header])
        return ws

    try:
        first_cell = ws.acell("A1").value
    except Exception:
        first_cell = None

    if first_cell != header[0]:
        ws.insert_row(header, 1)

    return ws


def get_sheets():
    wb = get_workbook()
    return {
        "events":   get_or_create_sheet(wb, "events",   EVENTS_HEADER),
        "rooms":    get_or_create_sheet(wb, "rooms",    ROOMS_HEADER),
        "spaces":   get_or_create_sheet(wb, "spaces",   SPACES_HEADER),
        "services": get_or_create_sheet(wb, "services", SERVICES_HEADER),
    }


def sheet_to_df(ws, header):
    values = ws.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame(columns=header)
    rows = values[1:]
    padded = [r + [""] * (len(header) - len(r)) for r in rows]
    df = pd.DataFrame(padded, columns=header)
    return df[df[header[0]].str.strip() != ""]


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    wb = get_workbook()
    titles = [ws.title for ws in wb.worksheets()]

    def safe_load(title, header):
        if title in titles:
            return sheet_to_df(wb.worksheet(title), header)
        return pd.DataFrame(columns=header)

    events_df   = safe_load("events",   EVENTS_HEADER)
    rooms_df    = safe_load("rooms",    ROOMS_HEADER)
    spaces_df   = safe_load("spaces",   SPACES_HEADER)
    services_df = safe_load("services", SERVICES_HEADER)

    for col in ["event_start", "event_end", "acc_start", "acc_end", "cut_off_date"]:
        if col in events_df.columns:
            events_df[col] = pd.to_datetime(events_df[col], errors="coerce")
    events_df["submitted_at"] = pd.to_datetime(events_df["submitted_at"], errors="coerce")

    if not events_df.empty:
        events_df = (
            events_df
            .sort_values("submitted_at")
            .groupby("event_name", as_index=False)
            .last()
        )

    return {
        "events":   events_df,
        "rooms":    rooms_df,
        "spaces":   spaces_df,
        "services": services_df,
    }


# ─────────────────────────────────────────────
# SAVE DATA
# ─────────────────────────────────────────────
def save_event(event_row, room_rows, space_rows, service_rows):
    sheets = get_sheets()

    sheets["events"].append_row(
        [str(event_row.get(c, "")) for c in EVENTS_HEADER],
        value_input_option="USER_ENTERED",
    )

    if room_rows:
        data = [[str(r.get(c, "")) for c in ROOMS_HEADER] for r in room_rows]
        sheets["rooms"].append_rows(data, value_input_option="USER_ENTERED")

    if space_rows:
        data = [[str(s.get(c, "")) for c in SPACES_HEADER] for s in space_rows]
        sheets["spaces"].append_rows(data, value_input_option="USER_ENTERED")

    if service_rows:
        data = [[str(sv.get(c, "")) for c in SERVICES_HEADER] for sv in service_rows]
        sheets["services"].append_rows(data, value_input_option="USER_ENTERED")

    load_data.clear()


# ─────────────────────────────────────────────
# ID GENERATION
# ─────────────────────────────────────────────
def generate_event_id(event_name: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    short = hashlib.md5(event_name.encode()).hexdigest()[:6]
    return f"{ts}_{short}"


def generate_space_id(event_id: str, space_name: str, idx: int) -> str:
    return f"{event_id}_sp{idx}"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def event_color(idx: int) -> str:
    return COLOR_PALETTE[idx % len(COLOR_PALETTE)]


def safe_date(val) -> date:
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return date.today()


def safe_int(val, default=0) -> int:
    try:
        return int(float(val or default))
    except Exception:
        return default


def safe_str(val, default="") -> str:
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return str(val).strip() if str(val).strip() else default


def num_days(row) -> int:
    try:
        return (row["event_end"] - row["event_start"]).days
    except Exception:
        return 0


def get_event_rooms(rooms_df, event_id):
    if rooms_df.empty:
        return pd.DataFrame()
    return rooms_df[rooms_df["event_id"] == event_id].copy()


def get_event_spaces(spaces_df, services_df, event_id):
    if spaces_df.empty:
        return []
    ev_spaces = spaces_df[spaces_df["event_id"] == event_id]
    result = []
    for _, sp in ev_spaces.iterrows():
        services = []
        if not services_df.empty:
            ev_services = services_df[services_df["space_id"] == sp["space_id"]]
            for _, sv in ev_services.iterrows():
                services.append({
                    "type": safe_str(sv.get("service_type")),
                    "pax":  safe_int(sv.get("service_pax")),
                })
        result.append({
            "space_id":   sp["space_id"],
            "space_name": sp["space_name"],
            "services":   services,
        })
    return result


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def init_form_state(prefix=""):
    if f"{prefix}num_rooms" not in st.session_state:
        st.session_state[f"{prefix}num_rooms"] = 1
    if f"{prefix}num_spaces" not in st.session_state:
        st.session_state[f"{prefix}num_spaces"] = 1
    if f"{prefix}space_services" not in st.session_state:
        st.session_state[f"{prefix}space_services"] = {1: 1}


def prefill_form_state(event_row, rooms_df, spaces_list, prefix=""):
    p = prefix
    room_types   = get_room_types()
    rate_plans   = get_rate_plans()
    event_types  = get_event_types()
    price_combos = get_price_combos()

    st.session_state[f"{p}submitted_by"]   = safe_str(event_row.get("submitted_by"))
    st.session_state[f"{p}event_name"]     = safe_str(event_row.get("event_name"))
    st.session_state[f"{p}event_type"]     = safe_str(event_row.get("event_type"), event_types[0] if event_types else "")
    st.session_state[f"{p}attendees"]      = safe_int(event_row.get("attendees"))
    st.session_state[f"{p}event_start"]    = safe_date(event_row.get("event_start"))
    st.session_state[f"{p}event_end"]      = safe_date(event_row.get("event_end"))
    st.session_state[f"{p}includes_accommodation"] = (
        safe_str(event_row.get("includes_accommodation")).lower() == "true"
    )
    st.session_state[f"{p}acc_start"]      = safe_date(event_row.get("acc_start"))
    st.session_state[f"{p}acc_end"]        = safe_date(event_row.get("acc_end"))
    st.session_state[f"{p}booking_code"]   = safe_str(event_row.get("booking_code"))
    st.session_state[f"{p}cut_off_date"]   = safe_date(event_row.get("cut_off_date"))
    st.session_state[f"{p}cancellation_policy"] = safe_str(event_row.get("cancellation_policy"), "Flexible")
    st.session_state[f"{p}cancellation_days"]   = safe_int(event_row.get("cancellation_days"))
    st.session_state[f"{p}deposit_days"]        = safe_int(event_row.get("deposit_days"))
    st.session_state[f"{p}minimum_stay"]        = safe_int(event_row.get("minimum_stay"))
    st.session_state[f"{p}includes_meeting_spaces"] = (
        safe_str(event_row.get("includes_meeting_spaces")).lower() == "true"
    )

    if not rooms_df.empty:
        for i, (_, r) in enumerate(rooms_df.iterrows(), start=1):
            st.session_state[f"{p}room{i}_type"]      = safe_str(r.get("room_type"), room_types[0] if room_types else "")
            st.session_state[f"{p}room{i}_count"]     = safe_int(r.get("room_count"), 1)
            st.session_state[f"{p}room{i}_rate_plan"] = safe_str(r.get("rate_plan"), rate_plans[0] if rate_plans else "")
            for combo in price_combos:
                k = f"price_{combo.replace('+', '_')}"
                st.session_state[f"{p}room{i}_{k}"] = safe_int(r.get(k), 0)
        st.session_state[f"{p}num_rooms"] = max(len(rooms_df), 1)
    else:
        st.session_state[f"{p}num_rooms"] = 1

    space_services = {}
    for i, sp in enumerate(spaces_list, start=1):
        st.session_state[f"{p}space{i}_name"] = sp["space_name"]
        num_sv = max(len(sp["services"]), 1)
        space_services[i] = num_sv
        for j, sv in enumerate(sp["services"], start=1):
            st.session_state[f"{p}space{i}_service{j}_type"] = sv["type"]
            st.session_state[f"{p}space{i}_service{j}_pax"]  = sv["pax"]
    st.session_state[f"{p}num_spaces"]     = max(len(spaces_list), 1)
    st.session_state[f"{p}space_services"] = space_services if space_services else {1: 1}


# ─────────────────────────────────────────────
# FORM UI BLOCKS
# ─────────────────────────────────────────────
def render_room_block(idx, prefix=""):
    room_types   = get_room_types()
    rate_plans   = get_rate_plans()
    price_combos = get_price_combos()

    with st.container(border=True):
        st.markdown(f"**🛏️ Room Type {idx}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.selectbox("Room Type", room_types, key=f"{prefix}room{idx}_type")
        with c2:
            st.number_input("Number of Rooms", min_value=1, step=1, value=1,
                            key=f"{prefix}room{idx}_count")
        with c3:
            st.selectbox("Rate Plan", rate_plans, key=f"{prefix}room{idx}_rate_plan")

        st.markdown("**Τιμές (€) — συμπλήρωσε όσα ισχύουν:**")
        pcols = st.columns(len(price_combos))
        for ci, combo in enumerate(price_combos):
            with pcols[ci]:
                st.number_input(
                    combo, min_value=0, step=1, value=0,
                    key=f"{prefix}room{idx}_price_{combo.replace('+', '_')}",
                )


def render_space_block(s_idx, prefix=""):
    space_names = get_space_names()
    services    = get_services()

    with st.container(border=True):
        st.markdown(f"**🏛️ Space {s_idx}**")
        st.selectbox("Space Name", space_names, key=f"{prefix}space{s_idx}_name")

        num_sv = st.session_state[f"{prefix}space_services"].get(s_idx, 1)
        for sv_idx in range(1, num_sv + 1):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.selectbox(f"Service {sv_idx}", services,
                             key=f"{prefix}space{s_idx}_service{sv_idx}_type")
            with c2:
                st.number_input(f"Pax {sv_idx}", min_value=0, step=1,
                                key=f"{prefix}space{s_idx}_service{sv_idx}_pax")

        if st.button("➕ Add Service", key=f"{prefix}add_service_{s_idx}"):
            st.session_state[f"{prefix}space_services"][s_idx] = num_sv + 1
            st.rerun()


# ─────────────────────────────────────────────
# FULL FORM
# ─────────────────────────────────────────────
def render_event_form(prefix="", submit_label="💾 Save Event"):
    init_form_state(prefix)

    event_types           = get_event_types()
    cancellation_policies = get_cancellation_policies()

    # 1. Basic Info
    st.subheader("1. Basic Information")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Your Name *", key=f"{prefix}submitted_by")
        st.text_input("Event Name *", key=f"{prefix}event_name")
        st.selectbox("Event Type *", event_types, key=f"{prefix}event_type")
        st.number_input("Number of Attendees", min_value=1, step=1,
                        key=f"{prefix}attendees")
    with c2:
        st.date_input("Event Start Date *", key=f"{prefix}event_start")
        st.date_input("Event End Date *",   key=f"{prefix}event_end")

    st.divider()

    # 2. Accommodation
    st.subheader("2. Accommodation")
    incl_acc = st.toggle("Includes Accommodation",
                         key=f"{prefix}includes_accommodation")
    if incl_acc:
        same_dates = st.toggle(
            "Same dates as the event",
            value=True,
            key=f"{prefix}acc_same_dates",
        )
        if not same_dates:
            c1, c2 = st.columns(2)
            with c1:
                st.date_input("Check-in Date",  key=f"{prefix}acc_start")
            with c2:
                st.date_input("Check-out Date", key=f"{prefix}acc_end")
        else:
            st.session_state[f"{prefix}acc_start"] = st.session_state.get(f"{prefix}event_start")
            st.session_state[f"{prefix}acc_end"]   = st.session_state.get(f"{prefix}event_end")
            c1, c2 = st.columns(2)
            with c1:
                st.date_input("Check-in Date",  key=f"{prefix}acc_start", disabled=True)
            with c2:
                st.date_input("Check-out Date", key=f"{prefix}acc_end",   disabled=True)

        st.markdown("#### Room Types")
        for i in range(1, st.session_state[f"{prefix}num_rooms"] + 1):
            render_room_block(i, prefix)
        if st.button("➕ Add Another Room Type", key=f"{prefix}add_room"):
            st.session_state[f"{prefix}num_rooms"] += 1
            st.rerun()

        st.markdown("#### Booking Terms")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Booking Code", key=f"{prefix}booking_code")
            st.number_input("Minimum Stay (nights)", min_value=0, step=1,
                            key=f"{prefix}minimum_stay")
        with c2:
            st.date_input("Cut-off Date", key=f"{prefix}cut_off_date")
        with c3:
            cancel_policy = st.selectbox(
                "Cancellation Policy", cancellation_policies,
                key=f"{prefix}cancellation_policy",
            )
        
        cc1, cc2 = st.columns([1,2])
        with cc1:
            st.number_input("Minimum Stay (nights)", min_value=0, step=1,
                            key=f"{prefix}minimum_stay")
        with cc2:
            if cancel_policy == "Flexible":
                st.number_input("Free cancellation up to X days before arrival",
                                min_value=0, step=1, key=f"{prefix}cancellation_days")
            elif cancel_policy == "Night Deposit":
                st.number_input("Deposit required X days before arrival",
                                min_value=0, step=1, key=f"{prefix}deposit_days")

    st.divider()

    # 3. Meeting Spaces
    st.subheader("3. Meeting Spaces & Events")
    incl_spaces = st.toggle("Includes Meeting Spaces / Events",
                            key=f"{prefix}includes_meeting_spaces")
    if incl_spaces:
        for s_idx in range(1, st.session_state[f"{prefix}num_spaces"] + 1):
            render_space_block(s_idx, prefix)
        if st.button("➕ Add Another Space", key=f"{prefix}add_space"):
            new_idx = st.session_state[f"{prefix}num_spaces"] + 1
            st.session_state[f"{prefix}num_spaces"] = new_idx
            st.session_state[f"{prefix}space_services"][new_idx] = 1
            st.rerun()

    st.divider()

    # Submit
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button(submit_label, type="primary", use_container_width=True,
                     key=f"{prefix}submit_btn"):
            errors = []
            if not st.session_state.get(f"{prefix}submitted_by", "").strip():
                errors.append("Το όνομά σου είναι υποχρεωτικό.")
            if not st.session_state.get(f"{prefix}event_name", "").strip():
                errors.append("Το όνομα του event είναι υποχρεωτικό.")
            if errors:
                for e in errors:
                    st.error(e)
                return False

            with st.spinner("Αποθήκευση..."):
                try:
                    _save_from_state(prefix, incl_acc, incl_spaces)
                    return True
                except Exception as e:
                    st.error(f"❌ Σφάλμα: {e}")
                    return False

    return False


# ─────────────────────────────────────────────
# BUILD & SAVE FROM STATE
# ─────────────────────────────────────────────
def _save_from_state(prefix, incl_acc, incl_spaces):
    p = prefix
    price_combos = get_price_combos()
    event_name   = st.session_state.get(f"{p}event_name", "")
    event_id     = generate_event_id(event_name)

    event_row = {
        "event_id":                event_id,
        "submitted_at":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "submitted_by":            st.session_state.get(f"{p}submitted_by", ""),
        "event_name":              event_name,
        "event_type":              st.session_state.get(f"{p}event_type", ""),
        "event_start":             str(st.session_state.get(f"{p}event_start", "")),
        "event_end":               str(st.session_state.get(f"{p}event_end", "")),
        "attendees":               st.session_state.get(f"{p}attendees", ""),
        "includes_accommodation":  str(incl_acc),
        "acc_start":               str(st.session_state.get(f"{p}acc_start", "")) if incl_acc else "",
        "acc_end":                 str(st.session_state.get(f"{p}acc_end", ""))   if incl_acc else "",
        "booking_code":            st.session_state.get(f"{p}booking_code", "")  if incl_acc else "",
        "cut_off_date":            str(st.session_state.get(f"{p}cut_off_date", "")) if incl_acc else "",
        "cancellation_policy":     st.session_state.get(f"{p}cancellation_policy", "") if incl_acc else "",
        "cancellation_days":       st.session_state.get(f"{p}cancellation_days", "") if incl_acc else "",
        "deposit_days":            st.session_state.get(f"{p}deposit_days", "")  if incl_acc else "",
        "minimum_stay":            st.session_state.get(f"{p}minimum_stay", "")  if incl_acc else "",
        "includes_meeting_spaces": str(incl_spaces),
    }

    room_rows = []
    if incl_acc:
        for i in range(1, st.session_state[f"{p}num_rooms"] + 1):
            rtype = st.session_state.get(f"{p}room{i}_type", "")
            if not rtype:
                continue
            r = {
                "event_id":   event_id,
                "room_type":  rtype,
                "room_count": st.session_state.get(f"{p}room{i}_count", 1),
                "rate_plan":  st.session_state.get(f"{p}room{i}_rate_plan", ""),
            }
            for combo in price_combos:
                k = f"price_{combo.replace('+', '_')}"
                r[k] = st.session_state.get(f"{p}room{i}_{k}", 0)
            room_rows.append(r)

    space_rows   = []
    service_rows = []
    if incl_spaces:
        for s_idx in range(1, st.session_state[f"{p}num_spaces"] + 1):
            sname = st.session_state.get(f"{p}space{s_idx}_name", "")
            if not sname:
                continue
            space_id = generate_space_id(event_id, sname, s_idx)
            space_rows.append({
                "space_id":   space_id,
                "event_id":   event_id,
                "space_name": sname,
            })
            num_sv = st.session_state[f"{p}space_services"].get(s_idx, 1)
            for sv_idx in range(1, num_sv + 1):
                stype = st.session_state.get(f"{p}space{s_idx}_service{sv_idx}_type", "")
                spax  = st.session_state.get(f"{p}space{s_idx}_service{sv_idx}_pax", 0)
                if stype:
                    service_rows.append({
                        "space_id":    space_id,
                        "event_id":    event_id,
                        "service_type":stype,
                        "service_pax": spax,
                    })

    save_event(event_row, room_rows, space_rows, service_rows)
