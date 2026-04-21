"""
shared.py — Κοινός κώδικας για όλες τις σελίδες
Schema: events / rooms / spaces / services / calendar / menus
"""

import sys
sys.dont_write_bytecode = True

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, time as time_type
import hashlib
from utils.db_config import *
from utils.mappings import (
    get_room_types, get_rate_plans, get_cancellation_policies,
    get_space_names, get_services, get_event_types,
    get_price_combos, get_menu_types,
)


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
        "calendar": get_or_create_sheet(wb, "calendar", CALENDAR_HEADER),
        "menus":    get_or_create_sheet(wb, "menus",    MENUS_HEADER),
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
    calendar_df = safe_load("calendar", CALENDAR_HEADER)
    menus_df    = safe_load("menus",    MENUS_HEADER)

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
        "calendar": calendar_df,
        "menus":    menus_df,
    }


# ─────────────────────────────────────────────
# SAVE DATA
# ─────────────────────────────────────────────
def save_event(event_row, room_rows, space_rows, service_rows, calendar_rows, menu_rows):
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
    if calendar_rows:
        data = [[str(cr.get(c, "")) for c in CALENDAR_HEADER] for cr in calendar_rows]
        sheets["calendar"].append_rows(data, value_input_option="USER_ENTERED")
    if menu_rows:
        data = [[str(mr.get(c, "")) for c in MENUS_HEADER] for mr in menu_rows]
        sheets["menus"].append_rows(data, value_input_option="USER_ENTERED")

    load_data.clear()


# ─────────────────────────────────────────────
# DELETE DATA
# ─────────────────────────────────────────────
def delete_event(event_id: str) -> None:
    sheets = get_sheets()
    # Column index where event_id lives in each sheet
    event_id_col = {
        "events":   0,
        "rooms":    0,
        "spaces":   1,
        "services": 1,
        "calendar": 1,
        "menus":    1,
    }
    for sheet_name, ws in sheets.items():
        col_idx = event_id_col[sheet_name]
        rows = ws.get_all_values()
        to_delete = [
            i for i, row in enumerate(rows[1:], start=2)
            if len(row) > col_idx and row[col_idx] == event_id
        ]
        for row_idx in reversed(to_delete):
            ws.delete_rows(row_idx)
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


def generate_calendar_id(event_id: str, day_idx: int) -> str:
    return f"{event_id}_day{day_idx}"


def generate_menu_id(event_id: str, menu_idx: int) -> str:
    return f"{event_id}_menu{menu_idx}"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def event_color(idx: int) -> str:
    return COLOR_PALETTE[idx % len(COLOR_PALETTE)]


def safe_date(val) -> date:
    if val is None or val is pd.NaT:
        return date.today()
    if isinstance(val, date):
        return val
    try:
        ts = pd.to_datetime(val)
        if pd.isna(ts):
            return date.today()
        return ts.date()
    except Exception:
        return date.today()


def safe_time(val) -> time_type:
    if isinstance(val, time_type):
        return val
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return time_type(0, 0)
    try:
        s = str(val).strip()[:5]
        h, m = s.split(":")
        return time_type(int(h), int(m))
    except Exception:
        return time_type(0, 0)


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
            for _, sv in services_df[services_df["space_id"] == sp["space_id"]].iterrows():
                services.append({
                    "type": safe_str(sv.get("service_type")),
                    "pax":  safe_int(sv.get("service_pax")),
                })
        result.append({
            "space_id":         sp["space_id"],
            "space_name":       safe_str(sp.get("space_name")),
            "venue_event_name": safe_str(sp.get("venue_event_name")),
            "venue_date":       sp.get("venue_date"),
            "venue_from":       safe_str(sp.get("venue_from")),
            "venue_to":         safe_str(sp.get("venue_to")),
            "venue_notes":      safe_str(sp.get("venue_notes")),
            "service_notes":    safe_str(sp.get("service_notes")),
            "services":         services,
        })
    return result


def get_event_calendar(calendar_df, event_id):
    if calendar_df.empty:
        return []
    ev_cal = calendar_df[calendar_df["event_id"] == event_id].copy()
    ev_cal["day_number"] = pd.to_numeric(ev_cal["day_number"], errors="coerce").fillna(0).astype(int)
    ev_cal = ev_cal.sort_values("day_number")
    return [
        {
            "calendar_id": row["calendar_id"],
            "day_number":  int(row["day_number"]),
            "day_date":    row.get("day_date"),
            "schedule":    safe_str(row.get("schedule")),
        }
        for _, row in ev_cal.iterrows()
    ]


def get_event_menus(menus_df, event_id):
    if menus_df.empty:
        return []
    return [
        {
            "menu_id":       row["menu_id"],
            "menu_name":     safe_str(row.get("menu_name")),
            "venue_name":    safe_str(row.get("venue_name")),
            "activity_name": safe_str(row.get("activity_name")),
            "menu_date":     row.get("menu_date"),
            "pax_min":       safe_int(row.get("pax_min")),
            "pax_max":       safe_int(row.get("pax_max")),
            "menu_items":    safe_str(row.get("menu_items")),
            "menu_notes":    safe_str(row.get("menu_notes")),
        }
        for _, row in menus_df[menus_df["event_id"] == event_id].iterrows()
    ]


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def init_form_state(prefix=""):
    p = prefix
    if f"{p}room_indices" not in st.session_state:
        st.session_state[f"{p}room_indices"]    = [1]
        st.session_state[f"{p}next_room_idx"]   = 2
    if f"{p}space_indices" not in st.session_state:
        st.session_state[f"{p}space_indices"]           = [1]
        st.session_state[f"{p}next_space_idx"]          = 2
        st.session_state[f"{p}space_service_indices"]   = {1: [1]}
        st.session_state[f"{p}space_next_service_idx"]  = {1: 2}
    if f"{p}calendar_indices" not in st.session_state:
        st.session_state[f"{p}calendar_indices"]  = [1]
        st.session_state[f"{p}next_calendar_idx"] = 2
    if f"{p}menu_indices" not in st.session_state:
        st.session_state[f"{p}menu_indices"]   = [1]
        st.session_state[f"{p}next_menu_idx"]  = 2


def prefill_form_state(event_row, rooms_df, spaces_list,
                       calendar_list=None, menus_list=None, prefix=""):
    p            = prefix
    room_types   = get_room_types()
    rate_plans   = get_rate_plans()
    event_types  = get_event_types()
    price_combos = get_price_combos()
    menu_types   = get_menu_types()
    space_names  = get_space_names()

    # ── Basic ──
    st.session_state[f"{p}submitted_by"]   = safe_str(event_row.get("submitted_by"))
    st.session_state[f"{p}event_name"]     = safe_str(event_row.get("event_name"))
    st.session_state[f"{p}event_type"]     = safe_str(event_row.get("event_type"), event_types[0] if event_types else "")
    st.session_state[f"{p}attendees"]      = safe_int(event_row.get("attendees"))
    st.session_state[f"{p}event_start"]    = safe_date(event_row.get("event_start"))
    st.session_state[f"{p}event_end"]      = safe_date(event_row.get("event_end"))
    st.session_state[f"{p}event_description"] = safe_str(event_row.get("event_description"))
    st.session_state[f"{p}important_info"]    = safe_str(event_row.get("important_info"))

    # ── Organizer ──
    st.session_state[f"{p}includes_organizer_info"] = (
        safe_str(event_row.get("includes_organizer_info")).lower() == "true"
    )
    st.session_state[f"{p}organizer"]      = safe_str(event_row.get("organizer"))
    st.session_state[f"{p}contact_info"]   = safe_str(event_row.get("contact_info"))
    st.session_state[f"{p}special_offers"] = safe_str(event_row.get("special_offers"))
    st.session_state[f"{p}organizer_notes"]= safe_str(event_row.get("organizer_notes"))

    # ── Calendar ──
    st.session_state[f"{p}includes_calendar"] = (
        safe_str(event_row.get("includes_calendar")).lower() == "true"
    )

    # ── Accommodation ──
    st.session_state[f"{p}includes_accommodation"] = (
        safe_str(event_row.get("includes_accommodation")).lower() == "true"
    )
    st.session_state[f"{p}acc_start"]           = safe_date(event_row.get("acc_start"))
    st.session_state[f"{p}acc_end"]             = safe_date(event_row.get("acc_end"))
    st.session_state[f"{p}booking_code"]        = safe_str(event_row.get("booking_code"))
    st.session_state[f"{p}cut_off_date"]        = safe_date(event_row.get("cut_off_date"))
    st.session_state[f"{p}cancellation_policy"] = safe_str(event_row.get("cancellation_policy"), "Flexible")
    st.session_state[f"{p}cancellation_days"]   = safe_int(event_row.get("cancellation_days"))
    st.session_state[f"{p}deposit_days"]        = safe_int(event_row.get("deposit_days"))
    st.session_state[f"{p}minimum_stay"]        = safe_int(event_row.get("minimum_stay"))
    st.session_state[f"{p}accommodation_notes"] = safe_str(event_row.get("accommodation_notes"))

    # ── Venues ──
    st.session_state[f"{p}includes_venues"]    = (
        safe_str(event_row.get("includes_venues")).lower() == "true"
    )
    st.session_state[f"{p}preparation_notes"]  = safe_str(event_row.get("preparation_notes"))

    # ── Menu ──
    st.session_state[f"{p}includes_menu"] = (
        safe_str(event_row.get("includes_menu")).lower() == "true"
    )

    # ── Rooms ──
    if not rooms_df.empty:
        room_idxs = list(range(1, len(rooms_df) + 1))
        st.session_state[f"{p}room_indices"]  = room_idxs
        st.session_state[f"{p}next_room_idx"] = len(rooms_df) + 1
        for i, (_, r) in enumerate(rooms_df.iterrows(), start=1):
            st.session_state[f"{p}room{i}_type"]      = safe_str(r.get("room_type"), room_types[0] if room_types else "")
            st.session_state[f"{p}room{i}_count"]     = safe_int(r.get("room_count"), 1)
            st.session_state[f"{p}room{i}_rate_plan"] = safe_str(r.get("rate_plan"), rate_plans[0] if rate_plans else "")
            st.session_state[f"{p}room{i}_notes"]     = safe_str(r.get("room_notes"))
            for combo in price_combos:
                k = f"price_{combo.replace('+', '_')}"
                st.session_state[f"{p}room{i}_{k}"] = safe_int(r.get(k), 0)
    else:
        st.session_state[f"{p}room_indices"]  = [1]
        st.session_state[f"{p}next_room_idx"] = 2

    # ── Spaces / Venues ──
    if spaces_list:
        sp_idxs      = list(range(1, len(spaces_list) + 1))
        svc_indices  = {}
        svc_next_idx = {}
        st.session_state[f"{p}space_indices"]  = sp_idxs
        st.session_state[f"{p}next_space_idx"] = len(spaces_list) + 1
        for i, sp in enumerate(spaces_list, start=1):
            st.session_state[f"{p}space{i}_name"]             = sp["space_name"]
            st.session_state[f"{p}space{i}_venue_event_name"] = sp.get("venue_event_name", "")
            st.session_state[f"{p}space{i}_venue_date"]       = safe_date(sp.get("venue_date"))
            st.session_state[f"{p}space{i}_venue_from"]       = safe_time(sp.get("venue_from"))
            st.session_state[f"{p}space{i}_venue_to"]         = safe_time(sp.get("venue_to"))
            st.session_state[f"{p}space{i}_venue_notes"]      = sp.get("venue_notes", "")
            st.session_state[f"{p}space{i}_service_notes"]    = sp.get("service_notes", "")
            svcs = sp.get("services", [])
            sv_idxs = list(range(1, len(svcs) + 1)) if svcs else [1]
            svc_indices[i]  = sv_idxs
            svc_next_idx[i] = len(svcs) + 1
            for j, sv in enumerate(svcs, start=1):
                st.session_state[f"{p}space{i}_service{j}_type"] = sv["type"]
                st.session_state[f"{p}space{i}_service{j}_pax"]  = sv["pax"]
        st.session_state[f"{p}space_service_indices"]  = svc_indices
        st.session_state[f"{p}space_next_service_idx"] = svc_next_idx
    else:
        st.session_state[f"{p}space_indices"]          = [1]
        st.session_state[f"{p}next_space_idx"]         = 2
        st.session_state[f"{p}space_service_indices"]  = {1: [1]}
        st.session_state[f"{p}space_next_service_idx"] = {1: 2}

    # ── Calendar ──
    cal = calendar_list or []
    if cal:
        cal_idxs = list(range(1, len(cal) + 1))
        st.session_state[f"{p}calendar_indices"]  = cal_idxs
        st.session_state[f"{p}next_calendar_idx"] = len(cal) + 1
        for i, day in enumerate(cal, start=1):
            st.session_state[f"{p}calendar_day{i}_date"]     = safe_date(day.get("day_date"))
            st.session_state[f"{p}calendar_day{i}_schedule"] = day.get("schedule", "")
    else:
        st.session_state[f"{p}calendar_indices"]  = [1]
        st.session_state[f"{p}next_calendar_idx"] = 2

    # ── Menus ──
    mens = menus_list or []
    if mens:
        menu_idxs = list(range(1, len(mens) + 1))
        st.session_state[f"{p}menu_indices"]  = menu_idxs
        st.session_state[f"{p}next_menu_idx"] = len(mens) + 1
        for i, mn in enumerate(mens, start=1):
            st.session_state[f"{p}menu{i}_name"]          = mn.get("menu_name", menu_types[0] if menu_types else "")
            st.session_state[f"{p}menu{i}_venue_name"]    = mn.get("venue_name", space_names[0] if space_names else "")
            st.session_state[f"{p}menu{i}_activity_name"] = mn.get("activity_name", "")
            st.session_state[f"{p}menu{i}_date"]          = safe_date(mn.get("menu_date"))
            st.session_state[f"{p}menu{i}_pax_min"]       = safe_int(mn.get("pax_min"))
            st.session_state[f"{p}menu{i}_pax_max"]       = safe_int(mn.get("pax_max"))
            st.session_state[f"{p}menu{i}_items"]         = mn.get("menu_items", "")
            st.session_state[f"{p}menu{i}_notes"]         = mn.get("menu_notes", "")
    else:
        st.session_state[f"{p}menu_indices"]  = [1]
        st.session_state[f"{p}next_menu_idx"] = 2


# ─────────────────────────────────────────────
# FORM UI BLOCKS
# ─────────────────────────────────────────────
def render_room_block(idx, prefix=""):
    p            = prefix
    room_types   = get_room_types()
    rate_plans   = get_rate_plans()
    price_combos = get_price_combos()

    with st.container(border=True):
        col_h, col_r = st.columns([10, 1])
        col_h.markdown(f"**🛏️ Room Type {idx}**")
        room_indices = st.session_state.get(f"{p}room_indices", [idx])
        if col_r.button("✖", key=f"{p}rm_room_{idx}", help="Delete",
                        disabled=len(room_indices) <= 1):
            room_indices.remove(idx)
            st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.selectbox("Room Type", room_types, key=f"{p}room{idx}_type")
        with c2:
            st.number_input("Number of Rooms", min_value=1, step=1, value=1,
                            key=f"{p}room{idx}_count")
        with c3:
            st.selectbox("Rate Plan", rate_plans, key=f"{p}room{idx}_rate_plan")

        st.markdown("**Prices (€) — fill in what applies:**")
        pcols = st.columns(len(price_combos))
        for ci, combo in enumerate(price_combos):
            with pcols[ci]:
                st.number_input(combo, min_value=0, step=1, value=0,
                                key=f"{p}room{idx}_price_{combo.replace('+', '_')}")

        st.text_area("Room Notes", key=f"{p}room{idx}_notes", height=80,
                     placeholder="Any notes about this room type...")


def render_venue_block(s_idx, prefix=""):
    p           = prefix
    space_names = get_space_names()
    services    = get_services()

    with st.container(border=True):
        col_h, col_r = st.columns([10, 1])
        col_h.markdown(f"**🏛️ Venue {s_idx}**")
        space_indices = st.session_state.get(f"{p}space_indices", [s_idx])
        if col_r.button("✖", key=f"{p}rm_space_{s_idx}", help="Delete",
                        disabled=len(space_indices) <= 1):
            space_indices.remove(s_idx)
            st.rerun()

        # ── Venue identification ──
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Event Name", key=f"{p}space{s_idx}_venue_event_name",
                          placeholder="e.g. Welcome Dinner")
        with c2:
            st.selectbox("Venue Name", space_names, key=f"{p}space{s_idx}_name")

        # ── Date & Time ──
        c1, c2, c3 = st.columns(3)
        with c1:
            st.date_input("Date", key=f"{p}space{s_idx}_venue_date")
        with c2:
            st.time_input("From", key=f"{p}space{s_idx}_venue_from",
                          value=time_type(9, 0), step=900)
        with c3:
            st.time_input("To", key=f"{p}space{s_idx}_venue_to",
                          value=time_type(18, 0), step=900)

        st.text_area("Venue Notes", key=f"{p}space{s_idx}_venue_notes", height=80,
                     placeholder="Setup, layout, equipment notes...")

        # ── Services ──
        st.markdown("**Services**")
        svc_indices = st.session_state.get(f"{p}space_service_indices", {}).get(s_idx, [1])
        for sv_idx in list(svc_indices):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.selectbox(f"Service {sv_idx}", services,
                             key=f"{p}space{s_idx}_service{sv_idx}_type")
            with c2:
                st.number_input(f"Pax {sv_idx}", min_value=0, step=1,
                                key=f"{p}space{s_idx}_service{sv_idx}_pax")
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✖", key=f"{p}rm_svc_{s_idx}_{sv_idx}", help="Delete",
                             disabled=len(svc_indices) <= 1):
                    svc_indices.remove(sv_idx)
                    st.session_state[f"{p}space_service_indices"][s_idx] = svc_indices
                    st.rerun()

        if st.button("➕ Add Service", key=f"{p}add_svc_{s_idx}"):
            nx = st.session_state.get(f"{p}space_next_service_idx", {}).get(s_idx, len(svc_indices) + 1)
            svc_indices.append(nx)
            st.session_state[f"{p}space_service_indices"][s_idx] = svc_indices
            st.session_state.setdefault(f"{p}space_next_service_idx", {})[s_idx] = nx + 1
            st.rerun()

        st.text_area("Service Notes", key=f"{p}space{s_idx}_service_notes", height=80,
                     placeholder="Catering notes, serving style...")


def render_calendar_block(day_idx, prefix=""):
    p = prefix
    with st.container(border=True):
        col_h, col_r = st.columns([10, 1])
        col_h.markdown(f"**📅 Day {day_idx}**")
        cal_indices = st.session_state.get(f"{p}calendar_indices", [day_idx])
        if col_r.button("✖", key=f"{p}rm_cal_{day_idx}", help="Delete"):
            cal_indices.remove(day_idx)
            st.rerun()

        st.date_input("Date", key=f"{p}calendar_day{day_idx}_date")
        st.text_area("Schedule", key=f"{p}calendar_day{day_idx}_schedule", height=120,
                     placeholder="Detailed daily schedule...")


def render_menu_block(menu_idx, prefix=""):
    p           = prefix
    menu_types  = get_menu_types()
    space_names = get_space_names()

    with st.container(border=True):
        col_h, col_r = st.columns([10, 1])
        col_h.markdown(f"**🍽️ Menu {menu_idx}**")
        menu_indices = st.session_state.get(f"{p}menu_indices", [menu_idx])
        if col_r.button("✖", key=f"{p}rm_menu_{menu_idx}", help="Delete"):
            menu_indices.remove(menu_idx)
            st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.selectbox("Menu Name", menu_types, key=f"{p}menu{menu_idx}_name")
        with c2:
            st.selectbox("Venue Name", space_names, key=f"{p}menu{menu_idx}_venue_name")
        with c3:
            st.text_input("Activity Name", key=f"{p}menu{menu_idx}_activity_name",
                          placeholder="e.g. Welcome Dinner")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.date_input("Date", key=f"{p}menu{menu_idx}_date")
        with c2:
            st.number_input("Pax Min", min_value=0, step=1, key=f"{p}menu{menu_idx}_pax_min")
        with c3:
            st.number_input("Pax Max", min_value=0, step=1, key=f"{p}menu{menu_idx}_pax_max")

        st.text_area("Menu Items", key=f"{p}menu{menu_idx}_items", height=100,
                     placeholder="Dish description, options, allergies...")
        st.text_area("Notes on the Menu", key=f"{p}menu{menu_idx}_notes", height=80,
                     placeholder="Special requirements, notes...")


# ─────────────────────────────────────────────
# FULL FORM
# ─────────────────────────────────────────────
def render_event_form(prefix="", submit_label="💾 Save Event"):
    init_form_state(prefix)
    p = prefix

    event_types           = get_event_types()
    cancellation_policies = get_cancellation_policies()

    # ═══════════════════════════════════════
    # 1. BASIC INFORMATION
    # ═══════════════════════════════════════
    st.subheader("1. Basic Information")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Your Name *", key=f"{p}submitted_by")
        st.text_input("Event Name *", key=f"{p}event_name")
        st.selectbox("Event Type *", event_types, key=f"{p}event_type")
    with c2:
        st.date_input("Event Start Date *", key=f"{p}event_start")
        st.date_input("Event End Date *",   key=f"{p}event_end")
        st.number_input("Number of Attendees", min_value=1, step=1, key=f"{p}attendees")

    st.text_area("Event Description", key=f"{p}event_description", height=120,
                 placeholder="Brief description of the event...")
    st.text_area("Important Info", key=f"{p}important_info", height=100,
                 placeholder="Important information, special requirements...")

    st.divider()

    # ═══════════════════════════════════════
    # 2. EVENT ORGANIZERS & VIPs
    # ═══════════════════════════════════════
    st.subheader("2. Event Organizers & VIPs")
    incl_organizer = st.toggle("Includes Organizer Info", key=f"{p}includes_organizer_info")
    if incl_organizer:
        st.text_input("Organizer", key=f"{p}organizer", placeholder="Name / Company")
        st.text_area("Contact Info", key=f"{p}contact_info", height=80,
                     placeholder="Other names, Phones, emails, etc")
        st.text_area("Special Offers", key=f"{p}special_offers", height=80,
                     placeholder="Special benefits / discounts for the organizer...")
        st.text_area("Notes", key=f"{p}organizer_notes", height=80,
                     placeholder="Any other notes...")

    st.divider()

    # ═══════════════════════════════════════
    # 3. ACTIVITY CALENDAR
    # ═══════════════════════════════════════
    st.subheader("3. Activity Calendar")
    incl_calendar = st.toggle("Includes Calendar", key=f"{p}includes_calendar")
    if incl_calendar:
        for day_idx in list(st.session_state[f"{p}calendar_indices"]):
            render_calendar_block(day_idx, p)
        if st.button("➕ Add Extra Day", key=f"{p}add_cal_day"):
            nx = st.session_state[f"{p}next_calendar_idx"]
            st.session_state[f"{p}calendar_indices"].append(nx)
            st.session_state[f"{p}next_calendar_idx"] = nx + 1
            st.rerun()

    st.divider()

    # ═══════════════════════════════════════
    # 4. ACCOMMODATION
    # ═══════════════════════════════════════
    st.subheader("4. Accommodation")
    incl_acc = st.toggle("Includes Accommodation", key=f"{p}includes_accommodation")
    if incl_acc:
        same_dates = st.toggle("Same dates as the event", value=True,
                               key=f"{p}acc_same_dates")
        if not same_dates:
            c1, c2 = st.columns(2)
            with c1:
                st.date_input("Check-in Date",  key=f"{p}acc_start")
            with c2:
                st.date_input("Check-out Date", key=f"{p}acc_end")
        else:
            st.session_state[f"{p}acc_start"] = st.session_state.get(f"{p}event_start")
            st.session_state[f"{p}acc_end"]   = st.session_state.get(f"{p}event_end")
            c1, c2 = st.columns(2)
            with c1:
                st.date_input("Check-in Date",  key=f"{p}acc_start", disabled=True)
            with c2:
                st.date_input("Check-out Date", key=f"{p}acc_end",   disabled=True)

        # ── Booking Terms ──
        st.markdown("#### Booking Terms")

        r1_c1, r1_c2 = st.columns(2)
        with r1_c1:
            st.text_input("Booking Code", key=f"{p}booking_code")
        with r1_c2:
            st.date_input("Cut-off Date", key=f"{p}cut_off_date")

        r2_c1, r2_c2 = st.columns(2)
        with r2_c1:
            st.number_input("Minimum Nights Stay (optional)", min_value=0, step=1,
                            key=f"{p}minimum_stay")
        with r2_c2:
            cancel_policy = st.selectbox(
                "Cancellation Policy", cancellation_policies,
                key=f"{p}cancellation_policy",
            )

        if cancel_policy == "Flexible":
            st.number_input("Free cancellation up to X days before arrival",
                            min_value=0, step=1, key=f"{p}cancellation_days")
        elif cancel_policy == "Night Deposit":
            st.number_input("X Nights Deposit (Non Refundable)",
                            min_value=0, step=1, key=f"{p}deposit_days")

        st.text_area("Accommodation Notes", key=f"{p}accommodation_notes", height=100,
                     placeholder="Special requests, comments about the rooms...")

        # ── Room Types ──
        st.markdown("#### Room Types")
        for i in list(st.session_state[f"{p}room_indices"]):
            render_room_block(i, p)
        if st.button("➕ Add Another Room Type", key=f"{p}add_room"):
            nx = st.session_state[f"{p}next_room_idx"]
            st.session_state[f"{p}room_indices"].append(nx)
            st.session_state[f"{p}next_room_idx"] = nx + 1
            st.rerun()

    st.divider()

    # ═══════════════════════════════════════
    # 5. VENUES & SERVICES
    # ═══════════════════════════════════════
    st.subheader("5. Venues & Services")
    incl_venues = st.toggle("Includes Venues & Services", key=f"{p}includes_venues")
    if incl_venues:
        st.text_area("Preparation Notes", key=f"{p}preparation_notes", height=100,
                     placeholder="General preparation notes for all venues...")
        for s_idx in list(st.session_state[f"{p}space_indices"]):
            render_venue_block(s_idx, p)
        if st.button("➕ Add Another Venue", key=f"{p}add_space"):
            nx = st.session_state[f"{p}next_space_idx"]
            st.session_state[f"{p}space_indices"].append(nx)
            st.session_state[f"{p}next_space_idx"] = nx + 1
            st.session_state[f"{p}space_service_indices"][nx] = [1]
            st.session_state[f"{p}space_next_service_idx"][nx] = 2
            st.rerun()

    st.divider()

    # ═══════════════════════════════════════
    # 6. MENUS
    # ═══════════════════════════════════════
    st.subheader("6. Menus")
    incl_menu = st.toggle("Includes Menu", key=f"{p}includes_menu")
    if incl_menu:
        for menu_idx in list(st.session_state[f"{p}menu_indices"]):
            render_menu_block(menu_idx, p)
        if st.button("➕ Add Extra Menu", key=f"{p}add_menu"):
            nx = st.session_state[f"{p}next_menu_idx"]
            st.session_state[f"{p}menu_indices"].append(nx)
            st.session_state[f"{p}next_menu_idx"] = nx + 1
            st.rerun()

    st.divider()

    # ── Submit ──
    _, col2, _ = st.columns(3)
    with col2:
        if st.button(submit_label, type="primary", use_container_width=True,
                     key=f"{p}submit_btn"):
            errors = []
            if not st.session_state.get(f"{p}submitted_by", "").strip():
                errors.append("Your name is required..")
            if not st.session_state.get(f"{p}event_name", "").strip():
                errors.append("Event name is required.")
            if errors:
                for e in errors:
                    st.error(e)
                return False
            with st.spinner("Saving..."):
                try:
                    _save_from_state(p)
                    return True
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    return False
    return False


# ─────────────────────────────────────────────
# BUILD & SAVE FROM STATE
# ─────────────────────────────────────────────
def _save_from_state(prefix):
    p            = prefix
    price_combos = get_price_combos()
    event_name   = st.session_state.get(f"{p}event_name", "")
    event_id     = generate_event_id(event_name)

    incl_acc       = st.session_state.get(f"{p}includes_accommodation", False)
    incl_organizer = st.session_state.get(f"{p}includes_organizer_info", False)
    incl_calendar  = st.session_state.get(f"{p}includes_calendar", False)
    incl_venues    = st.session_state.get(f"{p}includes_venues", False)
    incl_menu      = st.session_state.get(f"{p}includes_menu", False)

    event_row = {
        "event_id":               event_id,
        "submitted_at":           datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "submitted_by":           st.session_state.get(f"{p}submitted_by", ""),
        "event_name":             event_name,
        "event_type":             st.session_state.get(f"{p}event_type", ""),
        "event_start":            str(st.session_state.get(f"{p}event_start", "")),
        "event_end":              str(st.session_state.get(f"{p}event_end", "")),
        "attendees":              st.session_state.get(f"{p}attendees", ""),
        "includes_accommodation": str(incl_acc),
        "acc_start":              str(st.session_state.get(f"{p}acc_start", "")) if incl_acc else "",
        "acc_end":                str(st.session_state.get(f"{p}acc_end", ""))   if incl_acc else "",
        "booking_code":           st.session_state.get(f"{p}booking_code", "")  if incl_acc else "",
        "cut_off_date":           str(st.session_state.get(f"{p}cut_off_date", "")) if incl_acc else "",
        "cancellation_policy":    st.session_state.get(f"{p}cancellation_policy", "") if incl_acc else "",
        "cancellation_days":      st.session_state.get(f"{p}cancellation_days", "") if incl_acc else "",
        "deposit_days":           st.session_state.get(f"{p}deposit_days", "")  if incl_acc else "",
        "minimum_stay":           st.session_state.get(f"{p}minimum_stay", "")  if incl_acc else "",
        "includes_venues":        str(incl_venues),
        "event_description":      st.session_state.get(f"{p}event_description", ""),
        "important_info":         st.session_state.get(f"{p}important_info", ""),
        "includes_organizer_info":str(incl_organizer),
        "organizer":              st.session_state.get(f"{p}organizer", "")       if incl_organizer else "",
        "contact_info":           st.session_state.get(f"{p}contact_info", "")   if incl_organizer else "",
        "special_offers":         st.session_state.get(f"{p}special_offers", "") if incl_organizer else "",
        "organizer_notes":        st.session_state.get(f"{p}organizer_notes", "")if incl_organizer else "",
        "includes_calendar":      str(incl_calendar),
        "accommodation_notes":    st.session_state.get(f"{p}accommodation_notes", "") if incl_acc else "",
        "preparation_notes":      st.session_state.get(f"{p}preparation_notes", "") if incl_venues else "",
        "includes_menu":          str(incl_menu),
    }

    # ── Rooms ──
    room_rows = []
    if incl_acc:
        for i in st.session_state.get(f"{p}room_indices", []):
            rtype = st.session_state.get(f"{p}room{i}_type", "")
            if not rtype:
                continue
            r = {
                "event_id":   event_id,
                "room_type":  rtype,
                "room_count": st.session_state.get(f"{p}room{i}_count", 1),
                "rate_plan":  st.session_state.get(f"{p}room{i}_rate_plan", ""),
                "room_notes": st.session_state.get(f"{p}room{i}_notes", ""),
            }
            for combo in price_combos:
                k = f"price_{combo.replace('+', '_')}"
                r[k] = st.session_state.get(f"{p}room{i}_{k}", 0)
            room_rows.append(r)

    # ── Venues / Spaces ──
    space_rows, service_rows = [], []
    if incl_venues:
        for s_idx in st.session_state.get(f"{p}space_indices", []):
            sname = st.session_state.get(f"{p}space{s_idx}_name", "")
            if not sname:
                continue
            space_id = generate_space_id(event_id, sname, s_idx)
            from_val = st.session_state.get(f"{p}space{s_idx}_venue_from", time_type(0, 0))
            to_val   = st.session_state.get(f"{p}space{s_idx}_venue_to",   time_type(0, 0))
            from_str = from_val.strftime("%H:%M") if isinstance(from_val, time_type) else str(from_val)[:5]
            to_str   = to_val.strftime("%H:%M")   if isinstance(to_val,   time_type) else str(to_val)[:5]
            space_rows.append({
                "space_id":         space_id,
                "event_id":         event_id,
                "space_name":       sname,
                "venue_event_name": st.session_state.get(f"{p}space{s_idx}_venue_event_name", ""),
                "venue_date":       str(st.session_state.get(f"{p}space{s_idx}_venue_date", "")),
                "venue_from":       from_str,
                "venue_to":         to_str,
                "venue_notes":      st.session_state.get(f"{p}space{s_idx}_venue_notes", ""),
                "service_notes":    st.session_state.get(f"{p}space{s_idx}_service_notes", ""),
            })
            svc_indices = st.session_state.get(f"{p}space_service_indices", {}).get(s_idx, [])
            for sv_idx in svc_indices:
                stype = st.session_state.get(f"{p}space{s_idx}_service{sv_idx}_type", "")
                spax  = st.session_state.get(f"{p}space{s_idx}_service{sv_idx}_pax", 0)
                if stype:
                    service_rows.append({
                        "space_id":    space_id,
                        "event_id":    event_id,
                        "service_type":stype,
                        "service_pax": spax,
                    })

    # ── Calendar ──
    calendar_rows = []
    if incl_calendar:
        for day_idx in st.session_state.get(f"{p}calendar_indices", []):
            calendar_rows.append({
                "calendar_id": generate_calendar_id(event_id, day_idx),
                "event_id":    event_id,
                "day_number":  day_idx,
                "day_date":    str(st.session_state.get(f"{p}calendar_day{day_idx}_date", "")),
                "schedule":    st.session_state.get(f"{p}calendar_day{day_idx}_schedule", ""),
            })

    # ── Menus ──
    menu_rows = []
    if incl_menu:
        for menu_idx in st.session_state.get(f"{p}menu_indices", []):
            menu_rows.append({
                "menu_id":       generate_menu_id(event_id, menu_idx),
                "event_id":      event_id,
                "menu_name":     st.session_state.get(f"{p}menu{menu_idx}_name", ""),
                "venue_name":    st.session_state.get(f"{p}menu{menu_idx}_venue_name", ""),
                "activity_name": st.session_state.get(f"{p}menu{menu_idx}_activity_name", ""),
                "menu_date":     str(st.session_state.get(f"{p}menu{menu_idx}_date", "")),
                "pax_min":       st.session_state.get(f"{p}menu{menu_idx}_pax_min", 0),
                "pax_max":       st.session_state.get(f"{p}menu{menu_idx}_pax_max", 0),
                "menu_items":    st.session_state.get(f"{p}menu{menu_idx}_items", ""),
                "menu_notes":    st.session_state.get(f"{p}menu{menu_idx}_notes", ""),
            })

    save_event(event_row, room_rows, space_rows, service_rows, calendar_rows, menu_rows)
