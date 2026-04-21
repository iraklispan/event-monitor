# Location => ./pages/1_dashboard.py

import sys
sys.dont_write_bytecode = True

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import base64
import streamlit.components.v1 as components

from shared import (
    load_data, event_color, num_days,
    get_event_rooms, get_event_spaces, get_event_calendar, get_event_menus,
    render_event_form, prefill_form_state, init_form_state,
    delete_event,
)
from utils.mappings import get_price_combos
from utils.sidebar import sidebar
from utils.auth import require_login, is_admin

st.set_page_config(
    page_title="Event Dashboard",
    page_icon="📊",
    layout="wide",
)

require_login()
sidebar()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def count_rooms_from_df(rooms_df, event_id):
    if rooms_df.empty:
        return 0
    ev = rooms_df[rooms_df["event_id"] == event_id]
    total = 0
    for _, r in ev.iterrows():
        try:
            total += int(float(r.get("room_count", 0) or 0))
        except Exception:
            pass
    return total


def count_spaces_from_df(spaces_df, event_id):
    if spaces_df.empty:
        return 0
    return len(spaces_df[spaces_df["event_id"] == event_id])


def generate_printable_html(event_row, rooms_df, spaces_list, color):
    price_combos = get_price_combos()
    ev_start = event_row["event_start"].strftime("%d/%m/%Y") if pd.notna(event_row.get("event_start")) else "—"
    ev_end   = event_row["event_end"].strftime("%d/%m/%Y")   if pd.notna(event_row.get("event_end"))   else "—"
    duration  = f"{num_days(event_row)} nights"
    attendees = int(event_row.get("attendees", 0) or 0)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Print - {event_row['event_name']}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #1e293b; line-height: 1.5; }}
            .card-header {{ border-left: 6px solid {color}; padding: 15px 25px; background: #f8fafc; border-radius: 8px; margin-bottom: 30px; }}
            h1 {{ margin: 0 0 5px 0; font-size: 24px; }}
            p.subtitle {{ margin: 0; color: #64748b; font-size: 14px; }}
            h2 {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; margin-top: 30px; font-size: 18px; color: #0f172a; }}
            .section {{ margin-bottom: 25px; page-break-inside: avoid; break-inside: avoid; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; page-break-inside: avoid; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 10px; text-align: left; }}
            th {{ background-color: #f1f5f9; font-weight: 600; }}
            .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-top: 15px; page-break-inside: avoid; }}
            .metric-box {{ background: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; }}
            .metric-label {{ font-size: 12px; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px; margin-bottom: 5px; }}
            .metric-value {{ font-size: 18px; font-weight: 600; color: #0f172a; }}
            .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: 500; margin-top: 10px; }}
            .badge-flexible {{ background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }}
            .badge-deposit  {{ background: #fef08a; color: #854d0e; border: 1px solid #fde047; }}
            .badge-nonref   {{ background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}
            @media print {{
                body {{ padding: 0; }}
                .no-print {{ display: none !important; }}
            }}
            .print-btn {{
                display: block; width: 200px; margin: 0 auto 30px auto; padding: 12px;
                background: #334155; color: white; text-align: center; border-radius: 6px;
                text-decoration: none; font-weight: bold; cursor: pointer; border: none;
            }}
            .print-btn:hover {{ background: #0f172a; }}
        </style>
    </head>
    <body onload="window.print()">
    <button class="no-print print-btn" onclick="window.print()">🖨️ Εκτύπωση / Save as PDF</button>

        <div class="card-header section">
            <h1>{event_row['event_name']}</h1>
            <p class="subtitle">Submitted by <b>{event_row.get('submitted_by', '—')}</b></p>
        </div>

        <div class="section">
            <h2>📌 General Information</h2>
            <div class="metrics-grid">
                <div class="metric-box"><div class="metric-label">Type</div><div class="metric-value">{event_row.get("event_type") or "—"}</div></div>
                <div class="metric-box"><div class="metric-label">Start</div><div class="metric-value">{ev_start}</div></div>
                <div class="metric-box"><div class="metric-label">End</div><div class="metric-value">{ev_end}</div></div>
                <div class="metric-box"><div class="metric-label">Duration</div><div class="metric-value">{duration}</div></div>
                <div class="metric-box"><div class="metric-label">Attendees</div><div class="metric-value">{attendees}</div></div>
            </div>
        </div>
    """

    if str(event_row.get("includes_accommodation", "")).lower() == "true":
        acc_start = event_row.get("acc_start")
        acc_end   = event_row.get("acc_end")
        a_start_str = acc_start.strftime("%d/%m/%Y") if pd.notna(acc_start) else "—"
        a_end_str   = acc_end.strftime("%d/%m/%Y")   if pd.notna(acc_end)   else "—"
        b_code  = event_row.get("booking_code") or "—"
        m_stay  = f"{int(event_row.get('minimum_stay', 0) or 0)} nights"
        policy  = event_row.get("cancellation_policy", "—")

        policy_html = ""
        if policy == "Flexible":
            days = int(event_row.get('cancellation_days', 0) or 0)
            policy_html = f'<div class="badge badge-flexible">✅ Flexible — Free cancellation up to {days} days before arrival</div>'
        elif policy == "Night Deposit":
            days = int(event_row.get('deposit_days', 0) or 0)
            policy_html = f'<div class="badge badge-deposit">💳 Night Deposit — Required {days} days before arrival</div>'
        elif policy == "Non Refundable":
            policy_html = '<div class="badge badge-nonref">🔒 Non Refundable</div>'

        cut_off     = event_row.get("cut_off_date")
        cut_off_str = cut_off.strftime("%d/%m/%Y") if pd.notna(cut_off) else "—"

        html += f"""
        <div class="section">
            <h2>🛏️ Accommodation</h2>
            <div class="metrics-grid">
                <div class="metric-box"><div class="metric-label">Check-in</div><div class="metric-value">{a_start_str}</div></div>
                <div class="metric-box"><div class="metric-label">Check-out</div><div class="metric-value">{a_end_str}</div></div>
                <div class="metric-box"><div class="metric-label">Booking Code</div><div class="metric-value">{b_code}</div></div>
                <div class="metric-box"><div class="metric-label">Min Stay</div><div class="metric-value">{m_stay}</div></div>
            </div>
            {policy_html}
            <div style="margin-top: 15px; font-size: 14px;"><b>Cut-off Date:</b> {cut_off_str}</div>
        """

        if not rooms_df.empty:
            html += """
            <h3 style="margin-top: 20px; font-size: 16px;">Room Types</h3>
            <table>
                <thead><tr><th>Room Type</th><th>Count</th><th>Rate Plan</th><th>Prices</th></tr></thead>
                <tbody>
            """
            for _, r in rooms_df.iterrows():
                prices = []
                for combo in price_combos:
                    k = f"price_{combo.replace('+', '_')}"
                    try:
                        v = int(float(r.get(k, 0) or 0))
                    except Exception:
                        v = 0
                    if v > 0:
                        prices.append(f"{combo}: €{v}")
                prices_str = ", ".join(prices) if prices else "—"
                html += f"""
                    <tr>
                        <td>{r.get('room_type', '')}</td>
                        <td>{int(float(r.get('room_count', 0) or 0))}</td>
                        <td>{r.get('rate_plan', '—')}</td>
                        <td>{prices_str}</td>
                    </tr>
                """
            html += "</tbody></table>"
        html += "</div>"

    if str(event_row.get("includes_venues", "")).lower() == "true" and spaces_list:
        html += '<div class="section"><h2>🏛️ Venues &amp; Services</h2>'
        prep = event_row.get("preparation_notes", "")
        if prep:
            html += f'<p style="margin-bottom:12px;"><b>Preparation Notes:</b> {prep}</p>'
        for sp in spaces_list:
            venue_date = sp.get("venue_date", "")
            if hasattr(venue_date, "strftime"):
                venue_date = venue_date.strftime("%d/%m/%Y") if pd.notna(venue_date) else "—"
            html += f"""
            <div class="section" style="margin-bottom:15px;border:1px solid #e2e8f0;padding:15px;border-radius:6px;">
                <h3 style="margin-top:0;margin-bottom:6px;">{sp.get('venue_event_name') or sp['space_name']}</h3>
                <p style="margin:0 0 8px 0;color:#64748b;font-size:13px;">
                    📍 {sp['space_name']} &nbsp;|&nbsp;
                    📅 {venue_date} &nbsp;|&nbsp;
                    🕐 {sp.get('venue_from','—')} – {sp.get('venue_to','—')}
                </p>
            """
            if sp.get("venue_notes"):
                html += f'<p style="font-size:13px;"><b>Venue Notes:</b> {sp["venue_notes"]}</p>'
            if sp["services"]:
                html += """
                <table>
                    <thead><tr><th>Service</th><th>Pax</th></tr></thead>
                    <tbody>
                """
                for sv in sp["services"]:
                    html += f"<tr><td>{sv['type']}</td><td>{sv['pax']}</td></tr>"
                html += "</tbody></table>"
            if sp.get("service_notes"):
                html += f'<p style="margin-top:8px;font-size:13px;"><b>Service Notes:</b> {sp["service_notes"]}</p>'
            html += "</div>"
        html += "</div>"

    html += "</body></html>"
    return html


# ─────────────────────────────────────────────
# CLIENT CARD
# ─────────────────────────────────────────────
def render_client_card(event_row, rooms_df, spaces_list, color, row_idx,
                       calendar_list=None, menus_list=None):
    price_combos   = get_price_combos()
    calendar_list  = calendar_list or []
    menus_list     = menus_list or []

    st.markdown(
        f"""<div style="border-left:5px solid {color};padding:0.6rem 1.2rem;
        background:#f8fafc;border-radius:8px;margin-bottom:1rem;">
        <h3 style="margin:0;color:#1e293b;">{event_row['event_name']}</h3>
        <p style="margin:0;color:#64748b;">Submitted by
        <b>{event_row.get('submitted_by','—')}</b></p>
        </div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([2, 2, 8])
    with c1:
        if st.button("✏️ Edit", key=f"edit_btn_{row_idx}"):
            st.session_state["editing_event"] = event_row["event_name"]
            init_form_state("edit_")
            prefill_form_state(event_row, rooms_df, spaces_list,
                               calendar_list, menus_list, prefix="edit_")
            st.rerun()

    with c2:
        if is_admin() and st.button("🗑️ Delete", key=f"del_btn_{row_idx}", type="secondary"):
            @st.dialog("🗑️ Διαγραφή Event")
            def _confirm_delete():
                st.write(f"Διαγραφή του event **{event_row['event_name']}**;")
                st.warning("Η ενέργεια είναι μη αναστρέψιμη — διαγράφονται όλα τα δεδομένα του event.")
                d1, d2 = st.columns(2)
                with d1:
                    if st.button("✅ Διαγραφή", type="primary", use_container_width=True, key="del_ok"):
                        with st.spinner("Διαγραφή..."):
                            delete_event(event_row["event_id"])
                        st.rerun()
                with d2:
                    if st.button("❌ Άκυρο", use_container_width=True, key="del_cancel"):
                        st.rerun()
            _confirm_delete()

    with c3:
        html_content = generate_printable_html(event_row, rooms_df, spaces_list, color)
        b64 = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
        button_html = f"""
        <style>
        body {{ margin: 0; padding: 0; }}
        .print-btn {{
            padding: 6px 14px; background-color: white; color: #334155;
            border-radius: 6px; border: 1px solid #cbd5e1; font-weight: 500;
            font-size: 14px; font-family: 'Segoe UI', Roboto, sans-serif;
            cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: all 0.2s;
        }}
        .print-btn:hover {{ border-color: #94a3b8; background-color: #f8fafc; }}
        </style>
        <button class="print-btn" onclick="
            const binary = atob('{b64}');
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {{ bytes[i] = binary.charCodeAt(i); }}
            const decodedHtml = new TextDecoder('utf-8').decode(bytes);
            const w = window.open('', '_blank');
            w.document.open(); w.document.write(decodedHtml); w.document.close();
        ">🖨️ Εκτύπωση / PDF</button>
        """
        components.html(button_html, height=40)

    # ── General Information ──
    with st.expander("📌 General Information", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Type", event_row.get("event_type") or "—")
        c2.metric("Start", event_row["event_start"].strftime("%d/%m/%Y")
                  if pd.notna(event_row["event_start"]) else "—")
        c3.metric("End", event_row["event_end"].strftime("%d/%m/%Y")
                  if pd.notna(event_row["event_end"]) else "—")
        c4.metric("Duration", f"{num_days(event_row)} nights")
        c5.metric("Attendees", int(event_row.get("attendees", 0) or 0))
        desc = event_row.get("event_description", "")
        info = event_row.get("important_info", "")
        if desc:
            st.markdown(f"**Description:** {desc}")
        if info:
            st.markdown(f"**Important Info:** {info}")

    # ── Organizers & VIPs ──
    if str(event_row.get("includes_organizer_info", "")).lower() == "true":
        with st.expander("👤 Organizers & VIPs", expanded=False):
            st.markdown(f"**Organizer:** {event_row.get('organizer') or '—'}")
            if event_row.get("contact_info"):
                st.markdown(f"**Contact:** {event_row['contact_info']}")
            if event_row.get("special_offers"):
                st.markdown(f"**Special Offers:** {event_row['special_offers']}")
            if event_row.get("organizer_notes"):
                st.markdown(f"**Notes:** {event_row['organizer_notes']}")

    # ── Activity Calendar ──
    if str(event_row.get("includes_calendar", "")).lower() == "true" and calendar_list:
        with st.expander("📅 Activity Calendar", expanded=False):
            for day in calendar_list:
                day_date = day.get("day_date", "")
                if hasattr(day_date, "strftime"):
                    try:
                        day_date = pd.to_datetime(day_date).strftime("%d/%m/%Y")
                    except Exception:
                        day_date = str(day_date)
                st.markdown(f"**Day {day['day_number']} — {day_date}**")
                if day.get("schedule"):
                    st.markdown(day["schedule"])
                st.markdown("---")

    # ── Accommodation ──
    if str(event_row.get("includes_accommodation", "")).lower() == "true":
        with st.expander("🛏️ Accommodation", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            acc_start = event_row.get("acc_start")
            acc_end   = event_row.get("acc_end")
            c1.metric("Check-in",  acc_start.strftime("%d/%m/%Y") if pd.notna(acc_start) else "—")
            c2.metric("Check-out", acc_end.strftime("%d/%m/%Y")   if pd.notna(acc_end)   else "—")
            c3.metric("Booking Code", event_row.get("booking_code") or "—")
            c4.metric("Min Stay", f"{int(event_row.get('minimum_stay', 0) or 0)} nights")

            policy = event_row.get("cancellation_policy", "—")
            if policy == "Flexible":
                st.info(f"✅ Flexible — Free cancellation up to "
                        f"**{int(event_row.get('cancellation_days', 0) or 0)} days** before arrival")
            elif policy == "Night Deposit":
                st.warning(f"💳 Night Deposit — Required "
                           f"**{int(event_row.get('deposit_days', 0) or 0)} days** before arrival")
            elif policy == "Non Refundable":
                st.error("🔒 Non Refundable")

            cut_off = event_row.get("cut_off_date")
            if pd.notna(cut_off):
                st.markdown(f"**Cut-off Date:** {cut_off.strftime('%d/%m/%Y')}")

            if event_row.get("accommodation_notes"):
                st.markdown(f"**Notes:** {event_row['accommodation_notes']}")

            if not rooms_df.empty:
                st.markdown("---")
                st.markdown("**Room Types**")
                room_table = []
                for _, r in rooms_df.iterrows():
                    prices = {}
                    for combo in price_combos:
                        k = f"price_{combo.replace('+', '_')}"
                        try:
                            v = int(float(r.get(k, 0) or 0))
                        except Exception:
                            v = 0
                        if v > 0:
                            prices[combo] = f"€{v}"
                    row_data = {
                        "Room Type": r.get("room_type", ""),
                        "Count":     int(float(r.get("room_count", 0) or 0)),
                        "Rate Plan": r.get("rate_plan", "—"),
                        **prices,
                    }
                    if r.get("room_notes"):
                        row_data["Notes"] = r["room_notes"]
                    room_table.append(row_data)
                st.dataframe(pd.DataFrame(room_table), use_container_width=True, hide_index=True)

    # ── Venues & Services ──
    if str(event_row.get("includes_venues", "")).lower() == "true" and spaces_list:
        with st.expander("🏛️ Venues & Services", expanded=True):
            if event_row.get("preparation_notes"):
                st.info(f"**Preparation Notes:** {event_row['preparation_notes']}")
            for sp in spaces_list:
                venue_date = sp.get("venue_date", "")
                if hasattr(venue_date, "strftime"):
                    try:
                        venue_date = pd.to_datetime(venue_date).strftime("%d/%m/%Y")
                    except Exception:
                        venue_date = str(venue_date)
                label = sp.get("venue_event_name") or sp["space_name"]
                st.markdown(
                    f"**{label}** — 📍 {sp['space_name']}  |  📅 {venue_date}  |  "
                    f"🕐 {sp.get('venue_from','—')} – {sp.get('venue_to','—')}"
                )
                if sp.get("venue_notes"):
                    st.caption(f"Venue Notes: {sp['venue_notes']}")
                if sp["services"]:
                    svc_df = pd.DataFrame([
                        {"Service": sv["type"], "Pax": sv["pax"]}
                        for sv in sp["services"]
                    ])
                    st.dataframe(svc_df, use_container_width=True, hide_index=True)
                if sp.get("service_notes"):
                    st.caption(f"Service Notes: {sp['service_notes']}")
                st.markdown("---")

    # ── Menus ──
    if menus_list:
        with st.expander("🍽️ Menus", expanded=False):
            for mn in menus_list:
                menu_date = mn.get("menu_date", "")
                try:
                    menu_date = pd.to_datetime(menu_date).strftime("%d/%m/%Y")
                except Exception:
                    pass
                st.markdown(
                    f"**{mn.get('menu_name','—')}** — {mn.get('activity_name') or ''}  |  "
                    f"📍 {mn.get('venue_name','—')}  |  📅 {menu_date}  |  "
                    f"Pax {mn.get('pax_min',0)}–{mn.get('pax_max',0)}"
                )
                if mn.get("menu_items"):
                    st.markdown(mn["menu_items"])
                if mn.get("menu_notes"):
                    st.caption(f"Notes: {mn['menu_notes']}")
                st.markdown("---")


# ─────────────────────────────────────────────
# EDIT CARD
# ─────────────────────────────────────────────
def render_edit_card(event_name):
    st.markdown(
        f"""<div style="border-left:5px solid #F59E0B;padding:0.6rem 1.2rem;
        background:#fffbeb;border-radius:8px;margin-bottom:1rem;">
        <h3 style="margin:0;color:#92400e;">✏️ Editing: {event_name}</h3>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("❌ Cancel Edit"):
        st.session_state["editing_event"] = None
        st.rerun()

    success = render_event_form(prefix="edit_", submit_label="💾 Save Changes")
    if success:
        st.success("✅ Οι αλλαγές αποθηκεύτηκαν!")
        st.session_state["editing_event"] = None
        st.rerun()


# ─────────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────────
def render_gantt(df_plot, rooms_df, spaces_df, selected_year):
    import plotly.express as px

    df_plot = df_plot.dropna(subset=["event_start", "event_end"]).copy()
    if df_plot.empty:
        st.info(f"Δεν υπάρχουν events με έγκυρες ημερομηνίες για το {selected_year}.")
        return

    records = []
    for idx, row in df_plot.iterrows():
        eid  = row["event_id"]
        days = (row["event_end"] - row["event_start"]).days or 1
        records.append({
            "Event":     row["event_name"],
            "Type":      row.get("event_type", ""),
            "Start":     row["event_start"],
            "Finish":    row["event_end"],
            "Attendees": int(row.get("attendees", 0) or 0),
            "Nights":    days,
            "Rooms":     count_rooms_from_df(rooms_df, eid),
            "Spaces":    count_spaces_from_df(spaces_df, eid),
            "Color":     event_color(idx),
        })

    df_gantt = pd.DataFrame(records)
    fig = px.timeline(
        df_gantt,
        x_start="Start", x_end="Finish", y="Event",
        color="Event",
        color_discrete_sequence=df_gantt["Color"].tolist(),
        custom_data=["Type", "Nights", "Attendees", "Rooms", "Spaces"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Type: %{customdata[0]}<br>"
            "📅 %{base|%d/%m/%Y} → %{x|%d/%m/%Y}<br>"
            "🌙 %{customdata[1]} nights<br>"
            "👥 %{customdata[2]} attendees<br>"
            "🛏️ %{customdata[3]} rooms | 🏛️ %{customdata[4]} spaces"
            "<extra></extra>"
        )
    )
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12), title="", fixedrange=True)
    fig.update_xaxes(
        range=[f"{selected_year}-03-01", f"{selected_year}-10-31"],
        showgrid=True, gridcolor="#e2e8f0", gridwidth=1,
        minor=dict(ticklen=4, tickcolor="#cbd5e1"),
        tickfont=dict(size=12), fixedrange=False,
    )
    fig.update_layout(
        height=max(500, len(df_plot) * 40),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=40),
        bargap=0, bargroupgap=0.0, showlegend=False,
        title=dict(text=f"Events | {selected_year}", font=dict(size=18)),
        dragmode="zoom",
    )
    for _, row in df_gantt.iterrows():
        if row["Nights"] >= 3:
            mid = row["Start"] + (row["Finish"] - row["Start"]) / 2
            fig.add_annotation(
                x=mid, y=row["Event"], text=row["Event"],
                showarrow=False,
                font=dict(color="white", size=10, family="Arial Bold"),
                xref="x", yref="y",
            )
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": False,
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "doubleClick": "reset",
    })


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
st.title("📊 Event Dashboard")

if "editing_event" not in st.session_state:
    st.session_state["editing_event"] = None

with st.spinner("Φόρτωση δεδομένων..."):
    data = load_data()

events_df   = data["events"]
rooms_df    = data["rooms"]
spaces_df   = data["spaces"]
services_df = data["services"]
calendar_df = data["calendar"]
menus_df    = data["menus"]

if events_df.empty:
    st.warning("Δεν υπάρχουν δεδομένα ακόμα.")
    st.stop()

available_years = sorted(events_df["event_start"].dropna().dt.year.unique().tolist())
if not available_years:
    st.warning("Δεν βρέθηκαν έγκυρες ημερομηνίες.")
    st.stop()

selected_year = st.selectbox("📅 Έτος", available_years, index=len(available_years) - 1)
df_year = events_df[
    events_df["event_start"].dt.year == selected_year
].copy().reset_index(drop=True)

tab1, tab2 = st.tabs(["📋 Events", "📅 Gantt Chart"])

with tab1:
    st.subheader(f"Events | {selected_year} | {len(df_year)} total")

    hcols = st.columns([0.4, 0.2, 3, 1.5, 1.5, 1, 1.2, 1, 1])
    for col, label in zip(hcols[2:], ["Event", "Start", "End", "Nights", "Attendees", "Rooms", "Spaces"]):
        col.markdown(f"**{label}**")
    st.divider()

    selected_idx = None
    for i, row in df_year.iterrows():
        color = event_color(i)
        eid   = row["event_id"]
        cols  = st.columns([0.4, 0.2, 3, 1.5, 1.5, 1, 1.2, 1, 1])

        checked = cols[0].checkbox("", key=f"chk_{i}", label_visibility="collapsed")
        cols[1].markdown(
            f'<div style="width:14px;height:14px;border-radius:50%;'
            f'background:{color};margin-top:8px;"></div>',
            unsafe_allow_html=True,
        )
        cols[2].markdown(f"**{row.get('event_name', '')}**")
        cols[3].write(row["event_start"].strftime("%d/%m/%Y") if pd.notna(row["event_start"]) else "—")
        cols[4].write(row["event_end"].strftime("%d/%m/%Y")   if pd.notna(row["event_end"])   else "—")
        cols[5].write(str(num_days(row)))
        cols[6].write(str(int(row.get("attendees", 0) or 0)))
        cols[7].write(str(count_rooms_from_df(rooms_df, eid)))
        cols[8].write(str(count_spaces_from_df(spaces_df, eid)))

        if checked:
            selected_idx = i

    if selected_idx is not None:
        st.divider()
        st.markdown("<br>" * 3, unsafe_allow_html=True)
        st.subheader("📄 Client Card")
        selected_row = df_year.loc[selected_idx]
        color        = event_color(selected_idx)
        eid            = selected_row["event_id"]
        ev_rooms_df    = get_event_rooms(rooms_df, eid)
        ev_spaces      = get_event_spaces(spaces_df, services_df, eid)
        ev_calendar    = get_event_calendar(calendar_df, eid)
        ev_menus       = get_event_menus(menus_df, eid)

        editing = st.session_state.get("editing_event")
        if editing and editing == selected_row["event_name"]:
            render_edit_card(editing)
        else:
            render_client_card(selected_row, ev_rooms_df, ev_spaces, color, selected_idx,
                               ev_calendar, ev_menus)

with tab2:
    render_gantt(df_year, rooms_df, spaces_df, selected_year)
