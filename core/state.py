"""Central session-state initialization so every page sees the same defaults."""
from __future__ import annotations

import streamlit as st
from core import database


def init_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = database.new_session("moderate")
    if "profile_key" not in st.session_state:
        st.session_state.profile_key = "moderate"
    if "investigation" not in st.session_state:
        st.session_state.investigation = None
    if "data_degraded" not in st.session_state:
        st.session_state.data_degraded = False
    if "force_conflict" not in st.session_state:
        st.session_state.force_conflict = False
    if "use_live_data" not in st.session_state:
        st.session_state.use_live_data = True
    if "ticker" not in st.session_state:
        st.session_state.ticker = "RELIANCE"
