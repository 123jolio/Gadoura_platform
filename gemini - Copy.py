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

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ", page_icon="💧")
# --------------------------------------------------------------------

# --- Global Configuration & Constants ---
DEBUG = False 
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
LOGO_PATH = os.path.join(APP_BASE_DIR, "logo.jpg") 

WATERBODY_FOLDERS = {
    "Γαδουρά": "Gadoura",
}

SESSION_KEY_WATERBODY = "waterbody_choice_main"
SESSION_KEY_INDEX = "index_choice_main"
SESSION_KEY_ANALYSIS = "analysis_choice_main"
SESSION_KEY_DEFAULT_RESULTS_DASHBOARD = "dashboard_default_sampling_results"
SESSION_KEY_UPLOAD_RESULTS_DASHBOARD = "dashboard_upload_sampling_results"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF = "dash_def_current_image_idx"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL = "dash_upl_current_image_idx"


def debug_message(*args, **kwargs):
    if DEBUG:
        with st.expander("Debug Messages", expanded=False):
            st.write(*args, **kwargs)

def inject_custom_css():
    custom_css = """
    <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
        .block-container { background: #161b22; color: #e0e0e0; padding: 1.2rem; }
        .stSidebar > div:first-child { background: #23272f; border-right: 1px solid #3a3f47; }
        .card {
            background: #1a1a1d; padding: 2rem 2.5rem; border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25); margin-bottom: 2rem;
            animation: fadein 1.0s ease-in-out;
        }
        @keyframes fadein { 
            0% {opacity:0; transform: translateY(10px);} 
            100%{opacity:1; transform: translateY(0px);} 
        }
        .header-title {
            color: #ffd600; margin-bottom: 1.5rem; font-size: 2.2rem;
            text-align: center; letter-spacing: 0.5px; font-weight: 700;
        }
        .nav-section {
            padding: 1rem 1.2rem; background: #2c2f36; border-radius: 10px;
            margin-bottom: 1.2rem; border-left: 4px solid #ffd600;
        }
        .nav-section h4 { margin: 0; color: #ffd600; font-weight: 500; font-size: 1.1rem; }
        .stButton button {
            background-color: #009688; color: #ffffff; border-radius: 8px;
            padding: 10px 22px; border: none; box-shadow: 0 3px 8px rgba(0,0,0,0.15);
            font-size: 1.05rem; transition: background-color 0.2s, box-shadow 0.2s, transform 0.2s;
            cursor: pointer;
        }
        .stButton button:hover {
            background-color: #00796b; box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }
        .stButton button:active { background-color: #00695c; transform: translateY(0px); }
        .plotly-graph-div { border: 1px solid #2a2e37; border-radius: 10px; }
        .footer {
            text-align:center; color: #7a828e; font-size:0.85rem;
            padding: 2rem 0 0.5rem 0; border-top: 1px solid #2a2e37;
        }
        .footer a { color: #009688; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def render_footer():
    st.markdown("""
        <hr style="border-color: #2a2e37;">
        <div class='footer'>
            © 2024 EYATH SA • Powered by Google Gemini & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
        </div>
    """, unsafe_allow_html=True)

def run_intro_page_custom():
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_logo, col_text = st.columns([0.3, 0.7], gap="large")
        with col_logo:
            if os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=240, output_format="auto")
            else:
                st.markdown("💧", help="Λογότυπο ΕΥΑΘ")
        with col_text:
            st.markdown("""
                <h2 class='header-title'>Εφαρμογή Ανάλυσης Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ</h2>
                <p style='font-size:1.15rem;text-align:center; line-height:1.6;'>
                Εξερευνήστε τα δεδομένα ποιότητας με ευκολία.<br>
                Επιλέξτε τι θέλετε να δείτε από το πλάι παράγοντας δυναμικά, διαδραστικά γραφήματα
                </p>
                """, unsafe_allow_html=True)
        with st.expander("🔰 Οδηγίες Χρήσης", expanded=False):
            st.markdown("""
                - **Επιλογή Παραμέτρων:** Στην πλαϊνή μπάρα (αριστερά), επιλέξτε το υδάτινο σώμα, τον δείκτη ποιότητας και το είδος της ανάλυσης που επιθυμείτε.
                - **Πλοήγηση στα Αποτελέσματα:** Μετά την επιλογή, τα αποτελέσματα και τα διαδραστικά γραφήματα θα εμφανιστούν στην κύρια περιοχή. Χρησιμοποιήστε τις καρτέλες (tabs) για να δείτε διαφορετικές οπτικοποιήσεις.
                - **Προσαρμοσμένη Δειγματοληψία:** Στην ενότητα "Προφίλ ποιότητας και στάθμης", μπορείτε να ανεβάσετε το δικό σας αρχείο KML για ανάλυση σε συγκεκριμένα σημεία ενδιαφέροντος.
                - **Φίλτρα:** Σε ορισμένες αναλύσεις, θα βρείτε επιπλέον φίλτρα στην πλαϊνή μπάρα (π.χ., εύρος ημερομηνιών, τιμές pixel) για να προσαρμόσετε τα αποτελέσματα.
                - **Επεξηγήσεις:** Κάντε κλικ στα εικονίδια ℹ️ ή στα expanders για περισσότερες πληροφορίες σχετικά με κάθε γράφημα ή επιλογή.
                - **Ασφάλεια Δεδομένων:** Όλα τα δεδομένα και τα αρχεία που ανεβάζετε επεξεργάζονται τοπικά στον περιηγητή σας και δεν μεταφορτώνονται σε εξωτερικούς διακομιστές.
            """)
        st.markdown('</div>', unsafe_allow_html=True)

def run_custom_sidebar_ui_custom():
    st.sidebar.markdown("<div class='nav-section'><h4>🛠️ Επιλογές Ανάλυσης</h4></div>", unsafe_allow_html=True)
    st.sidebar.info("❔ Επιλέξτε τις ρυθμίσεις σας και προχωρήστε στα αποτελέσματα!")
    
    waterbody_options = list(WATERBODY_FOLDERS.keys())
    default_wb_idx = 0 if waterbody_options else None

    waterbody = st.sidebar.selectbox("🌊 Υδάτινο σώμα", waterbody_options, index=default_wb_idx, key=SESSION_KEY_WATERBODY)
    index_name = st.sidebar.selectbox("🔬 Δείκτης", ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"], key=SESSION_KEY_INDEX)
    analysis_type = st.sidebar.selectbox( "📊 Είδος Ανάλυσης",
        ["Επιφανειακή Αποτύπωση", "Προφίλ ποιότητας και στάθμης", "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"],
        key=SESSION_KEY_ANALYSIS
    )
    st.sidebar.markdown(
        f"""<div style="padding: 0.7rem; background:#2c2f36; border-radius:8px; margin-top:1.2rem;">
        <strong>🌊 Υδάτινο σώμα:</strong> {waterbody or "<i>-</i>"}<br>
        <strong>🔬 Δείκτης:</strong> {index_name or "<i>-</i>"}<br>
        <strong>📊 Ανάλυση:</strong> {analysis_type or "<i>-</i>"}
        </div>""",
        unsafe_allow_html=True
    )
    st.sidebar.markdown("---")

@st.cache_data
def parse_sampling_kml(kml_source) -> list:
    try:
        if hasattr(kml_source, "seek"): kml_source.seek(0)
        tree = ET.parse(kml_source) if hasattr(kml_source, "read") else ET.parse(str(kml_source))
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        points = []
        for i_ls, ls in enumerate(root.findall('.//kml:LineString', ns)):
            coords_text_elem = ls.find('kml:coordinates', ns)
            if coords_text_elem is not None and coords_text_elem.text:
                coords = coords_text_elem.text.strip().split()
                for i_coord, coord_str in enumerate(coords):
                    try:
                        lon, lat, *_ = coord_str.split(',')
                        point_name = f"LS{i_ls+1}_P{i_coord+1}"
                        points.append((point_name, float(lon), float(lat)))
                    except ValueError: debug_message(f"Warning: KML: Παράλειψη συντεταγμένης '{coord_str}'")
        if not points: st.warning("Δεν βρέθηκαν σημεία LineString στο KML.")
        return points
    except Exception as e: st.error(f"Σφάλμα ανάλυσης KML: {e}"); return []

def analyze_sampling_generic(sampling_points, first_image_data, first_transform,
                             images_folder, lake_height_path, selected_points_names,
                             lower_thresh=0, upper_thresh=255, date_min=None, date_max=None):
    results_colors = {name: [] for name, _, _ in sampling_points}
    results_mg = {name: [] for name, _, _ in sampling_points}
    
    if not os.path.isdir(images_folder):
        st.error(f"Ο φάκελος εικόνων '{images_folder}' δεν βρέθηκε."); return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    for filename in sorted(os.listdir(images_folder)):
        if not filename.lower().endswith(('.tif', '.tiff')): continue
        m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
        if not m: continue
        try: date_obj = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: debug_message(f"Παράλειψη {filename}: μη έγκυρη ημερομηνία."); continue
        
        if (date_min and date_obj.date() < date_min) or \
           (date_max and date_obj.date() > date_max): continue

        try:
            with rasterio.open(os.path.join(images_folder, filename)) as src:
                if src.count < 3: debug_message(f"Παράλειψη {filename}: <3 κανάλια."); continue
                for name, lon, lat in sampling_points:
                    if name not in selected_points_names: continue
                    col, row = map(int, (~src.transform) * (lon, lat))
                    if not (0 <= col < src.width and 0 <= row < src.height): continue
                    win = rasterio.windows.Window(col,row,1,1)
                    try:
                        r,g,b = src.read(1,window=win)[0,0], src.read(2,window=win)[0,0], src.read(3,window=win)[0,0]
                        mg_val = (g / 255.0) * 2.0 
                        results_mg[name].append((date_obj, mg_val))
                        results_colors[name].append((date_obj, (r/255., g/255., b/255.)))
                    except IndexError: debug_message(f"Σφάλμα Index pixel για {name} στο {filename}.")
        except Exception as e: st.warning(f"Σφάλμα επεξεργασίας {filename}: {e}")

    rgb_disp = first_image_data.transpose((1,2,0))/255.
    fig_geo = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία'); fig_geo.update_layout(height=600, uirevision='geo')
    for n,lon,lat in sampling_points:
        if n in selected_points_names:
            col,row = map(int, (~first_transform) * (lon,lat))
            fig_geo.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text',marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right"))
    fig_geo.update_xaxes(visible=False); fig_geo.update_yaxes(visible=False,scaleanchor="x",scaleratio=1)

    df_h = pd.DataFrame(columns=['Date','Height'])
    if os.path.exists(str(lake_height_path)):
        try: 
            df_h_temp = pd.read_excel(lake_height_path)
            if not df_h_temp.empty and len(df_h_temp.columns) >=2:
                 df_h['Date']=pd.to_datetime(df_h_temp.iloc[:,0],errors='coerce'); df_h['Height']=pd.to_numeric(df_h_temp.iloc[:,1],errors='coerce')
                 df_h.dropna(inplace=True); df_h.sort_values('Date',inplace=True)
        except Exception: df_h = pd.DataFrame(columns=['Date','Height'])
    
    fig_colors = make_subplots(specs=[[{"secondary_y":True}]]); pt_y_map={n:i for i,n in enumerate(selected_points_names)}
    for n_iter in selected_points_names:
        if n_iter in results_colors and results_colors[n_iter]:
            dts,cols=zip(*sorted(results_colors[n_iter],key=lambda x:x[0])) if results_colors[n_iter] else ([],[])
            c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
            fig_colors.add_trace(go.Scatter(x=list(dts),y=[pt_y_map.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
    if not df_h.empty: fig_colors.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη',mode='lines',line=dict(color='blue')),secondary_y=True)
    fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη',yaxis=dict(tickmode='array',tickvals=list(pt_y_map.values()),ticktext=list(pt_y_map.keys())),yaxis2=dict(title='Στάθμη (m)'), uirevision='colors')
    
    all_mg_by_d={}; 
    for p_name in selected_points_names: 
        if p_name in results_mg: 
            for d,v in results_mg[p_name]: all_mg_by_d.setdefault(d,[]).append(v)
    s_dts_mg=sorted(all_mg_by_d.keys()); mean_mg=[np.mean(all_mg_by_d[d]) for d in s_dts_mg if all_mg_by_d[d]]
    fig_mg=go.Figure(); 
    if s_dts_mg and mean_mg: fig_mg.add_trace(go.Scatter(x=s_dts_mg,y=mean_mg,mode='lines+markers',marker=dict(color=mean_mg,colorscale='Viridis',colorbar=dict(title='mg/m³'),size=8)))
    fig_mg.update_layout(title='Μέσο mg/m³', uirevision='mg')

    fig_dual=make_subplots(specs=[[{"secondary_y":True}]])
    if not df_h.empty: fig_dual.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη',mode='lines'),secondary_y=False)
    if s_dts_mg and mean_mg: fig_dual.add_trace(go.Scatter(x=s_dts_mg,y=mean_mg,name='Μέσο mg/m³',mode='lines+markers', marker=dict(color=mean_mg, colorscale='Viridis', showscale=False)),secondary_y=True)
    fig_dual.update_layout(title='Στάθμη & Μέσο mg/m³', uirevision='dual', 
                           yaxis=dict(title=dict(text="Στάθμη (m)",font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"), side='left'),
                           yaxis2=dict(title=dict(text="Μέσο mg/m³",font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"), overlaying='y', side='right'))
    return fig_geo,fig_dual,fig_colors,fig_mg,results_colors,results_mg,df_h

@st.cache_resource
def create_chl_legend_figure(orientation="horizontal", theme_bg_color=None, theme_text_color=None):
    levels = [0, 6, 12, 20, 30, 50]
    colors = ["#496FF2", "#82D35F", "#FEFD05", "#FD0004", "#8E2026", "#D97CF5"]
    cmap = mcolors.LinearSegmentedColormap.from_list("ChlLegend", list(zip(np.linspace(0, 1, len(levels)), colors)))
    norm = mcolors.Normalize(vmin=levels[0], vmax=levels[-1])
    
    if orientation == "horizontal":
        fig, ax = plt.subplots(figsize=(7, 1.2))
        fig.subplots_adjust(bottom=0.45, top=0.9, left=0.05, right=0.95)
        cbar_orientation = "horizontal"
    else:
        fig, ax = plt.subplots(figsize=(1.8, 6))
        fig.subplots_adjust(left=0.3, right=0.7, top=0.95, bottom=0.05)
        cbar_orientation = "vertical"

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([]) 
    cbar = fig.colorbar(sm, cax=ax, orientation=cbar_orientation, ticks=levels, aspect=30 if orientation=="horizontal" else 20, shrink=0.95)
    
    label_text = "Συγκέντρωση Χλωροφύλλης-α (mg/m³)"
    tick_labels = [str(l) for l in levels]

    if orientation == "horizontal":
        ax.set_xlabel(label_text, fontsize=10)
        ax.set_xticklabels(tick_labels, fontsize=9)
    else:
        ax.set_ylabel(label_text, fontsize=10)
        ax.set_yticklabels(tick_labels, fontsize=9)

    if theme_bg_color:
        fig.patch.set_facecolor(theme_bg_color)
        ax.set_facecolor(theme_bg_color)
    if theme_text_color:
        ax.xaxis.label.set_color(theme_text_color)
        ax.yaxis.label.set_color(theme_text_color)
        ax.tick_params(axis='x', colors=theme_text_color)
        ax.tick_params(axis='y', colors=theme_text_color)
        cbar.ax.xaxis.label.set_color(theme_text_color)
        cbar.ax.yaxis.label.set_color(theme_text_color)
        cbar.ax.tick_params(axis='x', colors=theme_text_color)
        cbar.ax.tick_params(axis='y', colors=theme_text_color)

    plt.tight_layout(pad=0.5)
    return fig

@st.cache_data
def get_data_folder(waterbody: str, index_name: str) -> str | None:
    waterbody_folder_name = WATERBODY_FOLDERS.get(waterbody)
    if not waterbody_folder_name:
        st.error(f"Δεν έχει οριστεί αντιστοίχιση φακέλου για το υδάτινο σώμα: '{waterbody}'.")
        return None

    index_specific_folder = ""
    if index_name == "Πραγματικό":
        if waterbody == "Κορώνεια": 
            index_specific_folder = "Pragmatiko"
        else: 
            index_specific_folder = "Πραγματικό"
    elif index_name == "Χλωροφύλλη":
        index_specific_folder = "Chlorophyll"
    elif index_name == "Θολότητα":
        index_specific_folder = "Θολότητα" 
    else:
        index_specific_folder = index_name 

    data_folder = os.path.join(APP_BASE_DIR, waterbody_folder_name, index_specific_folder)
    debug_message(f"DEBUG: Αναζήτηση φακέλου δεδομένων: {data_folder}")
    
    if not os.path.exists(data_folder) or not os.path.isdir(data_folder):
        return None
    
    return data_folder

@st.cache_data
def extract_date_from_filename(filename: str) -> tuple[int | None, datetime | None]:
    basename = os.path.basename(filename)
    match = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', basename)
    
    if match:
        year, month, day = map(int, match.groups())
        try:
            date_obj = datetime(year, month, day)
            day_of_year = date_obj.timetuple().tm_yday
            return day_of_year, date_obj
        except ValueError as e:
            debug_message(f"DEBUG: Σφάλμα μετατροπής ημερομηνίας από '{basename}': {e}")
            return None, None
    return None, None

@st.cache_data
def load_lake_shape_from_xml(xml_file_path: str, bounds: tuple = None,
                             xml_width: float = 518.0, xml_height: float = 505.0):
    debug_message(f"DEBUG: Φόρτωση περιγράμματος από: {xml_file_path}")
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        points_xml = []
        for point_elem in root.findall("point"):
            x_str, y_str = point_elem.get("x"), point_elem.get("y")
            if x_str and y_str: points_xml.append([float(x_str), float(y_str)])
        
        if not points_xml:
            st.warning(f"Δεν βρέθηκαν σημεία στο XML: {os.path.basename(xml_file_path)}"); return None
            
        points_to_return = points_xml
        if bounds:
            minx, miny, maxx, maxy = bounds
            points_to_return = [[minx + (x/xml_width)*(maxx-minx), maxy - (y/xml_height)*(maxy-miny)] for x,y in points_xml]

        if points_to_return and (points_to_return[0] != points_to_return[-1]):
            points_to_return.append(points_to_return[0])
        
        debug_message(f"DEBUG: Φορτώθηκαν {len(points_to_return)} σημεία περιγράμματος.")
        return {"type": "Polygon", "coordinates": [points_to_return]}
    except FileNotFoundError:
        st.error(f"Το αρχείο XML περιγράμματος δεν βρέθηκε: {xml_file_path}"); return None
    except Exception as e:
        st.error(f"Σφάλμα φόρτωσης περιγράμματος από {os.path.basename(xml_file_path)}: {e}"); return None

@st.cache_data
def read_image(file_path: str, lake_shape: dict = None):
    debug_message(f"DEBUG: Ανάγνωση εικόνας: {file_path}")
    try:
        with rasterio.open(file_path) as src:
            img = src.read(1).astype(np.float32)
            profile = src.profile.copy(); profile.update(dtype="float32")
            
            if src.nodata is not None: img = np.where(img == src.nodata, np.nan, img)
            img = np.where(img == 0, np.nan, img)

            if lake_shape:
                from rasterio.features import geometry_mask
                poly_mask = geometry_mask([lake_shape], transform=src.transform, invert=False, out_shape=img.shape)
                img = np.where(~poly_mask, img, np.nan)
            return img, profile
    except Exception as e:
        st.warning(f"Προειδοποίηση: Σφάλμα ανάγνωσης εικόνας {os.path.basename(file_path)}: {e}. Παραλείπεται."); return None, None

@st.cache_data
def load_data_for_lake_processing(input_folder: str, shapefile_name="shapefile.xml"):
    debug_message(f"DEBUG: load_data_for_lake_processing για: {input_folder}")
    if not os.path.exists(input_folder):
        st.error(f"Ο φάκελος εισόδου δεν υπάρχει: {input_folder}"); return None, None, None, None

    shape_file_path = next((sp for sp in [os.path.join(input_folder, shapefile_name), os.path.join(input_folder, "shapefile.txt")] if os.path.exists(sp)), None)
    if shape_file_path: debug_message(f"Βρέθηκε αρχείο περιγράμματος: {shape_file_path}")
    
    tif_files = sorted([fp for fp in glob.glob(os.path.join(input_folder, "*.tif")) if os.path.basename(fp).lower() != "mask.tif"])
    if not tif_files:
        st.warning(f"Δεν βρέθηκαν GeoTIFF αρχεία στον φάκελο: {input_folder}"); return None, None, None, None

    first_profile, lake_geom = None, None
    try:
        with rasterio.open(tif_files[0]) as src_first:
            first_profile = src_first.profile.copy()
            if shape_file_path: lake_geom = load_lake_shape_from_xml(shape_file_path, bounds=src_first.bounds)
    except Exception as e:
        st.error(f"Σφάλμα προετοιμασίας φόρτωσης (πρώτη εικόνα/shapefile): {e}"); return None, None, None, None

    images, days, dates_list = [], [], []
    for fp_iter in tif_files:
        day_yr, date_obj = extract_date_from_filename(fp_iter)
        if day_yr is None: continue
        img_data, _ = read_image(fp_iter, lake_shape=lake_geom) 
        if img_data is not None: images.append(img_data); days.append(day_yr); dates_list.append(date_obj)
            
    if not images:
        st.warning(f"Δεν φορτώθηκαν έγκυρες εικόνες από τον φάκελο: {input_folder}."); return None, None, None, None
    return np.stack(images, axis=0), np.array(days), dates_list, first_profile

def run_lake_processing_app(waterbody: str, index_name: str):
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.header(f"Επιφανειακή Αποτύπωση: {waterbody} - {index_name}")

        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder:
            expected_folder_name = ""
            if index_name == "Πραγματικό":
                if waterbody == "Κορώνεια": expected_folder_name = "Pragmatiko"
                else: expected_folder_name = "Πραγματικό"
            elif index_name == "Χλωροφύλλη": expected_folder_name = "Chlorophyll"
            elif index_name == "Θολότητα": expected_folder_name = "Θολότητα"
            else: expected_folder_name = index_name
            
            st.error(f"Ο φάκελος δεδομένων για '{waterbody} - {index_name}' δεν βρέθηκε. "
                     f"Ελέγξτε ότι ο φάκελος '{expected_folder_name}' "
                     f"υπάρχει μέσα στον κατάλογο '{os.path.join(APP_BASE_DIR, WATERBODY_FOLDERS.get(waterbody, ''))}'.")
            st.markdown('</div>', unsafe_allow_html=True); return

        input_folder_geotiffs = os.path.join(data_folder, "GeoTIFFs")
        
        with st.spinner(f"Φόρτωση δεδομένων για {waterbody} - {index_name}..."):
            STACK, DAYS, DATES, _ = load_data_for_lake_processing(input_folder_geotiffs)

        if STACK is None or not DATES:
            st.markdown('</div>', unsafe_allow_html=True); return

        st.sidebar.subheader(f"Φίλτρα Επεξεργασίας Λίμνης ({index_name})")
        min_avail_date = min(DATES).date() if DATES else date.today()
        max_avail_date = max(DATES).date() if DATES else date.today()
        unique_years_avail = sorted(list(set(d.year for d in DATES if d))) if DATES else []

        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name) 
        key_suffix = f"_lp_{waterbody}_{clean_index_name_for_key}"

        threshold_range_val = st.sidebar.slider("Εύρος τιμών pixel:", 0, 255, (0, 255), 
                                            key=f"thresh{key_suffix}", 
                                            help="Ορίστε το κατώφλι και ανώφλι για τις τιμές pixel.")
        
        col_start_lp, col_end_lp = st.sidebar.columns(2)
        refined_start_val = col_start_lp.date_input("Έναρξη περιόδου:", value=min_avail_date, 
                                                   min_value=min_avail_date, max_value=max_avail_date, 
                                                   key=f"refined_start{key_suffix}")
        refined_end_val = col_end_lp.date_input("Λήξη περιόδου:", value=max_avail_date, 
                                                 min_value=min_avail_date, max_value=max_avail_date, 
                                                 key=f"refined_end{key_suffix}")
        
        if refined_start_val > refined_end_val:
            st.sidebar.error("Η ημερομηνία έναρξης πρέπει να είναι πριν ή ίδια με την ημερομηνία λήξης.")
            st.markdown('</div>', unsafe_allow_html=True); return
            
        display_option_val = st.sidebar.radio("Εμφάνιση Μέσου Δείγματος:", 
                                          options=["Thresholded", "Original"], index=0, 
                                          key=f"display_opt{key_suffix}", horizontal=True)

        month_options_map = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        
        selected_months_val = st.sidebar.multiselect("Επιλογή Μηνών:",
                                                 options=list(month_options_map.keys()),
                                                 format_func=lambda x: month_options_map[x],
                                                 default=st.session_state.get(f"sel_months{key_suffix}", list(month_options_map.keys())),
                                                 key=f"sel_months{key_suffix}")
        
        selected_years_val = st.sidebar.multiselect("Επιλογή Ετών:", 
                                                options=unique_years_avail,
                                                default=st.session_state.get(f"sel_years{key_suffix}", unique_years_avail),
                                                key=f"sel_years{key_suffix}")
        
        start_dt_conv = datetime.combine(refined_start_val, datetime.min.time())
        end_dt_conv = datetime.combine(refined_end_val, datetime.max.time())

        indices_to_keep = [
            i for i, dt_obj in enumerate(DATES)
            if (start_dt_conv <= dt_obj <= end_dt_conv and
                (not selected_months_val or dt_obj.month in selected_months_val) and
                (not selected_years_val or dt_obj.year in selected_years_val))
        ]

        if not indices_to_keep:
            st.info("Δεν υπάρχουν δεδομένα για την επιλεγμένη περίοδο/μήνες/έτη. Παρακαλώ προσαρμόστε τα φίλτρα.")
            st.markdown('</div>', unsafe_allow_html=True); return

        with st.spinner("Επεξεργασία φιλτραρισμένων δεδομένων και δημιουργία γραφημάτων..."):
            stack_filt = STACK[indices_to_keep, :, :]
            days_filt = DAYS[indices_to_keep] 
            filtered_dates_objects = [DATES[i] for i in indices_to_keep]

            lower_t, upper_t = threshold_range_val
            in_range_bool_mask = np.logical_and(stack_filt >= lower_t, stack_filt <= upper_t)
            
            st.subheader("Ανάλυση Χαρτών")
            expander_col1, expander_col2 = st.columns(2)

            with expander_col1:
                with st.expander("Χάρτης: Ημέρες εντός Εύρους Τιμών", expanded=True):
                    days_in_range_map = np.nansum(in_range_bool_mask, axis=0)
                    fig_days = px.imshow(days_in_range_map, color_continuous_scale="plasma", labels={"color": "Ημέρες"})
                    st.plotly_chart(fig_days, use_container_width=True, key=f"fig_days_map{key_suffix}")
                    st.caption("Δείχνει πόσες ημέρες κάθε pixel ήταν εντός του επιλεγμένου εύρους τιμών.")

            tick_vals_days = [1,32,60,91,121,152,182,213,244,274,305,335,365]
            tick_text_days = ["Ιαν","Φεβ","Μαρ","Απρ","Μαΐ","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ",""]

            with expander_col2:
                with st.expander("Χάρτης: Μέση Ημέρα Εμφάνισης εντός Εύρους", expanded=True):
                    days_array_expanded = days_filt.reshape((-1, 1, 1))
                    sum_days_in_range = np.nansum(days_array_expanded * in_range_bool_mask, axis=0)
                    count_pixels_in_range = np.nansum(in_range_bool_mask, axis=0)
                    mean_day_map = np.divide(sum_days_in_range, count_pixels_in_range, 
                                             out=np.full(sum_days_in_range.shape, np.nan), 
                                             where=(count_pixels_in_range != 0))
                    fig_mean_day = px.imshow(mean_day_map, color_continuous_scale="RdBu", 
                                             labels={"color": "Μέση Ημέρα (1-365)"},
                                             color_continuous_midpoint=182)
                    fig_mean_day.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
                    st.plotly_chart(fig_mean_day, use_container_width=True, key=f"fig_mean_day_map{key_suffix}")
                    st.caption("Δείχνει τη μέση ημέρα του έτους που ένα pixel ήταν εντός του εύρους τιμών.")

            st.subheader("Ανάλυση Δείγματος Εικόνας")
            expander_col3, expander_col4 = st.columns(2)

            with expander_col3:
                with st.expander("Χάρτης: Μέσο Δείγμα Εικόνας", expanded=True):
                    average_sample_img_display = None
                    if display_option_val.lower() == "thresholded":
                        filtered_stack_for_avg = np.where(in_range_bool_mask, stack_filt, np.nan)
                        average_sample_img_display = np.nanmean(filtered_stack_for_avg, axis=0)
                    else: 
                        average_sample_img_display = np.nanmean(stack_filt, axis=0)

                    if average_sample_img_display is not None and not np.all(np.isnan(average_sample_img_display)):
                        avg_min_disp = float(np.nanmin(average_sample_img_display))
                        avg_max_disp = float(np.nanmax(average_sample_img_display))
                        fig_sample_disp = px.imshow(average_sample_img_display, color_continuous_scale="jet",
                                                range_color=[avg_min_disp, avg_max_disp] if avg_min_disp < avg_max_disp else None,
                                                labels={"color": "Τιμή Pixel"})
                        st.plotly_chart(fig_sample_disp, use_container_width=True, key=f"fig_sample_map{key_suffix}")
                        st.caption(f"Μέση τιμή pixel (εμφάνιση: {display_option_val}).")
                    else:
                        st.caption("Δεν υπάρχουν δεδομένα για το 'Μέσο Δείγμα Εικόνας'.")
            
            with expander_col4:
                 with st.expander("Χάρτης: Χρόνος Μέγιστης Εμφάνισης εντός Εύρους", expanded=True):
                    stack_for_time_max = np.where(in_range_bool_mask, stack_filt, np.nan) 
                    time_max_map = np.full(stack_for_time_max.shape[1:], np.nan, dtype=float)
                    valid_pixels_mask = ~np.all(np.isnan(stack_for_time_max), axis=0)
                    
                    if np.any(valid_pixels_mask) and filtered_dates_objects: 
                        max_indices_flat = np.nanargmax(stack_for_time_max[:, valid_pixels_mask], axis=0)
                        days_for_time_max = np.array([d.timetuple().tm_yday for d in filtered_dates_objects])
                        if len(days_for_time_max) > 0: 
                            valid_max_indices = np.clip(max_indices_flat, 0, len(days_for_time_max) - 1)
                            time_max_map[valid_pixels_mask] = days_for_time_max[valid_max_indices]

                    fig_time_max = px.imshow(time_max_map, color_continuous_scale="RdBu", 
                                             labels={"color": "Ημέρα Μέγιστης (1-365)"},
                                             color_continuous_midpoint=182,
                                             range_color=[1,365])
                    fig_time_max.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
                    st.plotly_chart(fig_time_max, use_container_width=True, key=f"fig_time_max_map{key_suffix}")
                    st.caption("Δείχνει την ημέρα του έτους που κάθε pixel είχε τη μέγιστη τιμή (εντός του εύρους).")

            st.subheader("Πρόσθετη Ανάλυση Κατανομής Ημερών εντός Εύρους")
            stack_full_in_range = (STACK >= lower_t) & (STACK <= upper_t)
            num_cols_display = 3
            
            with st.expander("Μηνιαία Κατανομή Ημερών εντός Εύρους", expanded=False):
                st.caption("Εμφανίζονται μόνο οι μήνες που έχουν επιλεγεί παραπάνω.")
                months_to_show = [m for m in range(1, 13) if m in selected_months_val]
                if not months_to_show:
                    st.info("Δεν έχουν επιλεγεί μήνες για την μηνιαία ανάλυση.")
                else:
                    cols_monthly = st.columns(num_cols_display)
                    col_idx_monthly = 0
                    for month_num in months_to_show:
                        indices_for_month = [i for i, dt_obj in enumerate(DATES) if dt_obj.month == month_num]
                        if indices_for_month:
                            monthly_sum_in_range = np.sum(stack_full_in_range[indices_for_month, :, :], axis=0)
                            month_name_disp = month_options_map[month_num]
                            fig_month_disp = px.imshow(monthly_sum_in_range, color_continuous_scale="plasma", title=month_name_disp, labels={"color": "Ημέρες"})
                            fig_month_disp.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=350)
                            fig_month_disp.update_coloraxes(showscale=False)
                            cols_monthly[col_idx_monthly].plotly_chart(fig_month_disp, use_container_width=True, key=f"fig_month_{month_num}{key_suffix}")
                            col_idx_monthly = (col_idx_monthly + 1) % num_cols_display
            
            with st.expander("Ετήσια Κατανομή Ημερών εντός Εύρους", expanded=False):
                st.caption("Εμφανίζονται μόνο τα έτη που έχουν επιλεγεί παραπάνω.")
                years_to_show = [y for y in unique_years_avail if y in selected_years_val]
                if not years_to_show:
                    st.info("Δεν έχουν επιλεγεί έτη για την ετήσια ανάλυση.")
                else:
                    cols_yearly = st.columns(num_cols_display)
                    col_idx_yearly = 0
                    for year_val in years_to_show:
                        indices_for_year = [i for i, dt_obj in enumerate(DATES) if dt_obj.year == year_val]
                        if indices_for_year:
                            yearly_sum_in_range = np.sum(stack_full_in_range[indices_for_year, :, :], axis=0)
                            fig_year_disp = px.imshow(yearly_sum_in_range, color_continuous_scale="plasma", title=f"Έτος: {year_val}", labels={"color": "Ημέρες"})
                            fig_year_disp.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=350)
                            fig_year_disp.update_coloraxes(showscale=False)
                            cols_yearly[col_idx_yearly].plotly_chart(fig_year_disp, use_container_width=True, key=f"fig_year_{year_val}{key_suffix}")
                            col_idx_yearly = (col_idx_yearly + 1) % num_cols_display

        st.markdown('</div>', unsafe_allow_html=True)

def image_navigation_ui(images_folder: str, available_dates_map: dict, 
                        session_state_key_for_idx: str, key_prefix: str,
                        show_legend: bool = False, index_name_for_legend: str = ""):
    if not available_dates_map:
        st.info("Δεν υπάρχουν διαθέσιμες εικόνες με ημερομηνία."); return None

    sorted_date_strings = sorted(available_dates_map.keys())
    
    if session_state_key_for_idx not in st.session_state:
        st.session_state[session_state_key_for_idx] = 0

    current_idx = st.session_state[session_state_key_for_idx]

    col_prev, col_select, col_next = st.columns([1,2,1])
    if col_prev.button("<< Προηγ.", key=f"{key_prefix}_prev", help="Προηγούμενη εικόνα"):
        current_idx = max(0, current_idx - 1)
        st.session_state[session_state_key_for_idx] = current_idx; st.rerun()

    if col_next.button("Επόμ. >>", key=f"{key_prefix}_next", help="Επόμενη εικόνα"):
        current_idx = min(len(sorted_date_strings) - 1, current_idx + 1)
        st.session_state[session_state_key_for_idx] = current_idx; st.rerun()
            
    def update_idx_from_select_nav(): 
        selected_val = st.session_state[f"{key_prefix}_select_nav"]
        st.session_state[session_state_key_for_idx] = sorted_date_strings.index(selected_val)

    col_select.selectbox("Επιλογή Ημερομηνίας:", options=sorted_date_strings, index=current_idx, 
                         key=f"{key_prefix}_select_nav", on_change=update_idx_from_select_nav,
                         label_visibility="collapsed")
    
    # Ensure current_idx is up-to-date after potential on_change callback
    current_idx = st.session_state[session_state_key_for_idx] 
    actual_selected_date_str = sorted_date_strings[current_idx] if current_idx < len(sorted_date_strings) else sorted_date_strings[0]

    st.caption(f"Εμφανίζεται εικόνα για: {actual_selected_date_str}")
    image_filename = available_dates_map[actual_selected_date_str]
    image_full_path = os.path.join(images_folder, image_filename)

    if os.path.exists(image_full_path):
        st.image(image_full_path, caption=f"{image_filename}", use_column_width=True)
        if show_legend and index_name_for_legend == "Χλωροφύλλη":
            st.pyplot(create_chl_legend_figure(orientation="horizontal"))
    else:
        st.error(f"Το αρχείο εικόνας δεν βρέθηκε: {image_full_path}")
    return image_full_path

def analyze_sampling_for_dashboard(sampling_points: list, first_image_data_rgb, first_image_transform,
                                   images_folder_path: str, lake_height_excel_path: str, 
                                   selected_point_names_for_plot: list | None = None):
    def _geographic_to_pixel(lon: float, lat: float, transform_matrix) -> tuple[int, int]:
        inv_transform = ~transform_matrix; px, py = inv_transform * (lon, lat); return int(px), int(py)

    def _map_rgb_to_mg(r_val: float, g_val: float, b_val: float, mg_factor: float = 2.0) -> float:
        return (g_val / 255.0) * mg_factor

    def _mg_to_color_for_plot(mg_value: float) -> str: 
        scale = [(0.00, "#0000ff"),(0.02, "#0007f2"),(0.04, "#0011de"),(0.06, "#0017d0"),
                 (0.5, "#00A0C0"), (1.0, "#FFFF00"), (1.5, "#FFA500"), 
                 (1.98, "#80007d"),(2.00, "#800080")] 
        if mg_value <= scale[0][0]: return f"rgb({int(scale[0][1][1:3],16)},{int(scale[0][1][3:5],16)},{int(scale[0][1][5:7],16)})"
        if mg_value >= scale[-1][0]: return f"rgb({int(scale[-1][1][1:3],16)},{int(scale[-1][1][3:5],16)},{int(scale[-1][1][5:7],16)})"
        for i in range(len(scale) - 1):
            lm, lc_hex = scale[i]; hm, hc_hex = scale[i+1]
            if lm <= mg_value <= hm:
                t = 0.0 if hm == lm else (mg_value - lm) / (hm - lm)
                lr,lg,lb = (int(lc_hex[j:j+2],16) for j in (1,3,5))
                hr,hg,hb = (int(hc_hex[j:j+2],16) for j in (1,3,5))
                r,g,b = (int(lr+t*(hr-lr)), int(lg+t*(hg-lg)), int(lb+t*(hb-lb)))
                return f"rgb({r},{g},{b})"
        return f"rgb(0,0,0)" 

    results_colors_dash, results_mg_dash = {n:[] for n,_,_ in sampling_points}, {n:[] for n,_,_ in sampling_points}
    if not os.path.isdir(images_folder_path):
        st.error(f"Ο φάκελος εικόνων '{images_folder_path}' δεν βρέθηκε για dashboard."); return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    for filename in sorted(os.listdir(images_folder_path)):
        if not filename.lower().endswith(('.tif', '.tiff')): continue
        m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
        if not m: continue
        try: date_obj = datetime(int(m.groups()[0]), int(m.groups()[1]), int(m.groups()[2]))
        except ValueError: continue

        try:
            with rasterio.open(os.path.join(images_folder_path, filename)) as src:
                if src.count < 3: continue
                for name, lon, lat in sampling_points:
                    col, row = _geographic_to_pixel(lon, lat, src.transform)
                    if 0 <= col < src.width and 0 <= row < src.height:
                        win = rasterio.windows.Window(col,row,1,1)
                        r,g,b = src.read(1,window=win)[0,0], src.read(2,window=win)[0,0], src.read(3,window=win)[0,0]
                        mg_v = _map_rgb_to_mg(r,g,b)
                        results_mg_dash[name].append((date_obj, mg_v))
                        results_colors_dash[name].append((date_obj, (r/255.,g/255.,b/255.)))
        except Exception as e: debug_message(f"Σφάλμα {filename} για dashboard: {e}"); continue
            
    rgb_disp = first_image_data_rgb.transpose((1,2,0))/255.
    fig_geo_d = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία Δειγματοληψίας')
    for n,lon,lat in sampling_points:
        col,row=_geographic_to_pixel(lon,lat,first_image_transform)
        fig_geo_d.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text', marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right", hovertemplate=f'<b>{n}</b><br>Lon:{lon:.4f}<br>Lat:{lat:.4f}<extra></extra>'))
    fig_geo_d.update_xaxes(visible=False); fig_geo_d.update_yaxes(visible=False,scaleanchor="x",scaleratio=1); fig_geo_d.update_layout(height=600,showlegend=True,legend_title_text="Σημεία",uirevision='dashboard_geo')

    df_h_d = pd.DataFrame(columns=['Date', 'Height']) 
    if os.path.exists(str(lake_height_excel_path)):
        try:
            df_tmp=pd.read_excel(lake_height_excel_path)
            if not df_tmp.empty and len(df_tmp.columns)>=2:
                df_h_d['Date']=pd.to_datetime(df_tmp.iloc[:,0],errors='coerce'); df_h_d['Height']=pd.to_numeric(df_tmp.iloc[:,1],errors='coerce')
                df_h_d.dropna(inplace=True); df_h_d.sort_values('Date',inplace=True)
        except Exception as e: st.warning(f"Σφάλμα ανάγνωσης στάθμης (dashboard): {e}")
            
    fig_colors_d=make_subplots(specs=[[{"secondary_y":True}]])
    pts_plot = selected_point_names_for_plot if selected_point_names_for_plot else [p[0] for p in sampling_points]
    pt_y_idx={n:i for i,n in enumerate(pts_plot)}
    for n_iter in pts_plot:
        if n_iter in results_colors_dash and results_colors_dash[n_iter]:
            d_list=sorted(results_colors_dash[n_iter],key=lambda x:x[0])
            if d_list:
                dts_c,cols_c_norm=zip(*d_list)
                cols_rgb_s=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols_c_norm]
                y_p=pt_y_idx.get(n_iter,-1)
                fig_colors_d.add_trace(go.Scatter(x=list(dts_c),y=[y_p]*len(dts_c),mode='markers',marker=dict(color=cols_rgb_s,size=10),name=n_iter,legendgroup=n_iter),secondary_y=False)
    if not df_h_d.empty: fig_colors_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='blue',width=2),legendgroup="h_grp"),secondary_y=True)
    fig_colors_d.update_layout(title='Χρώματα Pixel & Στάθμη',xaxis_title='Ημερομηνία',yaxis=dict(title='Σημεία',tickmode='array',tickvals=list(pt_y_idx.values()),ticktext=list(pt_y_idx.keys()),showgrid=False),yaxis2=dict(title='Στάθμη (m)',showgrid=True,gridcolor='rgba(128,128,128,0.2)'),showlegend=True,uirevision='dashboard_colors')

    all_mg_vals_date_d={};
    for p_n in pts_plot:
        if p_n in results_mg_dash:
            for d_obj,val_mg in results_mg_dash[p_n]: all_mg_vals_date_d.setdefault(d_obj,[]).append(val_mg)
    s_dates_mg_d=sorted(all_mg_vals_date_d.keys())
    avg_mg_d=[np.mean(all_mg_vals_date_d[d_obj]) for d_obj in s_dates_mg_d if all_mg_vals_date_d[d_obj]]
    fig_mg_d=go.Figure()
    if s_dates_mg_d and avg_mg_d: fig_mg_d.add_trace(go.Scatter(x=s_dates_mg_d,y=avg_mg_d,mode='lines+markers',name='Μέσο mg/m³',marker=dict(color=avg_mg_d,colorscale='Viridis',reversescale=True,colorbar=dict(title='mg/m³',thickness=15),size=10),line=dict(color='grey')))
    fig_mg_d.update_layout(title='Μέσο mg/m³ (Επιλεγμένα Σημεία)',xaxis_title='Ημερομηνία',yaxis_title='mg/m³',uirevision='dashboard_mg')

    fig_dual_d=make_subplots(specs=[[{"secondary_y":True}]])
    if not df_h_d.empty: 
        fig_dual_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='deepskyblue')),secondary_y=False)
    if s_dates_mg_d and avg_mg_d: 
        fig_dual_d.add_trace(go.Scatter(x=s_dates_mg_d,y=avg_mg_d,name='Μέσο mg/m³',mode='lines+markers',marker=dict(color=avg_mg_d,colorscale='Viridis',reversescale=True,size=10,showscale=False),line=dict(color='lightgreen')),secondary_y=True)
    
    fig_dual_d.update_layout(
        title='Στάθμη & Μέσο mg/m³',
        xaxis_title='Ημερομηνία',
        uirevision='dashboard_dual', 
        yaxis=dict(
            title=dict(text="Στάθμη (m)", font=dict(color="deepskyblue")), 
            tickfont=dict(color="deepskyblue"),
            side='left'
        ),
        yaxis2=dict(
            title=dict(text="mg/m³", font=dict(color="lightgreen")), 
            tickfont=dict(color="lightgreen"),
            overlaying='y', 
            side='right'
        )
    )
    
    return fig_geo_d,fig_dual_d,fig_colors_d,fig_mg_d,results_colors_dash,results_mg_dash,df_h_d

def run_water_quality_dashboard(waterbody: str, index_name: str):
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.header(f"Προφίλ Ποιότητας και Στάθμης: {waterbody} - {index_name}")
        
        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name)
        key_suffix_dash = f"_dash_{waterbody}_{clean_index_name_for_key}"

        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder: 
            st.error(f"Φάκελος δεδομένων για '{waterbody} - {index_name}' δεν βρέθηκε. Παρακαλώ ελέγξτε τις ρυθμίσεις και τη δομή των φακέλων σας.")
            st.markdown('</div>', unsafe_allow_html=True); return

        images_folder_path = os.path.join(data_folder,"GeoTIFFs")
        lake_height_excel_path = os.path.join(data_folder,"lake height.xlsx")
        default_sampling_kml_path = os.path.join(data_folder,"sampling.kml")
        
        vid_path = next((p for n in ["timelapse.mp4","timelapse.gif","Sentinel-2_L1C-202307221755611-timelapse.gif"] for p in [os.path.join(data_folder,n), os.path.join(images_folder_path,n)] if os.path.exists(p)), None)
        
        st.sidebar.subheader(f"Ρυθμίσεις Πίνακα ({index_name})")
        available_tifs = {str(d.date()):fn for fn in (os.listdir(images_folder_path) if os.path.exists(images_folder_path) else []) if fn.lower().endswith(('.tif','.tiff')) for _,d in [extract_date_from_filename(fn)] if d}
        
        first_img_rgb, first_img_transform = None, None
        if available_tifs:
            sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:", sorted(available_tifs.keys(),reverse=True), key=f"bg_date{key_suffix_dash}")
            if sel_bg_date:
                try:
                    with rasterio.open(os.path.join(images_folder_path,available_tifs[sel_bg_date])) as src:
                        if src.count>=3: first_img_rgb,first_img_transform = src.read([1,2,3]),src.transform
                        else: st.sidebar.error("Εικόνα < 3 κανάλια.")
                except Exception as e: st.sidebar.error(f"Σφάλμα φόρτωσης αναφοράς: {e}")
        else: st.sidebar.warning("Δεν βρέθηκαν GeoTIFF για εικόνα αναφοράς.")

        if first_img_rgb is None: 
            st.error("Απαιτείται έγκυρη εικόνα αναφοράς GeoTIFF για τη συνέχεια της ανάλυσης.")
            st.markdown('</div>', unsafe_allow_html=True); return

        tabs_ctrl = st.tabs(["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"])
        
        with tabs_ctrl[0]: # Default Sampling
            st.markdown("##### Ανάλυση με Προεπιλεγμένα Σημεία")
            def_pts = parse_sampling_kml(default_sampling_kml_path) if os.path.exists(default_sampling_kml_path) else []
            if def_pts:
                sel_pts_def = st.multiselect("Σημεία (Προεπιλογή):", [n for n,_,_ in def_pts], default=[n for n,_,_ in def_pts], key=f"sel_def{key_suffix_dash}")
                if st.button("Εκτέλεση (Προεπιλογή)", key=f"run_def{key_suffix_dash}", type="primary", use_container_width=True):
                    with st.spinner("Εκτέλεση ανάλυσης για προεπιλεγμένα σημεία..."): 
                        st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(def_pts,first_img_rgb,first_img_transform,images_folder_path,lake_height_excel_path,sel_pts_def)
            else: st.caption("Δεν βρέθηκε το προεπιλεγμένο αρχείο δειγματοληψίας (sampling.kml).")

            if SESSION_KEY_DEFAULT_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]:
                res=st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]
                if isinstance(res,tuple) and len(res)==7:
                    fig_g,fig_d,fig_c,fig_m,res_c_data,res_m_data,_ = res 
                    n_tabs_titles = ["GeoTIFF","Εικόνες","Video/GIF","Χρώματα Pixel","Μέσο mg/m³","Συνδυασμένο","mg/m³ ανά Σημείο"]
                    n_tabs_def_display=st.tabs(n_tabs_titles)
                    
                    with n_tabs_def_display[0]:
                        st.plotly_chart(fig_g,use_container_width=True, key=f"geo_d_chart_disp{key_suffix_dash}")
                        if index_name=="Χλωροφύλλη":st.pyplot(create_chl_legend_figure())
                    
                    with n_tabs_def_display[1]: 
                        image_navigation_ui(images_folder_path,available_tifs,SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF,f"nav_def_disp{key_suffix_dash}",index_name=="Χλωροφύλλη",index_name)
                    
                    with n_tabs_def_display[2]: 
                        if vid_path: 
                            if vid_path.endswith(".mp4"): 
                                st.video(vid_path) # ΑΦΑΙΡΕΘΗΚΕ ΤΟ KEY
                            else: 
                                st.image(vid_path) # ΑΦΑΙΡΕΘΗΚΕ ΤΟ KEY
                            if index_name=="Χλωροφύλλη":
                                st.pyplot(create_chl_legend_figure())
                        else: 
                            st.caption("Δεν βρέθηκε video/timelapse.")
                    
                    with n_tabs_def_display[3]: 
                        c1_disp,c2_disp=st.columns([.85,.15])
                        c1_disp.plotly_chart(fig_c,use_container_width=True, key=f"colors_d_chart_disp{key_suffix_dash}")
                        if index_name=="Χλωροφύλλη":
                            c2_disp.pyplot(create_chl_legend_figure("vertical"))
                    
                    with n_tabs_def_display[4]: 
                        st.plotly_chart(fig_m,use_container_width=True, key=f"mg_d_chart_disp{key_suffix_dash}")
                    
                    with n_tabs_def_display[5]: 
                        st.plotly_chart(fig_d,use_container_width=True, key=f"dual_d_chart_disp{key_suffix_dash}")
                    
                    with n_tabs_def_display[6]:
                        sel_pt_d_disp=st.selectbox("Σημείο για mg/m³:",list(res_m_data.keys()),key=f"detail_d_sel_disp{key_suffix_dash}")
                        if sel_pt_d_disp and res_m_data.get(sel_pt_d_disp): 
                            mg_d_p_list=sorted(res_m_data[sel_pt_d_disp],key=lambda x:x[0])
                            if mg_d_p_list: 
                                dts_detail,vals_detail=zip(*mg_d_p_list)
                                mk_cols_detail = px.colors.sample_colorscale("Viridis", [v/(max(vals_detail) if max(vals_detail)>0 else 1) for v in vals_detail])
                                fig_det_d_disp=go.Figure(go.Scatter(x=list(dts_detail),y=list(vals_detail),mode='lines+markers',marker=dict(color=mk_cols_detail,size=10),line=dict(color="grey"),name=sel_pt_d_disp))
                                fig_det_d_disp.update_layout(title=f"mg/m³ για {sel_pt_d_disp}",xaxis_title="Ημερομηνία",yaxis_title="mg/m³")
                                st.plotly_chart(fig_det_d_disp,use_container_width=True, key=f"detail_d_chart_disp{key_suffix_dash}")
                            else: st.caption(f"Δεν υπάρχουν επεξεργασμένα δεδομένα mg/m³ για το σημείο '{sel_pt_d_disp}'.")
                        else: st.caption(f"Επιλέξτε σημείο ή δεν υπάρχουν δεδομένα mg/m³ για το σημείο.")
                else: 
                    st.error("Σφάλμα μορφής αποτελεσμάτων (Προεπιλογή).")
        
        with tabs_ctrl[1]: # Upload KML
            st.markdown("##### Ανάλυση με Ανεβασμένο KML")
            upl_file=st.file_uploader("Ανέβασμα KML:",type="kml",key=f"upl_kml{key_suffix_dash}")
            if upl_file:
                upl_pts=parse_sampling_kml(upl_file)
                if upl_pts:
                    st.success(f"Βρέθηκαν {len(upl_pts)} σημεία.")
                    sel_pts_upl=st.multiselect("Σημεία (KML):",[n for n,_,_ in upl_pts],default=[n for n,_,_ in upl_pts],key=f"sel_upl{key_suffix_dash}")
                    if st.button("Εκτέλεση (KML)",key=f"run_upl{key_suffix_dash}",type="primary", use_container_width=True):
                        with st.spinner("Εκτέλεση..."): 
                            st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]=analyze_sampling_for_dashboard(
                                upl_pts,first_img_rgb,first_img_transform,
                                images_folder_path,lake_height_excel_path,sel_pts_upl
                            )
                else: 
                    st.error("Το KML δεν περιείχε έγκυρα σημεία ή δεν μπόρεσε να αναλυθεί.")
            
            if SESSION_KEY_UPLOAD_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]:
                res_u=st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]
                if isinstance(res_u,tuple) and len(res_u)==7: 
                    fig_g_u,fig_d_u,fig_c_u,fig_m_u,res_c_data_u,res_m_data_u,_ = res_u 
                    n_tabs_u_titles = ["GeoTIFF ","Εικόνες ","Video/GIF ","Χρώματα ","Μέσο mg/m³ ","Διπλό ","mg/m³ ανά Σημείο "]
                    n_tabs_upl_display=st.tabs(n_tabs_u_titles)
                    
                    with n_tabs_upl_display[0]: 
                        st.plotly_chart(fig_g_u,use_container_width=True, key=f"geo_u_chart_disp{key_suffix_dash}")
                        if index_name=="Χλωροφύλλη":st.pyplot(create_chl_legend_figure())
                    
                    with n_tabs_upl_display[1]: 
                        image_navigation_ui(images_folder_path,available_tifs,SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL,f"nav_upl_disp{key_suffix_dash}",index_name=="Χλωροφύλλη",index_name)
                    
                    with n_tabs_upl_display[2]:
                        if vid_path: 
                            if vid_path.endswith(".mp4"): 
                                st.video(vid_path) # ΑΦΑΙΡΕΘΗΚΕ ΤΟ KEY
                            else: 
                                st.image(vid_path) # ΑΦΑΙΡΕΘΗΚΕ ΤΟ KEY
                            if index_name=="Χλωροφύλλη":
                                st.pyplot(create_chl_legend_figure())
                        else: 
                            st.caption("Δεν βρέθηκε video/timelapse.")
                    
                    with n_tabs_upl_display[3]:
                        c1u_disp,c2u_disp=st.columns([.85,.15])
                        c1u_disp.plotly_chart(fig_c_u,use_container_width=True, key=f"colors_u_chart_disp{key_suffix_dash}")
                        if index_name=="Χλωροφύλλη":
                            c2u_disp.pyplot(create_chl_legend_figure("vertical"))
                    
                    with n_tabs_upl_display[4]: 
                        st.plotly_chart(fig_m_u,use_container_width=True, key=f"mg_u_chart_disp{key_suffix_dash}")
                    
                    with n_tabs_upl_display[5]: 
                        st.plotly_chart(fig_d_u,use_container_width=True, key=f"dual_u_chart_disp{key_suffix_dash}")
                    
                    with n_tabs_upl_display[6]:
                        sel_pt_u_disp=st.selectbox("Σημείο για mg/m³ (KML):",list(res_m_data_u.keys()),key=f"detail_u_sel_disp{key_suffix_dash}")
                        if sel_pt_u_disp and res_m_data_u.get(sel_pt_u_disp):
                            mg_d_pu_list=sorted(res_m_data_u[sel_pt_u_disp],key=lambda x:x[0])
                            if mg_d_pu_list:
                                dts_u_detail,vals_u_detail=zip(*mg_d_pu_list)
                                mk_cols_u_detail = px.colors.sample_colorscale("Viridis", [v/(max(vals_u_detail) if max(vals_u_detail)>0 else 1) for v in vals_u_detail])
                                fig_det_u_disp=go.Figure(go.Scatter(x=list(dts_u_detail),y=list(vals_u_detail),mode='lines+markers',marker=dict(color=mk_cols_u_detail,size=10),line=dict(color="grey"),name=sel_pt_u_disp))
                                fig_det_u_disp.update_layout(title=f"mg/m³ για {sel_pt_u_disp} (KML)",xaxis_title="Ημερομηνία",yaxis_title="mg/m³")
                                st.plotly_chart(fig_det_u_disp,use_container_width=True, key=f"detail_u_chart_disp{key_suffix_dash}")
                            else:
                                st.caption(f"Δεν υπάρχουν επεξεργασμένα δεδομένα mg/m³ για το σημείο '{sel_pt_u_disp}'.")
                        else: 
                            st.caption(f"Επιλέξτε σημείο ή δεν υπάρχουν δεδομένα mg/m³ για το σημείο.")
                else: 
                    st.error("Σφάλμα μορφής αποτελεσμάτων (Upload KML).")
        st.markdown('</div>', unsafe_allow_html=True)

def run_predictive_tools(waterbody: str, initial_selected_index: str):
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.header(f"Εργαλεία Πρόβλεψης & Έγκαιρης Ενημέρωσης: {waterbody}")
        st.markdown(f"Παράλληλη Ανάλυση για Δείκτες: **Πραγματικό, Χλωροφύλλη, Θολότητα**")
        
        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', initial_selected_index) # Χρήση του αρχικού δείκτη για το suffix αν χρειάζεται για μοναδικότητα εκτός βρόχου
        key_suffix_pred_section = f"_pred_tool_{waterbody}_{clean_index_name_for_key}"

        chart_display_options = {
            "GeoTIFF": "geo", 
            "Χρώματα Pixel & Στάθμη": "colors", 
            "Στάθμη Λίμνης (Μόνο)": "lake_height_only",
            "Μέσο mg/m³": "mg",
            "Συνδυασμένο (Στάθμη & Μέσο mg/m³)": "dual"
        }
        selected_charts_to_display = st.multiselect(
            "Επιλέξτε τύπους διαγραμμάτων για εμφάνιση:",
            options=list(chart_display_options.keys()),
            default=list(chart_display_options.keys()),
            key=f"select_charts{key_suffix_pred_section}"
        )

        st.subheader("Κοινές Παράμετροι Φιλτραρίσματος για όλους τους Δείκτες")
        col_filt1, col_filt2 = st.columns(2)
        with col_filt1:
            lower_thresh_common, upper_thresh_common = st.slider(
                "Εύρος τιμών pixel:", 0, 255, (0, 255), 
                key=f"thresh_common{key_suffix_pred_section}"
            )
            sampling_type_common = st.radio(
                "Σύνολο Σημείων Δειγματοληψίας:", 
                ["Προεπιλογή", "Ανέβασμα KML"], 
                key=f"sampling_type_common{key_suffix_pred_section}", 
                horizontal=True
            )
        with col_filt2:
            date_min_common = st.date_input("Ημερομηνία από:", value=date(2015, 1, 1), key=f"date_min_common{key_suffix_pred_section}")
            date_max_common = st.date_input("Ημερομηνία έως:", value=date.today(), key=f"date_max_common{key_suffix_pred_section}")

        uploaded_kml_common = None
        if sampling_type_common == "Ανέβασμα KML":
            uploaded_kml_common = st.file_uploader(
                "Ανεβάστε ένα αρχείο KML (θα χρησιμοποιηθεί για όλους τους δείκτες):", 
                type="kml", 
                key=f"kml_upload_common{key_suffix_pred_section}"
            )

        if st.button("Εκτέλεση Παράλληλης Ανάλυσης & Εμφάνιση Αποτελεσμάτων", key=f"recalc_parallel{key_suffix_pred_section}", type="primary", use_container_width=True):
            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]
            analysis_results_all_indices = {} 
            
            sampling_points_to_use = None
            if sampling_type_common == "Προεπιλογή":
                # Χρήση του KML από τον πρώτο διαθέσιμο φάκελο δείκτη ως default για όλα
                # Αυτό μπορεί να χρειαστεί προσαρμογή αν κάθε δείκτης ΠΡΕΠΕΙ να έχει το δικό του default kml
                default_kml_found = False
                for idx_for_kml in indices_to_analyze: # Προσπάθεια εύρεσης ενός default KML
                    temp_data_folder_for_kml = get_data_folder(waterbody, idx_for_kml)
                    if temp_data_folder_for_kml:
                        default_kml_path_common = os.path.join(temp_data_folder_for_kml, "sampling.kml")
                        if os.path.exists(default_kml_path_common):
                            sampling_points_to_use = parse_sampling_kml(default_kml_path_common)
                            if sampling_points_to_use:
                                default_kml_found = True
                                st.caption(f"Χρήση προεπιλεγμένου KML από τον φάκελο του δείκτη: {idx_for_kml}")
                                break 
                if not default_kml_found:
                     st.error(f"Δεν βρέθηκε προεπιλεγμένο αρχείο KML (sampling.kml) σε κανέναν από τους φακέλους των δεικτών για το {waterbody}.")
            elif sampling_type_common == "Ανέβασμα KML":
                if uploaded_kml_common:
                    sampling_points_to_use = parse_sampling_kml(uploaded_kml_common)
                else:
                    st.error("Επιλέξατε ανέβασμα KML, αλλά δεν έχει μεταφορτωθεί αρχείο.")
            
            if not sampling_points_to_use:
                st.error("Δεν ήταν δυνατός ο ορισμός των σημείων δειγματοληψίας. Η ανάλυση ακυρώνεται.")
                st.markdown('</div>', unsafe_allow_html=True); return

            all_point_names_to_use = [pt[0] for pt in sampling_points_to_use]

            with st.spinner("Εκτέλεση αναλύσεων για όλους τους δείκτες... Αυτό μπορεί να διαρκέσει λίγο."):
                for current_idx_name in indices_to_analyze:
                    progress_bar = st.progress(0, text=f"Επεξεργασία δείκτη: {current_idx_name}...")
                    
                    data_folder_idx = get_data_folder(waterbody, current_idx_name)
                    if not data_folder_idx:
                        analysis_results_all_indices[current_idx_name] = {"error": f"Δεν βρέθηκε φάκελος δεδομένων."}
                        st.warning(f"Παράλειψη '{current_idx_name}': Δεν βρέθηκε φάκελος δεδομένων.")
                        progress_bar.progress(100, text=f"Παράλειψη δείκτη: {current_idx_name} (δεν βρέθηκε φάκελος)")
                        continue

                    images_folder_idx = os.path.join(data_folder_idx, "GeoTIFFs")
                    lake_height_excel_idx = os.path.join(data_folder_idx, "lake height.xlsx")
                    
                    tif_files_idx = sorted(glob.glob(os.path.join(images_folder_idx, "*.tif")))
                    if not tif_files_idx:
                        analysis_results_all_indices[current_idx_name] = {"error": "Δεν βρέθηκαν αρχεία GeoTIFF."}
                        st.warning(f"Παράλειψη '{current_idx_name}': Δεν βρέθηκαν αρχεία GeoTIFF.")
                        progress_bar.progress(100, text=f"Παράλειψη δείκτη: {current_idx_name} (δεν βρέθηκαν GeoTIFFs)")
                        continue

                    first_img_data_idx, first_transform_idx = None, None
                    try:
                        with rasterio.open(tif_files_idx[0]) as src:
                            if src.count < 3:
                                analysis_results_all_indices[current_idx_name] = {"error": "Η 1η εικόνα GeoTIFF δεν έχει 3 κανάλια."}
                                st.warning(f"Παράλειψη '{current_idx_name}': Η 1η εικόνα GeoTIFF δεν έχει 3 κανάλια.")
                                progress_bar.progress(100, text=f"Παράλειψη δείκτη: {current_idx_name} (σφάλμα εικόνας)")
                                continue
                            first_img_data_idx = src.read([1,2,3])
                            first_transform_idx = src.transform
                    except Exception as e:
                        analysis_results_all_indices[current_idx_name] = {"error": f"Σφάλμα φόρτωσης 1ης εικόνας GeoTIFF: {e}"}
                        st.warning(f"Παράλειψη '{current_idx_name}': Σφάλμα φόρτωσης 1ης εικόνας GeoTIFF.")
                        progress_bar.progress(100, text=f"Παράλειψη δείκτη: {current_idx_name} (σφάλμα φόρτωσης εικόνας)")
                        continue
                    
                    try:
                        figs = analyze_sampling_generic(
                            sampling_points=sampling_points_to_use,
                            first_image_data=first_img_data_idx,
                            first_transform=first_transform_idx,
                            images_folder=images_folder_idx,
                            lake_height_path=lake_height_excel_idx,
                            selected_points_names=all_point_names_to_use,
                            lower_thresh=lower_thresh_common,
                            upper_thresh=upper_thresh_common,
                            date_min=date_min_common,
                            date_max=date_max_common
                        )
                        analysis_results_all_indices[current_idx_name] = {
                            "geo": figs[0], "dual": figs[1], "colors": figs[2], "mg": figs[3], "df_h": figs[6]
                        }
                        progress_bar.progress(100, text=f"Ολοκληρώθηκε: {current_idx_name}")
                    except Exception as e_analyze:
                        analysis_results_all_indices[current_idx_name] = {"error": f"Σφάλμα κατά την ανάλυση: {e_analyze}"}
                        st.warning(f"Σφάλμα κατά την ανάλυση του δείκτη '{current_idx_name}'.")
                        progress_bar.progress(100, text=f"Σφάλμα ανάλυσης: {current_idx_name}")
                
                # Αποθήκευση των αποτελεσμάτων στο session state για να μην χαθούν αν αλλάξει κάτι άλλο
                st.session_state[f"predictive_tool_results{key_suffix_pred_section}"] = analysis_results_all_indices
                st.session_state[f"predictive_tool_selected_charts{key_suffix_pred_section}"] = selected_charts_to_display
                st.success("Όλες οι αναλύσεις ολοκληρώθηκαν!")


        # Εμφάνιση αποτελεσμάτων (αν υπάρχουν στο session state)
        if f"predictive_tool_results{key_suffix_pred_section}" in st.session_state:
            analysis_results_all_indices = st.session_state[f"predictive_tool_results{key_suffix_pred_section}"]
            charts_to_show_from_session = st.session_state.get(f"predictive_tool_selected_charts{key_suffix_pred_section}", [])
            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]

            st.markdown("---")
            st.subheader("Αποτελέσματα Παράλληλης Ανάλυσης")

            for chart_name_key, fig_internal_key in chart_display_options.items():
                if chart_name_key not in charts_to_show_from_session:
                    continue

                st.markdown(f"#### {chart_name_key}")

                if chart_name_key == "Χρώματα Pixel & Στάθμη":
                    # Ειδική διάταξη: το ένα κάτω από το άλλο, πλήρες πλάτος
                    for idx_name_iter in indices_to_analyze:
                        with st.container():
                            st.markdown(f"##### {idx_name_iter}")
                            result_for_idx = analysis_results_all_indices.get(idx_name_iter, {})
                            
                            if "error" in result_for_idx:
                                st.error(f"{idx_name_iter}: {result_for_idx['error']}")
                                continue

                            fig_to_plot = result_for_idx.get(fig_internal_key) # "colors"

                            if fig_to_plot:
                                fig_to_plot.update_layout(height=500, uirevision=f"{fig_internal_key}_{idx_name_iter}_full{key_suffix_pred_section}") 
                                st.plotly_chart(fig_to_plot, use_container_width=True, key=f"chart_{fig_internal_key}_{idx_name_iter}_full{key_suffix_pred_section}")
                                # Για το "Χρώματα Pixel & Στάθμη", το υπόμνημα χλωροφύλλης δεν είναι άμεσα σχετικό
                            else:
                                st.caption(f"Δεν υπάρχουν δεδομένα για '{chart_name_key}' ({idx_name_iter}).")
                        st.markdown("---" if idx_name_iter != indices_to_analyze[-1] else "") # Διαχωριστικό μεταξύ δεικτών
                else:
                    # Κανονική διάταξη 3 στηλών για τους άλλους τύπους γραφημάτων
                    inner_cols = st.columns(len(indices_to_analyze)) 
                    for i, idx_name_iter in enumerate(indices_to_analyze):
                        with inner_cols[i]:
                            st.markdown(f"##### {idx_name_iter}")
                            result_for_idx = analysis_results_all_indices.get(idx_name_iter, {})
                            
                            if "error" in result_for_idx:
                                st.error(result_for_idx["error"])
                                continue

                            fig_to_plot = None
                            if fig_internal_key == "lake_height_only":
                                fig_dual_source = result_for_idx.get("dual")
                                if fig_dual_source and hasattr(fig_dual_source, 'data') and fig_dual_source.data:
                                    height_trace = next((trace for trace in fig_dual_source.data if hasattr(trace, 'name') and trace.name == 'Στάθμη Λίμνης'), None)
                                    if height_trace:
                                        df_h_data = result_for_idx.get("df_h")
                                        title_text = "Στάθμη Λίμνης"
                                        if df_h_data is not None and not df_h_data.empty:
                                             title_text = f"Στάθμη Λίμνης ({idx_name_iter})"
                                        else:
                                             title_text = f"Στάθμη Λίμνης ({idx_name_iter} - Δεν βρέθηκαν δεδομένα Excel)"

                                        fig_to_plot = go.Figure([height_trace]).update_layout(title=title_text, height=400)
                                else:
                                    st.caption(f"Δεν βρέθηκε trace στάθμης για {idx_name_iter}.")
                            else:
                                fig_to_plot = result_for_idx.get(fig_internal_key)

                            if fig_to_plot:
                                fig_to_plot.update_layout(height=400, uirevision=f"{fig_internal_key}_{idx_name_iter}_col{key_suffix_pred_section}") 
                                st.plotly_chart(fig_to_plot, use_container_width=True, key=f"chart_{fig_internal_key}_{idx_name_iter}_col{key_suffix_pred_section}")
                                if fig_internal_key == "geo" and idx_name_iter == "Χλωροφύλλη":
                                    st.pyplot(create_chl_legend_figure(orientation="horizontal"))
                            elif fig_internal_key != "lake_height_only": # Μην εμφανίζεις μήνυμα αν το lake_height_only απέτυχε λόγω έλλειψης trace
                                st.caption(f"Δεν υπάρχουν δεδομένα για '{chart_name_key}'.")
                st.markdown("""<hr style="border:1px solid #444; margin-top:1.5rem; margin-bottom:1.5rem;">""", unsafe_allow_html=True) # Πιο έντονο διαχωριστικό

        st.markdown('</div>', unsafe_allow_html=True)
def main_app():
    inject_custom_css() 
    run_intro_page_custom() 
    run_custom_sidebar_ui_custom() 

    selected_wb = st.session_state.get(SESSION_KEY_WATERBODY)
    selected_idx = st.session_state.get(SESSION_KEY_INDEX)
    selected_an = st.session_state.get(SESSION_KEY_ANALYSIS)

    if not all([selected_wb, selected_idx, selected_an]):
        render_footer() 
        return 

    if selected_wb == "Γαδουρά" and selected_idx in ["Χλωροφύλλη", "Πραγματικό", "Θολότητα"]:
        if selected_an == "Επιφανειακή Αποτύπωση":
            run_lake_processing_app(selected_wb, selected_idx)
        elif selected_an == "Προφίλ ποιότητας και στάθμης":
            run_water_quality_dashboard(selected_wb, selected_idx)
        elif selected_an == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
            run_predictive_tools(selected_wb, selected_idx)
    else:
        st.warning(f"Δεν υπάρχουν διαθέσιμες αναλύσεις ή δεδομένα για τον συνδυασμό: "
                   f"Υδάτινο Σώμα '{selected_wb}' και Δείκτης '{selected_idx}'. "
                   f"Παρακαλώ δοκιμάστε έναν άλλο συνδυασμό.")
    
    render_footer() 

if __name__ == "__main__":
    main_app()