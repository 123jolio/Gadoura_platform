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

# ---------------------------------------------------
# Footer Branding
# ---------------------------------------------------
def render_footer():
    st.markdown("""
        <hr>
        <div class='footer'>
            &copy; 2025 EYATH SA • Powered by OpenAI & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
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

# ---------------------------------------------------
# Data Processing Functions
# ---------------------------------------------------
def parse_sampling_kml(kml_source) -> list:
    try:
        if hasattr(kml_source, "seek"):
            kml_source.seek(0)
        tree = ET.parse(kml_source) if hasattr(kml_source, "read") else ET.parse(str(kml_source))
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

def analyze_sampling(sampling_points, first_image_data, first_transform,
                     images_folder, lake_height_path, selected_points,
                     lower_thresh=0, upper_thresh=255,
                     date_min=None, date_max=None):
    results_colors = {name: [] for name, _, _ in sampling_points}
    results_mg = {name: [] for name, _, _ in sampling_points}
    
    for filename in sorted(os.listdir(images_folder)):
        if not filename.lower().endswith(('.tif', '.tiff')):
            continue
        m = re.search(r'(\d{4}[_-]?\d{2}[_-]?\d{2})', filename)
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

# ---------------------------------------------------
# Main App Logic
# ---------------------------------------------------
def run_analysis(waterbody, index, analysis):
    st.title(f"Ανάλυση Υδάτινου Σώματος: {waterbody} - {index}")
    
    # Get data folder based on waterbody and index
    data_folder = os.path.join("data", "Gadoura", index)
    if not os.path.exists(data_folder):
        st.error(f"Ο φάκελος δεδομένων δεν βρέθηκε: {data_folder}")
        return
    
    # Upload KML file for sampling points
    kml_file = st.file_uploader("Upload KML file for sampling points", type=["kml"])
    if kml_file:
        sampling_points = parse_sampling_kml(kml_file)
        selected_points = st.multiselect("Επιλέξτε σημεία δειγματοληψίας", 
                                       [p[0] for p in sampling_points],
                                       default=[p[0] for p in sampling_points])
    else:
        sampling_points = []
        selected_points = []

    # Date range filters
    date_min = st.date_input("Minimum Date", value=None, key="date_min")
    date_max = st.date_input("Maximum Date", value=None, key="date_max")

    # Threshold controls
    lower_thresh = st.slider("Lower Threshold", 0, 255, 0, key="lower_thresh")
    upper_thresh = st.slider("Upper Threshold", 0, 255, 255, key="upper_thresh")

    if st.button("Ανάλυση"):
        if sampling_points and selected_points:
            # Find first image for reference
            first_image_path = next((os.path.join(data_folder, f) 
                                  for f in sorted(os.listdir(data_folder)) 
                                  if f.lower().endswith(('.tif', '.tiff'))), None)
            if first_image_path:
                with rasterio.open(first_image_path) as src:
                    first_image_data = src.read()
                    first_transform = src.transform

                # Process analysis
                fig_geo, fig_dual, fig_colors, fig_mg, results_colors, results_mg, df_h = \
                    analyze_sampling(sampling_points, first_image_data, first_transform,
                                   data_folder, os.path.join(data_folder, "lake_height.xlsx"),
                                   selected_points, lower_thresh, upper_thresh,
                                   date_min, date_max)

                # Display results
                st.plotly_chart(fig_geo)
                st.plotly_chart(fig_dual)
                st.plotly_chart(fig_colors)
                st.plotly_chart(fig_mg)
            else:
                st.error("Δεν βρέθηκαν εικόνες GeoTIFF στον φάκελο δεδομένων.")
        else:
            st.warning("Παρακαλώ επιλέξτε σημεία δειγματοληψίας.")

if __name__ == "__main__":
    inject_custom_css()
    run_intro_page()
    run_custom_ui()
    
    # Get selected options from sidebar
    waterbody = st.session_state.get("waterbody_choice", "Γαδουρά")
    index = st.session_state.get("index_choice", "Πραγματικό")
    analysis = st.session_state.get("analysis_choice", "Επιφανειακή Αποτύπωση")
    
    run_analysis(waterbody, index, analysis)
    render_footer()
