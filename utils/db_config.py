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

# Existing columns stay in original order (backward-compat with sheet data).
# New columns appended at the end.
EVENTS_HEADER = [
    "event_id", "submitted_at", "submitted_by",
    "event_name", "event_type", "event_start", "event_end", "attendees",
    "includes_accommodation", "acc_start", "acc_end",
    "booking_code", "cut_off_date",
    "cancellation_policy", "cancellation_days", "deposit_days",
    "minimum_stay", "includes_venues",
    "event_description", "important_info",
    "includes_organizer_info", "organizer", "contact_info", "special_offers", "organizer_notes",
    "includes_calendar",
    "accommodation_notes",
    "preparation_notes",
    "includes_menu",
]

ROOMS_HEADER = [
    "event_id", "room_type", "room_count", "rate_plan",
    "price_1_0", "price_2_0", "price_2_1", "price_2_2",
    "price_3_0", "price_3_1", "price_4_0",
    "room_notes",
]

SPACES_HEADER = [
    "space_id", "event_id", "space_name",
    "venue_event_name", "venue_date", "venue_from", "venue_to",
    "venue_notes", "service_notes",
]

SERVICES_HEADER = ["space_id", "event_id", "service_type", "service_pax"]

CALENDAR_HEADER = ["calendar_id", "event_id", "day_number", "day_date", "schedule"]

MENUS_HEADER = [
    "menu_id", "event_id", "menu_name", "venue_name",
    "activity_name", "menu_date", "pax_min", "pax_max",
    "menu_items", "menu_notes",
]