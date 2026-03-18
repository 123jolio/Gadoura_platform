"""
╔══════════════════════════════════════════════════════════════════╗
║  Πλατφόρμα Παρακολούθησης Ταμιευτήρα Γαδουρά  ·  ΕΥΑΘ ΑΕ      ║
╚══════════════════════════════════════════════════════════════════╝
Redesigned UI — modern dark theme, Greek labels, button case-selector,
separate reservoir-level panel.
"""

from __future__ import annotations

import base64
from datetime import date
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

import altair as alt
import folium
import numpy as np
import pandas as pd
import rasterio
import streamlit as st
from streamlit_folium import st_folium


# ── Paths ──────────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent

def _resolve_platform_root(app_dir: Path) -> Path:
    # Search upwards so this works for:
    # - repo root
    # - code/
    # - code/mobile version/
    for candidate in [app_dir, *app_dir.parents]:
        if (candidate / "satellite data").exists() or (candidate / "field data").exists():
            return candidate
    return app_dir

PLATFORM_ROOT = _resolve_platform_root(APP_DIR)
CODE_EXEC_PATH = (PLATFORM_ROOT / "code").resolve()
SATELLITE_DATA_ROOT = PLATFORM_ROOT / "satellite data"
DATA_ROOT = SATELLITE_DATA_ROOT / "DATA"

# Backward compatibility for legacy layout without "satellite data" folder.
if not DATA_ROOT.exists():
    legacy_data_root = PLATFORM_ROOT / "DATA"
    if legacy_data_root.exists():
        DATA_ROOT = legacy_data_root

# Keep legacy variable name used in the rest of the script.
GADOURA_ROOT = SATELLITE_DATA_ROOT if SATELLITE_DATA_ROOT.exists() else PLATFORM_ROOT

LOGO_URL = "https://chatbot.eyath.gr/_astro/eyath-logo-2.DriaSExn_1jOI34.svg"
DATE_RE  = re.compile(r"(?P<y>\d{4})_(?P<m>\d{2})_(?P<d>\d{2})")
PROFILE_LINE_KMZ_NAME = "Γραμμή.kmz"
TURBIDITY_SCALE_IMAGE_NAME = "output.png"
CHL_ALERT_THRESHOLD = 24.0
TURBIDITY_ALERT_THRESHOLD = 1.85


def _resolve_profile_line_kmz() -> Path:
    candidates = [
        PLATFORM_ROOT / "field data" / PROFILE_LINE_KMZ_NAME,
        GADOURA_ROOT.parent / "field data" / PROFILE_LINE_KMZ_NAME,
        APP_DIR.parent / "field data" / PROFILE_LINE_KMZ_NAME,
        APP_DIR.parent.parent / "field data" / PROFILE_LINE_KMZ_NAME,
    ]
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return candidates[0]


PROFILE_LINE_KMZ = _resolve_profile_line_kmz()


def _resolve_turbidity_scale_image() -> Path:
    candidates = [
        SATELLITE_DATA_ROOT / "Θολότητα" / TURBIDITY_SCALE_IMAGE_NAME,
        PLATFORM_ROOT / "satellite data" / "Θολότητα" / TURBIDITY_SCALE_IMAGE_NAME,
        GADOURA_ROOT / "Θολότητα" / TURBIDITY_SCALE_IMAGE_NAME,
        APP_DIR.parent.parent / "satellite data" / "Θολότητα" / TURBIDITY_SCALE_IMAGE_NAME,
    ]
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return candidates[0]


TURBIDITY_SCALE_IMAGE = _resolve_turbidity_scale_image()


# ── Case configuration ─────────────────────────────────────────────────────────
def _image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _resolve_optional_asset(*candidates: Path) -> Path:
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return candidates[0]


CASE_CONFIG = [
    {
        "key":   "level",
        "label": "Στάθμη",
        "icon":  "📈",
        "folders": [],
        "has_chl": False,
        "is_level": True,
    },    {
        "key":   "bgr",
        "label": "ΦΑΙΝΟΜΕΝΑ ΛΕΥΚΑΣΜΟΥ",
        "icon":  "🌫️",
        "folders": [GADOURA_ROOT / "BGR" / "GeoTIFFs"],
        "has_chl": False,
        "has_bgr": True,
    },
    {
        "key":   "burned_areas",
        "label": "ΠΥΡΚΑΓΙΑ 2023",
        "icon":  "🔥",
        "folders": [
            GADOURA_ROOT / "Burned Areas"       / "GeoTIFFs",
            GADOURA_ROOT / "Burned Areas_large" / "GeoTIFFs",
        ],
        "has_chl": False,
    },
    {
        "key":   "chlorophyll_validated",
        "label": "ΧΛΩΡΟΦΥΛΛΗ",
        "label_full": "ΣΥΓΚΕΝΤΡΩΣΕΙΣ ΧΛΩΡΟΦΥΛΛΗΣ",
        "icon":  "🟢",
        "folders": [
            # Support both spellings found across datasets/repos.
            GADOURA_ROOT / "Chlorophyl_validated"  / "code" / "GeoTIFFs",
            GADOURA_ROOT / "Chlorophyll_validated" / "code" / "GeoTIFFs",
            GADOURA_ROOT / "Chlorophyll"           / "GeoTIFFs",
        ],
        "has_chl": True,
    },
    {
        "key":   "uncalibrated_satellite",
        "label": "ΜΗ ΒΑΘΜΟΝΟΜΗΜΕΝΕΣ ΔΟΡΥΦΟΡΙΚΕΣ ΕΙΚΟΝΕΣ",
        "label_full": "Μη βαθμονομημένες δορυφορικές εικόνες",
        "icon":  "🧫",
        "folders": [],
        "has_chl": False,
        "children": ["cya", "cdom", "doc", "color"],
    },
    {
        "key":   "cya",
        "label": "CYA",
        "label_full": "Cya (Se2WaQ)",
        "icon":  "🧫",
        "folders": [GADOURA_ROOT / "Cya" / "GeoTIFFs"],
        "chart_image": _resolve_optional_asset(
            DATA_ROOT / "charts_cya" / "lake_sampling_chart.png",
            GADOURA_ROOT / "Cya" / "lake_sampling_chart.png",
        ),
        "chart_expander_title": "📊 Διαγράμματα",
        "chart_caption": "Δειγματοληψία λίμνης",
        "has_chl": False,
    },
    {
        "key":   "cdom",
        "label": "CDOM",
        "label_full": "CDOM",
        "icon":  "🧫",
        "folders": [GADOURA_ROOT / "CDOM" / "GeoTIFFs"],
        "chart_image": _resolve_optional_asset(
            DATA_ROOT / "charts_cdom" / "lake_sampling_chart.png",
            GADOURA_ROOT / "CDOM" / "lake_sampling_chart.png",
        ),
        "chart_expander_title": "📊 Διαγράμματα",
        "chart_caption": "Δειγματοληψία λίμνης",
        "has_chl": False,
    },
    {
        "key":   "doc",
        "label": "DOC",
        "label_full": "DOC",
        "icon":  "🧫",
        "folders": [GADOURA_ROOT / "DOC" / "GeoTIFFs"],
        "chart_image": _resolve_optional_asset(
            DATA_ROOT / "charts_dom" / "lake_sampling_chart.png",
            GADOURA_ROOT / "DOC" / "lake_sampling_chart.png",
        ),
        "chart_expander_title": "📊 Διαγράμματα",
        "chart_caption": "Δειγματοληψία λίμνης",
        "has_chl": False,
    },
    {
        "key":   "color",
        "label": "COLOR",
        "label_full": "COLOR",
        "icon":  "🧫",
        "folders": [GADOURA_ROOT / "Color" / "GeoTIFFs"],
        "chart_image": _resolve_optional_asset(
            DATA_ROOT / "charts_color" / "lake_sampling_chart.png",
            GADOURA_ROOT / "Color" / "lake_sampling_chart.png",
        ),
        "chart_expander_title": "📊 Διαγράμματα",
        "chart_caption": "Δειγματοληψία λίμνης",
        "has_chl": False,
    },
    {
        "key":   "tholotita",
        "label": "Θολότητα",
        "icon":  "💧",
        "folders": [
            GADOURA_ROOT / "Θολότητα"            / "GeoTIFFs",
            GADOURA_ROOT / "Turbidity validated" / "code" / "GeoTIFFs",
        ],
        "has_chl": False,
        "has_turbidity": True,
    },
    {
        "key":   "pragmatiki",
        "label": "Πραγματική εικόνα",
        "icon":  "🛰️",
        "folders": [GADOURA_ROOT / "Πραγματικό" / "GeoTIFFs"],
        "has_chl": False,
    },
]
CASE_BY_KEY = {c["key"]: c for c in CASE_CONFIG}
CASE_GROUP_PARENT_BY_CHILD = {
    child: cfg["key"]
    for cfg in CASE_CONFIG
    for child in cfg.get("children", [])
}
CASE_DISPLAY_ORDER = [
    "level",
    "pragmatiki",
    "chlorophyll_validated",
    "tholotita",
    "burned_areas",
    "bgr",
    "uncalibrated_satellite",
]


# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
CSS = """
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700;12..96,800&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
:root{
  --bg:#060d18;--bg2:#0a1525;--sf:#0e1e30;--sf2:#122236;
  --ac:#06d6f0;--acd:rgba(6,214,240,.12);--abdr:rgba(6,214,240,.22);
  --tx:#dff2fa;--mid:#6ab4ce;--dim:#2e6480;--bdr:rgba(6,214,240,.13);
  --sh:0 10px 52px rgba(0,0,0,.7);--r:16px;
  --fh:'Bricolage Grotesque',sans-serif;
  --fb:'Plus Jakarta Sans',sans-serif;
  --fm:'JetBrains Mono',monospace;
}
html,body,[data-testid="stApp"]{background:var(--bg)!important;color:var(--tx)!important;font-family:var(--fb)!important;}
[data-testid="stApp"]::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(6,214,240,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(6,214,240,.018) 1px,transparent 1px);background-size:56px 56px;}
#MainMenu,footer,header,[data-testid="stDecoration"],[data-testid="stToolbar"]{display:none!important;}
.block-container{padding-top:1.4rem!important;padding-bottom:5rem!important;max-width:1480px!important;position:relative;z-index:1;}

.hcard{background:linear-gradient(140deg,#091726 0%,#0d2340 55%,#071520 100%);border:1px solid var(--abdr);border-top:2px solid rgba(6,214,240,.55);border-radius:var(--r);padding:1.6rem 2.5rem;margin-bottom:2rem;display:flex;align-items:center;gap:2.4rem;box-shadow:var(--sh),inset 0 1px 0 rgba(255,255,255,.04);position:relative;overflow:hidden;}
.hcard::before{content:'';position:absolute;top:-80px;right:-80px;width:260px;height:260px;background:radial-gradient(circle,rgba(6,214,240,.08) 0%,transparent 70%);pointer-events:none;}
.hcard h1{font-family:var(--fh)!important;font-size:1.45rem!important;font-weight:700!important;color:#f0faff!important;margin:0 0 .35rem 0!important;line-height:1.3!important;letter-spacing:-.02em!important;}
.hcard .sub{font-size:.72rem;color:var(--dim);letter-spacing:.1em;text-transform:uppercase;font-weight:500;}
.badge{display:inline-flex;align-items:center;gap:.4rem;background:var(--acd);border:1px solid var(--abdr);color:var(--ac);border-radius:99px;padding:.22rem .9rem;font-family:var(--fh);font-size:.65rem;font-weight:600;letter-spacing:.05em;margin-top:.5rem;}
.pathbox{margin-top:.8rem;padding:.72rem .9rem;border:1px solid var(--abdr);border-radius:12px;background:rgba(8,25,41,.72);max-width:100%;}
.pathbox .label{display:block;font-size:.6rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);}
.pathbox code{display:block;margin-top:.28rem;font-family:Consolas,"Courier New",monospace;font-size:.72rem;color:#d7f4ff;white-space:pre-wrap;word-break:break-all;}

.slabel{font-family:var(--fh);font-size:.6rem;font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--dim);margin-bottom:.75rem;padding-left:.15rem;}

[data-testid="stButton"]>button{background:var(--sf)!important;border:1px solid var(--bdr)!important;color:var(--mid)!important;border-radius:12px!important;font-family:var(--fh)!important;font-size:.75rem!important;font-weight:600!important;padding:.7rem 1rem!important;transition:all .18s ease!important;white-space:normal!important;line-height:1.18!important;}
[data-testid="stButton"]>button:hover{background:var(--sf2)!important;border-color:rgba(6,214,240,.5)!important;color:var(--tx)!important;transform:translateY(-1px)!important;box-shadow:0 6px 22px rgba(0,0,0,.45)!important;}
[data-testid="stButton"]>button[kind="primary"]{background:linear-gradient(135deg,#073d60,#052e4a)!important;border-color:var(--ac)!important;color:#e0f8ff!important;box-shadow:0 0 24px rgba(6,214,240,.18)!important;}

[data-testid="stDateInput"] label,[data-testid="stSlider"] label,[data-testid="stSelectbox"] label,[data-testid="stRadio"] label{font-family:var(--fh)!important;font-size:.62rem!important;letter-spacing:.13em!important;text-transform:uppercase!important;color:var(--dim)!important;font-weight:600!important;}
[data-testid="stDateInput"] input{background:var(--bg2)!important;border:1px solid var(--bdr)!important;color:var(--mid)!important;border-radius:8px!important;font-family:var(--fm)!important;font-size:.8rem!important;}
[data-testid="stSelectbox"] [data-baseweb="select"]>div{background:var(--bg2)!important;border-color:var(--bdr)!important;color:var(--mid)!important;border-radius:8px!important;}
[data-baseweb="slider"] [role="slider"]{background:var(--ac)!important;box-shadow:0 0 0 3px rgba(6,214,240,.2)!important;}
[data-baseweb="slider"]>div>div>div:first-child{background:var(--ac)!important;}

.mapwrap{position:relative;border:1px solid var(--abdr);border-top:2px solid rgba(6,214,240,.5);border-radius:var(--r);overflow:hidden;box-shadow:0 18px 70px rgba(0,0,0,.78),inset 0 1px 0 rgba(255,255,255,.03);margin-bottom:1.8rem;}
.turbidity-corner{position:absolute;left:12px;bottom:12px;z-index:999;width:min(180px,34vw);padding:.35rem .4rem .4rem;background:rgba(8,17,31,.88);border:1px solid rgba(56,189,248,.16);border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 8px 24px rgba(0,0,0,.35);}
.turbidity-corner-label{font-size:.46rem;letter-spacing:.12em;text-transform:uppercase;color:#9acbe2;margin-bottom:.25rem;font-weight:700;}
.turbidity-corner img{display:block;width:100%;height:auto;border-radius:6px;background:#fff;}

.sstrip{display:flex;align-items:center;gap:.75rem;margin:.3rem 0 1.1rem;font-size:.77rem;color:var(--mid);font-family:var(--fb);background:var(--acd);border:1px solid var(--bdr);border-radius:10px;padding:.5rem 1rem;}
.sdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;background:var(--ac);box-shadow:0 0 10px var(--ac);animation:_pulse 2.5s ease-in-out infinite;}
@keyframes _pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.35;transform:scale(.8);}}

[data-testid="stMetric"]{background:linear-gradient(135deg,var(--sf),var(--bg2))!important;border:1px solid var(--bdr)!important;border-top:2px solid rgba(6,214,240,.3)!important;border-radius:14px!important;padding:1rem 1.2rem!important;}
[data-testid="stMetricLabel"]{font-family:var(--fh)!important;font-size:.6rem!important;letter-spacing:.12em!important;text-transform:uppercase!important;color:var(--dim)!important;font-weight:600!important;}
[data-testid="stMetricValue"]{font-family:var(--fh)!important;font-size:1.6rem!important;color:var(--ac)!important;font-weight:700!important;letter-spacing:-.02em!important;}

.lcard{background:linear-gradient(135deg,var(--sf),var(--bg2));border:1px solid var(--bdr);border-top:2px solid rgba(6,214,240,.42);border-radius:var(--r);padding:1.6rem 2rem;margin-top:1.5rem;box-shadow:var(--sh);}
.lcard-title{font-family:var(--fh);font-size:1.05rem;font-weight:700;color:var(--tx);margin:0 0 1.2rem;display:flex;align-items:center;gap:.6rem;letter-spacing:-.01em;}

[data-testid="stTabs"] [role="tablist"]{border-bottom:1px solid var(--bdr)!important;gap:.2rem!important;}
[data-testid="stTabs"] [role="tab"]{font-family:var(--fh)!important;font-size:.7rem!important;font-weight:600!important;letter-spacing:.07em!important;text-transform:uppercase!important;color:var(--dim)!important;padding:.5rem 1.1rem!important;border-radius:8px 8px 0 0!important;transition:all .15s!important;}
[data-testid="stTabs"] [role="tab"]:hover{color:var(--mid)!important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{color:var(--ac)!important;border-bottom:2px solid var(--ac)!important;background:var(--acd)!important;}

[data-testid="stExpander"]{background:var(--sf)!important;border:1px solid var(--bdr)!important;border-radius:12px!important;}
[data-testid="stExpander"] summary{font-family:var(--fh)!important;font-size:.8rem!important;font-weight:600!important;color:var(--mid)!important;}

[data-testid="stCaptionContainer"]{color:var(--dim)!important;font-size:.68rem!important;font-family:var(--fm)!important;}
[data-testid="stInfo"]{background:rgba(6,214,240,.06)!important;border:1px solid rgba(6,214,240,.2)!important;border-radius:10px!important;color:var(--mid)!important;}

::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:#1a3d58;border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#2a5472;}
hr{border-color:var(--bdr)!important;}

/* ═══════════════════════════════════════════════════════════════
   MOBILE RESPONSIVE — screens < 768px
   ═══════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {

  /* ── Layout ──────────────────────────────────────────────── */
  .block-container {
    padding-top: .8rem !important;
    padding-left: .75rem !important;
    padding-right: .75rem !important;
    padding-bottom: 5rem !important;
  }

  /* ── Header: stack logo above text on small screens ──────── */
  .hcard {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 1rem !important;
    padding: 1.2rem 1.4rem !important;
    border-radius: 14px !important;
    margin-bottom: 1.2rem !important;
  }
  .hcard img { height: 44px !important; }
  .hcard h1  { font-size: 1.1rem !important; }
  .hcard .sub{ font-size: .65rem !important; }

  /* ── Streamlit columns → stack vertically ────────────────── */
  [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: .75rem !important;
  }
  [data-testid="stColumn"] {
    width: 100% !important;
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }

  /* ── Metric cards ─────────────────────────────────────────── */
  .metric-card {
    padding: .9rem 1rem !important;
    border-radius: 12px !important;
  }
  .metric-val { font-size: 1.5rem !important; }
  .metric-label { font-size: .58rem !important; }

  /* ── Buttons — bigger touch targets ──────────────────────── */
  [data-testid="stButton"] > button {
    min-height: 48px !important;
    font-size: .78rem !important;
    padding: .8rem 1rem !important;
    border-radius: 10px !important;
    width: 100% !important;
  }

  /* ── Tabs — scrollable on mobile ─────────────────────────── */
  [data-testid="stTabs"] [role="tablist"] {
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    padding-bottom: 2px !important;
  }
  [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display:none; }
  [data-testid="stTabs"] [role="tab"] {
    white-space: nowrap !important;
    font-size: .65rem !important;
    padding: .45rem .85rem !important;
    min-width: fit-content !important;
  }

  /* ── Select boxes & inputs ────────────────────────────────── */
  [data-testid="stSelectbox"] [data-baseweb="select"] > div,
  [data-testid="stDateInput"] input {
    font-size: .85rem !important;
    min-height: 44px !important;
  }

  /* ── Map — full width, reasonable height ──────────────────── */
  .mapwrap { border-radius: 12px !important; }
  .turbidity-corner {
    left: 10px !important;
    bottom: 10px !important;
    width: min(150px, 42vw) !important;
    padding: .32rem .36rem .36rem !important;
  }
  .turbidity-corner-label {
    font-size: .42rem !important;
    margin-bottom: .2rem !important;
  }
  [data-testid="stIFrame"] { min-height: 340px !important; }
  iframe { min-height: 340px !important; }

  /* ── Status strip ─────────────────────────────────────────── */
  .sstrip {
    font-size: .72rem !important;
    padding: .4rem .75rem !important;
  }

  /* ── Section labels ───────────────────────────────────────── */
  .slabel { font-size: .58rem !important; letter-spacing: .16em !important; }

  /* ── Sidebar: auto-hides on mobile in Streamlit ──────────── */
  [data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem !important;
  }

  /* ── Plotly charts ────────────────────────────────────────── */
  [data-testid="stPlotlyChart"] { overflow-x: auto !important; }
  [data-testid="stPlotlyChart"] > div { min-width: 0 !important; }

  /* ── Caption/mono text ────────────────────────────────────── */
  [data-testid="stCaptionContainer"] { font-size: .62rem !important; }

  /* ── pydeck/folium map containers ────────────────────────── */
  [data-testid="stDeckGlJsonChart"],
  .stFolium { border-radius: 12px !important; overflow: hidden !important; }

  /* ── Expander ─────────────────────────────────────────────── */
  [data-testid="stExpander"] summary {
    font-size: .75rem !important;
    padding: .8rem !important;
  }
}

/* ── Extra-small phones (< 420px) ──────────────────────────────── */
@media (max-width: 420px) {
  .hcard h1  { font-size: .95rem !important; }
  .metric-val { font-size: 1.35rem !important; }
  [data-testid="stTabs"] [role="tab"] {
    font-size: .6rem !important;
    padding: .4rem .7rem !important;
  }
}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def resolve_logo() -> str:
    for name in ["eyath_logo.png","eyath_logo.svg","logo.png","logo.svg"]:
        p = APP_DIR / name
        if p.exists():
            return str(p)
    return LOGO_URL


def has_tifs(p: Path) -> bool:
    return p.is_dir() and any(p.glob("*.tif"))


def resolve_folder(key: str) -> Path | None:
    for f in CASE_BY_KEY[key]["folders"]:
        if has_tifs(f):
            return f
    return None


def is_case_available(key: str) -> bool:
    cfg = CASE_BY_KEY[key]
    if cfg.get("is_level"):
        return True
    if cfg.get("children"):
        return any(is_case_available(child) for child in cfg["children"] if child in CASE_BY_KEY)
    return resolve_folder(key) is not None


def parse_date(p: Path) -> date | None:
    m = DATE_RE.search(p.stem)
    if not m:
        return None
    try:
        return date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
    except ValueError:
        return None


@st.cache_data(show_spinner=False)
def list_tifs(folder: str) -> list[dict]:
    rows = []
    for tif in sorted(Path(folder).glob("*.tif")):
        d = parse_date(tif)
        if d:
            rows.append({"path": str(tif), "name": tif.name, "date": d})
    return rows


def nearest(target: date, pool: list[date]) -> date:
    return min(pool, key=lambda d: abs((d - target).days))


def to_rgb(data: np.ndarray) -> np.ndarray:
    if data.shape[0] == 1:
        rgb = np.repeat(data[0][..., np.newaxis], 3, axis=2)
    else:
        rgb = np.transpose(data[:3], (1, 2, 0))
    if rgb.dtype != np.uint8:
        rgb = rgb.astype(np.float32)
        lo, hi = float(np.nanmin(rgb)), float(np.nanmax(rgb))
        rgb = ((rgb - lo) / (hi - lo + 1e-9) * 255).astype(np.uint8)
    return rgb


@st.cache_data(show_spinner=False)
def load_tif(path: str):
    with rasterio.open(path) as src:
        data   = src.read()
        bounds = src.bounds
    rgb  = to_rgb(data)
    ib   = [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
    ctr  = [(bounds.bottom + bounds.top) / 2, (bounds.left + bounds.right) / 2]
    return rgb, ib, ctr


def _parse_kml_coordinates(coord_text: str) -> list[list[float]]:
    points: list[list[float]] = []
    for token in coord_text.replace("\n", " ").replace("\t", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        points.append([lat, lon])
    return points


@st.cache_data(show_spinner=False)
def load_profile_line_coords(kmz_path: str) -> list[list[float]]:
    path = Path(kmz_path)
    if not path.exists():
        return []
    try:
        with zipfile.ZipFile(path) as archive:
            kml_names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
            longest: list[list[float]] = []
            for name in kml_names:
                root = ET.fromstring(archive.read(name))
                for node in root.findall(".//{*}LineString/{*}coordinates"):
                    coords = _parse_kml_coordinates(node.text or "")
                    if len(coords) > len(longest):
                        longest = coords
            return longest
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def load_chl_points(csv: str) -> pd.DataFrame:
    return load_profile_points(
        csv=csv,
        value_regex=r"Chl-a[^:]*:\s*(-?\d+(?:\.\d+)?)",
        value_name="chl_a",
    )


@st.cache_data(show_spinner=False)
def load_profile_points(csv: str, value_regex: str, value_name: str) -> pd.DataFrame:
    p = Path(csv)
    if not p.exists():
        return pd.DataFrame(columns=["date", "point", value_name, "color"])
    raw = pd.read_csv(p, encoding="utf-8-sig")
    if raw.shape[1] < 4:
        return pd.DataFrame(columns=["date", "point", value_name, "color"])

    styles = raw.iloc[:, 2].astype(str)
    details = raw.iloc[:, 3].astype(str)
    df = pd.DataFrame({
        "date": pd.to_datetime(
            details.str.extract(r"(\d{4}-\d{2}-\d{2})", expand=False),
            errors="coerce",
        ),
        "point": pd.to_numeric(raw.iloc[:, 1], errors="coerce"),
        value_name: pd.to_numeric(
            details.str.extract(value_regex, expand=False), errors="coerce"
        ),
        "color": styles.str.extract(
            r"fill-color:\s*(#[0-9A-Fa-f]{6})", expand=False
        ).str.upper(),
    }).dropna(subset=["date", value_name])
    df["point"] = df["point"].fillna(-1).astype(int)
    return df.sort_values(["date", "point"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_chl_avg(csv: str) -> pd.DataFrame:
    p = Path(csv)
    if not p.exists():
        return pd.DataFrame(columns=["date","value"])
    df = pd.read_csv(p, encoding="utf-8-sig")
    return pd.DataFrame({
        "date":  pd.to_datetime(df.iloc[:, 0], errors="coerce"),
        "value": pd.to_numeric(df.iloc[:, 1], errors="coerce"),
    }).dropna().sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_turbidity_avg(csv: str) -> pd.DataFrame:
    p = Path(csv)
    if not p.exists():
        return pd.DataFrame(columns=["date", "field", "satellite"])
    df = pd.read_csv(p, encoding="utf-8-sig")
    if df.empty:
        return pd.DataFrame(columns=["date", "field", "satellite"])

    # Expected columns: Date, Field turbidity (1m NTU), Satellite raw value
    out = pd.DataFrame({
        "date": pd.to_datetime(df.iloc[:, 0], errors="coerce"),
        "field": pd.to_numeric(df.iloc[:, 1], errors="coerce") if df.shape[1] > 1 else np.nan,
        "satellite": pd.to_numeric(df.iloc[:, 2], errors="coerce")
        if df.shape[1] > 2
        else pd.to_numeric(df.iloc[:, 1], errors="coerce"),
    })
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return out


@st.cache_data(show_spinner=False)
def load_bgr_avg(csv: str) -> pd.DataFrame:
    p = Path(csv)
    if not p.exists():
        return pd.DataFrame(columns=["date", "value"])
    df = pd.read_csv(p, encoding="utf-8-sig")
    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    date_raw = df.iloc[:, 0].astype(str).str.replace("\u202f", " ", regex=False)
    val_raw = (
        df.iloc[:, 1]
        .astype(str)
        .str.replace("\u202f", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(date_raw, errors="coerce"),
            "value": pd.to_numeric(val_raw, errors="coerce"),
        }
    )
    out = out.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
    return out


@st.cache_data(show_spinner=False)
def load_bgr_points(csv: str) -> pd.DataFrame:
    p = Path(csv)
    if not p.exists():
        return pd.DataFrame(columns=["date", "point", "bgr", "color"])

    raw = None
    for enc in ("utf-8-sig", "utf-8", "cp1253", "latin-1"):
        try:
            raw = pd.read_csv(p, encoding=enc)
            break
        except Exception:
            continue
    if raw is None or raw.shape[1] < 2:
        return pd.DataFrame(columns=["date", "point", "bgr", "color"])

    col0 = raw.iloc[:, 0].astype(str).str.replace("\u202f", " ", regex=False).str.replace("\xa0", " ", regex=False)
    date_from_col = pd.to_datetime(col0, errors="coerce")
    point = pd.to_numeric(raw.iloc[:, 1], errors="coerce")

    styles = raw.iloc[:, 2].astype(str) if raw.shape[1] > 2 else pd.Series([""] * len(raw))
    details = raw.iloc[:, 3].astype(str) if raw.shape[1] > 3 else pd.Series([""] * len(raw))
    date_from_details = pd.to_datetime(
        details.str.extract(r"(\d{4}-\d{2}-\d{2})", expand=False),
        errors="coerce",
    )
    date = date_from_col.fillna(date_from_details)

    val = details.str.extract(r"AreaBGR[^:]*:\s*(-?\d[\d,]*(?:\.\d+)?)", expand=False)
    if val.isna().all():
        val = details.str.extract(r"\bBGR[^:]*:\s*(-?\d[\d,]*(?:\.\d+)?)", expand=False)
    if val.isna().all():
        val = details.str.extract(r"(-?\d[\d,]*(?:\.\d+)?)\s*$", expand=False)
    bgr = pd.to_numeric(val.astype(str).str.replace(",", "", regex=False), errors="coerce")

    color = styles.str.extract(r"fill-color:\s*(#[0-9A-Fa-f]{6})", expand=False).str.upper()

    out = pd.DataFrame({"date": date, "point": point, "bgr": bgr, "color": color}).dropna(subset=["date", "bgr"])
    out["point"] = out["point"].fillna(-1).astype(int)
    return out.sort_values(["date", "point"]).reset_index(drop=True)


def _extract_alarm_rows(df: pd.DataFrame, value_col: str, threshold: float) -> pd.DataFrame:
    if df.empty or "date" not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=["date", "value"])
    alarms = df.loc[df[value_col] > threshold, ["date", value_col]].copy()
    alarms = alarms.rename(columns={value_col: "value"})
    alarms["date"] = pd.to_datetime(alarms["date"], errors="coerce").dt.normalize()
    alarms = alarms.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return alarms


def _build_alarm_correlation(chl_avg: pd.DataFrame, turb_avg: pd.DataFrame) -> dict:
    empty = {
        "chl_alarm_count": 0,
        "turb_alarm_count": 0,
        "shared_alarm_count": 0,
        "jaccard": np.nan,
        "chl_overlap": np.nan,
        "turb_overlap": np.nan,
        "pearson": np.nan,
        "paired_points": 0,
        "shared_dates": [],
    }
    if chl_avg.empty or turb_avg.empty:
        return empty
    if "date" not in chl_avg.columns or "value" not in chl_avg.columns:
        return empty
    if "date" not in turb_avg.columns or "satellite" not in turb_avg.columns:
        return empty

    chl = chl_avg[["date", "value"]].copy()
    turb = turb_avg[["date", "satellite"]].copy()
    chl["date"] = pd.to_datetime(chl["date"], errors="coerce").dt.normalize()
    turb["date"] = pd.to_datetime(turb["date"], errors="coerce").dt.normalize()
    chl = chl.dropna(subset=["date", "value"]).groupby("date", as_index=False)["value"].mean()
    turb = turb.dropna(subset=["date", "satellite"]).groupby("date", as_index=False)["satellite"].mean()

    chl_alarm_dates = set(chl.loc[chl["value"] > CHL_ALERT_THRESHOLD, "date"])
    turb_alarm_dates = set(turb.loc[turb["satellite"] > TURBIDITY_ALERT_THRESHOLD, "date"])
    shared_dates = sorted(chl_alarm_dates & turb_alarm_dates)
    union_count = len(chl_alarm_dates | turb_alarm_dates)

    aligned = chl.rename(columns={"value": "chl"}).merge(
        turb.rename(columns={"satellite": "turb"}),
        on="date",
        how="inner",
    )
    pearson = np.nan
    if len(aligned) >= 2:
        pearson = float(aligned["chl"].corr(aligned["turb"], method="pearson"))

    return {
        "chl_alarm_count": len(chl_alarm_dates),
        "turb_alarm_count": len(turb_alarm_dates),
        "shared_alarm_count": len(shared_dates),
        "jaccard": (len(shared_dates) / union_count) if union_count else np.nan,
        "chl_overlap": (len(shared_dates) / len(chl_alarm_dates)) if chl_alarm_dates else np.nan,
        "turb_overlap": (len(shared_dates) / len(turb_alarm_dates)) if turb_alarm_dates else np.nan,
        "pearson": pearson,
        "paired_points": len(aligned),
        "shared_dates": [d.strftime("%Y-%m-%d") for d in shared_dates],
    }


@st.cache_data(show_spinner=False)
def load_level(root: str) -> pd.DataFrame:
    r = Path(root)
    candidates = (
        list(r.glob("*level*.csv"))  + list(r.glob("*Level*.csv"))   +
        list(r.glob("*υψος*.csv"))   + list(r.glob("*ύψος*.csv"))    +
        list(r.glob("*storage*.csv"))+ list(r.glob("*water*.csv"))
    )
    if not candidates:
        return pd.DataFrame()
    raw = pd.read_csv(candidates[0], encoding="utf-8-sig")
    date_col = next((c for c in raw.columns if any(k in c.lower() for k in ["date","ημερ"])), raw.columns[0])
    val_col  = next((c for c in raw.columns if any(k in c.lower() for k in ["level","υψ","ύψ","height","storage","value"])),
                    raw.columns[1] if len(raw.columns) > 1 else raw.columns[0])
    out = pd.DataFrame({
        "date":  pd.to_datetime(raw[date_col], errors="coerce"),
        "value": pd.to_numeric(raw[val_col],   errors="coerce"),
        "col":   val_col,
    }).dropna(subset=["date","value"])
    return out.sort_values("date").reset_index(drop=True)


# ── Altair theme helper ────────────────────────────────────────────────────────
_AX = dict(
    labelColor="#5aa8c4", titleColor="#dff2fa",
    labelFont="Plus Jakarta Sans, sans-serif", titleFont="Bricolage Grotesque, sans-serif",
    labelFontSize=11, titleFontSize=11, titleFontWeight=600,
    gridColor="rgba(6,214,240,.06)", domainColor="rgba(6,214,240,.18)",
    tickColor="rgba(6,214,240,.18)", tickSize=4,
)
def _chart_cfg(c):
    return (c
        .configure_view(fill="#060d18", stroke=None, continuousWidth=700, continuousHeight=300)
        .configure_axis(**_AX)
        .configure_title(color="#c8e4f4", fontSize=13)
        .interactive()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  UI SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
def render_profile_line_toggle_button() -> None:
    show_line = st.session_state.get("show_profile_line_on_map", False)
    label = "Απόκρυψη γραμμής" if show_line else "Εμφάνιση γραμμής"
    if st.button(label, key="btn_profile_line_toggle", use_container_width=False):
        st.session_state["show_profile_line_on_map"] = not show_line
        st.rerun()


def _legacy_section_chlorophyll_broken() -> None:
    points_csv = DATA_ROOT / "VALIDATED_CHLOROPHYL.csv"
    avg_csv    = DATA_ROOT / "VALIDATED_AVERAGED CHLOROPHYLL.csv"

    st.markdown("<div class='slabel'>📊 Διαγράμματα Επικυρωμένης Χλωροφύλλης</div>",
                unsafe_allow_html=True)
    render_profile_line_toggle_button()
    pts_raw = load_profile_points(
        csv=str(points_csv),
        value_regex=r"NDTI[^:]*:\s*(-?\d+(?:\.\d+)?)",
        value_name="ndti",
    )
    avg_raw = load_turbidity_avg(str(avg_csv))

    turb_date_parts: list[pd.Series] = []
    if not pts_raw.empty and "date" in pts_raw.columns:
        turb_date_parts.append(pd.to_datetime(pts_raw["date"], errors="coerce"))
    if not avg_raw.empty and "date" in avg_raw.columns:
        turb_date_parts.append(pd.to_datetime(avg_raw["date"], errors="coerce"))

    turb_start = None
    turb_end = None
    if turb_date_parts:
        turb_dates = pd.concat(turb_date_parts, ignore_index=True).dropna()
        if not turb_dates.empty:
            dmin = turb_dates.min().date()
            dmax = turb_dates.max().date()
            turb_range = st.date_input(
                "Χρονικό διάστημα διαγραμμάτων θολότητας",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="mobile_turb_section_date_range",
            )
            if isinstance(turb_range, (list, tuple)) and len(turb_range) == 2:
                turb_start = pd.Timestamp(turb_range[0])
                turb_end = pd.Timestamp(turb_range[1])
    pts_raw = load_chl_points(str(points_csv))
    avg_raw = load_chl_avg(str(avg_csv))

    date_parts: list[pd.Series] = []
    if not pts_raw.empty and "date" in pts_raw.columns:
        date_parts.append(pd.to_datetime(pts_raw["date"], errors="coerce"))
    if not avg_raw.empty and "date" in avg_raw.columns:
        date_parts.append(pd.to_datetime(avg_raw["date"], errors="coerce"))

    chl_start = None
    chl_end = None
    if date_parts:
        date_all = pd.concat(date_parts, ignore_index=True).dropna()
        if not date_all.empty:
            dmin = date_all.min().date()
            dmax = date_all.max().date()
            chl_range = st.date_input(
                "Χρονικό διάστημα διαγραμμάτων χλωροφύλλης",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="mobile_chl_section_date_range",
            )
            if isinstance(chl_range, (list, tuple)) and len(chl_range) == 2:
                chl_start = pd.Timestamp(chl_range[0])
                chl_end = pd.Timestamp(chl_range[1])
    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = pts_raw.copy()
        if chl_start is not None and chl_end is not None and not pts.empty:
            pts = pts[(pts["date"] >= chl_start) & (pts["date"] <= chl_end)].copy()
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα.")
        else:
            c1, c2 = st.columns(1) if _is_mobile else st.columns(2)
            sz = c1.slider("Μέγεθος κουκκίδας", 10, 130, 58, 4)
            op = c2.slider("Διαφάνεια κουκκίδας", .2, 1., .88, .02)
            plot = pts[pts["point"] >= 0].copy()
            plot["color"] = plot["color"].fillna("#6E778A")
            uc = sorted(plot["color"].unique().tolist())
            ch = (
                alt.Chart(plot)
                .mark_circle(size=int(sz), opacity=float(op))
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία",
                            axis=alt.Axis(format="%b %y", labelAngle=-30)),
                    y=alt.Y("point:Q", title="Θέση (σημείο)"),
                    color=alt.Color("color:N",
                                    scale=alt.Scale(domain=uc, range=uc), legend=None),
                    tooltip=[
                        alt.Tooltip("date:T",  title="Ημερομηνία"),
                        alt.Tooltip("point:Q", title="Σημείο"),
                        alt.Tooltip("chl_a:Q", title="Chl-a", format=".3f"),
                    ],
                )
                .properties(height=460)
            )
            st.altair_chart(_chart_cfg(ch), use_container_width=True)
            m1,m2,m3 = st.columns(3)
            m1.metric("Εγγραφές",      f"{len(pts):,}")
            m2.metric("Ημερομηνίες",   f"{plot['date'].nunique():,}")
            m3.metric("Σημεία μέτρησης",f"{plot['point'].nunique():,}")

    with tab_avg:
        avg = avg_raw.copy()
        if chl_start is not None and chl_end is not None and not avg.empty:
            avg = avg[(avg["date"] >= chl_start) & (avg["date"] <= chl_end)].copy()
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής.")
        else:
            smooth = st.slider("Εξομάλυνση (ημέρες)", 1, 30, 1)
            avg = avg.copy()
            avg["display"] = avg["value"].rolling(smooth, min_periods=1).mean()
            avg["chl_alarm"] = avg["value"] > CHL_ALERT_THRESHOLD
            chl_alarm_rows = _extract_alarm_rows(avg, "value", CHL_ALERT_THRESHOLD)
            area = (
                alt.Chart(avg)
                .mark_area(
                    line={"color":"#06d6f0","strokeWidth":2},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="rgba(6,214,240,.4)", offset=0),
                            alt.GradientStop(color="rgba(6,214,240,.02)", offset=1),
                        ],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                )
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("display:Q", title="Μέση Chl-a", scale=alt.Scale(domain=[0, 30], clamp=True)),
                    tooltip=[
                        alt.Tooltip("date:T",    title="Ημερομηνία"),
                        alt.Tooltip("display:Q", title="Chl-a", format=".3f"),
                    ],
                )
                .properties(height=360)
            )
            danger_zone = (
                alt.Chart(pd.DataFrame({"ymin": [CHL_ALERT_THRESHOLD], "ymax": [30.0]}))
                .mark_rect(color="#ef4444", opacity=0.16)
                .encode(y="ymin:Q", y2="ymax:Q")
            )
            limit_rule = (
                alt.Chart(avg)
                .mark_rule(color="#ef4444", strokeWidth=3, strokeDash=[8, 5], opacity=0.95)
                .encode(y=alt.datum(CHL_ALERT_THRESHOLD))
            )
            alarm_points = (
                alt.Chart(avg[avg["chl_alarm"]])
                .mark_circle(color="#ef4444", size=70)
                .encode(
                    x="date:T",
                    y="display:Q",
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("value:Q", title="Μέση Chl-a", format=".3f"),
                    ],
                )
            )
            st.altair_chart(_chart_cfg(alt.layer(area, danger_zone, limit_rule, alarm_points)), use_container_width=True)
            if chl_alarm_rows.empty:
                st.success("Δεν υπάρχουν alarms χλωροφύλλης πάνω από 24.")
            else:
                st.warning(f"Καταγράφηκαν {len(chl_alarm_rows)} alarms χλωροφύλλης (> 24).")
                st.dataframe(
                    pd.DataFrame({
                        "Ημερομηνία": chl_alarm_rows["date"].dt.strftime("%Y-%m-%d"),
                        "Μέση Chl-a": chl_alarm_rows["value"].round(3),
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
            m1,m2,m3 = st.columns(3)
            m1.metric("Ελάχιστη", f"{avg['value'].min():.3f}")
            m2.metric("Μέγιστη",  f"{avg['value'].max():.3f}")
            m3.metric("Μέση",     f"{avg['value'].mean():.3f}")


def _legacy_section_turbidity_broken() -> None:
    charts_root = DATA_ROOT / "charts_turbidity"
    points_csv = charts_root / "homvoller turbidity.csv"
    avg_csv = charts_root / "average turbidity.csv"

    st.markdown("<div class='slabel'>📉 Διαγράμματα Θολότητας</div>", unsafe_allow_html=True)
    render_profile_line_toggle_button()
    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = pts_raw.copy()
        if turb_start is not None and turb_end is not None and not pts.empty:
            pts = pts[(pts["date"] >= turb_start) & (pts["date"] <= turb_end)].copy()
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα θολότητας.")
        else:
            c1, c2 = st.columns(1) if _is_mobile else st.columns(2)
            size = c1.slider("Μέγεθος κουκκίδας", 10, 130, 58, 4, key="turb_size")
            opacity = c2.slider("Διαφάνεια κουκκίδας", 0.2, 1.0, 0.88, 0.02, key="turb_opacity")

            plot = pts[pts["point"] >= 0].copy()
            plot["color"] = plot["color"].fillna("#6E778A")
            unique_colors = sorted(plot["color"].unique().tolist())
            ch = (
                alt.Chart(plot)
                .mark_circle(size=int(size), opacity=float(opacity))
                .encode(
                    x=alt.X(
                        "date:T",
                        title="Ημερομηνία",
                        axis=alt.Axis(format="%b %y", labelAngle=-30),
                    ),
                    y=alt.Y("point:Q", title="Θέση (σημείο)"),
                    color=alt.Color(
                        "color:N",
                        scale=alt.Scale(domain=unique_colors, range=unique_colors),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("point:Q", title="Σημείο"),
                        alt.Tooltip("ndti:Q", title="NDTI", format=".3f"),
                    ],
                )
                .properties(height=460)
            )
            st.altair_chart(_chart_cfg(ch), use_container_width=True)

            m1, m2, m3 = st.columns(1) if _is_mobile else st.columns(3)
            m1.metric("Εγγραφές", f"{len(pts):,}")
            m2.metric("Ημερομηνίες", f"{plot['date'].nunique():,}")
            m3.metric("Σημεία μέτρησης", f"{plot['point'].nunique():,}")

    with tab_avg:
        avg = avg_raw.copy()
        if turb_start is not None and turb_end is not None and not avg.empty:
            avg = avg[(avg["date"] >= turb_start) & (avg["date"] <= turb_end)].copy()
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής θολότητας.")
        else:
            smooth = st.slider("Εξομάλυνση (ημέρες)", 1, 30, 1, key="turb_smooth")
            avg = avg.copy()
            avg["satellite_display"] = avg["satellite"].rolling(smooth, min_periods=1).mean()
            avg["turb_alarm"] = avg["satellite"] > TURBIDITY_ALERT_THRESHOLD
            turb_alarm_rows = _extract_alarm_rows(avg, "satellite", TURBIDITY_ALERT_THRESHOLD)

            sat_line = (
                alt.Chart(avg)
                .mark_line(color="#06d6f0", strokeWidth=2.2)
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("satellite_display:Q", title="Δορυφορική τιμή (NDTI)"),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("satellite_display:Q", title="NDTI", format=".3f"),
                    ],
                )
            )
            sat_points = alt.Chart(avg).mark_point(color="#06d6f0", size=35, opacity=0.85).encode(
                x="date:T", y="satellite_display:Q"
            )
            sat_limit_rule = (
                alt.Chart(avg)
                .mark_rule(color="#ef4444", strokeWidth=3, strokeDash=[8, 5], opacity=0.95)
                .encode(y=alt.datum(TURBIDITY_ALERT_THRESHOLD))
            )
            sat_alarm_points = (
                alt.Chart(avg[avg["turb_alarm"]])
                .mark_circle(color="#ef4444", size=70)
                .encode(
                    x="date:T",
                    y="satellite_display:Q",
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("satellite:Q", title="Μέση NDTI", format=".3f"),
                    ],
                )
            )

            layers = [sat_line, sat_points, sat_limit_rule, sat_alarm_points]
            if avg["field"].notna().any():
                field = avg.dropna(subset=["field"]).copy()
                field["field_display"] = field["field"].rolling(smooth, min_periods=1).mean()
                field_line = (
                    alt.Chart(field)
                    .mark_line(color="#f59e0b", strokeWidth=2.2, strokeDash=[6, 4])
                    .encode(
                        x="date:T",
                        y=alt.Y(
                            "field_display:Q",
                            title="Μετρήσεις πεδίου (NTU)",
                            axis=alt.Axis(titleColor="#f59e0b", labelColor="#f59e0b"),
                        ),
                        tooltip=[
                            alt.Tooltip("date:T", title="Ημερομηνία"),
                            alt.Tooltip("field_display:Q", title="NTU", format=".3f"),
                        ],
                    )
                )
                field_points = alt.Chart(field).mark_point(color="#f59e0b", size=42, opacity=0.9).encode(
                    x="date:T", y="field_display:Q"
                )
                layers.extend([field_line, field_points])

            chart = alt.layer(*layers).resolve_scale(y="independent").properties(height=360)
            st.altair_chart(_chart_cfg(chart), use_container_width=True)

            if turb_alarm_rows.empty:
                st.success("Δεν υπάρχουν alarms θολότητας πάνω από 1.85.")
            else:
                st.warning(f"Καταγράφηκαν {len(turb_alarm_rows)} alarms θολότητας (> 1.85).")
                st.dataframe(
                    pd.DataFrame({
                        "Ημερομηνία": turb_alarm_rows["date"].dt.strftime("%Y-%m-%d"),
                        "Μέση NDTI": turb_alarm_rows["value"].round(3),
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

            chl_avg_for_corr = load_chl_avg(str(DATA_ROOT / "VALIDATED_AVERAGED CHLOROPHYLL.csv"))
            if turb_start is not None and turb_end is not None and not chl_avg_for_corr.empty:
                chl_avg_for_corr = chl_avg_for_corr[
                    (chl_avg_for_corr["date"] >= turb_start) & (chl_avg_for_corr["date"] <= turb_end)
                ].copy()
            alarm_corr = _build_alarm_correlation(chl_avg_for_corr, avg)
            st.markdown("#### Συσχέτιση alarms χλωροφύλλης-θολότητας")
            c1, c2, c3, c4 = st.columns(2) + st.columns(2) if _is_mobile else st.columns(4)
            c1.metric("Κοινά alarms", f"{alarm_corr['shared_alarm_count']}")
            c2.metric("Alarm ημέρες Chl-a", f"{alarm_corr['chl_alarm_count']}")
            c3.metric("Alarm ημέρες NDTI", f"{alarm_corr['turb_alarm_count']}")
            if np.isnan(alarm_corr["pearson"]):
                c4.metric("Pearson r", "n/a")
            else:
                c4.metric("Pearson r", f"{alarm_corr['pearson']:.3f}")

            overlap_text = []
            if not np.isnan(alarm_corr["jaccard"]):
                overlap_text.append(f"Jaccard overlap: {alarm_corr['jaccard']:.1%}")
            if not np.isnan(alarm_corr["chl_overlap"]):
                overlap_text.append(f"Κάλυψη alarm Chl-a: {alarm_corr['chl_overlap']:.1%}")
            if not np.isnan(alarm_corr["turb_overlap"]):
                overlap_text.append(f"Κάλυψη alarm NDTI: {alarm_corr['turb_overlap']:.1%}")
            if alarm_corr["paired_points"] > 0:
                overlap_text.append(f"Κοινές ημερομηνίες για Pearson: {alarm_corr['paired_points']}")
            if overlap_text:
                st.caption(" | ".join(overlap_text))

            if alarm_corr["shared_dates"]:
                st.dataframe(
                    pd.DataFrame({"Κοινές ημερομηνίες alarm": alarm_corr["shared_dates"]}),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Δεν βρέθηκαν κοινές ημερομηνίες όπου και οι δύο δείκτες ήταν σε alarm.")

            m1, m2, m3, m4 = (st.columns(2) + st.columns(2)) if _is_mobile else st.columns(4)
            m1.metric("Ελάχιστη (NDTI)", f"{avg['satellite'].min():.3f}")
            m2.metric("Μέγιστη (NDTI)", f"{avg['satellite'].max():.3f}")
            m3.metric("Μέση (NDTI)", f"{avg['satellite'].mean():.3f}")
            m4.metric("Μετρήσεις πεδίου", f"{avg['field'].notna().sum():,}")


def section_chlorophyll() -> None:
    points_csv = DATA_ROOT / "VALIDATED_CHLOROPHYL.csv"
    avg_csv = DATA_ROOT / "VALIDATED_AVERAGED CHLOROPHYLL.csv"

    st.markdown(
        "<div class='slabel'>📊 Διαγράμματα Επικυρωμένης Χλωροφύλλης</div>",
        unsafe_allow_html=True,
    )
    render_profile_line_toggle_button()
    pts_raw = load_chl_points(str(points_csv))
    avg_raw = load_chl_avg(str(avg_csv))

    date_parts: list[pd.Series] = []
    if not pts_raw.empty and "date" in pts_raw.columns:
        date_parts.append(pd.to_datetime(pts_raw["date"], errors="coerce"))
    if not avg_raw.empty and "date" in avg_raw.columns:
        date_parts.append(pd.to_datetime(avg_raw["date"], errors="coerce"))

    chl_start = None
    chl_end = None
    if date_parts:
        date_all = pd.concat(date_parts, ignore_index=True).dropna()
        if not date_all.empty:
            dmin = date_all.min().date()
            dmax = date_all.max().date()
            chl_range = st.date_input(
                "Χρονικό διάστημα διαγραμμάτων χλωροφύλλης",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="mobile_chl_section_date_range",
            )
            if isinstance(chl_range, (list, tuple)) and len(chl_range) == 2:
                chl_start = pd.Timestamp(chl_range[0])
                chl_end = pd.Timestamp(chl_range[1])

    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = pts_raw.copy()
        if chl_start is not None and chl_end is not None and not pts.empty:
            pts = pts[(pts["date"] >= chl_start) & (pts["date"] <= chl_end)].copy()
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα για το επιλεγμένο χρονικό διάστημα.")
        else:
            c1, c2 = st.columns(1) if _is_mobile else st.columns(2)
            sz = c1.slider("Μέγεθος κουκκίδας", 10, 130, 58, 4)
            op = c2.slider("Διαφάνεια κουκκίδας", 0.2, 1.0, 0.88, 0.02)
            plot = pts[pts["point"] >= 0].copy()
            plot["color"] = plot["color"].fillna("#6E778A")
            uc = sorted(plot["color"].unique().tolist())
            ch = (
                alt.Chart(plot)
                .mark_circle(size=int(sz), opacity=float(op))
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία", axis=alt.Axis(format="%b %y", labelAngle=-30)),
                    y=alt.Y("point:Q", title="Θέση (σημείο)"),
                    color=alt.Color("color:N", scale=alt.Scale(domain=uc, range=uc), legend=None),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("point:Q", title="Σημείο"),
                        alt.Tooltip("chl_a:Q", title="Chl-a", format=".3f"),
                    ],
                )
                .properties(height=460)
            )
            st.altair_chart(_chart_cfg(ch), use_container_width=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Εγγραφές", f"{len(pts):,}")
            m2.metric("Ημερομηνίες", f"{plot['date'].nunique():,}")
            m3.metric("Σημεία μέτρησης", f"{plot['point'].nunique():,}")

    with tab_avg:
        avg = avg_raw.copy()
        if chl_start is not None and chl_end is not None and not avg.empty:
            avg = avg[(avg["date"] >= chl_start) & (avg["date"] <= chl_end)].copy()
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής για το επιλεγμένο χρονικό διάστημα.")
        else:
            smooth = st.slider("Εξομάλυνση (ημέρες)", 1, 30, 1)
            avg = avg.copy()
            avg["display"] = avg["value"].rolling(smooth, min_periods=1).mean()
            avg["chl_alarm"] = avg["value"] > CHL_ALERT_THRESHOLD
            chl_alarm_rows = _extract_alarm_rows(avg, "value", CHL_ALERT_THRESHOLD)

            area = (
                alt.Chart(avg)
                .mark_area(
                    line={"color": "#06d6f0", "strokeWidth": 2},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="rgba(6,214,240,.4)", offset=0),
                            alt.GradientStop(color="rgba(6,214,240,.02)", offset=1),
                        ],
                        x1=1,
                        x2=1,
                        y1=1,
                        y2=0,
                    ),
                )
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("display:Q", title="Μέση Chl-a", scale=alt.Scale(domain=[0, 30], clamp=True)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("display:Q", title="Chl-a", format=".3f"),
                    ],
                )
                .properties(height=360)
            )
            danger_zone = (
                alt.Chart(pd.DataFrame({"ymin": [CHL_ALERT_THRESHOLD], "ymax": [30.0]}))
                .mark_rect(color="#ef4444", opacity=0.16)
                .encode(y="ymin:Q", y2="ymax:Q")
            )
            limit_rule = (
                alt.Chart(avg)
                .mark_rule(color="#ef4444", strokeWidth=3, strokeDash=[8, 5], opacity=0.95)
                .encode(y=alt.datum(CHL_ALERT_THRESHOLD))
            )
            alarm_points = (
                alt.Chart(avg[avg["chl_alarm"]])
                .mark_circle(color="#ef4444", size=70)
                .encode(
                    x="date:T",
                    y="display:Q",
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("value:Q", title="Μέση Chl-a", format=".3f"),
                    ],
                )
            )
            st.altair_chart(_chart_cfg(alt.layer(area, danger_zone, limit_rule, alarm_points)), use_container_width=True)
            if chl_alarm_rows.empty:
                st.success("Δεν υπάρχουν alarms χλωροφύλλης πάνω από 24.")
            else:
                st.warning(f"Καταγράφηκαν {len(chl_alarm_rows)} alarms χλωροφύλλης (> 24).")
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Ημερομηνία": chl_alarm_rows["date"].dt.strftime("%Y-%m-%d"),
                            "Μέση Chl-a": chl_alarm_rows["value"].round(3),
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            m1, m2, m3 = st.columns(3)
            m1.metric("Ελάχιστη", f"{avg['value'].min():.3f}")
            m2.metric("Μέγιστη", f"{avg['value'].max():.3f}")
            m3.metric("Μέση", f"{avg['value'].mean():.3f}")


def section_turbidity() -> None:
    charts_root = DATA_ROOT / "charts_turbidity"
    points_csv = charts_root / "homvoller turbidity.csv"
    avg_csv = charts_root / "average turbidity.csv"

    st.markdown("<div class='slabel'>📉 Διαγράμματα Θολότητας</div>", unsafe_allow_html=True)
    render_profile_line_toggle_button()
    pts_raw = load_profile_points(
        csv=str(points_csv),
        value_regex=r"NDTI[^:]*:\s*(-?\d+(?:\.\d+)?)",
        value_name="ndti",
    )
    avg_raw = load_turbidity_avg(str(avg_csv))

    turb_date_parts: list[pd.Series] = []
    if not pts_raw.empty and "date" in pts_raw.columns:
        turb_date_parts.append(pd.to_datetime(pts_raw["date"], errors="coerce"))
    if not avg_raw.empty and "date" in avg_raw.columns:
        turb_date_parts.append(pd.to_datetime(avg_raw["date"], errors="coerce"))

    turb_start = None
    turb_end = None
    if turb_date_parts:
        turb_dates = pd.concat(turb_date_parts, ignore_index=True).dropna()
        if not turb_dates.empty:
            dmin = turb_dates.min().date()
            dmax = turb_dates.max().date()
            turb_range = st.date_input(
                "Χρονικό διάστημα διαγραμμάτων θολότητας",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="mobile_turb_section_date_range",
            )
            if isinstance(turb_range, (list, tuple)) and len(turb_range) == 2:
                turb_start = pd.Timestamp(turb_range[0])
                turb_end = pd.Timestamp(turb_range[1])

    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = pts_raw.copy()
        if turb_start is not None and turb_end is not None and not pts.empty:
            pts = pts[(pts["date"] >= turb_start) & (pts["date"] <= turb_end)].copy()
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα θολότητας για το επιλεγμένο χρονικό διάστημα.")
        else:
            c1, c2 = st.columns(1) if _is_mobile else st.columns(2)
            size = c1.slider("Μέγεθος κουκκίδας", 10, 130, 58, 4, key="turb_size")
            opacity = c2.slider("Διαφάνεια κουκκίδας", 0.2, 1.0, 0.88, 0.02, key="turb_opacity")

            plot = pts[pts["point"] >= 0].copy()
            plot["color"] = plot["color"].fillna("#6E778A")
            unique_colors = sorted(plot["color"].unique().tolist())
            ch = (
                alt.Chart(plot)
                .mark_circle(size=int(size), opacity=float(opacity))
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία", axis=alt.Axis(format="%b %y", labelAngle=-30)),
                    y=alt.Y("point:Q", title="Θέση (σημείο)"),
                    color=alt.Color("color:N", scale=alt.Scale(domain=unique_colors, range=unique_colors), legend=None),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("point:Q", title="Σημείο"),
                        alt.Tooltip("ndti:Q", title="NDTI", format=".3f"),
                    ],
                )
                .properties(height=460)
            )
            st.altair_chart(_chart_cfg(ch), use_container_width=True)

            m1, m2, m3 = st.columns(1) if _is_mobile else st.columns(3)
            m1.metric("Εγγραφές", f"{len(pts):,}")
            m2.metric("Ημερομηνίες", f"{plot['date'].nunique():,}")
            m3.metric("Σημεία μέτρησης", f"{plot['point'].nunique():,}")

    with tab_avg:
        avg = avg_raw.copy()
        if turb_start is not None and turb_end is not None and not avg.empty:
            avg = avg[(avg["date"] >= turb_start) & (avg["date"] <= turb_end)].copy()
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής θολότητας για το επιλεγμένο χρονικό διάστημα.")
        else:
            smooth = st.slider("Εξομάλυνση (ημέρες)", 1, 30, 1, key="turb_smooth")
            avg = avg.copy()
            avg["satellite_display"] = avg["satellite"].rolling(smooth, min_periods=1).mean()
            avg["turb_alarm"] = avg["satellite"] > TURBIDITY_ALERT_THRESHOLD
            turb_alarm_rows = _extract_alarm_rows(avg, "satellite", TURBIDITY_ALERT_THRESHOLD)

            sat_line = (
                alt.Chart(avg)
                .mark_line(color="#06d6f0", strokeWidth=2.2)
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("satellite_display:Q", title="Δορυφορική τιμή (NDTI)"),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("satellite_display:Q", title="NDTI", format=".3f"),
                    ],
                )
            )
            sat_points = alt.Chart(avg).mark_point(color="#06d6f0", size=35, opacity=0.85).encode(
                x="date:T", y="satellite_display:Q"
            )
            sat_limit_rule = (
                alt.Chart(avg)
                .mark_rule(color="#ef4444", strokeWidth=3, strokeDash=[8, 5], opacity=0.95)
                .encode(y=alt.datum(TURBIDITY_ALERT_THRESHOLD))
            )
            sat_alarm_points = (
                alt.Chart(avg[avg["turb_alarm"]])
                .mark_circle(color="#ef4444", size=70)
                .encode(
                    x="date:T",
                    y="satellite_display:Q",
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("satellite:Q", title="Μέση NDTI", format=".3f"),
                    ],
                )
            )

            layers = [sat_line, sat_points, sat_limit_rule, sat_alarm_points]
            if avg["field"].notna().any():
                field = avg.dropna(subset=["field"]).copy()
                field["field_display"] = field["field"].rolling(smooth, min_periods=1).mean()
                field_line = (
                    alt.Chart(field)
                    .mark_line(color="#f59e0b", strokeWidth=2.2, strokeDash=[6, 4])
                    .encode(
                        x="date:T",
                        y=alt.Y(
                            "field_display:Q",
                            title="Μετρήσεις πεδίου (NTU)",
                            axis=alt.Axis(titleColor="#f59e0b", labelColor="#f59e0b"),
                        ),
                        tooltip=[
                            alt.Tooltip("date:T", title="Ημερομηνία"),
                            alt.Tooltip("field_display:Q", title="NTU", format=".3f"),
                        ],
                    )
                )
                field_points = alt.Chart(field).mark_point(color="#f59e0b", size=42, opacity=0.9).encode(
                    x="date:T", y="field_display:Q"
                )
                layers.extend([field_line, field_points])

            chart = alt.layer(*layers).resolve_scale(y="independent").properties(height=360)
            st.altair_chart(_chart_cfg(chart), use_container_width=True)

            if turb_alarm_rows.empty:
                st.success("Δεν υπάρχουν alarms θολότητας πάνω από 1.85.")
            else:
                st.warning(f"Καταγράφηκαν {len(turb_alarm_rows)} alarms θολότητας (> 1.85).")
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Ημερομηνία": turb_alarm_rows["date"].dt.strftime("%Y-%m-%d"),
                            "Μέση NDTI": turb_alarm_rows["value"].round(3),
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            chl_avg_for_corr = load_chl_avg(str(DATA_ROOT / "VALIDATED_AVERAGED CHLOROPHYLL.csv"))
            if turb_start is not None and turb_end is not None and not chl_avg_for_corr.empty:
                chl_avg_for_corr = chl_avg_for_corr[
                    (chl_avg_for_corr["date"] >= turb_start) & (chl_avg_for_corr["date"] <= turb_end)
                ].copy()
            alarm_corr = _build_alarm_correlation(chl_avg_for_corr, avg)
            st.markdown("#### Συσχέτιση alarms χλωροφύλλης-θολότητας")
            c1, c2, c3, c4 = st.columns(2) + st.columns(2) if _is_mobile else st.columns(4)
            c1.metric("Κοινά alarms", f"{alarm_corr['shared_alarm_count']}")
            c2.metric("Alarm ημέρες Chl-a", f"{alarm_corr['chl_alarm_count']}")
            c3.metric("Alarm ημέρες NDTI", f"{alarm_corr['turb_alarm_count']}")
            if np.isnan(alarm_corr["pearson"]):
                c4.metric("Pearson r", "n/a")
            else:
                c4.metric("Pearson r", f"{alarm_corr['pearson']:.3f}")

            overlap_text = []
            if not np.isnan(alarm_corr["jaccard"]):
                overlap_text.append(f"Jaccard overlap: {alarm_corr['jaccard']:.1%}")
            if not np.isnan(alarm_corr["chl_overlap"]):
                overlap_text.append(f"Κάλυψη alarm Chl-a: {alarm_corr['chl_overlap']:.1%}")
            if not np.isnan(alarm_corr["turb_overlap"]):
                overlap_text.append(f"Κάλυψη alarm NDTI: {alarm_corr['turb_overlap']:.1%}")
            if alarm_corr["paired_points"] > 0:
                overlap_text.append(f"Κοινές ημερομηνίες για Pearson: {alarm_corr['paired_points']}")
            if overlap_text:
                st.caption(" | ".join(overlap_text))

            if alarm_corr["shared_dates"]:
                st.dataframe(
                    pd.DataFrame({"Κοινές ημερομηνίες alarm": alarm_corr["shared_dates"]}),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Δεν βρέθηκαν κοινές ημερομηνίες όπου και οι δύο δείκτες ήταν σε alarm.")

            m1, m2, m3, m4 = (st.columns(2) + st.columns(2)) if _is_mobile else st.columns(4)
            m1.metric("Ελάχιστη (NDTI)", f"{avg['satellite'].min():.3f}")
            m2.metric("Μέγιστη (NDTI)", f"{avg['satellite'].max():.3f}")
            m3.metric("Μέση (NDTI)", f"{avg['satellite'].mean():.3f}")
            m4.metric("Μετρήσεις πεδίου", f"{avg['field'].notna().sum():,}")


def section_bgr() -> None:
    candidate_roots = [
        DATA_ROOT / "charts_BGR",
        DATA_ROOT / "charts_bgr",
        SATELLITE_DATA_ROOT / "DATA" / "charts_BGR",
        SATELLITE_DATA_ROOT / "DATA" / "charts_bgr",
    ]
    charts_root = next((root for root in candidate_roots if root.exists()), candidate_roots[0])
    points_csv = charts_root / "BGR.csv"
    avg_csv = charts_root / "BGR_AVERAGED.csv"

    st.markdown("<div class='slabel'>📈 Διαγράμματα Φαινομένων Λευκασμού (BGR)</div>", unsafe_allow_html=True)
    render_profile_line_toggle_button()
    if not points_csv.exists() and not avg_csv.exists():
        st.error("Δεν βρέθηκαν τα αρχεία BGR CSV για τα διαγράμματα.")
        st.code(
            "Expected files:\n"
            f"- {points_csv}\n"
            f"- {avg_csv}",
            language="text",
        )
        st.info("Κάντε push τον φάκελο `satellite data/DATA/charts_BGR/` (ή `charts_bgr/`) στο GitHub.")
        return

    pts_raw = load_bgr_points(str(points_csv))
    avg_raw = load_bgr_avg(str(avg_csv))
    avg_from_points = False
    if avg_raw.empty and not pts_raw.empty:
        avg_raw = (
            pts_raw.groupby("date", as_index=False)["bgr"]
            .mean()
            .rename(columns={"bgr": "value"})
            .sort_values("date")
            .reset_index(drop=True)
        )
        avg_from_points = True

    bgr_date_parts: list[pd.Series] = []
    if not pts_raw.empty and "date" in pts_raw.columns:
        bgr_date_parts.append(pd.to_datetime(pts_raw["date"], errors="coerce"))
    if not avg_raw.empty and "date" in avg_raw.columns:
        bgr_date_parts.append(pd.to_datetime(avg_raw["date"], errors="coerce"))

    bgr_start = None
    bgr_end = None
    if bgr_date_parts:
        bgr_dates = pd.concat(bgr_date_parts, ignore_index=True).dropna()
        if not bgr_dates.empty:
            dmin = bgr_dates.min().date()
            dmax = bgr_dates.max().date()
            bgr_range = st.date_input(
                "Χρονικό διάστημα διαγραμμάτων BGR",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="mobile_bgr_section_date_range",
            )
            if isinstance(bgr_range, (list, tuple)) and len(bgr_range) == 2:
                bgr_start = pd.Timestamp(bgr_range[0])
                bgr_end = pd.Timestamp(bgr_range[1])

    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = pts_raw.copy()
        if bgr_start is not None and bgr_end is not None and not pts.empty:
            pts = pts[(pts["date"] >= bgr_start) & (pts["date"] <= bgr_end)].copy()
        st.caption(f"Rows: points={len(pts_raw):,}, averaged={len(avg_raw):,}")
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα BGR για το επιλεγμένο χρονικό διάστημα.")
        else:
            c1, c2 = st.columns(1) if _is_mobile else st.columns(2)
            size = c1.slider("Μέγεθος κουκκίδας", 10, 130, 58, 4, key="mobile_bgr_size")
            opacity = c2.slider("Διαφάνεια κουκκίδας", 0.2, 1.0, 0.88, 0.02, key="mobile_bgr_opacity")
            plot = pts[pts["point"] >= 0].copy()
            plot["color"] = plot["color"].fillna("#6E778A")
            unique_colors = sorted(plot["color"].unique().tolist())
            ch = (
                alt.Chart(plot)
                .mark_circle(size=int(size), opacity=float(opacity))
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία", axis=alt.Axis(format="%b %y", labelAngle=-30)),
                    y=alt.Y("point:Q", title="Θέση (σημείο)"),
                    color=alt.Color("color:N", scale=alt.Scale(domain=unique_colors, range=unique_colors), legend=None),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("point:Q", title="Σημείο"),
                        alt.Tooltip("bgr:Q", title="AreaBGR", format=".3f"),
                    ],
                )
                .properties(height=460)
            )
            st.altair_chart(_chart_cfg(ch), use_container_width=True)
            m1, m2, m3 = st.columns(1) if _is_mobile else st.columns(3)
            m1.metric("Εγγραφές", f"{len(pts):,}")
            m2.metric("Ημερομηνίες", f"{plot['date'].nunique():,}")
            m3.metric("Σημεία μέτρησης", f"{plot['point'].nunique():,}")

    with tab_avg:
        avg = avg_raw.copy()
        if bgr_start is not None and bgr_end is not None and not avg.empty:
            avg = avg[(avg["date"] >= bgr_start) & (avg["date"] <= bgr_end)].copy()
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής BGR για το επιλεγμένο χρονικό διάστημα.")
        else:
            if avg_from_points:
                st.caption("Η μέση τιμή BGR υπολογίστηκε από το BGR.csv (fallback, επειδή το BGR_AVERAGED.csv δεν ήταν διαθέσιμο ή έγκυρο).")
            c1, c2 = st.columns(1) if _is_mobile else st.columns(2)
            smooth = c1.slider("Εξομάλυνση (ημέρες)", 1, 30, 1, key="mobile_bgr_smooth")
            p90 = float(avg["value"].quantile(0.90))
            threshold = c2.number_input(
                "Όριο υψηλών τιμών BGR",
                min_value=0.0,
                value=max(1.0, round(p90, 3)),
                step=1000.0,
                key="mobile_bgr_threshold",
            )
            avg["display"] = avg["value"].rolling(smooth, min_periods=1).mean()
            avg["bgr_alarm"] = avg["value"] > threshold
            bgr_alarm_rows = _extract_alarm_rows(avg, "value", float(threshold))

            area = (
                alt.Chart(avg)
                .mark_area(
                    line={"color": "#06d6f0", "strokeWidth": 2},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="rgba(6,214,240,.4)", offset=0),
                            alt.GradientStop(color="rgba(6,214,240,.02)", offset=1),
                        ],
                        x1=1,
                        x2=1,
                        y1=1,
                        y2=0,
                    ),
                )
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("display:Q", title="Μέση AreaBGR"),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("display:Q", title="AreaBGR", format=".3f"),
                    ],
                )
                .properties(height=360)
            )
            limit_rule = (
                alt.Chart(avg)
                .mark_rule(color="#ef4444", strokeWidth=3, strokeDash=[8, 5], opacity=0.95)
                .encode(y=alt.datum(float(threshold)))
            )
            alarm_points = (
                alt.Chart(avg[avg["bgr_alarm"]])
                .mark_circle(color="#ef4444", size=70)
                .encode(
                    x="date:T",
                    y="display:Q",
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("value:Q", title="AreaBGR", format=".3f"),
                    ],
                )
            )
            st.altair_chart(_chart_cfg(alt.layer(area, limit_rule, alarm_points)), use_container_width=True)

            if bgr_alarm_rows.empty:
                st.success("Δεν εντοπίστηκαν υψηλές τιμές BGR πάνω από το επιλεγμένο όριο.")
            else:
                st.warning(f"Εντοπίστηκαν {len(bgr_alarm_rows)} εγγραφές πάνω από το όριο BGR.")
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Ημερομηνία": bgr_alarm_rows["date"].dt.strftime("%Y-%m-%d"),
                            "AreaBGR": bgr_alarm_rows["value"].round(3),
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            m1, m2, m3 = st.columns(1) if _is_mobile else st.columns(3)
            m1.metric("Ελάχιστη", f"{avg['value'].min():,.3f}")
            m2.metric("Μέγιστη", f"{avg['value'].max():,.3f}")
            m3.metric("Μέση", f"{avg['value'].mean():,.3f}")


def section_level() -> None:
    st.markdown(
        "<div class='lcard'><div class='lcard-title'>📈 Ύψος Στάθμης Ταμιευτήρα Γαδουρά</div>",
        unsafe_allow_html=True,
    )
    df = load_level(str(DATA_ROOT))
    if df.empty:
        st.info(
            f"Δεν βρέθηκε αρχείο CSV για την στάθμη.  \n"
            f"Τοποθετήστε αρχείο με 'level' ή 'υψος' στο όνομα στον φάκελο:  \n`{DATA_ROOT}`"
        )
        return

    val_lbl = df["col"].iloc[0] if "col" in df.columns else "Τιμή (m)"
    dfp = df.drop(columns=["col"], errors="ignore")

    c1, c2, c3 = st.columns(1) if _is_mobile else st.columns([2,1,1])
    with c1:
        drng = st.date_input(
            "Εύρος ημερομηνιών",
            value=(dfp["date"].min().date(), dfp["date"].max().date()),
            min_value=dfp["date"].min().date(),
            max_value=dfp["date"].max().date(),
        )
    with c2:
        sm = st.slider("Εξομάλυνση (ημέρες)", 1, 90, 1)
    with c3:
        ctype = st.radio("Τύπος", ["Εμβαδόν","Γραμμή"], horizontal=True)

    if isinstance(drng, (list,tuple)) and len(drng)==2:
        dfp = dfp[(dfp["date"]>=pd.Timestamp(drng[0])) & (dfp["date"]<=pd.Timestamp(drng[1]))].copy()

    if dfp.empty:
        st.warning("Κανένα δεδομένο στο επιλεγμένο εύρος.")
        return

    dfp["display"] = dfp["value"].rolling(sm, min_periods=1).mean()

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Τελευταία",  f"{dfp['value'].iloc[-1]:.2f} m")
    m2.metric("Μέγιστη",    f"{dfp['value'].max():.2f} m")
    m3.metric("Ελάχιστη",   f"{dfp['value'].min():.2f} m")
    m4.metric("Μέση",       f"{dfp['value'].mean():.2f} m")

    tt = [alt.Tooltip("date:T",    title="Ημερομηνία"),
          alt.Tooltip("display:Q", title=val_lbl, format=".3f")]
    base = alt.Chart(dfp)
    if ctype == "Εμβαδόν":
        mark = base.mark_area(
            line={"color":"#06d6f0","strokeWidth":2},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="rgba(6,214,240,.45)", offset=0),
                    alt.GradientStop(color="rgba(6,214,240,.02)", offset=1),
                ],
                x1=1,x2=1,y1=1,y2=0,
            ),
        )
    else:
        mark = base.mark_line(color="#06d6f0", strokeWidth=2.2,
                              point=alt.OverlayMarkDef(color="#06d6f0", size=25))
    ch = (
        mark.encode(
            x=alt.X("date:T", title="Ημερομηνία"),
            y=alt.Y("display:Q", title=val_lbl, scale=alt.Scale(zero=False)),
            tooltip=tt,
        )
        .properties(height=320)
    )
    st.altair_chart(_chart_cfg(ch), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
# ── Mobile detection (module-level, runs on every rerun) ──────────────────────
_MOBILE_JS = """
<script>
(function() {
    const mobile = window.innerWidth < 768;
    const stored = sessionStorage.getItem('_st_mobile');
    if (mobile !== (stored === '1')) {
        sessionStorage.setItem('_st_mobile', mobile ? '1' : '0');
        const url = new URL(window.location.href);
        url.searchParams.set('_mobile', mobile ? '1' : '0');
        window.location.replace(url.toString());
    }
})();
</script>
"""
st.markdown(_MOBILE_JS, unsafe_allow_html=True)
_qp = st.query_params
_is_mobile = str(_qp.get("_mobile", "0")) == "1"


def render_satellite_dashboard(
    show_header: bool = True,
    show_footer: bool = True,
    show_debug: bool = False,
    apply_css: bool = True,
) -> None:
    if apply_css:
        st.markdown(CSS, unsafe_allow_html=True)

    # ── Header ──────────────────────────────────────────────────────────────
    if show_header:
        logo = resolve_logo()
        st.markdown(
            f"""<div class="hcard">
                  <img src="{logo}" style="height:60px;object-fit:contain;flex-shrink:0;"
                       onerror="this.style.display='none'" />
                  <div>
                    <h1>Εφαρμογή Παρακολούθησης Ποιότητας Επιφανειακών Υδάτων<br>
                        Ταμιευτήρα Γαδουρά &nbsp;·&nbsp; ΕΥΑΘ ΑΕ</h1>
                    <div class="sub">Οπτικοποίηση δορυφορικών GeoTIFF &amp; επικυρωμένων μετρήσεων in-situ</div>
                    <span class="badge">🛰️ Sentinel-2 · Rhodes, GR</span>
                    <div class="pathbox">
                      <span class="label">EXE Path</span>
                      <code>{CODE_EXEC_PATH}</code>
                    </div>
                  </div>
                </div>""",
            unsafe_allow_html=True,
        )

    # ── Case selector ────────────────────────────────────────────────────────
    st.markdown("<div class='slabel'>Επιλογή Θεματικής Ενότητας</div>",
                unsafe_allow_html=True)

    available_top_keys = [key for key in CASE_DISPLAY_ORDER if key in CASE_BY_KEY and is_case_available(key)]
    if not available_top_keys:
        st.error("Δεν υπάρχουν διαθέσιμες δορυφορικές ενότητες στο τρέχον περιβάλλον.")
        return

    default_top_key = "chlorophyll_validated" if "chlorophyll_validated" in available_top_keys else available_top_keys[0]
    current_top_key = st.session_state.get("case_key")
    if current_top_key in CASE_GROUP_PARENT_BY_CHILD:
        current_top_key = CASE_GROUP_PARENT_BY_CHILD[current_top_key]
    if current_top_key not in available_top_keys:
        st.session_state["case_key"] = default_top_key

    case_buttons = [CASE_BY_KEY[k] for k in available_top_keys]
    cols = st.columns(len(case_buttons))
    for col, cfg in zip(cols, case_buttons):
        active = st.session_state["case_key"] == cfg["key"]
        with col:
            if st.button(
                f"{cfg['icon']}\n{cfg['label']}",
                key=f"btn_{cfg['key']}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state["case_key"] = cfg["key"]
                st.rerun()

    top_key = st.session_state["case_key"]
    top_cfg = CASE_BY_KEY[top_key]
    active_key = top_key
    if top_cfg.get("children"):
        child_keys = [child for child in top_cfg["children"] if child in CASE_BY_KEY and is_case_available(child)]
        if not child_keys:
            st.warning("Δεν υπάρχουν διαθέσιμες υποκατηγορίες για αυτή την ενότητα.")
            return

        st.markdown("<div class='slabel'>Υποκατηγορία</div>", unsafe_allow_html=True)
        subcase_state_key = f"subcase::{top_key}"
        if st.session_state.get(subcase_state_key) not in child_keys:
            st.session_state[subcase_state_key] = child_keys[0]

        subcols = st.columns(len(child_keys))
        for col, child_key in zip(subcols, child_keys):
            child_cfg = CASE_BY_KEY[child_key]
            child_active = st.session_state[subcase_state_key] == child_key
            with col:
                if st.button(
                    child_cfg["label"],
                    key=f"subbtn_{top_key}_{child_key}",
                    use_container_width=True,
                    type="primary" if child_active else "secondary",
                ):
                    st.session_state[subcase_state_key] = child_key
                    st.rerun()

        active_key = st.session_state[subcase_state_key]

    cfg = CASE_BY_KEY[active_key]
    full_label = cfg.get("label_full", cfg["label"])
    if active_key != top_key:
        full_label = f"{top_cfg.get('label_full', top_cfg['label'])} · {full_label}"

    st.markdown(
        f"<div class='sstrip'><div class='sdot'></div>"
        f"Ενεργή ενότητα:&nbsp;<strong style='color:#b8dff5'>{full_label}</strong></div>",
        unsafe_allow_html=True,
    )

    if cfg.get("is_level", False):
        section_level()
        return

    # ── Resolve folder ───────────────────────────────────────────────────────
    folder = resolve_folder(active_key)
    if folder is None:
        st.error(f"⚠️ Δεν βρέθηκε φάκελος GeoTIFF για **{full_label}**. "
                 f"Ελέγξτε: `{GADOURA_ROOT}`")
        section_level()
        return

    records = list_tifs(str(folder))
    if not records:
        st.error("Δεν βρέθηκαν αρχεία `*.tif` με μορφή `YYYY_MM_DD`.")
        section_level()
        return

    grouped = {}
    for r in records:
        grouped.setdefault(r["date"], []).append(r)
    avail = sorted(grouped.keys())

    dk = f"date::{active_key}"
    cur = nearest(st.session_state.get(dk, avail[0]), avail)

    # ── Date / opacity controls ──────────────────────────────────────────────
    c_prev, c_date, c_next, c_op, c_tile = st.columns([.9, 1.6, .9, 2, 1.8])

    with c_prev:
        st.write("")
        if st.button("◀ Προηγ.", use_container_width=True):
            st.session_state[dk] = avail[max(0, avail.index(cur)-1)]
            st.rerun()

    with c_date:
        picked = st.date_input("Ημερομηνία", value=cur,
                               min_value=avail[0], max_value=avail[-1],
                               format="YYYY-MM-DD")
        sel = nearest(picked if isinstance(picked, date) else cur, avail)
        st.session_state[dk] = sel

    with c_next:
        st.write("")
        if st.button("Επόμ. ▶", use_container_width=True):
            st.session_state[dk] = avail[min(len(avail)-1, avail.index(sel)+1)]
            st.rerun()

    with c_op:
        opacity = st.slider("Διαφάνεια επικάλυψης", .10, 1.00, .78, .02)

    with c_tile:
        tile = st.selectbox(
            "Χάρτης βάσης",
            ["CartoDB dark_matter","OpenStreetMap","CartoDB positron","Stamen Terrain"],
        )

    fidx = avail.index(st.session_state[dk]) + 1
    st.caption(
        f"📅 {st.session_state[dk].strftime('%d %B %Y')}  ·  "
        f"Εικόνα {fidx}/{len(avail)}  ·  📁 `{folder.name}`"
    )

    # ── Map ──────────────────────────────────────────────────────────────────
    files = grouped[st.session_state[dk]]
    chosen = files[0]
    if len(files) > 1:
        chosen = st.selectbox("Πολλαπλά αρχεία — επιλέξτε:",
                              options=files, format_func=lambda x: x["name"])

    with st.spinner("Φόρτωση εικόνας…"):
        img, bounds, center = load_tif(chosen["path"])

    fmap = folium.Map(location=center, zoom_start=12, tiles=tile)
    folium.raster_layers.ImageOverlay(
        image=img, bounds=bounds, opacity=opacity,
        name=full_label, interactive=True, zindex=1,
    ).add_to(fmap)
    if st.session_state.get("show_profile_line_on_map", False) and (
        cfg.get("has_chl") or cfg.get("has_turbidity", False)
    ):
        profile_line = load_profile_line_coords(str(PROFILE_LINE_KMZ))
        if len(profile_line) >= 2:
            folium.PolyLine(
                locations=profile_line,
                color="#f59e0b",
                weight=4,
                opacity=0.95,
                tooltip="Γραμμή δειγματοληψίας",
                name="Γραμμή δειγματοληψίας",
            ).add_to(fmap)
    folium.LayerControl(position="bottomright").add_to(fmap)

    turbidity_scale_uri = None
    if cfg.get("has_turbidity", False) and TURBIDITY_SCALE_IMAGE.exists():
        turbidity_scale_uri = _image_data_uri(TURBIDITY_SCALE_IMAGE)

    st.markdown("<div class='mapwrap'>", unsafe_allow_html=True)
    st_folium(fmap, width=None, height=680, returned_objects=[])
    if turbidity_scale_uri:
        st.markdown(
            f"""<div class="turbidity-corner">
                  <div class="turbidity-corner-label">Κλίμακα Θολότητας</div>
                  <img src="{turbidity_scale_uri}" alt="Κλίμακα τιμών θολότητας" />
                </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if False and cfg.get("has_turbidity", False) and TURBIDITY_SCALE_IMAGE.exists():
        st.markdown("<div class='slabel'>Κλίμακα Θολότητας</div>", unsafe_allow_html=True)
        st.image(str(TURBIDITY_SCALE_IMAGE), caption="Κλίμακα τιμών θολότητας", use_container_width=True)

    # ── Chlorophyll charts (only for that case, hidden by default) ───────────
    if cfg["has_chl"]:
        with st.expander("📊 Διαγράμματα Χλωροφύλλης", expanded=False):
            section_chlorophyll()

    if cfg.get("has_turbidity", False):
        with st.expander("📉 Διαγράμματα Θολότητας", expanded=False):
            section_turbidity()

    # ── Footer ───────────────────────────────────────────────────────────────
    if cfg.get("has_bgr", False):
        with st.expander("📈 Διαγράμματα Φαινομένων Λευκασμού (BGR)", expanded=False):
            section_bgr()

    if cfg.get("chart_image"):
        with st.expander(cfg.get("chart_expander_title", "📊 Διαγράμματα"), expanded=False):
            chart_image = Path(cfg["chart_image"])
            if chart_image.exists():
                st.image(
                    str(chart_image),
                    caption=cfg.get("chart_caption"),
                    use_container_width=True,
                )
            else:
                st.info("Δεν βρέθηκε διαθέσιμο διάγραμμα για αυτή την ενότητα.")

    if show_footer:
        st.markdown(
            "<div style='text-align:center;margin-top:3rem;font-size:.68rem;"
            "color:#2b5570;letter-spacing:.08em;font-family:'Bricolage Grotesque',sans-serif;'>"
            "ΕΥΑΘ ΑΕ &nbsp;·&nbsp; Ταμιευτήρας Γαδουρά &nbsp;·&nbsp; "
            "Δορυφορική Παρακολούθηση &nbsp;·&nbsp; Sentinel-2</div>",
            unsafe_allow_html=True,
        )

    # ── Debug ────────────────────────────────────────────────────────────────
    if show_debug:
        with st.expander("🔧 Πληροφορίες διαδρομών", expanded=False):
            st.code(
                f"Script        : {Path(__file__).resolve()}\n"
                f"GADOURA_ROOT  : {GADOURA_ROOT}\n"
                f"DATA_ROOT     : {DATA_ROOT}\n"
                f"Active folder : {folder}",
                language="text",
            )


def main() -> None:
    st.set_page_config(
        page_title="Ταμιευτήρας Γαδουρά · ΕΥΑΘ",
        page_icon="🛰️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_satellite_dashboard(show_header=True, show_footer=True, show_debug=True, apply_css=True)


if __name__ == "__main__":
    main()
