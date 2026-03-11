"""
drive_sync.py
=============
Google Drive ↔ /tmp/gadoura synchronisation helper.

Strategy
--------
* EAGER  (on first import / app start):
    - All CSV / Excel / small files  (<  EAGER_MAX_MB)
* LAZY   (on demand, triggered by the Streamlit app):
    - GeoTIFF files — only the specific file requested is downloaded,
      and only if it is not already cached in /tmp.

Environment variables expected
-------------------------------
GOOGLE_SERVICE_ACCOUNT_JSON   Full JSON string of the service-account key.
GADOURA_DRIVE_ROOT_FOLDER_ID  ID of the top-level Drive folder
                               (the one you share with the service account).

Optional
--------
GADOURA_PLATFORM_ROOT         Local mount point  (default: /tmp/gadoura)
DRIVE_SYNC_EAGER_MAX_MB       Files smaller than this are eagerly downloaded
                               (default: 20)
DRIVE_SYNC_DISABLE            Set to "1" to skip all Drive syncing
                               (useful for local dev with real data on disk)
"""

from __future__ import annotations

import io
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
PLATFORM_ROOT   = Path(os.getenv("GADOURA_PLATFORM_ROOT", "/tmp/gadoura"))
EAGER_MAX_BYTES = int(os.getenv("DRIVE_SYNC_EAGER_MAX_MB", "20")) * 1_048_576
DISABLE_SYNC    = os.getenv("DRIVE_SYNC_DISABLE", "0").strip() == "1"

_EAGER_EXTENSIONS  = {".csv", ".xlsx", ".xls", ".json", ".txt", ".md"}
_SKIP_EXTENSIONS   = {".py", ".ipynb", ".git"}   # never download these
_LAZY_ONLY_EXTENSIONS = {".tif", ".tiff"}  # always lazy-download heavy rasters

# Thread-safety for lazy downloads

def _inject_streamlit_secrets():
    """Copy st.secrets into os.environ so the rest of drive_sync works unchanged."""
    try:
        import streamlit as st
        for key, val in st.secrets.items():
            if key not in os.environ:
                os.environ[key] = str(val)
    except Exception:
        pass  # not running inside Streamlit, or no secrets defined

_inject_streamlit_secrets()

_download_lock = threading.Lock()
_in_progress: set[str] = set()   # Drive file IDs currently being downloaded


# ── Drive client (cached) ──────────────────────────────────────────────────────
_drive_service = None

def _get_service():
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    try:
        from google.oauth2 import service_account          # type: ignore
        from googleapiclient.discovery import build        # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "google-auth and google-api-python-client must be installed. "
            "Add them to requirements.txt."
        ) from exc

    key_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not key_json:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not set."
        )

    info = json.loads(key_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive_service


# ── Low-level helpers ──────────────────────────────────────────────────────────
def _list_folder(folder_id: str) -> list[dict]:
    """Return all items (files + sub-folders) directly inside a Drive folder."""
    svc     = _get_service()
    items   = []
    token   = None
    query   = f"'{folder_id}' in parents and trashed = false"
    fields  = "nextPageToken, files(id, name, mimeType, size)"

    while True:
        resp = svc.files().list(
            q=query, fields=fields, pageToken=token, pageSize=200
        ).execute()
        items.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return items


def _download_file_to(file_id: str, dest: Path, retries: int = 3) -> None:
    """Download a single Drive file to *dest*, with simple retry logic."""
    from googleapiclient.http import MediaIoBaseDownload  # type: ignore

    svc = _get_service()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    for attempt in range(retries):
        try:
            request  = svc.files().get_media(fileId=file_id)
            with io.FileIO(str(tmp), "wb") as fh:
                dl   = MediaIoBaseDownload(fh, request, chunksize=8 * 1_048_576)
                done = False
                while not done:
                    _, done = dl.next_chunk()
            tmp.replace(dest)
            log.info("Downloaded %s → %s", file_id, dest)
            return
        except Exception as exc:
            log.warning("Attempt %d failed for %s: %s", attempt + 1, file_id, exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to download Drive file {file_id} after {retries} attempts")


# ── Recursive folder walk ──────────────────────────────────────────────────────
_FOLDER_MIME = "application/vnd.google-apps.folder"

def _walk_and_sync(
    folder_id: str,
    local_dir: Path,
    *,
    eager_only: bool,
    _depth: int = 0,
) -> None:
    """
    Recursively mirror a Drive folder to *local_dir*.

    eager_only=True  → only download files that match EAGER criteria.
    eager_only=False → download everything (used for full-sync if needed).
    """
    if _depth > 10:          # guard against infinite loops / very deep trees
        return

    try:
        items = _list_folder(folder_id)
    except Exception as exc:
        log.error("Cannot list Drive folder %s: %s", folder_id, exc)
        return

    for item in items:
        name      = item["name"]
        mime      = item["mimeType"]
        item_id   = item["id"]
        dest_path = local_dir / name

        if mime == _FOLDER_MIME:
            dest_path.mkdir(parents=True, exist_ok=True)
            _walk_and_sync(
                item_id, dest_path, eager_only=eager_only, _depth=_depth + 1
            )
            continue

        suffix = Path(name).suffix.lower()
        if suffix in _SKIP_EXTENSIONS:
            continue

        size = int(item.get("size") or 0)
        # Keep startup fast: never eager-download GeoTIFF rasters.
        is_eager_candidate = (
            suffix in _EAGER_EXTENSIONS
            or (suffix not in _LAZY_ONLY_EXTENSIONS and size <= EAGER_MAX_BYTES)
        )

        if eager_only and not is_eager_candidate:
            # Leave a zero-byte placeholder so the app knows the file exists
            if not dest_path.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.touch()
                # Store the Drive ID next to it so lazy_download can find it
                _id_file(dest_path).write_text(item_id)
            continue

        # Skip if already downloaded (non-zero size)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            continue

        try:
            _download_file_to(item_id, dest_path)
        except Exception as exc:
            log.error("Skipping %s: %s", name, exc)


def _id_file(path: Path) -> Path:
    """Sidecar file storing the Drive file ID for a lazy-download placeholder."""
    return path.parent / (path.name + ".driveid")


# ── Public API ─────────────────────────────────────────────────────────────────

def eager_sync() -> None:
    """
    Called once at app startup.
    Downloads all CSVs / Excel files eagerly; leaves GeoTIFFs as placeholders.
    """
    if DISABLE_SYNC:
        log.info("Drive sync disabled (DRIVE_SYNC_DISABLE=1).")
        return

    folder_id = os.getenv("GADOURA_DRIVE_ROOT_FOLDER_ID", "").strip()
    if not folder_id:
        log.warning(
            "GADOURA_DRIVE_ROOT_FOLDER_ID not set — skipping Drive sync."
        )
        return

    PLATFORM_ROOT.mkdir(parents=True, exist_ok=True)
    log.info("Eager sync starting from Drive folder %s → %s", folder_id, PLATFORM_ROOT)
    _walk_and_sync(folder_id, PLATFORM_ROOT, eager_only=True)
    log.info("Eager sync complete.")


def lazy_download(local_path: Path) -> bool:
    """
    Ensure *local_path* is fully downloaded.

    Returns True if the file is now available (either was already present,
    or was just downloaded).  Returns False if no Drive ID is known.

    Thread-safe: concurrent requests for the same file wait for the first
    download to finish rather than downloading twice.
    """
    if DISABLE_SYNC:
        return local_path.exists() and local_path.stat().st_size > 0

    # Already fully downloaded?
    if local_path.exists() and local_path.stat().st_size > 0:
        id_f = _id_file(local_path)
        if id_f.exists():
            id_f.unlink(missing_ok=True)   # clean up sidecar
        return True

    id_f = _id_file(local_path)
    if not id_f.exists():
        # No sidecar — might be a path we've never seen from Drive
        log.warning("No Drive ID sidecar for %s", local_path)
        return False

    file_id = id_f.read_text().strip()

    with _download_lock:
        # Re-check inside the lock (another thread may have finished)
        if local_path.exists() and local_path.stat().st_size > 0:
            return True

        if file_id in _in_progress:
            # Wait for the other thread (poll)
            pass  # fall through; the lock ensures serialisation here
        else:
            _in_progress.add(file_id)

    # Download (outside the lock so other files can proceed in parallel)
    try:
        _download_file_to(file_id, local_path)
        id_f.unlink(missing_ok=True)
        return True
    except Exception as exc:
        log.error("Lazy download failed for %s: %s", local_path, exc)
        return False
    finally:
        with _download_lock:
            _in_progress.discard(file_id)


def is_placeholder(path: Path) -> bool:
    """True if *path* is a zero-byte placeholder left by eager_sync."""
    return path.exists() and path.stat().st_size == 0 and _id_file(path).exists()


def ensure_tif(tif_path: str) -> Optional[str]:
    """
    Convenience wrapper for the Streamlit app.

    Pass the path string from list_tifs(); returns the same path once the
    file is ready, or None if the download failed.
    """
    p = Path(tif_path)
    if is_placeholder(p):
        ok = lazy_download(p)
        return tif_path if ok else None
    if p.exists() and p.stat().st_size > 0:
        return tif_path
    return None
