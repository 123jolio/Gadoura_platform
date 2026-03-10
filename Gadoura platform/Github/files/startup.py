"""
startup.py
==========
Import this module ONCE at the top of each Streamlit app to trigger the
eager Drive sync on the first run.

Usage (first lines of data_presentation_1.py and streamlit_geotiff_map_1.py):

    import startup   # noqa: F401  — triggers eager Drive sync

The sync is guarded by st.cache_resource so it runs only once per
container lifetime, not on every Streamlit rerun.
"""

import logging
import streamlit as st

log = logging.getLogger(__name__)


@st.cache_resource(show_spinner="🛰️ Συγχρονισμός δεδομένων από Google Drive…")
def _run_eager_sync() -> str:
    """Runs once per container lifetime."""
    try:
        from drive_sync import eager_sync, PLATFORM_ROOT
        eager_sync()
        return str(PLATFORM_ROOT)
    except Exception as exc:
        log.error("Drive eager sync failed: %s", exc)
        return "sync_failed"


# Trigger on import
_platform_root = _run_eager_sync()
