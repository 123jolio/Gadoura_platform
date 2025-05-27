#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import rasterio
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rasterio.errors import NotGeoreferencedWarning
import warnings
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Global debug flag (set to True for debugging output)
DEBUG = False

def debug(*args, **kwargs):
    if DEBUG:
        st.write(*args, **kwargs)

# ---------------------------------------------------
# Εξατομίκευση CSS & Animation για Pro Look
# ---------------------------------------------------
def inject_custom_css():
    custom_css = """
    <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        .block-container {
            background: #161b22;
            color: #e0e0e0;
            padding: 1.2rem;
        }
        .sidebar .sidebar-content {
            background: #23272f;
            border: none;
        }
        .card {
            background: #1a1a1d;
            padding: 2rem 2.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            margin-bottom: 2rem;
            animation: fadein 1.5s;
        }
        @keyframes fadein { 0% {opacity:0;} 100%{opacity:1;} }
        .header-title {
            color: #ffd600;
            margin-bottom: 1rem;
            font-size: 2rem;
            text-align: center;
            letter-spacing: 0.5px;
            font-weight: 700;
        }
        .nav-section {
            padding: 1rem;
            background: #2c2f36;
            border-radius: 10px;
            margin-bottom: 1.2rem;
        }
        .nav-section h4 {
            margin: 0;
            color: #ffd600;
            font-weight: 500;
        }
        .stButton button {
            background-color: #009688;
            color: #fff;
            border-radius: 8px;
            padding: 10px 20px;
            border: none;
            box-shadow: 0 3px 6px rgba(0,0,0,0.12);
            font-size: 1.05rem;
            transition: background-color 0.2s;
        }
        .stButton button:hover {
            background-color: #26a69a;
        }
        .plotly-graph-div {
            border: 1px solid #23272f;
            border-radius: 10px;
        }
        .legend {
            font-size: 0.95rem;
            color: #ffd600;
        }
        .footer {
            text-align:center;
            color:gray;
            font-size:0.9rem;
            padding:1.3rem 0 0.1rem 0;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

inject_custom_css()

# ---------------------------------------------------
# Footer Branding
# ---------------------------------------------------
def render_footer():
    st.markdown("""
        <hr>
        <div class='footer'>
            © 2025 EYATH SA • Powered by OpenAI & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# Καλωσόρισμα και οδηγίες
# ---------------------------------------------------
def run_intro_page():
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_logo, col_text = st.columns([1, 3])
        with col_logo:
            base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
            logo_path = os.path.join(base_dir, "logo.jpg")
            if os.path.exists(logo_path):
                st.image(logo_path, width=180, output_format="auto", caption="EYATH Water Quality")
            else:
                st.markdown("💧")
        with col_text:
            st.markdown("""
                <h2 class='header-title'>🚀 Καλωσορίσατε στην Εφαρμογή Ανάλυσης Υδάτων EYATH</h2>
                <p style='font-size:1.15rem;text-align:center'>
                Εξερευνήστε τα δεδομένα ποιότητας με ευκολία.<br>
                Επιλέξτε τι θέλετε να δείτε από το πλάι και απολαύστε δυναμικά, διαδραστικά γραφήματα!
                </p>
                """, unsafe_allow_html=True)
            with st.expander("🔰 Οδηγίες Χρήσης", expanded=False):
                st.write("""
                    - Επιλέξτε υδάτινο σώμα, δείκτη και ανάλυση στην πλαϊνή μπάρα.
                    - Περιηγηθείτε στις καρτέλες με τα διαγράμματα.
                    - Ανεβάστε το δικό σας KML για custom σημεία δειγματοληψίας.
                    - Όλα τα δεδομένα & εικόνες μένουν τοπικά.
                """)
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------
def run_custom_ui():
    st.sidebar.markdown("<div class='nav-section'><h4>🛠️ Επιλογές Ανάλυσης</h4></div>", unsafe_allow_html=True)
    st.sidebar.info("❔ Επιλέξτε τις ρυθμίσεις σας και προχωρήστε στα αποτελέσματα!")
    waterbody = st.sidebar.selectbox("🌊 Υδάτινο σώμα", ["Γαδουρά"], key="waterbody_choice")
    index = st.sidebar.selectbox("🔬 Δείκτης", ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"], key="index_choice")
    analysis = st.sidebar.selectbox(
        "📊 Είδος Ανάλυσης",
        [
            "Επιφανειακή Αποτύπωση",
            "Προφίλ ποιότητας και στάθμης",
            "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"
        ],
        key="analysis_choice"
    )
    st.sidebar.markdown(
        f"""<div style="padding: 0.7rem; background:#2c2f36; border-radius:8px; margin-top:1.2rem;">
        <strong>🌊 Υδάτινο σώμα:</strong> {waterbody}<br>
        <strong>🔬 Δείκτης:</strong> {index}<br>
        <strong>📊 Ανάλυση:</strong> {analysis}
        </div>""",
        unsafe_allow_html=True
    )

from rasterio.errors import NotGeoreferencedWarning
import warnings
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Global debug flag (set to True for debugging output)
DEBUG = False

def debug(*args, **kwargs):
    if DEBUG:
        st.write(*args, **kwargs)

# --------------------------------------------------------------------------
# Parsing KML -> sampling points
# --------------------------------------------------------------------------
def parse_sampling_kml(kml_source) -> list:
    try:
        # Κάνε reset το pointer αν είναι file uploader
        if hasattr(kml_source, "seek"):
            kml_source.seek(0)
        if hasattr(kml_source, "read"):
            tree = ET.parse(kml_source)
        else:
            tree = ET.parse(str(kml_source))
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        points = []
        for ls in root.findall('.//kml:LineString', ns):
            coords = ls.find('kml:coordinates', ns).text.strip().split()
            for i, coord in enumerate(coords):
                lon, lat, *_ = coord.split(',')
                points.append((f"Point {i+1}", float(lon), float(lat)))
        return points
    except Exception as e:
        st.error(f"Σφάλμα ανάλυσης KML: {e}")
        return []

# --------------------------------------------------------------------------
# Core sampling analyzer
# --------------------------------------------------------------------------
def analyze_sampling(sampling_points, first_image_data, first_transform,
                     images_folder, lake_height_path, selected_points,
                     lower_thresh=0, upper_thresh=255,
                     date_min=None, date_max=None):
    results_colors = {name: [] for name, _, _ in sampling_points}
    results_mg = {name: [] for name, _, _ in sampling_points}
    
    for filename in sorted(os.listdir(images_folder)):
        if not filename.lower().endswith(('.tif', '.tiff')):
            continue
        m = re.search(r'(\d{4}_\d{2}_\d{2})', filename)
        if not m:
            continue
        date_str = m.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y_%m_%d')
        except ValueError:
            continue
        if date_min and date_obj.date() < date_min:
            continue
        if date_max and date_obj.date() > date_max:
            continue

        path = os.path.join(images_folder, filename)
        with rasterio.open(path) as src:
            if src.count < 3:
                continue
            for name, lon, lat in sampling_points:
                col, row = (~src.transform) * (lon, lat)
                col, row = int(col), int(row)
                if not (0 <= col < src.width and 0 <= row < src.height):
                    continue
                window = rasterio.windows.Window(col, row, 1, 1)
                r = src.read(1, window=window)[0,0]
                g = src.read(2, window=window)[0,0]
                b = src.read(3, window=window)[0,0]
                mg = (g/255.0)*2.0
                results_mg[name].append((date_obj, mg))
                results_colors[name].append((date_obj, (r/255, g/255, b/255)))

    # GeoTIFF figure
    rgb = first_image_data.transpose((1,2,0))/255.0
    fig_geo = px.imshow(rgb, title='GeoTIFF with sampling points')
    for name, lon, lat in sampling_points:
        col, row = (~first_transform) * (lon, lat)
        fig_geo.add_trace(go.Scatter(x=[col], y=[row], mode='markers',
                                     marker=dict(color='red', size=8), name=name))
    fig_geo.update_xaxes(visible=False)
    fig_geo.update_yaxes(visible=False)
    fig_geo.update_layout(width=900, height=600)

    # lake height data
    try:
        df_h = pd.read_excel(lake_height_path)
        df_h['Date'] = pd.to_datetime(df_h.iloc[:,0])
        df_h.sort_values('Date', inplace=True)
    except Exception:
        df_h = pd.DataFrame(columns=['Date','Height'])

    # Pixel colors + lake height
    fig_colors = make_subplots(specs=[[{'secondary_y':True}]])
    for i, name in enumerate(sampling_points):
        n = name[0]
        if n not in selected_points:
            continue
        data = sorted(results_colors[n], key=lambda x:x[0])
        dates, cols = zip(*data) if data else ([],[])
        cols_rgb = [f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
        fig_colors.add_trace(go.Scatter(x=dates, y=[i]*len(dates), mode='markers',
                                        marker=dict(color=cols_rgb, size=10), name=n), secondary_y=False)
    if not df_h.empty:
        fig_colors.add_trace(go.Scatter(x=df_h['Date'], y=df_h.iloc[:,1],
                                        mode='lines', name='Lake Height', line=dict(color='blue')), secondary_y=True)
    fig_colors.update_layout(title='Pixel colors & Lake height')

    # Mean mg plot
    all_mg = {}
    for vals in results_mg.values():
        for d, v in vals:
            all_mg.setdefault(d, []).append(v)
    dates = sorted(all_mg)
    mean_mg = [np.mean(all_mg[d]) for d in dates]
    fig_mg = go.Figure(go.Scatter(x=dates, y=mean_mg, mode='markers',
                                   marker=dict(color=mean_mg, colorscale='Viridis', colorbar=dict(title='mg/m³'), size=8)))
    fig_mg.update_layout(title='Mean mg/m³ over time')

    # Dual plot
    fig_dual = make_subplots(specs=[[{'secondary_y':True}]])
    if not df_h.empty:
        fig_dual.add_trace(go.Scatter(x=df_h['Date'], y=df_h.iloc[:,1], name='Lake Height'), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=dates, y=mean_mg, name='Mean mg/m³', mode='markers'), secondary_y=True)
    fig_dual.update_layout(title='Lake Height & Mean mg/m³')

    return fig_geo, fig_dual, fig_colors, fig_mg, results_colors, results_mg, df_h

# -----------------------------------------------------------------------------
# Εξατομίκευση CSS για επαγγελματική εμφάνιση
# -----------------------------------------------------------------------------
def inject_custom_css():
    custom_css = """
    <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap" rel="stylesheet">
    <style>
        /* Γενική μορφοποίηση */
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        .block-container {
            background: #0d0d0d;
            color: #e0e0e0;
            padding: 1rem;
        }
        /* Μορφοποίηση πλαϊνής μπάρας */
        .sidebar .sidebar-content {
            background: #1b1b1b;
            border: none;
        }
        /* Μορφοποίηση καρτών */
        .card {
            background: #1e1e1e;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.6);
            margin-bottom: 2rem;
        }
        .header-title {
            color: #ffca28;
            margin-bottom: 1rem;
            font-size: 1.75rem;
            text-align: center;
        }
        /* Ενότητα πλοήγησης στην πλαϊνή μπάρα */
        .nav-section {
            padding: 1rem;
            background: #262626;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .nav-section h4 {
            margin: 0;
            color: #ffca28;
            font-weight: 500;
        }
        /* Μορφοποίηση κουμπιών */
        .stButton button {
            background-color: #3949ab;
            color: #fff;
            border-radius: 8px;
            padding: 10px 20px;
            border: none;
            box-shadow: 0 3px 6px rgba(0,0,0,0.3);
            transition: background-color 0.3s ease;
        }
        .stButton button:hover {
            background-color: #5c6bc0;
        }
        /* Μορφοποίηση Plotly διαγραμμάτων */
        .plotly-graph-div {
            border: 1px solid #333;
            border-radius: 8px;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

inject_custom_css()

# -----------------------------------------------------------------------------
# Helper Function: Create Chlorophyll‑a Legend Figure
# -----------------------------------------------------------------------------
def create_chl_legend_figure():
    """
    Creates a horizontal legend for chlorophyll‑a using the scale:
      scaleChl_a = [0, 6, 12, 20, 30, 50]
    and the colors:
      ["#496FF2", "#82D35F", "#FEFD05", "#FD0004", "#8E2026", "#D97CF5"]
    The legend is returned as a Matplotlib figure.
    """
    levels = [0, 6, 12, 20, 30, 50]
    colors = ["#496FF2", "#82D35F", "#FEFD05", "#FD0004", "#8E2026", "#D97CF5"]
    cmap = mcolors.LinearSegmentedColormap.from_list("ChlLegend", 
                                                      list(zip(np.linspace(0, 1, len(levels)), colors)))
    norm = mcolors.Normalize(vmin=levels[0], vmax=levels[-1])
    fig, ax = plt.subplots(figsize=(6, 1.5))
    fig.subplots_adjust(bottom=0.5)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=ax, orientation="horizontal", ticks=levels)
    cbar.ax.set_xticklabels([str(l) for l in levels])
    cbar.set_label("Chlorophyll‑a concentration (mg/m³)")
    return fig
def create_chl_legend_figure_vertical():
    levels = [0, 6, 12, 20, 30, 50]
    colors = ["#496FF2", "#82D35F", "#FEFD05", "#FD0004", "#8E2026", "#D97CF5"]
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "ChlLegend",
        list(zip(np.linspace(0, 1, len(levels)), colors))
    )
    norm = mcolors.Normalize(vmin=levels[0], vmax=levels[-1])
    fig, ax = plt.subplots(figsize=(1.2, 6))  # στενή και ψηλή
    fig.subplots_adjust(left=0.4, right=0.6, top=0.95, bottom=0.05)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=ax, orientation="vertical", ticks=levels)
    cbar.ax.set_yticklabels([str(l) for l in levels])
    cbar.set_label("Chlorophyll‑a (mg/m³)")
    plt.tight_layout()
    return fig
# -----------------------------------------------------------------------------
# Βοηθητική Συνάρτηση για Επιλογή φακέλου δεδομένων
# -----------------------------------------------------------------------------
def get_data_folder(waterbody: str, index: str) -> str:
    """
    Αντιστοιχεί το επιλεγμένο υδάτινο σώμα και δείκτη στον σωστό φάκελο δεδομένων.
    Επιστρέφει None αν δεν υπάρχει ο φάκελος.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_dir = os.getcwd()
    debug("DEBUG: Τρέχων φάκελος:", base_dir)
    waterbody_map = {
        "Γαδουρά": "Gadoura"
    }
    waterbody_folder = waterbody_map.get(waterbody, None)
    if waterbody_folder is None:
        return None
    if index == "Χλωροφύλλη":
        data_folder = os.path.join(base_dir, waterbody_folder, "Chlorophyll")
    elif index == "Θολότητα":
        data_folder = os.path.join(base_dir, waterbody_folder, "Θολότητα")
    elif index == "Πραγματικό" and waterbody == "Κορώνεια":
        data_folder = os.path.join(base_dir, waterbody_folder, "Pragmatiko")
    else:
        data_folder = os.path.join(base_dir, waterbody_folder, index)
    debug("DEBUG: Ο φάκελος δεδομένων επιλύθηκε σε:", data_folder)
    if data_folder is not None and not os.path.exists(data_folder):
        st.error(f"Ο φάκελος δεν υπάρχει: {data_folder}")
        return None
    return data_folder

# -----------------------------------------------------------------------------
# Εξαγωγή ημερομηνίας από όνομα αρχείου (με ή χωρίς διαχωριστικά)
# -----------------------------------------------------------------------------
def extract_date_from_filename(filename: str):
    """
    Εξάγει ημερομηνία (YYYY-MM-DD) από το όνομα του αρχείου χρησιμοποιώντας regex.
    Προσπαθεί πρώτα με διαχωριστικά (π.χ. 2023_07_22 ή 2023-07-22) και αν δεν βρεθεί, δοκιμάζει χωρίς διαχωριστικά (π.χ. 20230722).
    Επιστρέφει (day_of_year, datetime_obj) ή (None, None) αν δεν βρεθεί ταίριασμα.
    """
    basename = os.path.basename(filename)
    debug("DEBUG: Εξαγωγή ημερομηνίας από το όνομα:", basename)
    match = re.search(r'(\d{4})[_-](\d{2})[_-](\d{2})', basename)
    if not match:
        match = re.search(r'(\d{4})(\d{2})(\d{2})', basename)
    if match:
        year, month, day = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            day_of_year = date_obj.timetuple().tm_yday
            return day_of_year, date_obj
        except Exception as e:
            debug("DEBUG: Σφάλμα μετατροπής ημερομηνίας:", e)
            return None, None
    return None, None

# -----------------------------------------------------------------------------
# Σελίδα Εισαγωγής
# -----------------------------------------------------------------------------
def run_intro_page():
    """Εμφανίζει μια κάρτα εισαγωγής με λογότυπο και τίτλο."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_logo, col_text = st.columns([1, 3])
        with col_logo:
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                base_dir = os.getcwd()
            logo_path = os.path.join(base_dir, "logo.jpg")
            if os.path.exists(logo_path):
                st.image(logo_path, width=250)
            else:
                debug("DEBUG: Δεν βρέθηκε το λογότυπο.")
        with col_text:
            st.markdown(
                "<h2 class='header-title'>Ποιοτικά χαρακτηριστικά Επιφανειακού Ύδατος</h2>",
                unsafe_allow_html=True
            )
            st.markdown(
                "<p style='text-align: center; font-size: 1.1rem;'>"
                "Αυτή η εφαρμογή ανάλυσης χρησιμοποιεί εργαλεία δορυφορικής τηλεπισκόπησης. "
                "Επιλέξτε τις ρυθμίσεις στην πλαϊνή μπάρα και εξερευνήστε τα δεδομένα.</p>",
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Πλαϊνή Μπάρα Πλοήγησης (Custom UI)
# -----------------------------------------------------------------------------
def run_custom_ui():
    """Δημιουργεί την πλαϊνή μπάρα για επιλογή υδάτινου σώματος, δείκτη και είδους ανάλυσης."""
    st.sidebar.markdown("<div class='nav-section'><h4>Παραμετροποίηση Ανάλυσης</h4></div>", unsafe_allow_html=True)
    waterbody = st.sidebar.selectbox("Επιλογή υδάτινου σώματος",
        ["Γαδουρά"], key="waterbody_choice")
    index = st.sidebar.selectbox("Επιλογή Δείκτη",
        ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"], key="index_choice")
    analysis = st.sidebar.selectbox("Είδος Ανάλυσης",
        [
            "Επιφανειακή Αποτύπωση",
            "Προφίλ ποιότητας και στάθμης",
            "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"
        ],
        key="analysis_choice")
    st.sidebar.markdown(f""" <div style="padding: 0.5rem; background:#262626; border-radius:5px; margin-top:1rem;"> <strong>Υδάτινο σώμα:</strong> {waterbody}<br> <strong>Δείκτης:</strong> {index}<br> <strong>Ανάλυση:</strong> {analysis} </div> """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Βοηθητικές Συναρτήσεις για Εξαγωγή Δεδομένων και Επεξεργασία Εικόνας
# -----------------------------------------------------------------------------
def load_lake_shape_from_xml(xml_file: str, bounds: tuple = None,
                             xml_width: float = 518.0, xml_height: float = 505.0):
    """
    Φορτώνει το περίγραμμα μιας λίμνης από ένα προσαρμοσμένο XML αρχείο.
    Εάν δοθούν όρια, μετατρέπει τις συντεταγμένες.
    """
    debug("DEBUG: Φόρτωση περιγράμματος από:", xml_file)
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        points = []
        for point_elem in root.findall("point"):
            x_str = point_elem.get("x")
            y_str = point_elem.get("y")
            if x_str is None or y_str is None:
                continue
            points.append([float(x_str), float(y_str)])
        if not points:
            st.warning("Δεν βρέθηκαν σημεία στο XML:", xml_file)
            return None
        if bounds is not None:
            minx, miny, maxx, maxy = bounds
            transformed_points = []
            for x_xml, y_xml in points:
                x_geo = minx + (x_xml / xml_width) * (maxx - minx)
                y_geo = maxy - (y_xml / xml_height) * (maxy - miny)
                transformed_points.append([x_geo, y_geo])
            points = transformed_points
        if points and (points[0] != points[-1]):
            points.append(points[0])
        debug("DEBUG: Φορτώθηκαν", len(points), "σημεία.")
        return {"type": "Polygon", "coordinates": [points]}
    except Exception as e:
        st.error(f"Σφάλμα φόρτωσης περιγράμματος από {xml_file}: {e}")
        return None

def read_image(file_path: str, lake_shape: dict = None):
    """
    Διαβάζει ένα GeoTIFF αρχείο (1 κανάλι) και, εάν δοθεί, εφαρμόζει μάσκα βάσει του περιγράμματος.
    Επιστρέφει (εικόνα, profile).
    """
    debug("DEBUG: Ανάγνωση εικόνας από:", file_path)
    with rasterio.open(file_path) as src:
        img = src.read(1).astype(np.float32)
        profile = src.profile.copy()
        profile.update(dtype="float32")
        no_data_value = src.nodata
        if no_data_value is not None:
            img = np.where(img == no_data_value, np.nan, img)
        img = np.where(img == 0, np.nan, img)
        if lake_shape is not None:
            from rasterio.features import geometry_mask
            poly_mask = geometry_mask([lake_shape], transform=src.transform, invert=False, out_shape=img.shape)
            img = np.where(~poly_mask, img, np.nan)
    return img, profile

def load_data(input_folder: str, shapefile_name="shapefile.xml"):
    """
    Διαβάζει όλα τα TIF αρχεία από το input_folder, εφαρμόζει μάσκα (εάν υπάρχει) και εξάγει πληροφορίες ημερομηνίας.
    Επιστρέφει (stack, array ημερών, λίστα ημερομηνιών).
    """
    debug("DEBUG: load_data καλεσμένη με:", input_folder)
    if not os.path.exists(input_folder):
        raise Exception(f"Ο φάκελος δεν υπάρχει: {input_folder}")
    shapefile_path_xml = os.path.join(input_folder, shapefile_name)
    shapefile_path_txt = os.path.join(input_folder, "shapefile.txt")
    lake_shape = None
    if os.path.exists(shapefile_path_xml):
        shape_file = shapefile_path_xml
    elif os.path.exists(shapefile_path_txt):
        shape_file = shapefile_path_txt
    else:
        shape_file = None
        debug("DEBUG: Δεν βρέθηκε XML περιγράμματος στον φάκελο", input_folder)
    all_tif_files = sorted(glob.glob(os.path.join(input_folder, "*.tif")))
    tif_files = [fp for fp in all_tif_files if os.path.basename(fp).lower() != "mask.tif"]
    if not tif_files:
        raise Exception("Δεν βρέθηκαν GeoTIFF αρχεία.")
    with rasterio.open(tif_files[0]) as src:
        bounds = src.bounds
    if shape_file is not None:
        lake_shape = load_lake_shape_from_xml(shape_file, bounds=bounds)
    images, days, date_list = [], [], []
    for file_path in tif_files:
        day_of_year, date_obj = extract_date_from_filename(file_path)
        if day_of_year is None:
            continue
        img, _ = read_image(file_path, lake_shape=lake_shape)
        images.append(img)
        days.append(day_of_year)
        date_list.append(date_obj)
    if not images:
        raise Exception("Δεν βρέθηκαν έγκυρες εικόνες.")
    stack = np.stack(images, axis=0)
    return stack, np.array(days), date_list

# -----------------------------------------------------------------------------
# Επεξεργασία Λίμνης (Lake Processing) με Μηνιαία και Ετήσια Ανάλυση
# -----------------------------------------------------------------------------
def run_lake_processing_app(waterbody: str, index: str):
    """Κύρια συνάρτηση για την ανάλυση μιας λίμνης με μηνιαία και ετήσια διαγράμματα."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title(f"Επεξεργασία Λίμνης ({waterbody} - {index})")

        data_folder = get_data_folder(waterbody, index)
        if data_folder is None:
            st.error("Δεν υπάρχει φάκελος δεδομένων για το επιλεγμένο υδάτινο σώμα/δείκτη.")
            st.stop()

        input_folder = os.path.join(data_folder, "GeoTIFFs")
        try:
            STACK, DAYS, DATES = load_data(input_folder)
        except Exception as e:
            st.error(f"Σφάλμα φόρτωσης δεδομένων: {e}")
            st.stop()

        if not DATES:
            st.error("Δεν υπάρχουν διαθέσιμες πληροφορίες ημερομηνίας.")
            st.stop()

        # Βασικά φίλτρα από την πλαϊνή μπάρα
        min_date = min(DATES)
        max_date = max(DATES)
        unique_years = sorted({d.year for d in DATES if d is not None})

        st.sidebar.header(f"Φίλτρα (Επεξεργασία Λίμνης: {waterbody})")
        threshold_range = st.sidebar.slider("Εύρος τιμών pixel", 0, 255, (0, 255), key="thresh_lp")
        broad_date_range = st.sidebar.slider("Γενική περίοδος", min_value=min_date, max_value=max_date,
                                             value=(min_date, max_date), key="broad_date_lp")
        refined_date_range = st.sidebar.slider("Εξειδικευμένη περίοδος", min_value=min_date, max_value=max_date,
                                               value=(min_date, max_date), key="refined_date_lp")
        display_option = st.sidebar.radio("Τρόπος εμφάνισης", options=["Thresholded", "Original"], index=0, key="display_lp")

        st.sidebar.markdown("### Επιλογή Μηνών")
        month_options = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        if "selected_months" not in st.session_state:
            st.session_state.selected_months = list(month_options.keys())
        selected_months = st.sidebar.multiselect("Μήνες",
                                                 options=list(month_options.keys()),
                                                 format_func=lambda x: month_options[x],
                                                 default=st.session_state.selected_months,
                                                 key="months_lp")
        st.session_state.selected_years = unique_years
        selected_years = st.sidebar.multiselect("Έτη", options=unique_years,
                                                default=unique_years,
                                                key="years_lp")

        start_dt, end_dt = refined_date_range
        selected_indices = [i for i, d in enumerate(DATES)
                            if start_dt <= d <= end_dt and d.month in selected_months and d.year in selected_years]

        if not selected_indices:
            st.error("Δεν υπάρχουν δεδομένα για την επιλεγμένη περίοδο/μήνες/έτη.")
            st.stop()

        stack_filtered = STACK[selected_indices, :, :]
        days_filtered = np.array(DAYS)[selected_indices]
        filtered_dates = np.array(DATES)[selected_indices]

        lower_thresh, upper_thresh = threshold_range
        in_range = np.logical_and(stack_filtered >= lower_thresh, stack_filtered <= upper_thresh)

        # Διάγραμμα "Ημέρες σε Εύρος"
        days_in_range = np.nansum(in_range, axis=0)
        fig_days = px.imshow(days_in_range, color_continuous_scale="plasma",
                             title="Διάγραμμα: Ημέρες σε Εύρος", labels={"color": "Ημέρες σε Εύρος"})
        fig_days.update_layout(width=800, height=600)
        st.plotly_chart(fig_days, use_container_width=True, key="fig_days")
        with st.expander("Επεξήγηση: Ημέρες σε Εύρος"):
            st.write("Το διάγραμμα αυτό δείχνει πόσες ημέρες κάθε pixel βρίσκεται εντός του επιλεγμένου εύρους τιμών. Ρυθμίστε το 'Εύρος τιμών pixel' για να δείτε πώς αλλάζει το αποτέλεσμα.")

        tick_vals = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 365]
        tick_text = ["1 (Ιαν)", "32 (Φεβ)", "60 (Μαρ)", "91 (Απρ)",
                     "121 (Μαΐ)", "152 (Ιουν)", "182 (Ιουλ)", "213 (Αυγ)",
                     "244 (Σεπ)", "274 (Οκτ)", "305 (Νοε)", "335 (Δεκ)", "365 (Δεκ)"]

        days_array = days_filtered.reshape((-1, 1, 1))
        sum_days = np.nansum(days_array * in_range, axis=0)
        count_in_range = np.nansum(in_range, axis=0)
        mean_day = np.divide(sum_days, count_in_range,
                             out=np.full(sum_days.shape, np.nan),
                             where=(count_in_range != 0))
        fig_mean = px.imshow(mean_day, color_continuous_scale="RdBu",
                             title="Διάγραμμα: Μέση Ημέρα Εμφάνισης", labels={"color": "Μέση Ημέρα"})
        fig_mean.update_layout(width=800, height=600)
        fig_mean.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text))
        st.plotly_chart(fig_mean, use_container_width=True, key="fig_mean")
        with st.expander("Επεξήγηση: Μέση Ημέρα Εμφάνισης"):
            st.write("Το διάγραμμα αυτό παρουσιάζει τη μέση ημέρα εμφάνισης για τα pixels που πληρούν το επιλεγμένο εύρος τιμών. Πειραματιστείτε με το 'Εύρος τιμών pixel' για να δείτε πώς μεταβάλλεται η μέση ημέρα.")

        if display_option.lower() == "thresholded":
            filtered_stack = np.where(in_range, stack_filtered, np.nan)
        else:
            filtered_stack = stack_filtered

        average_sample_img = np.nanmean(filtered_stack, axis=0)
        if not np.all(np.isnan(average_sample_img)):
            avg_min = float(np.nanmin(average_sample_img))
            avg_max = float(np.nanmax(average_sample_img))
        else:
            avg_min, avg_max = 0, 0

        fig_sample = px.imshow(average_sample_img, color_continuous_scale="jet",
                               range_color=[avg_min, avg_max],
                               title="Διάγραμμα: Μέσο Δείγμα Εικόνας", labels={"color": "Τιμή Pixel"})
        fig_sample.update_layout(width=800, height=600)
        st.plotly_chart(fig_sample, use_container_width=True, key="fig_sample")
        with st.expander("Επεξήγηση: Μέσο Δείγμα Εικόνας"):
            st.write("Το διάγραμμα αυτό δείχνει τη μέση τιμή των pixels μετά την εφαρμογή του φίλτρου. Επιλέξτε 'Thresholded' ή 'Original' για να δείτε τη φιλτραρισμένη ή την αρχική εικόνα.")

        filtered_day_of_year = np.array([d.timetuple().tm_yday for d in filtered_dates])
        def nanargmax_or_nan(arr):
            return np.nan if np.all(np.isnan(arr)) else np.nanargmax(arr)
        max_index = np.apply_along_axis(nanargmax_or_nan, 0, filtered_stack)
        time_max = np.full(max_index.shape, np.nan, dtype=float)
        valid_mask = ~np.isnan(max_index)
        max_index_int = np.zeros_like(max_index, dtype=int)
        max_index_int[valid_mask] = max_index[valid_mask].astype(int)
        max_index_int[valid_mask] = np.clip(max_index_int[valid_mask], 0, len(filtered_day_of_year) - 1)
        time_max[valid_mask] = filtered_day_of_year[max_index_int[valid_mask]]
        fig_time = px.imshow(time_max, color_continuous_scale="RdBu",
                             range_color=[1, 365],
                             title="Διάγραμμα: Χρόνος Μέγιστης Εμφάνισης", labels={"color": "Ημέρα"})
        fig_time.update_layout(width=800, height=600)
        fig_time.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text))
        st.plotly_chart(fig_time, use_container_width=True, key="fig_time")
        with st.expander("Επεξήγηση: Χρόνος Μέγιστης Εμφάνισης"):
            st.write("Αυτό το διάγραμμα δείχνει την ημέρα του έτους κατά την οποία κάθε pixel πέτυχε τη μέγιστη τιμή εντός του επιλεγμένου εύρους. Πειραματιστείτε με το 'Εύρος τιμών pixel' για να δείτε πώς αλλάζει το αποτέλεσμα.")

        st.header("Χάρτες Ανάλυσης")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_days, use_container_width=True, key="fig_days_2")
        with col2:
            st.plotly_chart(fig_mean, use_container_width=True, key="fig_mean_2")

        st.header("Ανάλυση Δείγματος Εικόνας")
        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(fig_sample, use_container_width=True, key="fig_sample_2")
        with col4:
            st.plotly_chart(fig_time, use_container_width=True, key="fig_time_2")

        # ------------------------------
        # Επιπρόσθετη Ετήσια Ανάλυση: Μηνιαία Κατανομή Ημερών σε Εύρος
        # ------------------------------
        st.header("Επιπρόσθετη Ετήσια Ανάλυση: Μηνιαία Κατανομή Ημερών σε Εύρος")
        stack_full_in_range = (STACK >= lower_thresh) & (STACK <= upper_thresh)
        monthly_days_in_range = {}
        for m in range(1, 13):
            indices_m = [i for i, d in enumerate(DATES) if d is not None and d.month == m]
            if indices_m:
                monthly_days_in_range[m] = np.sum(stack_full_in_range[indices_m, :, :], axis=0)
            else:
                monthly_days_in_range[m] = None

        months_to_display = [m for m in list(range(1, 13)) if m in selected_months]
        months_in_order = sorted(months_to_display)
        if 3 in months_in_order:
            months_in_order = list(range(3, 13)) + [m for m in months_in_order if m < 3]
            seen = set()
            months_in_order = [x for x in months_in_order if not (x in seen or seen.add(x))]
        num_cols = 3
        cols = st.columns(num_cols)
        for idx, m in enumerate(months_in_order):
            col_index = idx % num_cols
            img = monthly_days_in_range[m]
            month_name = datetime(2000, m, 1).strftime('%B')
            if img is not None:
                fig_month = px.imshow(
                    img,
                    color_continuous_scale="plasma",
                    title=month_name,
                    labels={"color": "Ημέρες σε Εύρος"}
                )
                fig_month.update_layout(
                    width=500,
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                fig_month.update_coloraxes(showscale=False)
                cols[col_index].plotly_chart(fig_month, use_container_width=False)
            else:
                cols[col_index].info(f"Δεν υπάρχουν δεδομένα για τον μήνα {month_name}")
            if (idx + 1) % num_cols == 0 and (idx + 1) < len(months_in_order):
                cols = st.columns(num_cols)
        with st.expander("Επεξήγηση: Μηνιαία Κατανομή Ημερών σε Εύρος"):
            st.write(
                "Για κάθε μήνα που έχετε επιλέξει, το διάγραμμα δείχνει πόσες ημέρες κάθε pixel βρέθηκε "
                "εντός του επιλεγμένου εύρους τιμών. Οι μήνες που δεν έχουν επιλεγεί δεν εμφανίζονται και τα δεδομένα τους δεν περιλαμβάνονται."
            )

        # ------------------------------
        # Επιπρόσθετη Ετήσια Ανάλυση: Ετήσια Κατανομή Ημερών σε Εύρος
        # ------------------------------
        st.header("Επιπρόσθετη Ετήσια Ανάλυση: Ετήσια Κατανομή Ημερών σε Εύρος")
        unique_years_full = sorted({d.year for d in DATES if d is not None})
        years_to_display = [y for y in unique_years_full if y in selected_years]
        if not years_to_display:
            st.error("Δεν υπάρχουν έγκυρα έτη στα δεδομένα μετά το φίλτρο.")
            st.stop()
        stack_full_in_range = (STACK >= lower_thresh) & (STACK <= upper_thresh)
        yearly_days_in_range = {}
        for year in years_to_display:
            indices_y = [i for i, d in enumerate(DATES) if d.year == year]
            if indices_y:
                yearly_days_in_range[year] = np.sum(stack_full_in_range[indices_y, :, :], axis=0)
            else:
                yearly_days_in_range[year] = None
        num_cols = 3
        cols = st.columns(num_cols)
        for idx, year in enumerate(years_to_display):
            col_index = idx % num_cols
            img = yearly_days_in_range[year]
            if img is not None:
                fig_year = px.imshow(
                    img,
                    color_continuous_scale="plasma",
                    title=f"Έτος: {year}",
                    labels={"color": "Ημέρες σε Εύρος"}
                )
                fig_year.update_layout(
                    width=500,
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                fig_year.update_coloraxes(showscale=False)
                cols[col_index].plotly_chart(fig_year, use_container_width=False)
            else:
                cols[col_index].info(f"Δεν υπάρχουν δεδομένα για το έτος {year}")
            if (idx + 1) % num_cols == 0 and (idx + 1) < len(years_to_display):
                cols = st.columns(num_cols)
        with st.expander("Επεξήγηση: Ετήσια Κατανομή Ημερών σε Εύρος"):
            st.write("Για κάθε έτος που έχετε επιλέξει, το διάγραμμα δείχνει πόσες ημέρες κάθε pixel βρέθηκε εντός του επιλεγμένου εύρους τιμών. Τα έτη που δεν έχουν επιλεγεί δεν εμφανίζονται και τα δεδομένα τους δεν περιλαμβάνονται.")

        st.info("Τέλος Επεξεργασίας Λίμνης.")
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Επεξεργασία Υδάτινου Σώματος (Placeholder)
# -----------------------------------------------------------------------------
def run_water_processing(waterbody: str, index: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title(f"Επεξεργασία Υδάτινου Σώματος ({waterbody} - {index}) [Placeholder]")
        st.info("Δεν υπάρχουν δεδομένα ή λειτουργίες για την επεξεργασία υδάτινου σώματος.")
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Πίνακας Ποιότητας Ύδατος
# -----------------------------------------------------------------------------
def run_water_quality_dashboard(waterbody: str, index: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title(f"Πίνακας Ποιότητας Ύδατος ({waterbody} - {index})")

        data_folder = get_data_folder(waterbody, index)
        if data_folder is None:
            st.error("Δεν υπάρχει φάκελος δεδομένων για το επιλεγμένο υδάτινο σώμα/δείκτη.")
            st.stop()

        images_folder = os.path.join(data_folder, "GeoTIFFs")
        lake_height_path = os.path.join(data_folder, "lake height.xlsx")
        sampling_kml_path = os.path.join(data_folder, "sampling.kml")
        possible_video = [
            os.path.join(data_folder, "timelapse.mp4"),
            os.path.join(data_folder, "Sentinel-2_L1C-202307221755611-timelapse.gif"),
            os.path.join(images_folder, "Sentinel-2_L1C-202307221755611-timelapse.gif")
        ]
        video_path = None
        for v in possible_video:
            if os.path.exists(v):
                video_path = v
                break

        st.sidebar.header(f"Ρυθμίσεις Πίνακα ({waterbody} - Dashboard)")
        x_start = st.sidebar.date_input("Έναρξη", date(2015, 1, 1), key="wq_start")
        x_end = st.sidebar.date_input("Λήξη", date(2026, 12, 31), key="wq_end")
        x_start_dt = datetime.combine(x_start, datetime.min.time())
        x_end_dt = datetime.combine(x_end, datetime.min.time())

        tif_files = [f for f in os.listdir(images_folder) if f.lower().endswith('.tif')]
        available_dates = {}
        for filename in tif_files:
            # Use flexible regex to match either YYYY_MM_DD, YYYY-MM-DD or YYYYMMDD formats
            match = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
            if match:
                year, month, day = match.groups()
                date_str = f"{year}_{month}_{day}"
                try:
                    date_obj = datetime.strptime(date_str, '%Y_%m_%d').date()
                    available_dates[str(date_obj)] = filename
                except Exception as e:
                    debug("DEBUG: Σφάλμα εξαγωγής ημερομηνίας από", filename, ":", e)
                    continue

        if available_dates:
            sorted_dates = sorted(available_dates.keys())
            selected_bg_date = st.selectbox("Επιλέξτε ημερομηνία για το background", sorted_dates, key="wq_bg")
        else:
            selected_bg_date = None
            st.warning("Δεν βρέθηκαν GeoTIFF εικόνες με ημερομηνία.")

        if selected_bg_date is not None:
            bg_filename = available_dates[selected_bg_date]
            bg_path = os.path.join(images_folder, bg_filename)
            if os.path.exists(bg_path):
                with rasterio.open(bg_path) as src:
                    if src.count >= 3:
                        first_image_data = src.read([1, 2, 3])
                        first_transform = src.transform
                    else:
                        st.error("Το επιλεγμένο GeoTIFF δεν περιέχει τουλάχιστον 3 κανάλια.")
                        st.stop()
            else:
                st.error(f"Δεν βρέθηκε το GeoTIFF background: {bg_path}")
                st.stop()
        else:
            st.error("Δεν έχει επιλεγεί έγκυρη ημερομηνία για το background.")
            st.stop()

        def parse_sampling_kml(kml_file) -> list:
            try:
                tree = ET.parse(kml_file)
                root = tree.getroot()
                namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
                points = []
                for linestring in root.findall('.//kml:LineString', namespace):
                    coord_text = linestring.find('kml:coordinates', namespace).text.strip()
                    coords = coord_text.split()
                    for idx, coord in enumerate(coords):
                        lon_str, lat_str, *_ = coord.split(',')
                        points.append((f"Point {idx+1}", float(lon_str), float(lat_str)))
                return points
            except Exception as e:
                st.error("Σφάλμα ανάλυσης KML:", e)
                return []

        def geographic_to_pixel(lon: float, lat: float, transform) -> tuple:
            inverse_transform = ~transform
            col, row = inverse_transform * (lon, lat)
            return int(col), int(row)

        def map_rgb_to_mg(r: float, g: float, b: float, mg_factor: float = 2.0) -> float:
            return (g / 255.0) * mg_factor

        def mg_to_color(mg: float) -> str:
            scale = [
                (0.00, "#0000ff"), (0.02, "#0007f2"), (0.04, "#0011de"),
                (0.06, "#0017d0"), (1.98, "#80007d"), (2.00, "#800080")
            ]
            if mg <= scale[0][0]:
                color = scale[0][1]
            elif mg >= scale[-1][0]:
                color = scale[-1][1]
            else:
                for i in range(len(scale) - 1):
                    low_mg, low_color = scale[i]
                    high_mg, high_color = scale[i+1]
                    if low_mg <= mg <= high_mg:
                        t = (mg - low_mg) / (high_mg - low_mg)
                        low_rgb = tuple(int(low_color[j:j+2], 16) for j in (1, 3, 5))
                        high_rgb = tuple(int(high_color[j:j+2], 16) for j in (1, 3, 5))
                        rgb = tuple(int(low_rgb[k] + (high_rgb[k] - low_rgb[k]) * t) for k in range(3))
                        return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
            rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
            return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"

        def analyze_sampling(sampling_points: list, first_image_data, first_transform,
                             images_folder: str, lake_height_path: str, selected_points: list = None):
            results_colors = {name: [] for name, _, _ in sampling_points}
            results_mg = {name: [] for name, _, _ in sampling_points}
            for filename in sorted(os.listdir(images_folder)):
                if filename.lower().endswith(('.tif', '.tiff')):
                    match = re.search(r'(\d{4}_\d{2}_\d{2})', filename)
                    if not match:
                        continue
                    date_str = match.group(1)
                    try:
                        date_obj = datetime.strptime(date_str, '%Y_%m_%d')
                    except ValueError:
                        continue
                    image_path = os.path.join(images_folder, filename)
                    with rasterio.open(image_path) as src:
                        transform = src.transform
                        width, height = src.width, src.height
                        if src.count < 3:
                            continue
                        for name, lon, lat in sampling_points:
                            col, row = geographic_to_pixel(lon, lat, transform)
                            if 0 <= col < width and 0 <= row < height:
                                window = rasterio.windows.Window(col, row, 1, 1)
                                r = src.read(1, window=window)[0, 0]
                                g = src.read(2, window=window)[0, 0]
                                b = src.read(3, window=window)[0, 0]
                                mg_value = map_rgb_to_mg(r, g, b)
                                results_mg[name].append((date_obj, mg_value))
                                pixel_color = (r / 255, g / 255, b / 255)
                                results_colors[name].append((date_obj, pixel_color))
            rgb_image = first_image_data.transpose((1, 2, 0)) / 255.0
            fig_geo = px.imshow(rgb_image, title='Εικόνα GeoTIFF με Σημεία Δειγματοληψίας')
            for name, lon, lat in sampling_points:
                col, row = geographic_to_pixel(lon, lat, first_transform)
                fig_geo.add_trace(go.Scatter(x=[col], y=[row], mode='markers',
                                             marker=dict(color='red', size=8), name=name))
            fig_geo.update_xaxes(visible=False)
            fig_geo.update_yaxes(visible=False)
            fig_geo.update_layout(width=900, height=600, showlegend=True)
            try:
                lake_data = pd.read_excel(lake_height_path)
                lake_data['Date'] = pd.to_datetime(lake_data.iloc[:, 0])
                lake_data.sort_values('Date', inplace=True)
            except Exception as e:
                st.error(f"Σφάλμα ανάγνωσης αρχείου ύψους λίμνης: {e}")
                lake_data = pd.DataFrame()
            scatter_traces = []
            point_names = list(results_colors.keys())
            if selected_points is not None:
                point_names = [p for p in point_names if p in selected_points]
            for idx, name in enumerate(point_names):
                data_list = results_colors[name]
                if not data_list:
                    continue
                data_list.sort(key=lambda x: x[0])
                dates = [d for d, _ in data_list]
                colors = [f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for _, c in data_list]
                scatter_traces.append(go.Scatter(x=dates, y=[idx] * len(dates),
                                                 mode='markers',
                                                 marker=dict(color=colors, size=10),
                                                 name=name))
            fig_colors = make_subplots(specs=[[{"secondary_y": True}]])
            for trace in scatter_traces:
                fig_colors.add_trace(trace, secondary_y=False)
            if not lake_data.empty:
                trace_height = go.Scatter(
                    x=lake_data['Date'],
                    y=lake_data[lake_data.columns[1]],
                    name='Ύψος Λίμνης', mode='lines', line=dict(color='blue', width=2)
                )
                fig_colors.add_trace(trace_height, secondary_y=True)
            fig_colors.update_layout(title='Χρώματα Pixel και Ύψος Λίμνης με την πάροδο του χρόνου',
                                     xaxis_title='Ημερομηνία',
                                     yaxis_title='Σημεία Δειγματοληψίας',
                                     showlegend=True)
            fig_colors.update_yaxes(title_text="Ύψος Λίμνης", secondary_y=True)
            all_dates_dict = {}
            for data_list in results_mg.values():
                for date_obj, mg_val in data_list:
                    all_dates_dict.setdefault(date_obj, []).append(mg_val)
            sorted_dates = sorted(all_dates_dict.keys())
            avg_mg = [np.mean(all_dates_dict[d]) for d in sorted_dates]
            fig_mg = go.Figure()
            fig_mg.add_trace(go.Scatter(
                x=sorted_dates,
                y=avg_mg,
                mode='markers',
                marker=dict(color=avg_mg, colorscale='Viridis', reversescale=True,
                            colorbar=dict(title='mg/m³'), size=10),
                name='Μέσο mg/m³'
            ))
            fig_mg.update_layout(title='Μέσο mg/m³ με την πάροδο του χρόνου',
                                 xaxis_title='Ημερομηνία', yaxis_title='mg/m³',
                                 showlegend=False)
            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
            if not lake_data.empty:
                fig_dual.add_trace(go.Scatter(
                    x=lake_data['Date'],
                    y=lake_data[lake_data.columns[1]],
                    name='Ύψος Λίμνης', mode='lines'
                ), secondary_y=False)
            fig_dual.add_trace(go.Scatter(
                x=sorted_dates,
                y=avg_mg,
                name='Μέσο mg/m³',
                mode='markers',
                marker=dict(color=avg_mg, colorscale='Viridis', reversescale=True,
                            colorbar=dict(title='mg/m³'), size=10)
            ), secondary_y=True)
            fig_dual.update_layout(title='Ύψος Λίμνης και Μέσο mg/m³ με την πάροδο του χρόνου',
                                   xaxis_title='Ημερομηνία', showlegend=True)
            fig_dual.update_yaxes(title_text="Ύψος Λίμνης", secondary_y=False)
            fig_dual.update_yaxes(title_text="mg/m³", secondary_y=True)
            return fig_geo, fig_dual, fig_colors, fig_mg, results_colors, results_mg, lake_data

        # Δύο καρτέλες δειγματοληψίας
        if "default_results" not in st.session_state:
            st.session_state.default_results = None
        if "upload_results" not in st.session_state:
            st.session_state.upload_results = None

        tab_names = ["Δειγματοληψία 1 (Default)", "Δειγματοληψία 2 (Upload)"]
        sampling_tabs = st.tabs(tab_names)

        # Καρτέλα 1 (Default Sampling)
        with sampling_tabs[0]:
            st.header("Ανάλυση για Δειγματοληψία 1 (Default)")
            default_sampling_points = []
            if os.path.exists(sampling_kml_path):
                default_sampling_points = parse_sampling_kml(sampling_kml_path)
            else:
                st.warning("Το αρχείο δειγματοληψίας (sampling.kml) δεν βρέθηκε.")
            point_names = [name for name, _, _ in default_sampling_points]
            selected_points = st.multiselect("Επιλέξτε σημεία για ανάλυση mg/m³",
                                             options=point_names,
                                             default=point_names,
                                             key="default_points")
            if st.button("Εκτέλεση Ανάλυσης (Default)", key="default_run"):
                with st.spinner("Εκτέλεση ανάλυσης..."):
                    st.session_state.default_results = analyze_sampling(
                        default_sampling_points,
                        first_image_data,
                        first_transform,
                        images_folder,
                        lake_height_path,
                        selected_points
                    )
            if st.session_state.default_results is not None:
                results = st.session_state.default_results
                if isinstance(results, tuple) and len(results) == 7:
                    fig_geo, fig_dual, fig_colors, fig_mg, results_colors, results_mg, lake_data = results
                else:
                    st.error("Σφάλμα μορφοποίησης αποτελεσμάτων ανάλυσης. Παρακαλώ επαναλάβετε την ανάλυση.")
                    st.stop()
                nested_tabs = st.tabs(["GeoTIFF", "Επιλογή εικόνων", "Video/GIF", "Χρώματα Pixel", "Μέσο mg", "Διπλά Διαγράμματα", "Λεπτομερής ανάλυση mg"])
                # In each nested tab, we now add the legend below the main figure.
                with nested_tabs[0]:
                    st.plotly_chart(fig_geo, use_container_width=True, key="default_fig_geo")
                    st.markdown("### Legend for Chlorophyll‑a")
                    legend_fig = create_chl_legend_figure()
                    st.pyplot(legend_fig)
                with nested_tabs[1]:
                    st.header("Επιλογή εικόνων")
                    tif_files = [f for f in os.listdir(images_folder) if f.lower().endswith('.tif')]
                    available_dates = {}
                    for filename in tif_files:
                        match = re.search(r'(\d{4}_\d{2}_\d{2})', filename)
                        if match:
                            date_str = match.group(1)
                            try:
                                date_obj = datetime.strptime(date_str, '%Y_%m_%d').date()
                                available_dates[str(date_obj)] = filename
                            except Exception as e:
                                debug("DEBUG: Error extracting date from", filename, ":", e)
                                continue
                    if available_dates:
                        sorted_dates = sorted(available_dates.keys())
                        if 'current_image_index' not in st.session_state:
                            st.session_state.current_image_index = 0
                        col_prev, col_select, col_next = st.columns([1, 3, 1])
                        with col_prev:
                            if st.button("<< Previous"):
                                st.session_state.current_image_index = max(0, st.session_state.current_image_index - 1)
                        with col_next:
                            if st.button("Next >>"):
                                st.session_state.current_image_index = min(len(sorted_dates) - 1, st.session_state.current_image_index + 1)
                        with col_select:
                            selected_date = st.selectbox("Select date", sorted_dates, index=st.session_state.current_image_index, key="default_select_date")
                            st.session_state.current_image_index = sorted_dates.index(selected_date)
                        current_date = sorted_dates[st.session_state.current_image_index]
                        st.write(f"Selected Date: {current_date}")
                        image_filename = available_dates[current_date]
                        image_path = os.path.join(images_folder, image_filename)
                        if os.path.exists(image_path):
                            st.image(image_path, caption=f"Image for {current_date}", use_column_width=True)
                        else:
                            st.error("Image not found.")
                    else:
                        st.info("No images found with a date in the folder.")
                    st.markdown("### Legend for Chlorophyll‑a")
                    legend_fig = create_chl_legend_figure()
                    st.pyplot(legend_fig)
                with nested_tabs[2]:
                    if video_path is not None:
                        if video_path.endswith(".mp4"):
                            st.video(video_path, key="default_video")
                        else:
                            st.image(video_path)
                    else:
                        st.info("Δεν βρέθηκε αρχείο timelapse.")
                    st.markdown("### Legend for Chlorophyll‑a")
                    legend_fig = create_chl_legend_figure()
                    st.pyplot(legend_fig)
                with nested_tabs[3]:
                    st.plotly_chart(fig_colors, use_container_width=True, key="default_fig_colors")
                    st.markdown("### Legend for Chlorophyll‑a")
                    legend_fig = create_chl_legend_figure()
                    st.pyplot(legend_fig)
                with nested_tabs[4]:
                    st.plotly_chart(fig_mg, use_container_width=True, key="default_fig_mg")
                with nested_tabs[5]:
                    st.plotly_chart(fig_dual, use_container_width=True, key="default_fig_dual")
                with nested_tabs[6]:
                    selected_detail_point = st.selectbox("Επιλέξτε σημείο για λεπτομερή ανάλυση mg",
                                                         options=list(results_mg.keys()),
                                                         key="default_detail")
                    if selected_detail_point:
                        mg_data = results_mg[selected_detail_point]
                        if mg_data:
                            mg_data_sorted = sorted(mg_data, key=lambda x: x[0])
                            dates_mg = [d for d, _ in mg_data_sorted]
                            mg_values = [val for _, val in mg_data_sorted]
                            detail_colors = [mg_to_color(val) for val in mg_values]
                            fig_detail = go.Figure()
                            fig_detail.add_trace(go.Scatter(
                                x=dates_mg, y=mg_values, mode='lines+markers',
                                marker=dict(color=detail_colors, size=10),
                                line=dict(color="gray"),
                                name=selected_detail_point
                            ))
                            fig_detail.update_layout(title=f"Λεπτομερής ανάλυση mg για {selected_detail_point}",
                                                     xaxis_title="Ημερομηνία", yaxis_title="mg/m³")
                            st.plotly_chart(fig_detail, use_container_width=True, key="default_fig_detail")
                        else:
                            st.info("Δεν υπάρχουν δεδομένα mg για αυτό το σημείο.")
    # Καρτέλα 2 (Upload Sampling)
    with sampling_tabs[1]:
        st.header("Ανάλυση για ανεβασμένη δειγματοληψία")
        uploaded_file = st.file_uploader(
            "Ανεβάστε αρχείο KML για νέα σημεία δειγματοληψίας",
            type="kml",
            key="upload_kml"
        )
        if uploaded_file is not None:
            try:
                new_sampling_points = parse_sampling_kml(uploaded_file)
            except Exception as e:
                st.error(f"Σφάλμα επεξεργασίας ανεβασμένου αρχείου: {e}")
                new_sampling_points = []
            point_names = [name for name, _, _ in new_sampling_points]
            selected_points = st.multiselect(
                "Επιλέξτε σημεία για ανάλυση mg/m³",
                options=point_names,
                default=point_names,
                key="upload_points"
            )
            if st.button("Εκτέλεση Ανάλυσης (Upload)", key="upload_run"):
                with st.spinner("Εκτέλεση ανάλυσης..."):
                    st.session_state.upload_results = analyze_sampling(
                        new_sampling_points,
                        first_image_data,
                        first_transform,
                        images_folder,
                        lake_height_path,
                        selected_points
                    )
            if st.session_state.upload_results is not None:
                results = st.session_state.upload_results
                if isinstance(results, tuple) and len(results) == 7:
                    fig_geo, fig_dual, fig_colors, fig_mg, results_colors, results_mg, lake_data = results
                else:
                    st.error(
                        "Σφάλμα μορφοποίησης αποτελεσμάτων ανάλυσης (Upload). "
                        "Παρακαλώ επαναλάβετε."
                    )
                    st.stop()

                nested_tabs = st.tabs([
                    "GeoTIFF", "Επιλογή εικόνων", "Video/GIF",
                    "Χρώματα Pixel", "Μέσο mg",
                    "Διπλά Διαγράμματα", "Λεπτομερής ανάλυση mg"
                ])

                with nested_tabs[0]:
                    st.plotly_chart(fig_geo, use_container_width=True, key="upload_fig_geo")
                    # legend μόνο για Χλωροφύλλη
                    if index == "Χλωροφύλλη":
                        st.markdown("### Legend for Chlorophyll-a")
                        legend_fig = create_chl_legend_figure()
                        st.pyplot(legend_fig)

                with nested_tabs[1]:
                    st.header("Επιλογή εικόνων")
                    tif_files = [
                        f for f in os.listdir(images_folder)
                        if f.lower().endswith('.tif')
                    ]
                    available_dates = {}
                    for filename in tif_files:
                        match = re.search(r'(\d{4}_\d{2}_\d{2})', filename)
                        if match:
                            date_str = match.group(1)
                            try:
                                date_obj = datetime.strptime(date_str, '%Y_%m_%d').date()
                                available_dates[str(date_obj)] = filename
                            except Exception:
                                continue

                    if available_dates:
                        sorted_dates = sorted(available_dates.keys())
                        if 'current_upload_image_index' not in st.session_state:
                            st.session_state.current_upload_image_index = 0
                        col_prev, col_select, col_next = st.columns([1, 3, 1])
                        with col_prev:
                            if st.button("<< Previous", key="upload_prev"):
                                st.session_state.current_upload_image_index = max(
                                    0, st.session_state.current_upload_image_index - 1
                                )
                        with col_next:
                            if st.button("Next >>", key="upload_next"):
                                st.session_state.current_upload_image_index = min(
                                    len(sorted_dates) - 1,
                                    st.session_state.current_upload_image_index + 1
                                )
                        with col_select:
                            selected_date = st.selectbox(
                                "Select date",
                                sorted_dates,
                                index=st.session_state.current_upload_image_index,
                                key="upload_select_date"
                            )
                            st.session_state.current_upload_image_index = (
                                sorted_dates.index(selected_date)
                            )
                        current_date = sorted_dates[st.session_state.current_upload_image_index]
                        st.write(f"Selected Date: {current_date}")
                        image_filename = available_dates[current_date]
                        image_path = os.path.join(images_folder, image_filename)
                        if os.path.exists(image_path):
                            st.image(image_path, caption=f"Image for {current_date}", use_column_width=True)
                        else:
                            st.error("Image not found.")
                    else:
                        st.info("No images found with a date in the folder.")

                    # legend μόνο για Χλωροφύλλη
                    if index == "Χλωροφύλλη":
                        st.markdown("### Legend for Chlorophyll-a")
                        legend_fig = create_chl_legend_figure()
                        st.pyplot(legend_fig)

                with nested_tabs[2]:
                    if video_path is not None:
                        if video_path.endswith(".mp4"):
                            st.video(video_path, key="upload_video")
                        else:
                            st.image(video_path)
                    else:
                        st.info("Δεν βρέθηκε αρχείο Video/GIF.")
                    # legend μόνο για Χλωροφύλλη
                    if index == "Χλωροφύλλη":
                        st.markdown("### Legend for Chlorophyll-a")
                        legend_fig = create_chl_legend_figure()
                        st.pyplot(legend_fig)

                with nested_tabs[3]:
                    col1, col2 = st.columns([8, 1])
                    with col1:
                        fig_colors.update_layout(width=2000, height=500)
                        st.plotly_chart(fig_colors, use_container_width=True, key="default_fig_colors")
                    with col2:
                       if index == "Χλωροφύλλη":
                           st.markdown("#### Legend for Chlorophyll‑a")
                           legend_fig = create_chl_legend_figure_vertical()
                           st.pyplot(legend_fig)

                with nested_tabs[4]:
                    st.plotly_chart(fig_mg, use_container_width=True, key="upload_fig_mg")

                with nested_tabs[5]:
                    st.plotly_chart(fig_dual, use_container_width=True, key="upload_fig_dual")

                with nested_tabs[6]:
                    selected_detail_point = st.selectbox(
                        "Επιλέξτε σημείο για λεπτομερή ανάλυση mg",
                        options=list(results_mg.keys()),
                        key="upload_detail"
                    )
                    if selected_detail_point:
                        mg_data = results_mg[selected_detail_point]
                        if mg_data:
                            mg_data_sorted = sorted(mg_data, key=lambda x: x[0])
                            dates_mg = [d for d, _ in mg_data_sorted]
                            mg_values = [val for _, val in mg_data_sorted]
                            detail_colors = [mg_to_color(val) for val in mg_values]
                            fig_detail = go.Figure()
                            fig_detail.add_trace(go.Scatter(
                                x=dates_mg,
                                y=mg_values,
                                mode='lines+markers',
                                marker=dict(color=detail_colors, size=10),
                                line=dict(color="gray"),
                                name=selected_detail_point
                            ))
                            fig_detail.update_layout(
                                title=f"Λεπτομερής ανάλυση mg για {selected_detail_point}",
                                xaxis_title="Ημερομηνία",
                                yaxis_title="mg/m³"
                            )
                            st.plotly_chart(fig_detail, use_container_width=True, key="upload_fig_detail")
                        else:
                            st.info(
                                "Δεν υπάρχουν δεδομένα mg για αυτό το σημείο.",
                                key="upload_no_mg"
                            )
        else:
            st.info("Παρακαλώ ανεβάστε ένα αρχείο KML για νέα σημεία δειγματοληψίας.")

    st.info("Τέλος Πίνακα Ποιότητας Ύδατος.")
    st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Επεξεργασία Καμένων Περιοχών (Placeholder)
# -----------------------------------------------------------------------------
def run_burned_areas():
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title("Burned Areas γύρω από το ταμιευτήριο (μόνο Γαδουρά)")
        st.info("Δεν υπάρχουν δεδομένα ή λειτουργίες για ανάλυση καμένων περιοχών.")
        st.markdown('</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Predictive Tools with on-the-fly re-calculation for all indices
# --------------------------------------------------------------------------
def run_predictive_tools(waterbody: str, index: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title(f"Εργαλεία Πρόβλεψης & Έγκαιρης Ενημέρωσης ({waterbody} - {index})")

        # 1) Charts to recalc
        chart_options = ["GeoTIFF", "Pixel Colors", "Lake Height", "Μέσο mg/m³"]
        selected_charts = st.multiselect(
            "Επίλεξε διαγράμματα για επανυπολογισμό",
            options=chart_options,
            default=chart_options
        )

        # 2) Filtering params
        st.markdown("**Παράμετροι φιλτραρίσματος**")
        lower_thresh, upper_thresh = st.slider(
            "Threshold range (pixel)",
            0, 255, (0, 255)
        )
        date_min = st.date_input("Ημερομηνία από", value=date(2015, 1, 1))
        date_max = st.date_input("Ημερομηνία έως", value=date.today())
        sampling_type = st.radio("Sampling set", ["Default", "Upload"])

        # 3) Recompute when clicked
        if st.button("Επανυπολόγισε επιλεγμένα διαγράμματα"):
            for idx in ["Χλωροφύλλη", "Πραγματικό", "Θολότητα"]:
                st.header(f"--- Index: {idx} ---")

                folder = get_data_folder(waterbody, idx)
                if not folder:
                    st.error(f"Δεν υπάρχει φάκελος για {idx}.")
                    continue

                images_folder  = os.path.join(folder, "GeoTIFFs")
                lake_height_xl = os.path.join(folder, "lake height.xlsx")
                default_kml    = os.path.join(folder, "sampling.kml")

                # pick KML
                if sampling_type == "Default":
                    kml = default_kml
                else:
                    uploaded = st.file_uploader(f"Upload KML για {idx}", type="kml", key=f"upl_{idx}")
                    if not uploaded:
                        st.warning(f"Δεν ανέβηκε KML για {idx}.")
                        continue
                    kml = uploaded

                points = parse_sampling_kml(kml)
                if not points:
                    st.warning(f"Δεν βρέθηκαν σημεία για {idx}.")
                    continue

                # load first GeoTIFF for context
                tifs = sorted(glob.glob(os.path.join(images_folder, "*.tif")))
                if not tifs:
                    st.error(f"Δεν βρέθηκαν TIFF για {idx}.")
                    continue
                with rasterio.open(tifs[0]) as src:
                    if src.count < 3:
                        st.error(f"Το TIFF για {idx} δεν έχει 3 κανάλια.")
                        continue
                    first_img = src.read([1,2,3])
                    first_tr = src.transform

                # run analyzer
                try:
                    fig_geo, fig_dual, fig_colors, fig_mg, *_ = analyze_sampling(
                        sampling_points=points,
                        first_image_data=first_img,
                        first_transform=first_tr,
                        images_folder=images_folder,
                        lake_height_path=lake_height_xl,
                        selected_points=[pt[0] for pt in points],
                        lower_thresh=lower_thresh,
                        upper_thresh=upper_thresh,
                        date_min=date_min,
                        date_max=date_max
                    )
                except Exception as e:
                    st.error(f"Σφάλμα επανυπολογισμού για {idx}: {e}")
                    continue

                # draw only what was requested
                if "GeoTIFF" in selected_charts:
                    st.subheader("GeoTIFF εικόνα")
                    st.plotly_chart(fig_geo, use_container_width=True, key=f"fig_geo_{idx}")

                if "Pixel Colors" in selected_charts:
                    st.subheader("Pixel Colors over time")
                    st.plotly_chart(fig_colors, use_container_width=True, key=f"fig_colors_{idx}")

                if "Lake Height" in selected_charts:
                    st.subheader("Lake Height over time")
                    height_trace = fig_dual.data[0]
                    fig_h = go.Figure([height_trace]).update_layout(title="Lake Height")
                    st.plotly_chart(fig_h, use_container_width=True, key=f"fig_height_{idx}")

                if "Μέσο mg/m³" in selected_charts:
                    st.subheader("Μέσο mg/m³ over time")
                    st.plotly_chart(fig_mg, use_container_width=True, key=f"fig_mg_{idx}")

        st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Main Entry Point (drop-in)
# --------------------------------------------------------------------------
def main():
    run_intro_page()
    run_custom_ui()

    wb    = st.session_state.get("waterbody_choice")
    idx   = st.session_state.get("index_choice")
    analy = st.session_state.get("analysis_choice")

    # Οδηγεί στις αντίστοιχες ενότητες ανάλογα με το τι έχει διαλέξει ο χρήστης
    if wb == "Γαδουρά" and idx in ["Χλωροφύλλη", "Πραγματικό", "Θολότητα"]:
        if analy == "Επιφανειακή Αποτύπωση":
            run_lake_processing_app(wb, idx)
        elif analy == "Προφίλ ποιότητας και στάθμης":
            run_water_quality_dashboard(wb, idx)
        elif analy == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
            run_predictive_tools(wb, idx)
        else:
            st.info("Παρακαλώ επιλέξτε ένα είδος ανάλυσης.")
    elif analy == "Burned Areas":
        if wb == "Γαδουρά":
            run_burned_areas()
        else:
            st.warning("Το 'Burned Areas' είναι διαθέσιμο μόνο για το υδάτινο σώμα Γαδουρά.")
    else:
        st.warning("Δεν υπάρχουν διαθέσιμα δεδομένα για αυτόν τον συνδυασμό δείκτη/υδάτινου σώματος.")

    render_footer()

if __name__ == "__main__":
    main()
