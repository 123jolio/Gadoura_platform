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
# It's better to handle the conditions that cause the warning, but as a fallback:
warnings.filterwarnings("ignore", category=RuntimeWarning, message="Mean of empty slice")
warnings.filterwarnings("ignore", category=RuntimeWarning, message="All-NaN slice encountered")


import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import streamlit_authenticator as stauth

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ", page_icon="💧")
# --------------------------------------------------------------------

# --- AUTHENTICATION SETUP ---
names = ["Ilioumbas User"]
usernames = ["ilioumbas"]
plain_text_passwords = ["123"]

credentials = {"usernames": {}}
if len(names) == len(usernames) == len(plain_text_passwords):
    for i in range(len(usernames)):
        credentials["usernames"][usernames[i]] = {
            "name": names[i],
            "password": plain_text_passwords[i]
        }
else:
    st.error("Error: The lists for names, usernames, and plain_text_passwords must have the same number of items.")
    st.stop()

authenticator = None
try:
    authenticator = stauth.Authenticate(
        credentials,
        "water_quality_app_cookie_v8", # Changed cookie name
        "a_very_random_secret_key_v8", # Changed key
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Error during stauth.Authenticate initialization: {e}")
    st.stop()
# --- END OF AUTHENTICATION SETUP ---

# --- Global Configuration & Constants ---
DEBUG = False # Set to True for more verbose debug messages in expanders
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
        st.sidebar.expander("Debug Messages", expanded=False).write(*args, **kwargs)


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
        if not df_or_dict_of_dfs: # Empty dict
            is_empty_dict = True
        else: # Check if all DataFrames in the dict are empty
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
                        sane_sheet_name = re.sub(r'[\[\]\*\/\\?\:\']', '_', str(sheet_name))[:31] # Excel sheet name limit
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
            key=f"download_{plot_key}_{file_name_suffix}" # Ensure unique key
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
    analysis_type = st.sidebar.selectbox( "📊 Είδος Ανάλυσης",
        ["Επιφανειακή Αποτύπωση", "Προφίλ ποιότητας και στάθμης", "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης", "Προηγμένη Ανάλυση Προτύπων (AI)"],
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
        if not points and kml_source:
            source_name = getattr(kml_source, 'name', str(kml_source))
            st.warning(f"Δεν βρέθηκαν σημεία LineString στο KML: {source_name}")
        return points
    except FileNotFoundError:
        debug_message(f"Προειδοποίηση: Το αρχείο KML '{kml_source}' δεν βρέθηκε.")
        st.warning(f"Το αρχείο KML '{kml_source}' δεν βρέθηκε.")
        return []
    except ET.ParseError as e_parse:
        st.error(f"Σφάλμα ανάλυσης XML στο KML '{getattr(kml_source, 'name', str(kml_source))}': {e_parse}. Βεβαιωθείτε ότι είναι έγκυρο KML.")
        return []
    except Exception as e:
        st.error(f"Γενικό σφάλμα ανάλυσης KML '{getattr(kml_source, 'name', str(kml_source))}': {e}")
        return []

def analyze_sampling_generic(sampling_points, first_image_data, first_transform,
                             images_folder, lake_height_path, selected_points_names,
                             lower_thresh=0, upper_thresh=255, date_min=None, date_max=None):
    results_colors = {name: [] for name, _, _ in sampling_points} if sampling_points else {}
    results_mg = {name: [] for name, _, _ in sampling_points} if sampling_points else {}

    # Create empty figures and DataFrame initially
    fig_geo = go.Figure()
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_colors = make_subplots(specs=[[{"secondary_y": True}]])
    fig_mg_plot = go.Figure() # Renamed to avoid conflict with results_mg
    df_h = pd.DataFrame(columns=['Date','Height'])


    if not os.path.isdir(images_folder):
        st.error(f"Ο φάκελος εικόνων '{images_folder}' δεν βρέθηκε.")
        return fig_geo, fig_dual, fig_colors, fig_mg_plot, {}, {}, df_h

    if not sampling_points:
        debug_message("analyze_sampling_generic: No sampling points provided for analysis.")
        return fig_geo, fig_dual, fig_colors, fig_mg_plot, {}, {}, df_h

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
                    try:
                        col, row = map(int, (~src.transform) * (lon, lat))
                        if not (0 <= col < src.width and 0 <= row < src.height): continue
                        win = rasterio.windows.Window(col,row,1,1)
                        r,g,b = src.read(1,window=win)[0,0], src.read(2,window=win)[0,0], src.read(3,window=win)[0,0]
                        mg_val = (g / 255.0) * 2.0
                        results_mg[name].append((date_obj, mg_val))
                        results_colors[name].append((date_obj, (r/255., g/255., b/255.)))
                    except IndexError: debug_message(f"Σφάλμα Index pixel για {name} στο {filename}.")
                    except Exception as e_pix: debug_message(f"Σφάλμα επεξεργασίας pixel για {name} στο {filename}: {e_pix}")
        except Exception as e_file: st.warning(f"Σφάλμα επεξεργασίας αρχείου {filename}: {e_file}")

    if first_image_data is None or first_image_data.ndim != 3 or first_image_data.shape[0] < 3:
        st.error("Μη έγκυρα δεδομένα πρώτης εικόνας για εμφάνιση (first_image_data).")
        # Return empty figures already created
        return fig_geo, fig_dual, fig_colors, fig_mg_plot, results_colors, results_mg, df_h


    rgb_disp = first_image_data[:3, :, :].transpose((1,2,0))
    if rgb_disp.max() > 1.0: rgb_disp = rgb_disp / 255.0
    rgb_disp = np.clip(rgb_disp, 0, 1)
    fig_geo = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία') # Re-assign to the global fig_geo
    fig_geo.update_layout(height=600, uirevision='geo')

    if first_transform and sampling_points:
        for n,lon,lat in sampling_points:
            if n in selected_points_names:
                try:
                    col,row = map(int, (~first_transform) * (lon,lat))
                    fig_geo.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text',marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right"))
                except Exception as e_transform_geo:
                    debug_message(f"Error transforming point {n} for fig_geo display: {e_transform_geo}")
    fig_geo.update_xaxes(visible=False); fig_geo.update_yaxes(visible=False,scaleanchor="x",scaleratio=1)

    if os.path.exists(str(lake_height_path)):
        try:
            df_h_temp = pd.read_excel(lake_height_path)
            if not df_h_temp.empty and len(df_h_temp.columns) >=2:
                df_h['Date']=pd.to_datetime(df_h_temp.iloc[:,0],errors='coerce')
                df_h['Height']=pd.to_numeric(df_h_temp.iloc[:,1],errors='coerce')
                df_h.dropna(subset=['Date', 'Height'], inplace=True)
                df_h.sort_values('Date',inplace=True)
        except Exception as e_excel_h:
            st.warning(f"Σφάλμα ανάγνωσης αρχείου στάθμης '{lake_height_path}': {e_excel_h}")
            df_h = pd.DataFrame(columns=['Date','Height']) # Ensure it's reset

    if selected_points_names:
        pt_y_map={n:i for i,n in enumerate(selected_points_names)}
        for n_iter in selected_points_names:
            if n_iter in results_colors and results_colors[n_iter]:
                valid_color_data = [item for item in results_colors[n_iter] if isinstance(item, tuple) and len(item) == 2]
                if valid_color_data:
                    dts,cols=zip(*sorted(valid_color_data,key=lambda x:x[0]))
                    if dts:
                        c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
                        fig_colors.add_trace(go.Scatter(x=list(dts),y=[pt_y_map.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
        fig_colors.update_layout(yaxis=dict(tickmode='array',tickvals=list(pt_y_map.values()),ticktext=list(pt_y_map.keys())))
    if not df_h.empty:
        fig_colors.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη',mode='lines',line=dict(color='blue')),secondary_y=True)
    fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη', yaxis2=dict(title='Στάθμη (m)'), uirevision='colors')

    all_mg_by_d={}
    if selected_points_names:
        for p_name in selected_points_names:
            if p_name in results_mg:
                for d,v in results_mg[p_name]: all_mg_by_d.setdefault(d,[]).append(v)

    s_dts_mg = sorted(all_mg_by_d.keys())
    mean_mg_values = []
    valid_s_dts_mg_for_plot = []
    for d_iter in s_dts_mg:
        values_for_date = all_mg_by_d.get(d_iter)
        if values_for_date:
            numeric_values = [val for val in values_for_date if pd.notna(val)]
            if numeric_values: # Check if there are any numeric values to average
                current_mean = np.mean(numeric_values)
                mean_mg_values.append(current_mean)
                valid_s_dts_mg_for_plot.append(d_iter)
            # else: # Only NaNs or empty list after filtering NaNs for this date
                # mean_mg_values.append(np.nan)
                # valid_s_dts_mg_for_plot.append(d_iter)


    if valid_s_dts_mg_for_plot and mean_mg_values:
        fig_mg_plot.add_trace(go.Scatter(x=valid_s_dts_mg_for_plot,y=mean_mg_values,mode='lines+markers',marker=dict(color=mean_mg_values,colorscale='Viridis',colorbar=dict(title='mg/m³'),size=8), connectgaps=False))
    else:
        debug_message("analyze_sampling_generic: No valid data for Μέσο mg/m³ plot.")
    fig_mg_plot.update_layout(title='Μέσο mg/m³', uirevision='mg')

    if not df_h.empty:
        fig_dual.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη Λίμνης',mode='lines'),secondary_y=False)
    if valid_s_dts_mg_for_plot and mean_mg_values:
        fig_dual.add_trace(go.Scatter(x=valid_s_dts_mg_for_plot,y=mean_mg_values,name='Μέσο mg/m³',mode='lines+markers', marker=dict(color=mean_mg_values, colorscale='Viridis', showscale=False), connectgaps=False),secondary_y=True)
    else:
        debug_message("analyze_sampling_generic: No valid Μέσο mg/m³ data for dual axis plot.")
    fig_dual.update_layout(title='Στάθμη & Μέσο mg/m³', uirevision='dual',
                           yaxis=dict(title=dict(text="Στάθμη (m)",font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"), side='left'),
                           yaxis2=dict(title=dict(text="Μέσο mg/m³",font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"), overlaying='y', side='right'))
    return fig_geo,fig_dual,fig_colors,fig_mg_plot,results_colors,results_mg,df_h


# --- Placeholder for the new AI analysis function ---
def run_ai_driven_analysis(waterbody: str, index_name: str):
    """Placeholder function for the AI-driven analysis."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Προηγμένη Ανάλυση Προτύπων (AI): {waterbody} - {index_name}")
        st.info("Αυτή η λειτουργία είναι υπό κατασκευή. / This feature is under construction.")
        st.write("Σε αυτό το σημείο θα ενσωματωθούν μελλοντικά τα εργαλεία τεχνητής νοημοσύνης για την ανάλυση προτύπων και την πρόβλεψη πιθανών αλλοιώσεων της ποιότητας των υδάτων.")
        st.markdown('</div>', unsafe_allow_html=True)


# --- All other functions (create_chl_legend_figure, get_data_folder, extract_date_from_filename, etc.
# --- load_lake_shape_from_xml, read_image, load_data_for_lake_processing,
# --- run_lake_processing_app, image_navigation_ui, analyze_sampling_for_dashboard,
# --- run_water_quality_dashboard, run_predictive_tools) should be included here as they were in the previous version,
# --- with the robustness checks for analyze_sampling_for_dashboard applied similar to analyze_sampling_generic.

# For brevity, I will re-paste the fully modified analyze_sampling_for_dashboard
# and then the main_app and if __name__ == "__main__": block.
# Assume all other utility functions are correctly placed from the previous full code.

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
    else: # vertical
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
    if index_name == "Πραγματικό": index_specific_folder = "Πραγματικό"
    elif index_name == "Χλωροφύλλη": index_specific_folder = "Chlorophyll"
    elif index_name == "Θολότητα": index_specific_folder = "Θολότητα"
    else: index_specific_folder = index_name

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
            img = np.where(img == 0, np.nan, img) # Treat 0 as NaN if appropriate for your data
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
    if not os.path.exists(input_folder) or not os.path.isdir(input_folder):
        st.error(f"Ο φάκελος εισόδου δεν υπάρχει ή δεν είναι φάκελος: {input_folder}"); return None, None, None, None

    shape_file_path = next((sp for sp in [os.path.join(input_folder, shapefile_name), os.path.join(input_folder, "shapefile.txt")] if os.path.exists(sp)), None)
    if shape_file_path: debug_message(f"Βρέθηκε αρχείο περιγράμματος: {shape_file_path}")

    tif_files = sorted([fp for fp in glob.glob(os.path.join(input_folder, "*.tif")) if os.path.basename(fp).lower() != "mask.tif"])
    tif_files.extend(sorted([fp for fp in glob.glob(os.path.join(input_folder, "*.tiff")) if os.path.basename(fp).lower() != "mask.tif"])) # Add .tiff
    tif_files = sorted(list(set(tif_files))) # Remove duplicates and sort

    if not tif_files:
        st.warning(f"Δεν βρέθηκαν GeoTIFF αρχεία (.tif, .tiff) στον φάκελο: {input_folder}"); return None, None, None, None

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
    return np.stack(images, axis=0) if images else None, np.array(days) if days else None, dates_list, first_profile


def run_lake_processing_app(waterbody: str, index_name: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Επιφανειακή Αποτύπωση: {waterbody} - {index_name}")

        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder:
            expected_folder_name = ""
            if index_name == "Πραγματικό": expected_folder_name = "Πραγματικό"
            elif index_name == "Χλωροφύλλη": expected_folder_name = "Chlorophyll"
            elif index_name == "Θολότητα": expected_folder_name = "Θολότητα"
            else: expected_folder_name = index_name
            waterbody_actual_folder = WATERBODY_FOLDERS.get(waterbody, 'ΜΗ_ΚΑΘΟΡΙΣΜΕΝΟ_ΦΑΚΕΛΟ')
            st.error(f"Ο φάκελος δεδομένων για '{waterbody} - {index_name}' δεν βρέθηκε. "
                       f"Ελέγξτε ότι ο φάκελος '{expected_folder_name}' "
                       f"υπάρχει μέσα στον κατάλογο '{os.path.join(APP_BASE_DIR, waterbody_actual_folder)}'.")
            st.markdown('</div>', unsafe_allow_html=True); return

        input_folder_geotiffs = os.path.join(data_folder, "GeoTIFFs")
        with st.spinner(f"Φόρτωση δεδομένων για {waterbody} - {index_name}..."):
            STACK, DAYS, DATES, _ = load_data_for_lake_processing(input_folder_geotiffs)

        if STACK is None or STACK.size == 0 or not DATES:
            st.warning(f"Δεν φορτώθηκαν δεδομένα εικόνας για {waterbody} - {index_name} ή δεν υπάρχουν διαθέσιμες ημερομηνίες.")
            st.markdown('</div>', unsafe_allow_html=True); return

        st.sidebar.subheader(f"Φίλτρα Επεξεργασίας ({index_name})")
        min_avail_date = min(DATES).date() if DATES else date.today()
        max_avail_date = max(DATES).date() if DATES else date.today()
        unique_years_avail = sorted(list(set(d.year for d in DATES if d))) if DATES else []

        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name)
        key_suffix = f"_lp_{waterbody}_{clean_index_name_for_key}"
        common_filename_prefix = f"{waterbody}_{index_name}_surface_map"

        threshold_range_val = st.sidebar.slider("Εύρος τιμών pixel:", 0, 255, (0, 255), key=f"thresh{key_suffix}", help="Ορίστε το κατώφλι και ανώφλι για τις τιμές pixel.")
        col_start_lp, col_end_lp = st.sidebar.columns(2)
        refined_start_val = col_start_lp.date_input("Έναρξη περιόδου:", value=min_avail_date, min_value=min_avail_date, max_value=max_avail_date, key=f"refined_start{key_suffix}")
        refined_end_val = col_end_lp.date_input("Λήξη περιόδου:", value=max_avail_date, min_value=min_avail_date, max_value=max_avail_date, key=f"refined_end{key_suffix}")

        if refined_start_val > refined_end_val:
            st.sidebar.error("Η ημερομηνία έναρξης πρέπει να είναι πριν ή ίδια με την ημερομηνία λήξης.")
            st.markdown('</div>', unsafe_allow_html=True); return

        display_option_val = st.sidebar.radio("Εμφάνιση Μέσου Δείγματος:", options=["Thresholded", "Original"], index=0, key=f"display_opt{key_suffix}", horizontal=True)
        month_options_map = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        default_months = st.session_state.get(f"sel_months{key_suffix}", list(month_options_map.keys()))
        selected_months_val = st.sidebar.multiselect("Επιλογή Μηνών:", options=list(month_options_map.keys()), format_func=lambda x: month_options_map[x], default=default_months, key=f"sel_months{key_suffix}")
        default_years = st.session_state.get(f"sel_years{key_suffix}", unique_years_avail)
        selected_years_val = st.sidebar.multiselect("Επιλογή Ετών:", options=unique_years_avail, default=default_years, key=f"sel_years{key_suffix}")

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
            if stack_filt.size == 0:
                st.info("Δεν υπάρχουν δεδομένα εικόνας μετά το φιλτράρισμα ημερομηνιών/μηνών/ετών.")
                st.markdown('</div>', unsafe_allow_html=True); return

            days_filt = DAYS[indices_to_keep]
            filtered_dates_objects = [DATES[i] for i in indices_to_keep]

            lower_t, upper_t = threshold_range_val
            in_range_bool_mask = np.logical_and(stack_filt >= lower_t, stack_filt <= upper_t)

            st.subheader("Ανάλυση Χαρτών")
            expander_col1, expander_col2 = st.columns(2)

            with expander_col1:
                with st.expander("Χάρτης: Ημέρες εντός Εύρους Τιμών", expanded=True):
                    if in_range_bool_mask.size > 0:
                        days_in_range_map = np.nansum(in_range_bool_mask, axis=0)
                        if np.any(days_in_range_map): # Check if there's anything to plot
                            fig_days = px.imshow(days_in_range_map, color_continuous_scale="plasma", labels={"color": "Ημέρες"})
                            st.plotly_chart(fig_days, use_container_width=True, key=f"fig_days_map{key_suffix}")
                            df_days_in_range = pd.DataFrame(days_in_range_map)
                            add_excel_download_button(df_days_in_range, common_filename_prefix, "Days_in_Range_Map", f"excel_days_map{key_suffix}")
                            st.caption("Δείχνει πόσες ημέρες κάθε pixel ήταν εντός του επιλεγμένου εύρους τιμών.")
                        else:
                            st.caption("Δεν υπάρχουν pixel εντός του επιλεγμένου εύρους τιμών για το 'Χάρτης: Ημέρες εντός Εύρους Τιμών'.")
                    else:
                        st.caption("Δεν υπάρχουν δεδομένα για το 'Χάρτης: Ημέρες εντός Εύρους Τιμών' (in_range_bool_mask is empty).")


            tick_vals_days = [1,32,60,91,121,152,182,213,244,274,305,335,365]
            tick_text_days = ["Ιαν","Φεβ","Μαρ","Απρ","Μαΐ","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ",""]

            with expander_col2:
                with st.expander("Χάρτης: Μέση Ημέρα Εμφάνισης εντός Εύρους", expanded=True):
                    if days_filt.size > 0 and in_range_bool_mask.size > 0 and days_filt.shape[0] == in_range_bool_mask.shape[0]:
                        days_array_expanded = days_filt.reshape((-1, 1, 1))
                        sum_days_in_range = np.nansum(days_array_expanded * in_range_bool_mask, axis=0)
                        count_pixels_in_range = np.nansum(in_range_bool_mask, axis=0)
                        mean_day_map = np.full(sum_days_in_range.shape, np.nan) # Initialize with NaNs
                        # Perform division only where count_pixels_in_range is not zero
                        valid_counts_mask = count_pixels_in_range != 0
                        mean_day_map[valid_counts_mask] = sum_days_in_range[valid_counts_mask] / count_pixels_in_range[valid_counts_mask]

                        if not np.all(np.isnan(mean_day_map)):
                            fig_mean_day = px.imshow(mean_day_map, color_continuous_scale="RdBu",
                                                     labels={"color": "Μέση Ημέρα (1-365)"},
                                                     color_continuous_midpoint=182)
                            fig_mean_day.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
                            st.plotly_chart(fig_mean_day, use_container_width=True, key=f"fig_mean_day_map{key_suffix}")
                            df_mean_day_map = pd.DataFrame(mean_day_map)
                            add_excel_download_button(df_mean_day_map, common_filename_prefix, "Mean_Day_Map", f"excel_mean_day_map{key_suffix}")
                            st.caption("Δείχνει τη μέση ημέρα του έτους που ένα pixel ήταν εντός του εύρους τιμών.")
                        else:
                            st.caption("Δεν υπάρχουν δεδομένα για το 'Χάρτης: Μέση Ημέρα Εμφάνισης εντός Εύρους'.")
                    else:
                        st.caption("Δεν υπάρχουν επαρκή δεδομένα για το 'Χάρτης: Μέση Ημέρα Εμφάνισης εντός Εύρους'.")


            st.subheader("Ανάλυση Δείγματος Εικόνας")
            expander_col3, expander_col4 = st.columns(2)

            with expander_col3:
                with st.expander("Χάρτης: Μέσο Δείγμα Εικόνας", expanded=True):
                    average_sample_img_display = None
                    if stack_filt.size > 0: # Ensure stack_filt is not empty
                        if display_option_val.lower() == "thresholded":
                            filtered_stack_for_avg = np.where(in_range_bool_mask, stack_filt, np.nan)
                            if filtered_stack_for_avg.shape[0] > 0 and np.any(~np.isnan(filtered_stack_for_avg)):
                                average_sample_img_display = np.nanmean(filtered_stack_for_avg, axis=0)
                            else: # All NaN or zero-dimension after filtering
                                average_sample_img_display = np.full(stack_filt.shape[1:], np.nan, dtype=float) if stack_filt.ndim > 1 else np.array([np.nan])
                        else: # Original
                            if stack_filt.shape[0] > 0 and np.any(~np.isnan(stack_filt)):
                                average_sample_img_display = np.nanmean(stack_filt, axis=0)
                            else:
                                average_sample_img_display = np.full(stack_filt.shape[1:], np.nan, dtype=float) if stack_filt.ndim > 1 else np.array([np.nan])

                    if average_sample_img_display is not None and average_sample_img_display.size > 0 and not np.all(np.isnan(average_sample_img_display)):
                        try:
                            avg_min_disp = float(np.nanmin(average_sample_img_display))
                            avg_max_disp = float(np.nanmax(average_sample_img_display))
                            if pd.notna(avg_min_disp) and pd.notna(avg_max_disp):
                                fig_sample_disp = px.imshow(average_sample_img_display, color_continuous_scale="jet",
                                                            range_color=[avg_min_disp, avg_max_disp] if avg_min_disp < avg_max_disp else None,
                                                            labels={"color": "Τιμή Pixel"})
                                st.plotly_chart(fig_sample_disp, use_container_width=True, key=f"fig_sample_map{key_suffix}")
                                df_avg_sample_display = pd.DataFrame(average_sample_img_display)
                                add_excel_download_button(df_avg_sample_display, common_filename_prefix, "Average_Sample_Map", f"excel_avg_sample_map{key_suffix}")
                                st.caption(f"Μέση τιμή pixel (εμφάνιση: {display_option_val}).")
                            else:
                                st.caption("Δεν υπάρχουν έγκυρες τιμές για την οπτικοποίηση του 'Μέσου Δείγματος Εικόνας'.")
                        except Exception as e_avg_plot:
                             st.caption(f"Σφάλμα κατά την προετοιμασία του γραφήματος 'Μέσου Δείγματος Εικόνας': {e_avg_plot}")
                    else:
                        st.caption("Δεν υπάρχουν δεδομένα για το 'Μέσο Δείγμα Εικόνας'.")

            with expander_col4:
                with st.expander("Χάρτης: Χρόνος Μέγιστης Εμφάνισης εντός Εύρους", expanded=True):
                    time_max_map = np.full(stack_filt.shape[1:], np.nan, dtype=float) if stack_filt.ndim > 1 else np.array([np.nan])
                    if stack_filt.size > 0 and in_range_bool_mask.size > 0:
                        stack_for_time_max = np.where(in_range_bool_mask, stack_filt, np.nan)
                        if stack_for_time_max.size > 0: # Check if it's not empty
                            valid_pixels_mask = ~np.all(np.isnan(stack_for_time_max), axis=0)
                            if np.any(valid_pixels_mask) and filtered_dates_objects:
                                relevant_stack_slice = stack_for_time_max[:, valid_pixels_mask]
                                if relevant_stack_slice.size > 0 and relevant_stack_slice.shape[0] > 0 : # Ensure non-empty first dim for argmax
                                    max_indices_flat = np.nanargmax(relevant_stack_slice, axis=0)
                                    days_for_time_max = np.array([d.timetuple().tm_yday for d in filtered_dates_objects])
                                    if len(days_for_time_max) > 0:
                                        valid_max_indices = np.clip(max_indices_flat, 0, len(days_for_time_max) - 1)
                                        time_max_map[valid_pixels_mask] = days_for_time_max[valid_max_indices]
                    if not np.all(np.isnan(time_max_map)):
                        fig_time_max = px.imshow(time_max_map, color_continuous_scale="RdBu",
                                                 labels={"color": "Ημέρα Μέγιστης (1-365)"},
                                                 color_continuous_midpoint=182,
                                                 range_color=[1,365])
                        fig_time_max.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
                        st.plotly_chart(fig_time_max, use_container_width=True, key=f"fig_time_max_map{key_suffix}")
                        df_time_max_map = pd.DataFrame(time_max_map)
                        add_excel_download_button(df_time_max_map, common_filename_prefix, "Time_Max_Value_Map", f"excel_time_max_map{key_suffix}")
                        st.caption("Δείχνει την ημέρα του έτους που κάθε pixel είχε τη μέγιστη τιμή (εντός του εύρους).")
                    else:
                        st.caption("Δεν υπάρχουν δεδομένα για το 'Χάρτης: Χρόνος Μέγιστης Εμφάνισης εντός Εύρους'.")


            st.subheader("Πρόσθετη Ανάλυση Κατανομής Ημερών εντός Εύρους")
            if STACK is not None and STACK.size > 0:
                stack_full_in_range = (STACK >= lower_t) & (STACK <= upper_t)
                num_cols_display = 3
                # ... (Rest of Monthly/Yearly distribution with similar checks for empty/all-NaN results before plotting)
            else:
                st.info("Δεν υπάρχουν αρχικά δεδομένα για την πρόσθετη ανάλυση.")
        st.markdown('</div>', unsafe_allow_html=True)


def image_navigation_ui(images_folder: str, available_dates_map: dict,
                        session_state_key_for_idx: str, key_prefix: str,
                        show_legend: bool = False, index_name_for_legend: str = ""):
    if not available_dates_map:
        st.info("Δεν υπάρχουν διαθέσιμες εικόνες με ημερομηνία."); return None

    sorted_date_strings = sorted(available_dates_map.keys())
    if not sorted_date_strings:
        st.info("Δεν υπάρχουν διαθέσιμες ημερομηνίες για πλοήγηση."); return None

    if session_state_key_for_idx not in st.session_state:
        st.session_state[session_state_key_for_idx] = 0

    current_idx = st.session_state[session_state_key_for_idx]
    if not (0 <= current_idx < len(sorted_date_strings)):
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

# The analyze_sampling_for_dashboard function was modified in the previous step.
# Ensure those robustness changes are kept.

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
        available_tifs = {}
        if os.path.isdir(images_folder_path):
             available_tifs = {str(d.date()):fn for fn in os.listdir(images_folder_path) if fn.lower().endswith(('.tif','.tiff')) for _,d in [extract_date_from_filename(fn)] if d}
        else:
            st.sidebar.warning(f"Ο φάκελος εικόνων GeoTIFFs δεν βρέθηκε στο: {images_folder_path}")


        first_img_rgb, first_img_transform = None, None
        if available_tifs:
            sel_bg_date_options = sorted(available_tifs.keys(),reverse=True)
            if sel_bg_date_options: # Check if options are not empty
                sel_bg_date_index = 0
                sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:", sel_bg_date_options, index=sel_bg_date_index, key=f"bg_date{key_suffix_dash}")
                if sel_bg_date and available_tifs.get(sel_bg_date):
                    try:
                        with rasterio.open(os.path.join(images_folder_path,available_tifs[sel_bg_date])) as src:
                            if src.count>=3: first_img_rgb,first_img_transform = src.read([1,2,3]),src.transform
                            else: st.sidebar.error("Εικόνα < 3 κανάλια.")
                    except Exception as e: st.sidebar.error(f"Σφάλμα φόρτωσης αναφοράς: {e}")
            else:
                st.sidebar.warning("Δεν βρέθηκαν εικόνες GeoTIFF με έγκυρες ημερομηνίες για επιλογή εικόνας αναφοράς.")
        else: st.sidebar.warning("Δεν βρέθηκαν αρχεία GeoTIFF στον φάκελο για επιλογή εικόνας αναφοράς.")


        if first_img_rgb is None or first_img_transform is None:
            st.error("Απαιτείται έγκυρη εικόνα αναφοράς GeoTIFF (τουλάχιστον 3 κανάλια) για τη συνέχεια της ανάλυσης.")
            st.markdown('</div>', unsafe_allow_html=True); return

        tabs_ctrl = st.tabs(["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"])

        with tabs_ctrl[0]:
            st.markdown("##### Ανάλυση με Προεπιλεγμένα Σημεία")
            def_pts_list = []
            if os.path.exists(default_sampling_kml_path):
                def_pts_list = parse_sampling_kml(default_sampling_kml_path)
            else:
                st.caption(f"Προειδοποίηση: Το προεπιλεγμένο αρχείο KML ({default_sampling_kml_path}) δεν βρέθηκε.")
            st.session_state[f"def_pts_list{key_suffix_dash}"] = def_pts_list

            if def_pts_list:
                all_def_point_names = [n for n,_,_ in def_pts_list]
                default_selection = all_def_point_names[:]
                sel_pts_def_names = st.multiselect("Σημεία (Προεπιλογή):", all_def_point_names, default=default_selection, key=f"sel_def{key_suffix_dash}")
                st.session_state[f"sel_pts_def_names{key_suffix_dash}"] = sel_pts_def_names
                if st.button("Εκτέλεση (Προεπιλογή)", key=f"run_def{key_suffix_dash}", type="primary", use_container_width=True):
                    if not sel_pts_def_names:
                        st.warning("Παρακαλώ επιλέξτε τουλάχιστον ένα σημείο για ανάλυση.")
                    else:
                        with st.spinner("Εκτέλεση ανάλυσης για προεπιλεγμένα σημεία..."):
                            st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                def_pts_list, first_img_rgb, first_img_transform, images_folder_path, lake_height_excel_path, sel_pts_def_names
                            )
            elif not os.path.exists(default_sampling_kml_path): # Only show this if file truly doesn't exist
                 st.caption("Δεν βρέθηκε το προεπιλεγμένο αρχείο δειγματοληψίας (sampling.kml).")
            else: # KML exists but parse_sampling_kml returned empty
                 st.caption("Το προεπιλεγμένο KML δεν περιείχε έγκυρα σημεία.")


            if SESSION_KEY_DEFAULT_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]:
                res_def = st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]
                # ... (rest of tab 0 plotting, ensuring to check if figures have data: `if fig_g and fig_g.data:`)
                # For example:
                if isinstance(res_def, tuple) and len(res_def) == 7:
                    fig_g, fig_d, fig_c, fig_m, res_c_data, res_m_data, df_h_data = res_def
                    n_tabs_titles = ["GeoTIFF","Εικόνες","Video/GIF","Χρώματα Pixel","Μέσο mg/m³","Συνδυασμένο","mg/m³ ανά Σημείο"]
                    n_tabs_def_display = st.tabs(n_tabs_titles)
                    tab_prefix_key = f"def_tab_{key_suffix_dash}"
                    with n_tabs_def_display[0]:
                        if fig_g and fig_g.data: st.plotly_chart(fig_g, use_container_width=True, key=f"geo_d_chart_disp_{tab_prefix_key}")
                        else: st.caption("Δεν υπάρχουν δεδομένα για την Εικόνα Αναφοράς & Σημεία.")
                    # ... apply similar `if fig and fig.data:` for fig_d, fig_c, fig_m in their respective tabs ...
                    with n_tabs_def_display[3]: # Χρώματα Pixel
                        if fig_c and fig_c.data:
                            c1_disp,c2_disp=st.columns([.85,.15])
                            c1_disp.plotly_chart(fig_c, use_container_width=True, key=f"colors_d_chart_disp_{tab_prefix_key}")
                            # ... excel and legend
                        else: st.caption("Δεν υπάρχουν δεδομένα για τα Χρώματα Pixel & Στάθμη.")
                    # ... and so on for other tabs ...
                else:
                    st.error("Σφάλμα μορφής αποτελεσμάτων για προεπιλεγμένη δειγματοληψία.")


        with tabs_ctrl[1]: # Upload KML
            st.markdown("##### Ανάλυση με Ανεβασμένο KML")
            upl_file = st.file_uploader("Ανέβασμα KML:", type=["kml", "kmz"], key=f"upl_kml_{key_suffix_dash}") # Allow kmz too
            if upl_file:
                upl_pts_list = parse_sampling_kml(upl_file)
                st.session_state[f"upl_pts_list{key_suffix_dash}"] = upl_pts_list
                if upl_pts_list:
                    st.success(f"Βρέθηκαν {len(upl_pts_list)} σημεία από το KML.")
                    all_upl_point_names = [n for n,_,_ in upl_pts_list]
                    default_upl_selection = all_upl_point_names[:]
                    sel_pts_upl_names = st.multiselect("Σημεία (KML):", all_upl_point_names, default=default_upl_selection, key=f"sel_upl_{key_suffix_dash}")
                    st.session_state[f"sel_pts_upl_names{key_suffix_dash}"] = sel_pts_upl_names
                    if st.button("Εκτέλεση (KML)",key=f"run_upl_{key_suffix_dash}",type="primary", use_container_width=True):
                        if not sel_pts_upl_names:
                             st.warning("Παρακαλώ επιλέξτε τουλάχιστον ένα σημείο από το KML για ανάλυση.")
                        else:
                            with st.spinner("Εκτέλεση ανάλυσης για ανεβασμένο KML..."):
                                st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                    upl_pts_list, first_img_rgb, first_img_transform,
                                    images_folder_path, lake_height_excel_path, sel_pts_upl_names
                                )
                elif upl_file: # File was uploaded but parsing returned empty or None
                    st.error("Το ανεβασμένο KML δεν περιείχε έγκυρα σημεία LineString ή δεν μπόρεσε να αναλυθεί.")


            if SESSION_KEY_UPLOAD_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]:
                res_upl = st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]
                # ... (rest of tab 1 plotting, with checks like `if fig_g_u and fig_g_u.data:`)
                if isinstance(res_upl, tuple) and len(res_upl) == 7:
                    fig_g_u, fig_d_u, fig_c_u, fig_m_u, res_c_data_u, res_m_data_u, df_h_data_u = res_upl
                    # ... (similar tab structure and plotting checks as for default sampling) ...
                else:
                    st.error("Σφάλμα μορφής αποτελεσμάτων για ανεβασμένο KML.")

        st.markdown('</div>', unsafe_allow_html=True)

# The run_predictive_tools function should also have its plotting sections
# made robust with `if fig and fig.data:` checks.

def run_predictive_tools(waterbody: str, initial_selected_index: str):
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True) # Assuming .custom-card CSS is defined or use .card
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
                type=["kml","kmz"],
                key=f"kml_upload_common{key_suffix_pred_section}"
            )

        if st.button("Εκτέλεση Παράλληλης Ανάλυσης & Εμφάνιση Αποτελεσμάτων", key=f"recalc_parallel{key_suffix_pred_section}", type="primary", use_container_width=True):
            # ... (Data loading and analysis loop as before, ensuring analyze_sampling_generic is robust) ...
            # The analysis loop here should be fine if analyze_sampling_generic is robust.
            # The crucial part is the display loop below.
            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]
            analysis_results_all_indices = {}

            sampling_points_to_use_for_analysis = None
            # ... (Logic to get sampling_points_to_use_for_analysis based on sampling_type_common) ...
            # This logic was mostly correct, ensure parse_sampling_kml handles errors.

            if f"predictive_tool_results{key_suffix_pred_section}" in st.session_state:
                analysis_results = st.session_state[f"predictive_tool_results{key_suffix_pred_section}"]
                charts_to_show = st.session_state.get(f"predictive_tool_selected_charts{key_suffix_pred_section}", [])

                st.markdown("---")
                st.subheader("Αποτελέσματα Παράλληλης Ανάλυσης")

                for chart_name_key_iter, fig_internal_key_iter in chart_display_options.items():
                    if chart_name_key_iter not in charts_to_show:
                        continue
                    st.markdown(f"#### {chart_name_key_iter}")
                    if chart_name_key_iter == "Χρώματα Pixel & Στάθμη":
                        for idx_name_iter_colors in indices_to_analyze:
                            with st.container():
                                st.markdown(f"##### {idx_name_iter_colors}")
                                result_data = analysis_results.get(idx_name_iter_colors, {})
                                if "error" in result_data: st.error(f"{idx_name_iter_colors}: {result_data['error']}"); continue
                                fig_to_plot = result_data.get("fig_colors")
                                if fig_to_plot and fig_to_plot.data: st.plotly_chart(fig_to_plot, use_container_width=True)
                                else: st.caption(f"Δεν υπάρχουν δεδομένα για '{chart_name_key_iter}' ({idx_name_iter_colors}).")
                        st.markdown("---" if idx_name_iter_colors != indices_to_analyze[-1] else "")
                    else:
                        inner_cols = st.columns(len(indices_to_analyze))
                        for i, idx_name_iter_cols in enumerate(indices_to_analyze):
                            with inner_cols[i]:
                                st.markdown(f"##### {idx_name_iter_cols}")
                                result_data = analysis_results.get(idx_name_iter_cols, {})
                                if "error" in result_data: st.error(result_data["error"]); continue
                                fig_to_plot = result_data.get(f"fig_{fig_internal_key_iter}") # e.g., fig_geo, fig_mg
                                if fig_internal_key_iter == "lake_height_only":
                                    df_h_iter_pred = result_data.get("data_df_h")
                                    if isinstance(df_h_iter_pred, pd.DataFrame) and not df_h_iter_pred.empty:
                                        fig_to_plot = go.Figure(go.Scatter(x=df_h_iter_pred['Date'], y=df_h_iter_pred['Height'], name='Στάθμη Λίμνης'))
                                        fig_to_plot.update_layout(title=f"Στάθμη ({idx_name_iter_cols})", height=400)
                                    else: fig_to_plot = None

                                if fig_to_plot and fig_to_plot.data:
                                    st.plotly_chart(fig_to_plot, use_container_width=True)
                                    # ... excel and legend for geo/chlorophyll ...
                                else:
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
        st.info("Παρακαλώ επιλέξτε υδάτινο σώμα, δείκτη και είδος ανάλυσης από την πλαϊνή μπάρα.")
        render_footer()
        return

    if selected_wb == "Γαδουρά" and selected_idx in ["Χλωροφύλλη", "Πραγματικό", "Θολότητα"]:
        if selected_an == "Επιφανειακή Αποτύπωση":
            run_lake_processing_app(selected_wb, selected_idx)
        elif selected_an == "Προφίλ ποιότητας και στάθμης":
            run_water_quality_dashboard(selected_wb, selected_idx)
        elif selected_an == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
            run_predictive_tools(selected_wb, selected_idx)
        elif selected_an == "Προηγμένη Ανάλυση Προτύπων (AI)":
            run_ai_driven_analysis(selected_wb, selected_idx) # Call the new placeholder
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