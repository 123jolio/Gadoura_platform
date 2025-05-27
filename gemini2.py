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
import io

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

import streamlit_authenticator as stauth # <--- Προσθήκη για αυθεντικοποίηση

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ", page_icon="💧")
# --------------------------------------------------------------------

# --- AUTHENTICATION SETUP ---

# --- STEP 2: Define your users and their credentials ---
names = ["Ilioumbas User"]  # Display name for your user
usernames = ["ilioumbas"]   # Username for login
plain_text_passwords = ["123"] # <--- YOUR SINGLE PLAIN TEXT PASSWORD FOR 'ilioumbas'

# --- STEP 3 (Τροποποιημένο): Create credentials dictionary using PLAIN TEXT passwords ---
credentials = {"usernames": {}}
if len(names) == len(usernames) == len(plain_text_passwords): # Basic check
    for i in range(len(usernames)):
        credentials["usernames"][usernames[i]] = {
            "name": names[i],
            "password": plain_text_passwords[i]
        }
else:
    st.error("Error: The lists for names, usernames, and plain_text_passwords must have the same number of items.")
    st.stop()

# --- STEP 4: Initialize the Authenticator ---
authenticator = None
try:
    authenticator = stauth.Authenticate(
        credentials,
        "water_quality_app_cookie_v8", # Changed cookie name again
        "a_very_random_secret_key_v8", # Changed key again
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Error during stauth.Authenticate initialization: {e}")
    st.stop()
# --- END OF AUTHENTICATION SETUP ---

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
                        sane_sheet_name = re.sub(r'[\[\]\*\/\\?\:\']', '_', str(sheet_name))[:31]
                        data_df.to_excel(writer, index=False, sheet_name=sane_sheet_name)
                    elif isinstance(data_df, pd.DataFrame) and data_df.empty:
                        debug_message(f"Empty DataFrame for sheet '{sheet_name}' in Excel export: {button_label_suffix}")
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
    st.markdown(f"""
        <hr style="border-color: #2a2e37;">
        <div class='footer'>
            © {datetime.now().year} EYATH SA • Powered by Google Gemini & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
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
            user_name_display = st.session_state.get("name", "Επισκέπτη")
            st.markdown(f"""
                <h2 class='header-title'>Εφαρμογή Ανάλυσης Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ</h2>
                <p style='font-size:1.15rem;text-align:center; line-height:1.6;'>
                Καλωσήρθατε, <strong>{user_name_display}</strong>!<br>
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
    global authenticator
    if authenticator and st.session_state.get("authentication_status"):
        st.sidebar.success(f"Συνδεθήκατε ως: {st.session_state.get('name', 'N/A')}")
        authenticator.logout("Αποσύνδεση", "sidebar", key='unique_logout_button_key')
        st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    st.sidebar.markdown("<div class='nav-section'><h4>🛠️ Επιλογές Ανάλυσης</h4></div>", unsafe_allow_html=True)
    st.sidebar.info("❔ Επιλέξτε τις ρυθμίσεις σας και προχωρήστε στα αποτελέσματα!")

    waterbody_options = list(WATERBODY_FOLDERS.keys())
    default_wb_idx = 0 if waterbody_options else None

    waterbody = st.sidebar.selectbox("🌊 Υδάτινο σώμα", waterbody_options, index=default_wb_idx, key=SESSION_KEY_WATERBODY)
    index_name = st.sidebar.selectbox("🔬 Δείκτης", ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"], key=SESSION_KEY_INDEX)
    
    # --- MODIFIED: Removed "Επιφανειακή Αποτύπωση" from options ---
    analysis_type = st.sidebar.selectbox( "📊 Είδος Ανάλυσης",
        ["Προφίλ ποιότητας και στάθμης", "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"],
        key=SESSION_KEY_ANALYSIS
    )
    # --- END OF MODIFICATION ---

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
        if not points and kml_source:
                st.warning("Δεν βρέθηκαν σημεία LineString στο KML.")
        return points
    except FileNotFoundError:
        debug_message(f"Προειδοποίηση: Το αρχείο KML '{kml_source}' δεν βρέθηκε.")
        return []
    except Exception as e:
        st.error(f"Σφάλμα ανάλυσης KML '{kml_source}': {e}")
        return []

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

    if first_image_data is None or first_image_data.ndim != 3 or first_image_data.shape[0] < 3:
        st.error("Μη έγκυρα δεδομένα πρώτης εικόνας για εμφάνιση.")
        return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    rgb_disp = first_image_data[:3, :, :].transpose((1,2,0))
    if rgb_disp.max() > 1.0:
        rgb_disp = rgb_disp / 255.0
    rgb_disp = np.clip(rgb_disp, 0, 1)


    fig_geo = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία'); fig_geo.update_layout(height=600, uirevision='geo')
    if first_transform:
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
    if not df_h.empty: fig_dual.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη Λίμνης',mode='lines'),secondary_y=False)
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
                poly_mask = geometry_mask([lake_shape], transform=src.transform, invert=True, out_shape=img.shape)
                img = np.where(poly_mask, img, np.nan)
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


# --- REMOVED: def run_lake_processing_app(waterbody: str, index_name: str): ---
# The entire function for "Επιφανειακή Αποτύπωση" has been removed.
# If you need a placeholder or a message for this removed module, 
# you could define a simple function like this:
#
# def run_lake_processing_app_removed(waterbody: str, index_name: str):
#     with st.container():
#         st.markdown('<div class="card">', unsafe_allow_html=True)
#         st.header(f"Επιφανειακή Αποτύπωση: {waterbody} - {index_name}")
#         st.warning("Αυτή η ενότητα ανάλυσης ('Επιφανειακή Αποτύπωση') έχει απενεργοποιηθεί προσωρινά.")
#         st.info("Παρακαλώ επιλέξτε μια άλλη 'Είδος Ανάλυσης' από την πλαϊνή μπάρα.")
#         st.markdown('</div>', unsafe_allow_html=True)
#
# And then call run_lake_processing_app_removed in main_app if selected.
# For now, it's completely removed as per the request to "remove all the module".


def image_navigation_ui(images_folder: str, available_dates_map: dict,
                        session_state_key_for_idx: str, key_prefix: str,
                        show_legend: bool = False, index_name_for_legend: str = ""):
    if not available_dates_map:
        st.info("Δεν υπάρχουν διαθέσιμες εικόνες με ημερομηνία."); return None

    sorted_date_strings = sorted(available_dates_map.keys())

    if session_state_key_for_idx not in st.session_state:
        st.session_state[session_state_key_for_idx] = 0

    current_idx = st.session_state[session_state_key_for_idx]
    if current_idx >= len(sorted_date_strings):
        current_idx = 0
        st.session_state[session_state_key_for_idx] = current_idx


    col_prev, col_select, col_next = st.columns([1,2,1])
    if col_prev.button("<< Προηγ.", key=f"{key_prefix}_prev", help="Προηγούμενη εικόνα", use_container_width=True):
        current_idx = max(0, current_idx - 1)
        st.session_state[session_state_key_for_idx] = current_idx; st.rerun()

    if col_next.button("Επόμ. >>", key=f"{key_prefix}_next", help="Επόμενη εικόνα", use_container_width=True):
        current_idx = min(len(sorted_date_strings) - 1, current_idx + 1)
        st.session_state[session_state_key_for_idx] = current_idx; st.rerun()

    def update_idx_from_select_nav():
        selected_val = st.session_state[f"{key_prefix}_select_nav"]
        if selected_val in sorted_date_strings:
                st.session_state[session_state_key_for_idx] = sorted_date_strings.index(selected_val)

    col_select.selectbox("Επιλογή Ημερομηνίας:", options=sorted_date_strings, index=current_idx,
                        key=f"{key_prefix}_select_nav", on_change=update_idx_from_select_nav,
                        label_visibility="collapsed")

    current_idx = st.session_state[session_state_key_for_idx]
    actual_selected_date_str = sorted_date_strings[current_idx]

    st.caption(f"Εμφανίζεται εικόνα για: {actual_selected_date_str}")
    image_filename = available_dates_map[actual_selected_date_str]
    image_full_path = os.path.join(images_folder, image_filename)

    if os.path.exists(image_full_path):
        st.image(image_full_path, caption=f"{image_filename}", use_column_width=True)
        if show_legend and index_name_for_legend == "Χλωροφύλλη":
            try:
                theme_bg = st.get_option("theme.backgroundColor")
                theme_text = st.get_option("theme.textColor")
                legend_fig = create_chl_legend_figure(orientation="horizontal", theme_bg_color=theme_bg, theme_text_color=theme_text)
            except:
                legend_fig = create_chl_legend_figure(orientation="horizontal")
            st.pyplot(legend_fig)
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
                        pixel_data = src.read([1,2,3], window=win)
                        r,g,b = pixel_data[0,0,0], pixel_data[1,0,0], pixel_data[2,0,0]

                        mg_v = _map_rgb_to_mg(r,g,b)
                        results_mg_dash[name].append((date_obj, mg_v))
                        results_colors_dash[name].append((date_obj, (r/255.,g/255.,b/255.)))
        except Exception as e: debug_message(f"Σφάλμα {filename} για dashboard: {e}"); continue

    if first_image_data_rgb is None or first_image_transform is None:
        st.error("Δεδομένα εικόνας αναφοράς (first_image_data_rgb / first_image_transform) δεν είναι διαθέσιμα.")
        return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    rgb_disp_data = first_image_data_rgb.transpose((1,2,0))
    if rgb_disp_data.max() > 1:
        rgb_disp_data = rgb_disp_data / 255.0
    rgb_disp_data = np.clip(rgb_disp_data, 0, 1)

    fig_geo_d = px.imshow(rgb_disp_data, title='Εικόνα Αναφοράς & Σημεία Δειγματοληψίας')
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
                if y_p != -1:
                    fig_colors_d.add_trace(go.Scatter(x=list(dts_c),y=[y_p]*len(dts_c),mode='markers',marker=dict(color=cols_rgb_s,size=10),name=n_iter,legendgroup=n_iter),secondary_y=False)

    if not df_h_d.empty: fig_colors_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='blue',width=2),legendgroup="h_grp"),secondary_y=True)
    fig_colors_d.update_layout(title='Χρώματα Pixel & Στάθμη',xaxis_title='Ημερομηνία',
                                yaxis=dict(title='Σημεία',tickmode='array',tickvals=list(pt_y_idx.values()),ticktext=list(pt_y_idx.keys()),showgrid=False),
                                yaxis2=dict(title='Στάθμη (m)',showgrid=True,gridcolor='rgba(128,128,128,0.2)'),showlegend=True,uirevision='dashboard_colors')

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
        yaxis=dict(title=dict(text="Στάθμη (m)", font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"),side='left'),
        yaxis2=dict(title=dict(text="mg/m³", font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"),overlaying='y', side='right')
    )

    return fig_geo_d,fig_dual_d,fig_colors_d,fig_mg_d,results_colors_dash,results_mg_dash,df_h_d


def run_water_quality_dashboard(waterbody: str, index_name: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Προφίλ Ποιότητας και Στάθμης: {waterbody} - {index_name}")

        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name)
        key_suffix_dash = f"_dash_{waterbody}_{clean_index_name_for_key}"
        common_filename_prefix_dash = f"{waterbody}_{index_name}"

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
            sel_bg_date_options = sorted(available_tifs.keys(),reverse=True)
            sel_bg_date_index = 0 if sel_bg_date_options else None

            sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:", sel_bg_date_options, index=sel_bg_date_index, key=f"bg_date{key_suffix_dash}")
            if sel_bg_date and available_tifs.get(sel_bg_date):
                try:
                    with rasterio.open(os.path.join(images_folder_path,available_tifs[sel_bg_date])) as src:
                        if src.count>=3: first_img_rgb,first_img_transform = src.read([1,2,3]),src.transform
                        else: st.sidebar.error("Εικόνα < 3 κανάλια.")
                except Exception as e: st.sidebar.error(f"Σφάλμα φόρτωσης αναφοράς: {e}")
        else: st.sidebar.warning("Δεν βρέθηκαν GeoTIFF για εικόνα αναφοράς.")

        if first_img_rgb is None:
            st.error("Απαιτείται έγκυρη εικόνα αναφοράς GeoTIFF (τουλάχιστον 3 κανάλια) για τη συνέχεια της ανάλυσης.")
            st.markdown('</div>', unsafe_allow_html=True); return

        tabs_ctrl = st.tabs(["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"])

        with tabs_ctrl[0]: # Default Sampling
            st.markdown("##### Ανάλυση με Προεπιλεγμένα Σημεία")
            def_pts_list = parse_sampling_kml(default_sampling_kml_path) if os.path.exists(default_sampling_kml_path) else []
            st.session_state[f"def_pts_list{key_suffix_dash}"] = def_pts_list

            if def_pts_list:
                all_def_point_names = [n for n,_,_ in def_pts_list]
                default_selection = all_def_point_names[:]

                sel_pts_def_names = st.multiselect("Σημεία (Προεπιλογή):", all_def_point_names, default=default_selection, key=f"sel_def{key_suffix_dash}")
                st.session_state[f"sel_pts_def_names{key_suffix_dash}"] = sel_pts_def_names
                if st.button("Εκτέλεση (Προεπιλογή)", key=f"run_def{key_suffix_dash}", type="primary", use_container_width=True):
                    with st.spinner("Εκτέλεση ανάλυσης για προεπιλεγμένα σημεία..."):
                        st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                            def_pts_list, first_img_rgb, first_img_transform, images_folder_path, lake_height_excel_path, sel_pts_def_names
                        )
            else: st.caption("Δεν βρέθηκε το προεπιλεγμένο αρχείο δειγματοληψίας (sampling.kml).")

            if SESSION_KEY_DEFAULT_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]:
                res_def = st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]
                current_def_pts_list = st.session_state.get(f"def_pts_list{key_suffix_dash}", [])
                current_sel_pts_def_names_for_plot = st.session_state.get(f"sel_pts_def_names{key_suffix_dash}", [p[0] for p in current_def_pts_list])


                if isinstance(res_def, tuple) and len(res_def) == 7:
                    fig_g, fig_d, fig_c, fig_m, res_c_data, res_m_data, df_h_data = res_def

                    n_tabs_titles = ["GeoTIFF","Εικόνες","Video/GIF","Χρώματα Pixel","Μέσο mg/m³","Συνδυασμένο","mg/m³ ανά Σημείο"]
                    n_tabs_def_display = st.tabs(n_tabs_titles)
                    tab_prefix_key = f"def_tab_{key_suffix_dash}"

                    with n_tabs_def_display[0]:
                        st.plotly_chart(fig_g, use_container_width=True, key=f"geo_d_chart_disp_{tab_prefix_key}")
                        if current_def_pts_list:
                            points_to_export_df = pd.DataFrame(
                                [pt for pt in current_def_pts_list if pt[0] in current_sel_pts_def_names_for_plot],
                                columns=['PointName', 'Longitude', 'Latitude']
                            ) if current_sel_pts_def_names_for_plot else pd.DataFrame(current_def_pts_list, columns=['PointName', 'Longitude', 'Latitude'])

                            if not points_to_export_df.empty:
                                add_excel_download_button(points_to_export_df, f"{common_filename_prefix_dash}_default", "Sampling Points", f"excel_geo_def_{tab_prefix_key}")
                        if index_name == "Χλωροφύλλη":
                            try:
                                theme_bg = st.get_option("theme.backgroundColor")
                                theme_text = st.get_option("theme.textColor")
                                st.pyplot(create_chl_legend_figure(theme_bg_color=theme_bg, theme_text_color=theme_text))
                            except:
                                st.pyplot(create_chl_legend_figure())

                    with n_tabs_def_display[1]:
                        image_navigation_ui(images_folder_path,available_tifs,SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF,f"nav_def_disp_{key_suffix_dash}",index_name=="Χλωροφύλλη",index_name)
                    with n_tabs_def_display[2]:
                        if vid_path:
                            if vid_path.endswith(".mp4"): st.video(vid_path)
                            else: st.image(vid_path)
                            if index_name=="Χλωροφύλλη":
                                try:
                                    theme_bg = st.get_option("theme.backgroundColor")
                                    theme_text = st.get_option("theme.textColor")
                                    st.pyplot(create_chl_legend_figure(theme_bg_color=theme_bg, theme_text_color=theme_text))
                                except:
                                    st.pyplot(create_chl_legend_figure())
                        else: st.caption("Δεν βρέθηκε video/timelapse.")

                    with n_tabs_def_display[3]:
                        c1_disp,c2_disp=st.columns([.85,.15])
                        c1_disp.plotly_chart(fig_c, use_container_width=True, key=f"colors_d_chart_disp_{tab_prefix_key}")
                        excel_sheets_colors = {}
                        if isinstance(df_h_data, pd.DataFrame) and not df_h_data.empty:
                            excel_sheets_colors['LakeHeight'] = df_h_data.copy()
                        if res_c_data:
                            for point_name, data_list in res_c_data.items():
                                if data_list and (point_name in current_sel_pts_def_names_for_plot):
                                    df_point_colors = pd.DataFrame(data_list, columns=['Date', 'RGB_Normalized'])
                                    df_point_colors['R_norm'] = df_point_colors['RGB_Normalized'].apply(lambda x: x[0])
                                    df_point_colors['G_norm'] = df_point_colors['RGB_Normalized'].apply(lambda x: x[1])
                                    df_point_colors['B_norm'] = df_point_colors['RGB_Normalized'].apply(lambda x: x[2])
                                    excel_sheets_colors[f"{point_name}_Colors"] = df_point_colors[['Date', 'R_norm', 'G_norm', 'B_norm']].sort_values(by="Date")
                        if excel_sheets_colors:
                                add_excel_download_button(excel_sheets_colors, f"{common_filename_prefix_dash}_default", "Pixel Colors and Height", f"excel_colors_def_{tab_prefix_key}")
                        if index_name=="Χλωροφύλλη":
                            try:
                                theme_bg = st.get_option("theme.backgroundColor")
                                theme_text = st.get_option("theme.textColor")
                                c2_disp.pyplot(create_chl_legend_figure("vertical", theme_bg_color=theme_bg, theme_text_color=theme_text))
                            except:
                                c2_disp.pyplot(create_chl_legend_figure("vertical"))


                    with n_tabs_def_display[4]:
                        st.plotly_chart(fig_m, use_container_width=True, key=f"mg_d_chart_disp_{tab_prefix_key}")
                        temp_all_mg_by_d_loc = {}
                        for p_name_temp in current_sel_pts_def_names_for_plot:
                            if p_name_temp in res_m_data:
                                for d_obj_temp, val_mg_temp in res_m_data[p_name_temp]:
                                    temp_all_mg_by_d_loc.setdefault(d_obj_temp, []).append(val_mg_temp)

                        s_dts_mg_temp_loc = sorted(temp_all_mg_by_d_loc.keys())
                        mean_mg_temp_loc = [np.mean(temp_all_mg_by_d_loc[d]) for d in s_dts_mg_temp_loc if temp_all_mg_by_d_loc[d]]
                        st.session_state[f's_dts_mg_def{tab_prefix_key}'] = s_dts_mg_temp_loc
                        st.session_state[f'mean_mg_def{tab_prefix_key}'] = mean_mg_temp_loc

                        if s_dts_mg_temp_loc and mean_mg_temp_loc:
                            df_mean_mg = pd.DataFrame({'Date': s_dts_mg_temp_loc, 'Mean_mg_m3': mean_mg_temp_loc}).sort_values(by="Date")
                            add_excel_download_button(df_mean_mg, f"{common_filename_prefix_dash}_default", "Mean mg_m3 (Selected Points)", f"excel_mean_mg_def_{tab_prefix_key}")

                    with n_tabs_def_display[5]:
                        st.plotly_chart(fig_d, use_container_width=True, key=f"dual_d_chart_disp_{tab_prefix_key}")
                        s_dts_mg_for_dual = st.session_state.get(f's_dts_mg_def{tab_prefix_key}', [])
                        mean_mg_for_dual = st.session_state.get(f'mean_mg_def{tab_prefix_key}', [])
                        df_mean_mg_for_dual = pd.DataFrame({'Date': s_dts_mg_for_dual, 'Mean_mg_m3': mean_mg_for_dual}) if s_dts_mg_for_dual and mean_mg_for_dual else pd.DataFrame(columns=['Date', 'Mean_mg_m3'])
                        df_dual_export = pd.DataFrame()
                        if isinstance(df_h_data, pd.DataFrame) and not df_h_data.empty:
                            df_dual_export = df_h_data.copy()
                        if not df_mean_mg_for_dual.empty:
                            if not df_dual_export.empty:
                                df_dual_export = pd.merge(df_dual_export, df_mean_mg_for_dual, on='Date', how='outer')
                            else:
                                df_dual_export = df_mean_mg_for_dual
                        if not df_dual_export.empty:
                            df_dual_export.sort_values('Date', inplace=True, ignore_index=True)
                            add_excel_download_button(df_dual_export, f"{common_filename_prefix_dash}_default", "Height and Mean mg_m3", f"excel_dual_def_{tab_prefix_key}")

                    with n_tabs_def_display[6]:
                        point_options_for_detail = current_sel_pts_def_names_for_plot
                        if not point_options_for_detail:
                                st.caption("Δεν έχουν επιλεγεί σημεία για εμφάνιση.")
                        else:
                            sel_pt_d_disp = st.selectbox("Σημείο για mg/m³:", point_options_for_detail, key=f"detail_d_sel_disp_{tab_prefix_key}")
                            if sel_pt_d_disp and res_m_data.get(sel_pt_d_disp):
                                mg_d_p_list = sorted(res_m_data[sel_pt_d_disp], key=lambda x: x[0])
                                if mg_d_p_list:
                                    dts_detail, vals_detail = zip(*mg_d_p_list)
                                    max_val_detail = max(vals_detail) if vals_detail else 1
                                    mk_cols_detail = px.colors.sample_colorscale("Viridis", [v/(max_val_detail if max_val_detail > 0 else 1) for v in vals_detail])
                                    fig_det_d_disp = go.Figure(go.Scatter(x=list(dts_detail),y=list(vals_detail),mode='lines+markers',marker=dict(color=mk_cols_detail,size=10),line=dict(color="grey"),name=sel_pt_d_disp))
                                    fig_det_d_disp.update_layout(title=f"mg/m³ για {sel_pt_d_disp}",xaxis_title="Ημερομηνία",yaxis_title="mg/m³")
                                    st.plotly_chart(fig_det_d_disp,use_container_width=True, key=f"detail_d_chart_disp_{tab_prefix_key}")

                                    df_point_mg_detail = pd.DataFrame({'Date': list(dts_detail), f'mg_m3': list(vals_detail)}).sort_values(by="Date")
                                    add_excel_download_button(df_point_mg_detail, f"{common_filename_prefix_dash}_default_point_{sel_pt_d_disp}", f"mg_m3 for {sel_pt_d_disp}", f"excel_detail_mg_def_{sel_pt_d_disp}_{tab_prefix_key}")
                                else: st.caption(f"Δεν υπάρχουν επεξεργασμένα δεδομένα mg/m³ για το σημείο '{sel_pt_d_disp}'.")
                            elif sel_pt_d_disp: st.caption(f"Δεν βρέθηκαν δεδομένα mg/m³ για το σημείο '{sel_pt_d_disp}'.")
                            else: st.caption("Παρακαλώ επιλέξτε ένα σημείο.")
                else:
                    st.error("Σφάλμα μορφής αποτελεσμάτων (Προεπιλογή).")

        with tabs_ctrl[1]: # Upload KML
            st.markdown("##### Ανάλυση με Ανεβασμένο KML")
            upl_file = st.file_uploader("Ανέβασμα KML:", type="kml", key=f"upl_kml_{key_suffix_dash}")
            if upl_file:
                upl_pts_list = parse_sampling_kml(upl_file)
                st.session_state[f"upl_pts_list{key_suffix_dash}"] = upl_pts_list
                if upl_pts_list:
                    st.success(f"Βρέθηκαν {len(upl_pts_list)} σημεία.")
                    all_upl_point_names = [n for n,_,_ in upl_pts_list]
                    default_upl_selection = all_upl_point_names[:]

                    sel_pts_upl_names = st.multiselect("Σημεία (KML):", all_upl_point_names, default=default_upl_selection, key=f"sel_upl_{key_suffix_dash}")
                    st.session_state[f"sel_pts_upl_names{key_suffix_dash}"] = sel_pts_upl_names
                    if st.button("Εκτέλεση (KML)",key=f"run_upl_{key_suffix_dash}",type="primary", use_container_width=True):
                        with st.spinner("Εκτέλεση..."):
                            st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                upl_pts_list, first_img_rgb, first_img_transform,
                                images_folder_path, lake_height_excel_path, sel_pts_upl_names
                            )
                else:
                    st.error("Το KML δεν περιείχε έγκυρα σημεία ή δεν μπόρεσε να αναλυθεί.")

            if SESSION_KEY_UPLOAD_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]:
                res_upl = st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]
                current_upl_pts_list = st.session_state.get(f"upl_pts_list{key_suffix_dash}", [])
                current_sel_pts_upl_names_for_plot = st.session_state.get(f"sel_pts_upl_names{key_suffix_dash}", [p[0] for p in current_upl_pts_list])

                if isinstance(res_upl, tuple) and len(res_upl) == 7:
                    fig_g_u, fig_d_u, fig_c_u, fig_m_u, res_c_data_u, res_m_data_u, df_h_data_u = res_upl

                    n_tabs_u_titles = ["GeoTIFF","Εικόνες","Video/GIF","Χρώματα","Μέσο mg/m³","Διπλό","mg/m³ ανά Σημείο"]
                    n_tabs_upl_display = st.tabs(n_tabs_u_titles)
                    tab_prefix_key_upl = f"upl_tab_{key_suffix_dash}"

                    # Tab 0: GeoTIFF
                    with n_tabs_upl_display[0]:
                        st.plotly_chart(fig_g_u, use_container_width=True, key=f"geo_u_chart_disp_{tab_prefix_key_upl}")
                        if current_upl_pts_list:
                            points_to_export_df_upl = pd.DataFrame(
                                [pt for pt in current_upl_pts_list if pt[0] in current_sel_pts_upl_names_for_plot],
                                columns=['PointName', 'Longitude', 'Latitude']
                            ) if current_sel_pts_upl_names_for_plot else pd.DataFrame(current_upl_pts_list, columns=['PointName', 'Longitude', 'Latitude'])
                            if not points_to_export_df_upl.empty:
                                add_excel_download_button(points_to_export_df_upl, f"{common_filename_prefix_dash}_upload", "Sampling Points", f"excel_geo_upl_{tab_prefix_key_upl}")
                        if index_name == "Χλωροφύλλη":
                            try:
                                theme_bg = st.get_option("theme.backgroundColor")
                                theme_text = st.get_option("theme.textColor")
                                st.pyplot(create_chl_legend_figure(theme_bg_color=theme_bg, theme_text_color=theme_text))
                            except:
                                st.pyplot(create_chl_legend_figure())

                    # Tab 1: Images
                    with n_tabs_upl_display[1]:
                        image_navigation_ui(images_folder_path,available_tifs,SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL,f"nav_upl_disp_{key_suffix_dash}",index_name=="Χλωροφύλλη",index_name)
                    # Tab 2: Video/GIF
                    with n_tabs_upl_display[2]:
                        if vid_path:
                            if vid_path.endswith(".mp4"): st.video(vid_path)
                            else: st.image(vid_path)
                            if index_name=="Χλωροφύλλη":
                                try:
                                    theme_bg = st.get_option("theme.backgroundColor")
                                    theme_text = st.get_option("theme.textColor")
                                    st.pyplot(create_chl_legend_figure(theme_bg_color=theme_bg, theme_text_color=theme_text))
                                except:
                                    st.pyplot(create_chl_legend_figure())
                        else: st.caption("Δεν βρέθηκε video/timelapse.")
                    # Tab 3: Pixel Colors
                    with n_tabs_upl_display[3]:
                        c1u_disp, c2u_disp = st.columns([.85, .15])
                        c1u_disp.plotly_chart(fig_c_u, use_container_width=True, key=f"colors_u_chart_disp_{tab_prefix_key_upl}")
                        excel_sheets_colors_u = {}
                        if isinstance(df_h_data_u, pd.DataFrame) and not df_h_data_u.empty:
                            excel_sheets_colors_u['LakeHeight'] = df_h_data_u.copy()
                        if res_c_data_u:
                            for point_name, data_list in res_c_data_u.items():
                                if data_list and (point_name in current_sel_pts_upl_names_for_plot):
                                    df_point_colors = pd.DataFrame(data_list, columns=['Date', 'RGB_Normalized'])
                                    df_point_colors['R_norm'] = df_point_colors['RGB_Normalized'].apply(lambda x: x[0])
                                    df_point_colors['G_norm'] = df_point_colors['RGB_Normalized'].apply(lambda x: x[1])
                                    df_point_colors['B_norm'] = df_point_colors['RGB_Normalized'].apply(lambda x: x[2])
                                    excel_sheets_colors_u[f"{point_name}_Colors"] = df_point_colors[['Date', 'R_norm', 'G_norm', 'B_norm']].sort_values(by="Date")
                        if excel_sheets_colors_u:
                            add_excel_download_button(excel_sheets_colors_u, f"{common_filename_prefix_dash}_upload", "Pixel Colors and Height", f"excel_colors_upl_{tab_prefix_key_upl}")
                        if index_name == "Χλωροφύλλη":
                            try:
                                theme_bg = st.get_option("theme.backgroundColor")
                                theme_text = st.get_option("theme.textColor")
                                c2u_disp.pyplot(create_chl_legend_figure("vertical", theme_bg_color=theme_bg, theme_text_color=theme_text))
                            except:
                                c2u_disp.pyplot(create_chl_legend_figure("vertical"))
                    # Tab 4: Mean mg/m3
                    with n_tabs_upl_display[4]:
                        st.plotly_chart(fig_m_u, use_container_width=True, key=f"mg_u_chart_disp_{tab_prefix_key_upl}")
                        temp_all_mg_by_d_u_loc = {}
                        for p_name_temp in current_sel_pts_upl_names_for_plot:
                            if p_name_temp in res_m_data_u:
                                for d_obj_temp, val_mg_temp in res_m_data_u[p_name_temp]:
                                    temp_all_mg_by_d_u_loc.setdefault(d_obj_temp, []).append(val_mg_temp)
                        s_dts_mg_temp_u_loc = sorted(temp_all_mg_by_d_u_loc.keys())
                        mean_mg_temp_u_loc = [np.mean(temp_all_mg_by_d_u_loc[d]) for d in s_dts_mg_temp_u_loc if temp_all_mg_by_d_u_loc[d]]
                        st.session_state[f's_dts_mg_upl{tab_prefix_key_upl}'] = s_dts_mg_temp_u_loc
                        st.session_state[f'mean_mg_upl{tab_prefix_key_upl}'] = mean_mg_temp_u_loc
                        if s_dts_mg_temp_u_loc and mean_mg_temp_u_loc:
                            df_mean_mg_u = pd.DataFrame({'Date': s_dts_mg_temp_u_loc, 'Mean_mg_m3': mean_mg_temp_u_loc}).sort_values(by="Date")
                            add_excel_download_button(df_mean_mg_u, f"{common_filename_prefix_dash}_upload", "Mean mg_m3 (Selected Points)", f"excel_mean_mg_upl_{tab_prefix_key_upl}")
                    # Tab 5: Dual Axis
                    with n_tabs_upl_display[5]:
                        st.plotly_chart(fig_d_u, use_container_width=True, key=f"dual_u_chart_disp_{tab_prefix_key_upl}")
                        s_dts_mg_for_dual_u = st.session_state.get(f's_dts_mg_upl{tab_prefix_key_upl}', [])
                        mean_mg_for_dual_u = st.session_state.get(f'mean_mg_upl{tab_prefix_key_upl}', [])
                        df_mean_mg_for_dual_u = pd.DataFrame({'Date': s_dts_mg_for_dual_u, 'Mean_mg_m3': mean_mg_for_dual_u}) if s_dts_mg_for_dual_u and mean_mg_for_dual_u else pd.DataFrame(columns=['Date', 'Mean_mg_m3'])
                        df_dual_export_u = pd.DataFrame()
                        if isinstance(df_h_data_u, pd.DataFrame) and not df_h_data_u.empty:
                            df_dual_export_u = df_h_data_u.copy()
                        if not df_mean_mg_for_dual_u.empty:
                            if not df_dual_export_u.empty:
                                df_dual_export_u = pd.merge(df_dual_export_u, df_mean_mg_for_dual_u, on='Date', how='outer')
                            else:
                                df_dual_export_u = df_mean_mg_for_dual_u
                        if not df_dual_export_u.empty:
                            df_dual_export_u.sort_values('Date', inplace=True, ignore_index=True)
                            add_excel_download_button(df_dual_export_u, f"{common_filename_prefix_dash}_upload", "Height and Mean mg_m3", f"excel_dual_upl_{tab_prefix_key_upl}")

                    with n_tabs_upl_display[6]:
                        point_options_for_detail_u = current_sel_pts_upl_names_for_plot if current_sel_pts_upl_names_for_plot else list(res_m_data_u.keys())
                        if not point_options_for_detail_u:
                            st.caption("Δεν υπάρχουν διαθέσιμα σημεία για εμφάνιση.")
                        else:
                            sel_pt_u_disp = st.selectbox("Σημείο για mg/m³ (KML):", point_options_for_detail_u, key=f"detail_u_sel_disp_{tab_prefix_key_upl}")
                            if sel_pt_u_disp and res_m_data_u.get(sel_pt_u_disp):
                                mg_d_pu_list = sorted(res_m_data_u[sel_pt_u_disp], key=lambda x: x[0])
                                if mg_d_pu_list:
                                    dts_u_detail, vals_u_detail = zip(*mg_d_pu_list)
                                    mk_cols_u_detail = px.colors.sample_colorscale("Viridis", [v/(max(vals_u_detail) if max(vals_u_detail) and max(vals_u_detail)>0 else 1) for v in vals_u_detail])
                                    fig_det_u_disp = go.Figure(go.Scatter(x=list(dts_u_detail),y=list(vals_u_detail),mode='lines+markers',marker=dict(color=mk_cols_u_detail,size=10),line=dict(color="grey"),name=sel_pt_u_disp))
                                    fig_det_u_disp.update_layout(title=f"mg/m³ για {sel_pt_u_disp} (KML)",xaxis_title="Ημερομηνία",yaxis_title="mg/m³")
                                    st.plotly_chart(fig_det_u_disp, use_container_width=True, key=f"detail_u_chart_disp_{tab_prefix_key_upl}")


                                    df_point_mg_detail_u = pd.DataFrame({'Date': list(dts_u_detail), f'mg_m3': list(vals_u_detail)}).sort_values(by="Date")
                                    add_excel_download_button(df_point_mg_detail_u, f"{common_filename_prefix_dash}_upload_point_{sel_pt_u_disp}", f"mg_m3 for {sel_pt_u_disp}", f"excel_detail_mg_upl_{sel_pt_u_disp}_{tab_prefix_key_upl}")
                                else: st.caption(f"Δεν υπάρχουν επεξεργασμένα δεδομένα mg/m³ για το σημείο '{sel_pt_u_disp}'.")
                            elif sel_pt_u_disp : st.caption(f"Δεν βρέθηκαν δεδομένα mg/m³ για το σημείο '{sel_pt_u_disp}'.")
                            else: st.caption("Παρακαλώ επιλέξτε ένα σημείο.")
                else:
                    st.error("Σφάλμα μορφής αποτελεσμάτων (Upload KML).")
        st.markdown('</div>', unsafe_allow_html=True)


def run_predictive_tools(waterbody: str, initial_selected_index: str):
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.header(f"Εργαλεία Πρόβλεψης & Έγκαιρης Ενημέρωσης: {waterbody}")
        st.markdown(f"Παράλληλη Ανάλυση για Δείκτες: **Πραγματικό, Χλωροφύλλη, Θολότητα**")

        clean_initial_index_name = re.sub(r'[^a-zA-Z0-9_]', '', initial_selected_index)
        key_suffix_pred_section = f"_pred_tool_{waterbody}_{clean_initial_index_name}"

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

            sampling_points_to_use_for_analysis = None
            default_kml_found = False
            if sampling_type_common == "Προεπιλογή":
                for idx_for_kml in indices_to_analyze:
                    temp_data_folder_for_kml = get_data_folder(waterbody, idx_for_kml)
                    if temp_data_folder_for_kml:
                        default_kml_path_common = os.path.join(temp_data_folder_for_kml, "sampling.kml")
                        if os.path.exists(default_kml_path_common):
                            sampling_points_to_use_for_analysis = parse_sampling_kml(default_kml_path_common)
                            if sampling_points_to_use_for_analysis:
                                default_kml_found = True
                                st.caption(f"Χρήση προεπιλεγμένου KML από τον φάκελο του δείκτη: {idx_for_kml}")
                                break
                if not default_kml_found:
                    st.error(f"Δεν βρέθηκε προεπιλεγμένο αρχείο KML (sampling.kml) σε κανέναν από τους φακέλους των δεικτών για το {waterbody}.")
                    st.markdown('</div>', unsafe_allow_html=True); return
            elif sampling_type_common == "Ανέβασμα KML":
                if uploaded_kml_common:
                    sampling_points_to_use_for_analysis = parse_sampling_kml(uploaded_kml_common)
                    if not sampling_points_to_use_for_analysis:
                        st.error("Το ανεβασμένο KML δεν περιείχε έγκυρα σημεία ή απέτυχε η ανάλυση.")
                        st.markdown('</div>', unsafe_allow_html=True); return
                else:
                    st.error("Επιλέξατε ανέβασμα KML, αλλά δεν έχει μεταφορτωθεί αρχείο.")
                    st.markdown('</div>', unsafe_allow_html=True); return

            if not sampling_points_to_use_for_analysis:
                st.error("Δεν ήταν δυνατός ο ορισμός των σημείων δειγματοληψίας. Η ανάλυση ακυρώνεται.")
                st.markdown('</div>', unsafe_allow_html=True); return

            all_point_names_to_use_in_analysis = [pt[0] for pt in sampling_points_to_use_for_analysis]

            with st.spinner("Εκτέλεση αναλύσεων για όλους τους δείκτες... Αυτό μπορεί να διαρκέσει λίγο."):
                for i_prog, current_idx_name_iter in enumerate(indices_to_analyze):
                    progress_val = (i_prog + 1) / len(indices_to_analyze)
                    if 'progress_bar_pred' not in st.session_state:
                        st.session_state.progress_bar_pred = st.progress(0, text="Έναρξη επεξεργασίας δεικτών...")

                    st.session_state.progress_bar_pred.progress(progress_val / 2, text=f"Επεξεργασία δείκτη: {current_idx_name_iter} (φόρτωση)...")

                    data_folder_idx = get_data_folder(waterbody, current_idx_name_iter)
                    if not data_folder_idx:
                        analysis_results_all_indices[current_idx_name_iter] = {"error": f"Δεν βρέθηκε φάκελος δεδομένων."}
                        st.warning(f"Παράλειψη '{current_idx_name_iter}': Δεν βρέθηκε φάκελος δεδομένων.")
                        st.session_state.progress_bar_pred.progress(progress_val, text=f"Παράλειψη δείκτη: {current_idx_name_iter} (δεν βρέθηκε φάκελος)")
                        continue

                    images_folder_idx = os.path.join(data_folder_idx, "GeoTIFFs")
                    lake_height_excel_idx = os.path.join(data_folder_idx, "lake height.xlsx")

                    tif_files_idx = sorted(glob.glob(os.path.join(images_folder_idx, "*.tif")))
                    if not tif_files_idx:
                        analysis_results_all_indices[current_idx_name_iter] = {"error": "Δεν βρέθηκαν αρχεία GeoTIFF."}
                        st.warning(f"Παράλειψη '{current_idx_name_iter}': Δεν βρέθηκαν αρχεία GeoTIFF.")
                        st.session_state.progress_bar_pred.progress(progress_val, text=f"Παράλειψη δείκτη: {current_idx_name_iter} (δεν βρέθηκαν GeoTIFFs)")
                        continue

                    first_img_data_idx, first_transform_idx = None, None
                    try:
                        with rasterio.open(tif_files_idx[0]) as src:
                            if src.count < 3:
                                analysis_results_all_indices[current_idx_name_iter] = {"error": "Η 1η εικόνα GeoTIFF δεν έχει 3 κανάλια."}
                                st.warning(f"Παράλειψη '{current_idx_name_iter}': Η 1η εικόνα GeoTIFF δεν έχει 3 κανάλια.")
                                st.session_state.progress_bar_pred.progress(progress_val, text=f"Παράλειψη δείκτη: {current_idx_name_iter} (σφάλμα εικόνας)")
                                continue
                            first_img_data_idx = src.read([1,2,3])
                            first_transform_idx = src.transform
                    except Exception as e:
                        analysis_results_all_indices[current_idx_name_iter] = {"error": f"Σφάλμα φόρτωσης 1ης εικόνας GeoTIFF: {e}"}
                        st.warning(f"Παράλειψη '{current_idx_name_iter}': Σφάλμα φόρτωσης 1ης εικόνας GeoTIFF.")
                        st.session_state.progress_bar_pred.progress(progress_val, text=f"Παράλειψη δείκτη: {current_idx_name_iter} (σφάλμα φόρτωσης εικόνας)")
                        continue

                    try:
                        raw_figs_and_data = analyze_sampling_generic(
                            sampling_points=sampling_points_to_use_for_analysis,
                            first_image_data=first_img_data_idx,
                            first_transform=first_transform_idx,
                            images_folder=images_folder_idx,
                            lake_height_path=lake_height_excel_idx,
                            selected_points_names=all_point_names_to_use_in_analysis,
                            lower_thresh=lower_thresh_common,
                            upper_thresh=upper_thresh_common,
                            date_min=date_min_common,
                            date_max=date_max_common
                        )
                        analysis_results_all_indices[current_idx_name_iter] = {
                            "fig_geo": raw_figs_and_data[0],
                            "fig_dual": raw_figs_and_data[1],
                            "fig_colors": raw_figs_and_data[2],
                            "fig_mg": raw_figs_and_data[3],
                            "data_results_colors": raw_figs_and_data[4],
                            "data_results_mg": raw_figs_and_data[5],
                            "data_df_h": raw_figs_and_data[6]
                        }
                        st.session_state.progress_bar_pred.progress(progress_val, text=f"Ολοκληρώθηκε: {current_idx_name_iter}")
                    except Exception as e_analyze:
                        analysis_results_all_indices[current_idx_name_iter] = {"error": f"Σφάλμα κατά την ανάλυση: {e_analyze}"}
                        st.warning(f"Σφάλμα κατά την ανάλυση του δείκτη '{current_idx_name_iter}'.")
                        st.session_state.progress_bar_pred.progress(progress_val, text=f"Σφάλμα ανάλυσης: {current_idx_name_iter}")
                if 'progress_bar_pred' in st.session_state:
                    del st.session_state.progress_bar_pred

            st.session_state[f"predictive_tool_results{key_suffix_pred_section}"] = analysis_results_all_indices
            st.session_state[f"predictive_tool_selected_charts{key_suffix_pred_section}"] = selected_charts_to_display
            st.session_state[f"predictive_tool_sampling_points{key_suffix_pred_section}"] = sampling_points_to_use_for_analysis
            st.success("Όλες οι αναλύσεις ολοκληρώθηκαν!")


        if f"predictive_tool_results{key_suffix_pred_section}" in st.session_state:
            analysis_results = st.session_state[f"predictive_tool_results{key_suffix_pred_section}"]
            charts_to_show = st.session_state.get(f"predictive_tool_selected_charts{key_suffix_pred_section}", [])
            current_sampling_points_pred = st.session_state.get(f"predictive_tool_sampling_points{key_suffix_pred_section}", [])
            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]

            st.markdown("---")
            st.subheader("Αποτελέσματα Παράλληλης Ανάλυσης")

            for chart_name_key_iter, fig_internal_key_iter in chart_display_options.items():
                if chart_name_key_iter not in charts_to_show:
                    continue

                st.markdown(f"#### {chart_name_key_iter}")
                common_filename_prefix_chart = f"{waterbody}_predictive_{fig_internal_key_iter}"


                if chart_name_key_iter == "Χρώματα Pixel & Στάθμη":
                    for idx_name_iter_colors in indices_to_analyze:
                        with st.container():
                            st.markdown(f"##### {idx_name_iter_colors}")
                            result_data_for_idx_colors = analysis_results.get(idx_name_iter_colors, {})
                            excel_btn_key_colors = f"excel_pred_colors_{idx_name_iter_colors}_{key_suffix_pred_section}"

                            if "error" in result_data_for_idx_colors:
                                st.error(f"{idx_name_iter_colors}: {result_data_for_idx_colors['error']}")
                                continue

                            fig_colors_to_plot = result_data_for_idx_colors.get("fig_colors")
                            df_h_iter_colors = result_data_for_idx_colors.get("data_df_h")
                            results_colors_iter_data = result_data_for_idx_colors.get("data_results_colors")

                            if fig_colors_to_plot:
                                fig_colors_to_plot.update_layout(height=500, uirevision=f"colors_{idx_name_iter_colors}_full{key_suffix_pred_section}")
                                st.plotly_chart(fig_colors_to_plot, use_container_width=True, key=f"chart_colors_{idx_name_iter_colors}_full{key_suffix_pred_section}")

                                excel_sheets_pred_colors = {}
                                if isinstance(df_h_iter_colors, pd.DataFrame) and not df_h_iter_colors.empty:
                                    excel_sheets_pred_colors['LakeHeight'] = df_h_iter_colors.copy()
                                if results_colors_iter_data:
                                    for point_name_rc, data_list_rc in results_colors_iter_data.items():
                                        if data_list_rc:
                                            df_pt_colors = pd.DataFrame(data_list_rc, columns=['Date', 'RGB_Normalized'])
                                            df_pt_colors['R_norm'] = df_pt_colors['RGB_Normalized'].apply(lambda x: x[0])
                                            df_pt_colors['G_norm'] = df_pt_colors['RGB_Normalized'].apply(lambda x: x[1])
                                            df_pt_colors['B_norm'] = df_pt_colors['RGB_Normalized'].apply(lambda x: x[2])
                                            excel_sheets_pred_colors[f"{point_name_rc}_Colors"] = df_pt_colors[['Date', 'R_norm', 'G_norm', 'B_norm']].sort_values(by="Date")
                                if excel_sheets_pred_colors:
                                    add_excel_download_button(excel_sheets_pred_colors, f"{common_filename_prefix_chart}_{idx_name_iter_colors}", f"Pixel Colors & Height Data ({idx_name_iter_colors})", excel_btn_key_colors)
                            else:
                                st.caption(f"Δεν υπάρχουν δεδομένα για '{chart_name_key_iter}' ({idx_name_iter_colors}).")
                        st.markdown("---" if idx_name_iter_colors != indices_to_analyze[-1] else "")
                else:
                    inner_cols = st.columns(len(indices_to_analyze))
                    for i, idx_name_iter_cols in enumerate(indices_to_analyze):
                        with inner_cols[i]:
                            st.markdown(f"##### {idx_name_iter_cols}")
                            result_data_for_idx_cols = analysis_results.get(idx_name_iter_cols, {})
                            excel_button_key_base_cols = f"excel_pred_{fig_internal_key_iter}_{idx_name_iter_cols}_{key_suffix_pred_section}"

                            if "error" in result_data_for_idx_cols:
                                st.error(result_data_for_idx_cols["error"])
                                continue

                            fig_to_plot_cols = None
                            df_for_excel_pred_cols = None
                            excel_label_suffix_pred_cols = f"{chart_name_key_iter} ({idx_name_iter_cols})"

                            df_h_iter_cols = result_data_for_idx_cols.get("data_df_h")
                            results_mg_iter_cols = result_data_for_idx_cols.get("data_results_mg")


                            if fig_internal_key_iter == "geo":
                                fig_to_plot_cols = result_data_for_idx_cols.get("fig_geo")
                                if current_sampling_points_pred:
                                    df_for_excel_pred_cols = pd.DataFrame(current_sampling_points_pred, columns=['PointName', 'Longitude', 'Latitude'])
                                    excel_label_suffix_pred_cols = f"Sampling Points Data ({idx_name_iter_cols})"

                            elif fig_internal_key_iter == "lake_height_only":
                                if isinstance(df_h_iter_cols, pd.DataFrame) and not df_h_iter_cols.empty:
                                    df_for_excel_pred_cols = df_h_iter_cols.copy().sort_values(by="Date")
                                    excel_label_suffix_pred_cols = f"Lake Height Data ({idx_name_iter_cols})"
                                    fig_to_plot_cols = go.Figure(go.Scatter(x=df_h_iter_cols['Date'], y=df_h_iter_cols['Height'], name='Στάθμη Λίμνης'))
                                    fig_to_plot_cols.update_layout(title=f"Στάθμη Λίμνης ({idx_name_iter_cols})")
                                else:
                                    st.caption(f"Δεν υπάρχουν δεδομένα στάθμης για {idx_name_iter_cols}")

                            elif fig_internal_key_iter == "mg":
                                fig_to_plot_cols = result_data_for_idx_cols.get("fig_mg")
                                temp_all_mg_d_pred_cols = {}
                                if results_mg_iter_cols:
                                    for p_name_mg_iter, data_list_mg in results_mg_iter_cols.items():
                                        for d_obj_mg, val_mg_iter in data_list_mg:
                                            temp_all_mg_d_pred_cols.setdefault(d_obj_mg, []).append(val_mg_iter)
                                s_dts_mg_pred_cols = sorted(temp_all_mg_d_pred_cols.keys())
                                mean_mg_pred_cols = [np.mean(temp_all_mg_d_pred_cols[d]) for d in s_dts_mg_pred_cols if temp_all_mg_d_pred_cols[d]]
                                if s_dts_mg_pred_cols and mean_mg_pred_cols:
                                    df_for_excel_pred_cols = pd.DataFrame({'Date': s_dts_mg_pred_cols, 'Mean_mg_m3': mean_mg_pred_cols}).sort_values(by="Date")
                                    excel_label_suffix_pred_cols = f"Mean mg/m³ Data ({idx_name_iter_cols})"

                            elif fig_internal_key_iter == "dual":
                                fig_to_plot_cols = result_data_for_idx_cols.get("fig_dual")
                                df_mean_mg_for_dual_pred_cols = pd.DataFrame()
                                temp_all_mg_d_pred_dual_cols = {}
                                if results_mg_iter_cols:
                                    for p_name_mg_iter_d, data_list_mg_d in results_mg_iter_cols.items():
                                        for d_obj_mg_d, val_mg_iter_d in data_list_mg_d:
                                            temp_all_mg_d_pred_dual_cols.setdefault(d_obj_mg_d, []).append(val_mg_iter_d)
                                s_dts_mg_pred_d_cols = sorted(temp_all_mg_d_pred_dual_cols.keys())
                                mean_mg_pred_d_cols = [np.mean(temp_all_mg_d_pred_dual_cols[d]) for d in s_dts_mg_pred_d_cols if temp_all_mg_d_pred_dual_cols[d]]
                                if s_dts_mg_pred_d_cols and mean_mg_pred_d_cols:
                                    df_mean_mg_for_dual_pred_cols = pd.DataFrame({'Date': s_dts_mg_pred_d_cols, 'Mean_mg_m3': mean_mg_pred_d_cols})

                                df_dual_export_pred_cols = pd.DataFrame()
                                if isinstance(df_h_iter_cols, pd.DataFrame) and not df_h_iter_cols.empty:
                                    df_dual_export_pred_cols = df_h_iter_cols.copy()
                                if not df_mean_mg_for_dual_pred_cols.empty:
                                    if not df_dual_export_pred_cols.empty:
                                        df_dual_export_pred_cols = pd.merge(df_dual_export_pred_cols, df_mean_mg_for_dual_pred_cols, on='Date', how='outer')
                                    else:
                                        df_dual_export_pred_cols = df_mean_mg_for_dual_pred_cols
                                if not df_dual_export_pred_cols.empty:
                                    df_dual_export_pred_cols.sort_values('Date', inplace=True, ignore_index=True)
                                    df_for_excel_pred_cols = df_dual_export_pred_cols
                                    excel_label_suffix_pred_cols = f"Height & Mean mg/m³ Data ({idx_name_iter_cols})"

                            if fig_to_plot_cols:
                                fig_to_plot_cols.update_layout(height=400, uirevision=f"{fig_internal_key_iter}_{idx_name_iter_cols}_col{key_suffix_pred_section}")
                                st.plotly_chart(fig_to_plot_cols, use_container_width=True, key=f"chart_{fig_internal_key_iter}_{idx_name_iter_cols}_col{key_suffix_pred_section}")
                                if df_for_excel_pred_cols is not None:
                                    add_excel_download_button(df_for_excel_pred_cols, f"{common_filename_prefix_chart}_{idx_name_iter_cols}", excel_label_suffix_pred_cols, excel_button_key_base_cols)
                                if fig_internal_key_iter == "geo" and idx_name_iter_cols == "Χλωροφύλλη":
                                    st.pyplot(create_chl_legend_figure(orientation="horizontal"))
                            elif fig_internal_key_iter != "lake_height_only" and fig_internal_key_iter != "colors":
                                st.caption(f"Δεν υπάρχουν δεδομένα για '{chart_name_key_iter}' ({idx_name_iter_cols}).")
                st.markdown("""<hr style="border:1px solid #444; margin-top:1.5rem; margin-bottom:1.5rem;">""", unsafe_allow_html=True)
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
        # --- MODIFIED: Removed call to run_lake_processing_app ---
        if selected_an == "Επιφανειακή Αποτύπωση":
            # --- This option is removed from the sidebar, but as a fallback: ---
            st.warning("Η ενότητα 'Επιφανειακή Αποτύπωση' έχει αφαιρεθεί.")
            st.info("Παρακαλώ επιλέξτε μια άλλη 'Είδος Ανάλυσης' από την πλαϊνή μπάρα.")
        # --- END OF MODIFICATION ---
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
    authenticator.login('main')

    auth_status = st.session_state.get("authentication_status")

    if auth_status:
        main_app()
    elif auth_status is False:
        st.error('Το όνομα χρήστη ή ο κωδικός πρόσβασης είναι λανθασμένος (Username/password is incorrect)')
    elif auth_status is None:
        st.warning('Παρακαλώ εισάγετε το όνομα χρήστη και τον κωδικό πρόσβασής σας (Please enter your username and password)')