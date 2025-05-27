#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

import streamlit as st
import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET
import io

import numpy as np
import pandas as pd
import rasterio
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

def add_excel_download_button(df_or_dict_of_dfs, filename_prefix: str, button_label_suffix: str, plot_key: str):
    if df_or_dict_of_dfs is None:
        debug_message(f"No data provided for Excel export: {button_label_suffix}")
        return

    is_empty_df = isinstance(df_or_dict_of_dfs, pd.DataFrame) and df_or_dict_of_dfs.empty
    is_empty_dict = False
    if isinstance(df_or_dict_of_dfs, dict):
        if not df_or_dict_of_dfs:
            is_empty_dict = True
        else:
            all_dfs_in_dict_empty = True
            for df_item in df_or_dict_of_dfs.values():
                if isinstance(df_item, pd.DataFrame) and not df_item.empty:
                    all_dfs_in_dict_empty = False
                    break
            if all_dfs_in_dict_empty:
                is_empty_dict = True

    if is_empty_df or is_empty_dict:
        debug_message(f"Empty data provided for Excel export: {button_label_suffix}")
        return

    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if isinstance(df_or_dict_of_dfs, pd.DataFrame):
                df_or_dict_of_dfs.to_excel(writer, index=False, sheet_name='Data')
            elif isinstance(df_or_dict_of_dfs, dict):
                for sheet_name, data_df in df_or_dict_of_dfs.items():
                    if isinstance(data_df, pd.DataFrame) and not data_df.empty:
                        sane_sheet_name = re.sub(r'[^a-zA-Z0-9_]', '', str(sheet_name))[:31]
                        data_df.to_excel(writer, index=False, sheet_name=sane_sheet_name)
        excel_data = output.getvalue()
        if not excel_data:
            debug_message(f"No data written to Excel buffer for: {button_label_suffix}")
            return

        file_name_suffix = button_label_suffix.lower().replace(' ', '_').replace('/', '_').replace('&', 'and').replace('(', '').replace(')', '')
        st.download_button(
            label=f"📥 Save {button_label_suffix} to Excel",
            data=excel_data,
            file_name=f"{filename_prefix}_{file_name_suffix}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key=f"download_{plot_key}"
        )
    except Exception as e:
        st.warning(f"Could not generate Excel file for {button_label_suffix}: {e}")
        debug_message(f"Excel generation error for {button_label_suffix}: {e}")

def render_footer():
    st.markdown(f""
        <hr style="border-color: #2a2e37;">
        <div class='footer'>
            &copy; {datetime.now().year} EYATH SA • Powered by Google Gemini & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
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
            st.markdown(f"""
                <h2 class='header-title'>Εφαρμογή Ανάλυσης Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ</h2>
                <p style='font-size:1.15rem;text-align:center; line-height:1.6;'>
                Καλωσήρθατε στην εφαρμογή ανάλυσης ποιότητας υδάτων ΕΥΑΘ ΑΕ!<br>
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
        if hasattr(kml_source, "seek"):
            kml_source.seek(0)
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
                    except ValueError:
                        debug_message(f"Warning: KML: Παράλειψη συντεταγμένης '{coord_str}'")
        if not points and kml_source:  # Check if kml_source was provided but no points found
            st.warning("Δεν βρέθηκαν σημεία LineString στο KML.")
        return points
    except FileNotFoundError:
        debug_message(f"Προειδοποίηση: Το αρχείο KML '{kml_source}' δεν βρέθηκε.")
        return []
    except Exception as e:
        st.error(f"Σφάλμα ανάλυσης KML '{kml_source}': {e}")
        return []

@st.cache_data
def get_data_folder(waterbody: str, index_name: str) -> str | None:
    waterbody_folder_name = WATERBODY_FOLDERS.get(waterbody)
    if not waterbody_folder_name:
        st.error(f"Δεν έχει οριστεί αντιστοίχιση φακέλου για το υδάτινο σώμα: '{waterbody}'.")
        return None

    index_specific_folder = ""
    if index_name == "Πραγματικό":
        index_specific_folder = "Πραγματικό"
    elif index_name == "Χλωροφύλλη":
        index_specific_folder = "Chlorophyll"
    elif index_name == "Θολότητα":
        index_specific_folder = "Θολότητα"
    else:
        index_specific_folder = index_name  # Fallback

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
            points_to_return.append(points_to_return[0]) # Close the polygon

        debug_message(f"DEBUG: Φορτώθηκαν {len(points_to_return)} σημεία περιγράμματος.")
        return {"type": "Polygon", "coordinates": [points_to_return]}
    except FileNotFoundError:
        st.error(f"Το αρχείο XML περιγράμματος δεν βρέθηκε: {xml_file_path}"); return None
    except Exception as e:
        st.error(f"Σφάλμα φόρτωσης περιγράμματος από {os.path.basename(xml_file_path)}: {e}"); return None

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

    # Apply theme colors if provided
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
                        mg_val = (g / 255.0) * 2.0 # Placeholder conversion
                        results_mg[name].append((date_obj, mg_val))
                        results_colors[name].append((date_obj, (r/255., g/255., b/255.)))
                    except IndexError: debug_message(f"Σφάλμα Index pixel για {name} στο {filename}.")
        except Exception as e: st.warning(f"Σφάλμα επεξεργασίας {filename}: {e}")

    # Ensure first_image_data is suitable for px.imshow (e.g., 3 bands, normalized)
    if first_image_data is None or first_image_data.ndim != 3 or first_image_data.shape[0] < 3:
        st.error("Μη έγκυρα δεδομένα πρώτης εικόνας για εμφάνιση.")
        return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    rgb_disp = first_image_data[:3, :, :].transpose((1,2,0)) # Use first 3 bands
    if rgb_disp.max() > 1.0: # Normalize if not already in 0-1 range
        rgb_disp = rgb_disp / 255.0
    rgb_disp = np.clip(rgb_disp, 0, 1)

    fig_geo = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία'); fig_geo.update_layout(height=600, uirevision='geo')
    if first_transform: # Ensure transform is available
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

    fig_colors = make_subplots(specs=[[{"secondary_y":True}]])
    pt_y_map={n:i for i,n in enumerate(selected_points_names)}
    for n_iter in selected_points_names:
        if n_iter in results_colors and results_colors[n_iter]:
            dts,cols=zip(*sorted(results_colors[n_iter],key=lambda x:x[0])) if results_colors[n_iter] else ([],[])
            c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
            fig_colors.add_trace(go.Scatter(x=list(dts),y=[pt_y_map.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
    if not df_h.empty: fig_colors.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη',mode='lines',line=dict(color='blue')),secondary_y=True)
    fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη',yaxis=dict(tickmode='array',tickvals=list(pt_y_map.values()),ticktext=list(pt_y_map.keys())),yaxis2=dict(title='Στάθμη (m)'), uirevision='colors')

    all_mg_by_d={}
    for p_name in selected_points_names:
        if p_name in results_mg:
            for d,v in results_mg[p_name]: all_mg_by_d.setdefault(d,[]).append(v)
    s_dts_mg=sorted(all_mg_by_d.keys())
    mean_mg=[np.mean(all_mg_by_d[d]) for d in s_dts_mg if all_mg_by_d[d]]
    fig_mg=go.Figure()
    if s_dts_mg and mean_mg: fig_mg.add_trace(go.Scatter(x=s_dts_mg,y=mean_mg,mode='lines+markers',marker=dict(color=mean_mg,colorscale='Viridis',colorbar=dict(title='mg/m³'),size=8)))
    fig_mg.update_layout(title='Μέσο mg/m³', uirevision='mg')

    fig_dual=make_subplots(specs=[[{"secondary_y":True}]])
    if not df_h.empty: fig_dual.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη Λίμνης',mode='lines'),secondary_y=False)
    if s_dts_mg and mean_mg: fig_dual.add_trace(go.Scatter(x=s_dts_mg,y=mean_mg,name='Μέσο mg/m³',mode='lines+markers', marker=dict(color=mean_mg, colorscale='Viridis', showscale=False)),secondary_y=True)
    fig_dual.update_layout(title='Στάθμη & Μέσο mg/m³', uirevision='dual',
                            yaxis=dict(title=dict(text="Στάθμη (m)",font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"), side='left'),
                            yaxis2=dict(title=dict(text="Μέσο mg/m³",font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"), overlaying='y', side='right'))
    return fig_geo,fig_dual,fig_colors,fig_mg,results_colors,results_mg,df_h

# Main app logic
if __name__ == "__main__":
    inject_custom_css()
    run_intro_page_custom()
    run_custom_sidebar_ui_custom()
    render_footer()
