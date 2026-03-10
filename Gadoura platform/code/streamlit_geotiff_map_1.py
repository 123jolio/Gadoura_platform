"""
╔══════════════════════════════════════════════════════════════════╗
║  Πλατφόρμα Παρακολούθησης Ταμιευτήρα Γαδουρά  ·  ΕΥΑΘ ΑΕ      ║
╚══════════════════════════════════════════════════════════════════╝
Redesigned UI — modern dark theme, Greek labels, button case-selector,
separate reservoir-level panel.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import os

import altair as alt
import folium
import numpy as np
import pandas as pd
import rasterio
import streamlit as st
from streamlit_folium import st_folium


# ── Paths ──────────────────────────────────────────────────────────────────────
APP_DIR      = Path(__file__).resolve().parent
PLATFORM_ROOT = APP_DIR
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


# ── Case configuration ─────────────────────────────────────────────────────────
CASE_CONFIG = [
    {
        "key":   "level",
        "label": "ΣΤΑΘΜΗ",
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
            GADOURA_ROOT / "Chlorophyll_validated" / "code" / "GeoTIFFs",
            GADOURA_ROOT / "Chlorophyll"           / "GeoTIFFs",
        ],
        "has_chl": True,
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
CASE_DISPLAY_ORDER = [
    "level",
    "pragmatiki",
    "chlorophyll_validated",
    "tholotita",
    "burned_areas",
    "bgr",
]


# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
CSS = """
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&family=Noto+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">

<style>
/* ─── Global ──────────────────────────────────────────────────────── */
html, body, [data-testid="stApp"] {
    background:#09111f !important;
    color:#d0e8f5 !important;
    font-family:'DM Sans',sans-serif !important;
}
#MainMenu, footer, header,[data-testid="stDecoration"]{display:none!important;}
.block-container{
    padding-top:1.2rem!important;
    padding-bottom:4rem!important;
    max-width:1440px!important;
}

/* ─── Header card ─────────────────────────────────────────────────── */
.hcard{
    background:linear-gradient(130deg,#0b1d36 0%,#0d2540 55%,#0a2235 100%);
    border:1px solid rgba(56,189,248,.2);
    border-radius:20px;
    padding:1.5rem 2.2rem;
    margin-bottom:1.8rem;
    display:flex;
    align-items:center;
    gap:2rem;
    box-shadow:0 6px 48px rgba(0,0,0,.55),inset 0 1px 0 rgba(255,255,255,.05);
}
.hcard h1{
    font-family:'Noto Sans','DM Sans',sans-serif!important;
    font-size:1.35rem!important;
    font-weight:700!important;
    color:#e8f4ff!important;
    margin:0 0 .3rem 0!important;
    line-height:1.4!important;
    letter-spacing:.01em!important;
    text-rendering:optimizeLegibility;
}
.hcard .sub{
    font-size:.78rem;
    color:#5a9dc0;
    letter-spacing:.06em;
    text-transform:uppercase;
}
.badge{
    display:inline-block;
    background:rgba(56,189,248,.1);
    border:1px solid rgba(56,189,248,.3);
    color:#38bdf8;
    border-radius:99px;
    padding:.15rem .75rem;
    font-size:.68rem;
    font-weight:700;
    letter-spacing:.08em;
    margin-top:.45rem;
}

/* ─── Section label ───────────────────────────────────────────────── */
.slabel{
    font-family:'Syne',sans-serif;
    font-size:.63rem;
    font-weight:700;
    letter-spacing:.18em;
    text-transform:uppercase;
    color:#3d7898;
    margin-bottom:.65rem;
    padding-left:.1rem;
}

/* ─── Case buttons – we style the native st.button columns ───────── */
[data-testid="stButton"]>button{
    background:#0d1e32!important;
    border:1px solid rgba(56,189,248,.18)!important;
    color:#7ab3ce!important;
    border-radius:14px!important;
    font-family:'Syne',sans-serif!important;
    font-size:.78rem!important;
    font-weight:600!important;
    letter-spacing:.03em!important;
    padding:.65rem 1rem!important;
    transition:all .2s ease!important;
    line-height:1.35!important;
}
[data-testid="stButton"]>button:hover{
    background:#142840!important;
    border-color:rgba(56,189,248,.55)!important;
    color:#cfe8f8!important;
    transform:translateY(-2px)!important;
    box-shadow:0 8px 24px rgba(0,0,0,.45)!important;
}
[data-testid="stButton"]>button[kind="primary"]{
    background:linear-gradient(135deg,#0c3559,#0a2e4d)!important;
    border-color:#38bdf8!important;
    color:#e0f2fe!important;
    box-shadow:0 0 20px rgba(56,189,248,.22),inset 0 1px 0 rgba(255,255,255,.07)!important;
}

/* ─── Control inputs ──────────────────────────────────────────────── */
[data-testid="stDateInput"] label,
[data-testid="stSlider"]    label,
[data-testid="stSelectbox"] label{
    font-size:.67rem!important;
    letter-spacing:.1em!important;
    text-transform:uppercase!important;
    color:#355f7a!important;
    font-weight:600!important;
}
[data-testid="stDateInput"] input{
    background:#0b1827!important;
    border:1px solid rgba(56,189,248,.22)!important;
    color:#b8dff5!important;
    border-radius:8px!important;
}

/* ─── Map wrapper ─────────────────────────────────────────────────── */
.mapwrap{
    border:1px solid rgba(56,189,248,.22);
    border-top:2px solid rgba(56,189,248,.4);
    border-radius:18px;
    overflow:hidden;
    box-shadow:0 12px 60px rgba(0,0,0,.7),inset 0 1px 0 rgba(255,255,255,.04);
    margin-bottom:1.6rem;
}

/* ─── Status strip ────────────────────────────────────────────────── */
.sstrip{
    display:flex;
    align-items:center;
    gap:.7rem;
    margin:.2rem 0 1rem;
    font-size:.78rem;
    color:#4a88a8;
    background:rgba(56,189,248,.04);
    border:1px solid rgba(56,189,248,.1);
    border-radius:10px;
    padding:.45rem .9rem;
}
.sdot{width:7px;height:7px;border-radius:50%;background:#38bdf8;box-shadow:0 0 9px #38bdf8;flex-shrink:0;animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.5;}}

/* ─── Metrics ─────────────────────────────────────────────────────── */
[data-testid="stMetric"]{
    background:#0d1e2f!important;
    border:1px solid rgba(56,189,248,.12)!important;
    border-radius:12px!important;
    padding:.85rem 1.1rem!important;
}
[data-testid="stMetricLabel"]{
    font-size:.65rem!important;
    letter-spacing:.09em!important;
    text-transform:uppercase!important;
    color:#355f7a!important;
}
[data-testid="stMetricValue"]{
    font-family:'Syne',sans-serif!important;
    font-size:1.55rem!important;
    color:#38bdf8!important;
    font-weight:700!important;
}

/* ─── Level card ──────────────────────────────────────────────────── */
.lcard{
    background:linear-gradient(135deg,#0c1e30,#0a1c2c);
    border:1px solid rgba(56,189,248,.15);
    border-top:2px solid rgba(56,189,248,.35);
    border-radius:18px;
    padding:1.5rem 1.8rem 1.4rem;
    margin-top:2rem;
    box-shadow:0 8px 40px rgba(0,0,0,.45);
}
.lcard-title{
    font-family:'Syne',sans-serif;
    font-size:1rem;
    font-weight:700;
    color:#cfe8f8;
    margin:0 0 1.1rem 0;
    display:flex;
    align-items:center;
    gap:.6rem;
}

/* ─── Tabs ────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tab"]{
    font-family:'Syne',sans-serif!important;
    font-size:.76rem!important;
    letter-spacing:.05em!important;
    color:#355f7a!important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
    color:#38bdf8!important;
    border-bottom-color:#38bdf8!important;
}

/* ─── Expander ────────────────────────────────────────────────────── */
[data-testid="stExpander"]{
    background:#0c1a29!important;
    border:1px solid rgba(56,189,248,.1)!important;
    border-radius:12px!important;
}

/* ─── Divider ─────────────────────────────────────────────────────── */
hr{border-color:rgba(56,189,248,.1)!important;}

/* ─── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#09111f;}
::-webkit-scrollbar-thumb{background:#1a3a55;border-radius:3px;}
[data-testid="stCaptionContainer"]{color:#2e5b78!important;font-size:.7rem!important;}
[data-testid="stInfo"],[data-testid="stWarning"],[data-testid="stError"]{border-radius:10px!important;}
[data-testid="stSelectbox"] [data-baseweb="select"]>div{
    background:#0b1827!important;border-color:rgba(56,189,248,.22)!important;
    color:#b8dff5!important;border-radius:8px!important;
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
    labelColor="#5a8ba8", titleColor="#c8e4f4",
    labelFontSize=11, titleFontSize=11,
    gridColor="rgba(56,189,248,.07)", domainColor="rgba(56,189,248,.18)",
    tickColor="rgba(56,189,248,.18)", tickSize=4,
)
def _chart_cfg(c):
    return (c
        .configure_view(fill="#09111f", stroke=None, continuousWidth=700, continuousHeight=300)
        .configure_axis(**_AX)
        .configure_title(color="#c8e4f4", fontSize=13)
        .interactive()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  UI SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
def section_chlorophyll() -> None:
    points_csv = DATA_ROOT / "VALIDATED_CHLOROPHYL.csv"
    avg_csv    = DATA_ROOT / "VALIDATED_AVERAGED CHLOROPHYLL.csv"

    st.markdown("<div class='slabel'>📊 Διαγράμματα Επικυρωμένης Χλωροφύλλης</div>",
                unsafe_allow_html=True)
    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = load_chl_points(str(points_csv))
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα.")
        else:
            c1, c2 = st.columns(2)
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
        avg = load_chl_avg(str(avg_csv))
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής.")
        else:
            smooth = st.slider("Εξομάλυνση (ημέρες)", 1, 30, 1)
            avg = avg.copy()
            avg["display"] = avg["value"].rolling(smooth, min_periods=1).mean()
            area = (
                alt.Chart(avg)
                .mark_area(
                    line={"color":"#38bdf8","strokeWidth":2},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="rgba(56,189,248,.4)", offset=0),
                            alt.GradientStop(color="rgba(56,189,248,.02)", offset=1),
                        ],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                )
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("display:Q", title="Μέση Chl-a"),
                    tooltip=[
                        alt.Tooltip("date:T",    title="Ημερομηνία"),
                        alt.Tooltip("display:Q", title="Chl-a", format=".3f"),
                    ],
                )
                .properties(height=360)
            )
            st.altair_chart(_chart_cfg(area), use_container_width=True)
            m1,m2,m3 = st.columns(3)
            m1.metric("Ελάχιστη", f"{avg['value'].min():.3f}")
            m2.metric("Μέγιστη",  f"{avg['value'].max():.3f}")
            m3.metric("Μέση",     f"{avg['value'].mean():.3f}")


def section_turbidity() -> None:
    charts_root = DATA_ROOT / "charts_turbidity"
    points_csv = charts_root / "homvoller turbidity.csv"
    avg_csv = charts_root / "average turbidity.csv"

    st.markdown("<div class='slabel'>📉 Διαγράμματα Θολότητας</div>", unsafe_allow_html=True)
    tab_pts, tab_avg = st.tabs(["Τιμές κατά μήκος γραμμής", "Μέση τιμή ανά ημερομηνία"])

    with tab_pts:
        pts = load_profile_points(
            csv=str(points_csv),
            value_regex=r"NDTI[^:]*:\s*(-?\d+(?:\.\d+)?)",
            value_name="ndti",
        )
        if pts.empty:
            st.info("Δεν βρέθηκαν δεδομένα θολότητας.")
        else:
            c1, c2 = st.columns(2)
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

            m1, m2, m3 = st.columns(3)
            m1.metric("Εγγραφές", f"{len(pts):,}")
            m2.metric("Ημερομηνίες", f"{plot['date'].nunique():,}")
            m3.metric("Σημεία μέτρησης", f"{plot['point'].nunique():,}")

    with tab_avg:
        avg = load_turbidity_avg(str(avg_csv))
        if avg.empty:
            st.info("Δεν βρέθηκαν δεδομένα μέσης τιμής θολότητας.")
        else:
            smooth = st.slider("Εξομάλυνση (ημέρες)", 1, 30, 1, key="turb_smooth")
            avg = avg.copy()
            avg["satellite_display"] = avg["satellite"].rolling(smooth, min_periods=1).mean()

            sat_line = (
                alt.Chart(avg)
                .mark_line(color="#22d3ee", strokeWidth=2.2)
                .encode(
                    x=alt.X("date:T", title="Ημερομηνία"),
                    y=alt.Y("satellite_display:Q", title="Δορυφορική τιμή (NDTI)"),
                    tooltip=[
                        alt.Tooltip("date:T", title="Ημερομηνία"),
                        alt.Tooltip("satellite_display:Q", title="NDTI", format=".3f"),
                    ],
                )
            )
            sat_points = alt.Chart(avg).mark_point(color="#22d3ee", size=35, opacity=0.85).encode(
                x="date:T", y="satellite_display:Q"
            )

            layers = [sat_line, sat_points]
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

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Ελάχιστη (NDTI)", f"{avg['satellite'].min():.3f}")
            m2.metric("Μέγιστη (NDTI)", f"{avg['satellite'].max():.3f}")
            m3.metric("Μέση (NDTI)", f"{avg['satellite'].mean():.3f}")
            m4.metric("Μετρήσεις πεδίου", f"{avg['field'].notna().sum():,}")


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

    c1, c2, c3 = st.columns([2,1,1])
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
            line={"color":"#22d3ee","strokeWidth":2},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="rgba(34,211,238,.45)", offset=0),
                    alt.GradientStop(color="rgba(34,211,238,.02)", offset=1),
                ],
                x1=1,x2=1,y1=1,y2=0,
            ),
        )
    else:
        mark = base.mark_line(color="#22d3ee", strokeWidth=2.2,
                              point=alt.OverlayMarkDef(color="#22d3ee", size=25))
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
def main() -> None:
    st.set_page_config(
        page_title="Ταμιευτήρας Γαδουρά · ΕΥΑΘ",
        page_icon="🛰️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Header ──────────────────────────────────────────────────────────────
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
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

    # ── Case selector ────────────────────────────────────────────────────────
    st.markdown("<div class='slabel'>Επιλογή Θεματικής Ενότητας</div>",
                unsafe_allow_html=True)

    if "case_key" not in st.session_state:
        st.session_state["case_key"] = "chlorophyll_validated"

    case_buttons = [CASE_BY_KEY[k] for k in CASE_DISPLAY_ORDER if k in CASE_BY_KEY]
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

    key = st.session_state["case_key"]
    cfg = CASE_BY_KEY[key]
    full_label = cfg.get("label_full", cfg["label"])

    st.markdown(
        f"<div class='sstrip'><div class='sdot'></div>"
        f"Ενεργή ενότητα:&nbsp;<strong style='color:#b8dff5'>{full_label}</strong></div>",
        unsafe_allow_html=True,
    )

    if cfg.get("is_level", False):
        section_level()
        return

    # ── Resolve folder ───────────────────────────────────────────────────────
    folder = resolve_folder(key)
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

    dk = f"date::{key}"
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
    folium.LayerControl(position="bottomright").add_to(fmap)

    st.markdown("<div class='mapwrap'>", unsafe_allow_html=True)
    st_folium(fmap, width=None, height=680, returned_objects=[])
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chlorophyll charts (only for that case, hidden by default) ───────────
    if cfg["has_chl"]:
        with st.expander("📊 Διαγράμματα Χλωροφύλλης", expanded=False):
            section_chlorophyll()

    if cfg.get("has_turbidity", False):
        with st.expander("📉 Διαγράμματα Θολότητας", expanded=False):
            section_turbidity()

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center;margin-top:3rem;font-size:.68rem;"
        "color:#2b5570;letter-spacing:.08em;font-family:'Syne',sans-serif;'>"
        "ΕΥΑΘ ΑΕ &nbsp;·&nbsp; Ταμιευτήρας Γαδουρά &nbsp;·&nbsp; "
        "Δορυφορική Παρακολούθηση &nbsp;·&nbsp; Sentinel-2</div>",
        unsafe_allow_html=True,
    )

    # ── Debug ────────────────────────────────────────────────────────────────
    with st.expander("🔧 Πληροφορίες διαδρομών", expanded=False):
        st.code(
            f"Script        : {Path(__file__).resolve()}\n"
            f"GADOURA_ROOT  : {GADOURA_ROOT}\n"
            f"DATA_ROOT     : {DATA_ROOT}\n"
            f"Active folder : {folder}",
            language="text",
        )


if __name__ == "__main__":
    main()
