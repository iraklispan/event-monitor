# Location => ./utils/mappings.py

import sys
sys.dont_write_bytecode = True

import json
import streamlit as st
from paths.paths import (
    ROOM_TYPES_JSON, RATE_PLANS_JSON, CANCELLATION_JSON,
    SPACE_NAMES_JSON, SERVICES_JSON, EVENT_TYPES_JSON, PRICE_COMBOS_JSON,
)


def load_list(path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_list(path, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _clear_mapping_caches()


def _clear_mapping_caches() -> None:
    get_room_types.clear()
    get_rate_plans.clear()
    get_cancellation_policies.clear()
    get_space_names.clear()
    get_services.clear()
    get_event_types.clear()
    get_price_combos.clear()


@st.cache_data
def get_room_types() -> list:
    return load_list(ROOM_TYPES_JSON)


@st.cache_data
def get_rate_plans() -> list:
    return load_list(RATE_PLANS_JSON)


@st.cache_data
def get_cancellation_policies() -> list:
    return load_list(CANCELLATION_JSON)


@st.cache_data
def get_space_names() -> list:
    return load_list(SPACE_NAMES_JSON)


@st.cache_data
def get_services() -> list:
    return load_list(SERVICES_JSON)


@st.cache_data
def get_event_types() -> list:
    return load_list(EVENT_TYPES_JSON)


@st.cache_data
def get_price_combos() -> list:
    return load_list(PRICE_COMBOS_JSON)
