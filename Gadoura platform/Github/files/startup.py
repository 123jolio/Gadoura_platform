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
import os
import threading
import streamlit as st

log = logging.getLogger(__name__)


def _sync_job() -> None:
    """Background sync task."""
    try:
        from drive_sync import eager_sync
        eager_sync()
        log.info("Background eager sync finished.")
    except Exception as exc:
        log.error("Drive eager sync failed: %s", exc)


@st.cache_resource(show_spinner=False)
def _run_eager_sync() -> str:
    """Start eager sync once per container lifetime."""
    try:
        from drive_sync import PLATFORM_ROOT
        # Optional override to keep old blocking behavior when needed.
        blocking = os.getenv("DRIVE_SYNC_BLOCKING_STARTUP", "0").strip() == "1"
        if blocking:
            _sync_job()
            return str(PLATFORM_ROOT)

        t = threading.Thread(target=_sync_job, name="gadoura-eager-sync", daemon=True)
        t.start()
        return f"{PLATFORM_ROOT} (background sync)"
    except Exception as exc:
        log.error("Drive eager sync failed: %s", exc)
        return "sync_failed"


# Trigger on import
_platform_root = _run_eager_sync()
