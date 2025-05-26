#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

import datetime
from datetime import date, time # Added for date.today(), time.min, time.max
import os
import warnings
import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning
from rasterio.features import geometry_mask
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from typing import Optional, Tuple, Dict, Any, List, Union, Callable # Added Callable
import io # Added import for io.BytesIO
import re # Added import for re.sub, re.search
import xml.etree.ElementTree as ET # Added import for ET.parse
import glob # Added import for glob.glob

# Placeholder for _geographic_to_pixel - Replace with actual implementation
def _geographic_to_pixel(lon, lat, transform):
    """Placeholder: Converts geographic coordinates to pixel coordinates."""
    # Example: return transform * (lon, lat) 
    # This is highly dependent on the rasterio transform object and conventions
    # st.warning("_geographic_to_pixel function is a placeholder. Please implement it.")
    return (0, 0) # Default placeholder return

# Placeholder for _map_rgb_to_mg - Replace with actual implementation
def _map_rgb_to_mg(r, g, b):
    """Placeholder: Maps RGB values to mg values."""
    # st.warning("_map_rgb_to_mg function is a placeholder. Please implement it.")
    # Example: return some_conversion_formula(r, g, b)
    return 0.0 # Default placeholder return

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ", page_icon="💧")
# --------------------------------------------------------------------

# --- AUTHENTICATION SETUP ---

# --- STEP 1: (ΑΥΤΟ ΤΟ ΒΗΜΑ ΕΙΝΑΙ ΠΛΕΟΝ ΠΕΡΙΤΤΟ ΚΑΙ ΠΑΡΑΛΕΙΠΕΤΑΙ/ΣΧΟΛΙΑΖΕΤΑΙ) ---
# =======================================================================================
# # WHEN YOU RUN THIS SCRIPT FIRST, THIS BLOCK WILL BE ACTIVE:
# # import streamlit_authenticator as stauth # Already imported above
# # import streamlit as st
#
# # CHOOSE YOUR ACTUAL PASSWORDS HERE (MAKE SURE THEY ARE STRONG):
# # passwords_for_users = ['123'] # <--- YOUR SINGLE PASSWORD FOR 'ilioumbas'
#
# # Corrected Hasher usage
# # hashed_passwords_for_script = stauth.Hasher.hash_list(passwords_for_users)
# # st.write("--- IMPORTANT: HASHED PASSWORD GENERATION (Temporary) ---")
# # st.write("1. Copy this entire list (including the square brackets and quotes).")
# # st.write("2. Paste it to replace the 'hashed_passwords_list' variable below (in STEP 3).")
# # st.write("3. After pasting, comment out or delete this entire 'STEP 1' debug block.")
# # st.write("4. Re-run the Streamlit app with STEP 1 commented out.")
# # st.write("Generated Hashes:", hashed_passwords_for_script)
# # st.stop() # Stops the app here after printing, so you can copy the hashes
# =======================================================================================

# --- STEP 2: Define your users and their credentials ---
names = ["Ilioumbas User"]  # Display name for your user
usernames = ["ilioumbas"]   # Username for login
# Ορίστε εδώ τους κωδικούς πρόσβασης σε απλό κείμενο (plain text)
# Η βιβλιοθήκη θα τους κρυπτογραφήσει αυτόματα.
plain_text_passwords = ["123"] # <--- YOUR SINGLE PLAIN TEXT PASSWORD FOR 'ilioumbas'

# --- STEP 3 (Τροποποιημένο): Create credentials dictionary using PLAIN TEXT passwords ---
credentials = {"usernames": {}}
if len(names) == len(usernames) == len(plain_text_passwords): # Basic check
    for i in range(len(usernames)):
        credentials["usernames"][usernames[i]] = {
            "name": names[i],
            "password": plain_text_passwords[i]  # Χρησιμοποιούμε τον απλό κωδικό εδώ
        }
else:
    st.error("Error: The lists for names, usernames, and plain_text_passwords must have the same number of items.")
    st.error("Please ensure you have defined users and their plain text passwords correctly.")
    st.error(f"Debug: len(names)={len(names)}, len(usernames)={len(usernames)}, len(plain_text_passwords)={len(plain_text_passwords)}")
    st.stop()

# --- Optional Debugging: You can uncomment this to see the credentials (with plain passwords)
# --- before they are passed to the Authenticator. REMEMBER TO COMMENT IT OUT AGAIN.
# st.write("--- Debug: Credentials with PLAIN PASSWORDS (before auto-hashing) ---")
# st.write(credentials)
# st.write("--- End Debug ---")

# --- STEP 4: Initialize the Authenticator ---
# Η παράμετρος auto_hash είναι True από προεπιλογή.
# Αυτό σημαίνει ότι η βιβλιοθήκη θα κρυπτογραφήσει αυτόματα
# τους απλούς κωδικούς που παρέχονται στο 'credentials' dictionary.
authenticator = None # Initialize to None in case of error below
try:
    authenticator = stauth.Authenticate(
        credentials,
        "water_quality_app_cookie_v6",    # Changed cookie name slightly for freshness
        "a_very_random_secret_key_v6",  # Changed key slightly for freshness
        cookie_expiry_days=30
        # auto_hash=True # Αυτή είναι η προεπιλογή, δεν χρειάζεται να το ορίσετε ρητά
    )
except Exception as e:
    st.error(f"Error during stauth.Authenticate initialization: {e}")
    st.error("This often happens if the 'credentials' dictionary is malformed.")
    st.stop()

# --- Optional Debugging: Uncomment if you still face issues ---
# st.write("--- Debug: Authenticator Object Inspection (Post-User-Update) ---")
# st.write(f"Authenticator object after initialization: {authenticator}")
# if authenticator:
#     if hasattr(authenticator, 'credentials'): # The 'credentials' attribute of the authenticator object
#                                              # will now store the *hashed* passwords.
#         st.write(f"Authenticator.credentials (internal - should have hashed passwords now): {authenticator.credentials}")
#     else:
#         st.write("Authenticator object does NOT have a 'credentials' attribute after init.")
# else:
#     st.write("Authenticator object is None after initialization attempt.")
# st.write("--- End Debug: Authenticator Object Inspection ---")
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
            © {datetime.datetime.now().year} EYATH SA • Powered by Google Gemini & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
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
    global authenticator # Access the globally defined authenticator
    if authenticator and st.session_state.get("authentication_status"): # Check if authenticator is valid and user is logged in
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
        if not points and kml_source: # Check if kml_source was provided but no points found
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
        try: date_obj = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
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
                df_h.dropna(inplace=True); df_h.sort_values(by='Date',inplace=True)
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

    sm = matplotlib.cm.ScalarMappable(cmap=cmap, norm=norm) # Corrected: plt.cm to matplotlib.cm
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
        fig.set_facecolor(theme_bg_color) # Corrected: fig.patch.set_facecolor -> fig.set_facecolor
        ax.set_facecolor(theme_bg_color)
    if theme_text_color:
        ax.xaxis.label.set_color(theme_text_color)
        ax.yaxis.label.set_color(theme_text_color)
        ax.tick_params(axis='x', colors=theme_text_color)
        ax.tick_params(axis='y', colors=theme_text_color)
        cbar.ax.xaxis.label.set_color(theme_text_color) # Colorbar label for x-axis
        cbar.ax.yaxis.label.set_color(theme_text_color) # Colorbar label for y-axis
        cbar.ax.tick_params(axis='x', colors=theme_text_color) # Colorbar tick labels for x-axis
        cbar.ax.tick_params(axis='y', colors=theme_text_color) # Colorbar tick labels for y-axis


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
        index_specific_folder = index_name # Fallback

    data_folder = os.path.join(APP_BASE_DIR, waterbody_folder_name, index_specific_folder)
    debug_message(f"DEBUG: Αναζήτηση φακέλου δεδομένων: {data_folder}")

    if not os.path.exists(data_folder) or not os.path.isdir(data_folder):
        return None
    return data_folder

@st.cache_data
def extract_date_from_filename(filename: str) -> Tuple[Optional[int], Optional[datetime.datetime]]: # Corrected datetime type hint
    basename = os.path.basename(filename)
    match = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', basename)

    if match:
        year, month, day = map(int, match.groups())
        try:
            date_obj = datetime.datetime(year, month, day)
            # Assuming the first element of the tuple should be an int, e.g., year or None
            return year, date_obj # Example, adjust as per actual logic
        except ValueError:
            return None, None
    return None, None

@st.cache_data
def load_lake_shape_from_xml(xml_file_path: str, bounds: Optional[Tuple[float, float, float, float]] = None,
                                xml_width: float = 518.0, xml_height: float = 505.0) -> Optional[Dict[str, Any]]:
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

@st.cache_data
def read_image(file_path: str, lake_shape: Optional[Dict[str, Any]] = None) -> Tuple[Optional[np.ndarray], Optional[dict]]:
    debug_message(f"DEBUG: Ανάγνωση εικόνας: {file_path}")
    try:
        with rasterio.open(file_path) as src:
            img = src.read(1).astype(np.float32)
            profile = src.profile.copy(); profile.update(dtype="float32")

            if src.nodata is not None: img = np.where(img == src.nodata, np.nan, img)
            img = np.where(img == 0, np.nan, img) # Treat 0 as NaN if appropriate

            if lake_shape:
                from rasterio.features import geometry_mask
                poly_mask = geometry_mask([lake_shape], transform=src.transform, invert=True, out_shape=img.shape) # Invert=True to keep data INSIDE
                img = np.where(poly_mask, img, np.nan)
            return img, profile
    except Exception as e:
        st.warning(f"Προειδοποίηση: Σφάλμα ανάγνωσης εικόνας {os.path.basename(file_path)}: {e}. Παραλείπεται."); return None, None

@st.cache_data
def load_data_for_lake_processing(input_folder: str, shapefile_name="shapefile.xml") -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[Any]], Optional[Dict[str, Any]]]:
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
        img_data, _ = read_image(fp_iter, lake_shape=lake_geom) # lake_geom can be None, read_image handles Optional
        if img_data is not None: images.append(img_data); days.append(day_yr); dates_list.append(date_obj)

    if not images:
        st.warning(f"Δεν φορτώθηκαν έγκυρες εικόνες από τον φάκελο: {input_folder}."); return None, None, None, None
    return np.stack(images, axis=0), np.array(days), dates_list, first_profile


def run_lake_processing_app(authenticator):
    st.title("Επεξεργασία Δεδομένων Λίμνης")
    # Initialize session state variables if not present
    if "defined_points" not in st.session_state:
        st.session_state.defined_points = []
    if "selected_points_names_for_plot" not in st.session_state:
        st.session_state.selected_points_names_for_plot = []
    if "common_filename_prefix" not in st.session_state:
        st.session_state.common_filename_prefix = "lake_export_data"
    if "current_index_name" not in st.session_state:
        st.session_state.current_index_name = "DefaultIndexName" # Or some other default
    if "available_tifs_lake_processing" not in st.session_state:
        st.session_state.available_tifs_lake_processing = []
    if "key_suffix_lake_processing" not in st.session_state:
        st.session_state.key_suffix_lake_processing = "lake_proc"
    if "current_video_path_lake_processing" not in st.session_state:
        st.session_state.current_video_path_lake_processing = None
    if "images_folder_path_lake_processing" not in st.session_state:
        st.session_state.images_folder_path_lake_processing = "Gadoura/Chlorophyll/GeoTIFFs" # Example default
    if "SESSION_KEY_CURRENT_IMAGE_INDEX_LAKE_PROC" not in st.session_state:
        st.session_state.SESSION_KEY_CURRENT_IMAGE_INDEX_LAKE_PROC = 0


    # Fetch from session state or initialize
    current_def_pts_list: List[Any] = st.session_state.defined_points
    current_sel_pts_def_names_for_plot: List[str] = st.session_state.selected_points_names_for_plot
    common_filename_prefix_dash: str = st.session_state.common_filename_prefix
    index_name: str = st.session_state.current_index_name
    available_tifs: List[str] = st.session_state.available_tifs_lake_processing
    key_suffix_dash: str = st.session_state.key_suffix_lake_processing
    vid_path: Optional[str] = st.session_state.current_video_path_lake_processing
    images_folder_path: str = st.session_state.images_folder_path_lake_processing
    SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF = "SESSION_KEY_CURRENT_IMAGE_INDEX_LAKE_PROC" # Use the initialized one

    # Initialize other potentially unbound variables
    expander_col1 = None
    expander_col2 = None
    in_range_bool_mask: Optional[np.ndarray] = None
    days_filt: Optional[np.ndarray] = None
    stack_filt: Optional[np.ndarray] = None
    filtered_dates_objects: Optional[List[datetime.datetime]] = None
    lower_t: Optional[float] = None
    upper_t: Optional[float] = None
    DATES: Optional[List[datetime.datetime]] = None # Initialize DATES
    STACK: Optional[np.ndarray] = None # Initialize STACK

    # --- MAIN LOGIC ---
    waterbody = st.sidebar.selectbox("🌊 Υδάτινο σώμα", list(WATERBODY_FOLDERS.keys()), index=0, key=SESSION_KEY_WATERBODY)
    index_name = st.sidebar.selectbox("🔬 Δείκτης", ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"], key=SESSION_KEY_INDEX)
    analysis_type = st.sidebar.selectbox( "📊 Είδος Ανάλυσης",
        ["Επιφανειακή Αποτύπωση", "Προφίλ ποιότητας και στάθμης", "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"],
        key=SESSION_KEY_ANALYSIS
    )

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
        return

    input_folder_geotiffs = os.path.join(data_folder, "GeoTIFFs")
    
    with st.spinner(f"Φόρτωση δεδομένων για {waterbody} - {index_name}..."):
        STACK, DAYS, DATES, _ = load_data_for_lake_processing(input_folder_geotiffs)

    if STACK is None or not DATES:
        return

    st.sidebar.subheader(f"Φίλτρα Επεξεργασίας ({index_name})") # Simplified title
    min_avail_date = min(DATES).date() if DATES else date.today()
    max_avail_date = max(DATES).date() if DATES else date.today()
    unique_years_avail = sorted(list(set(d.year for d in DATES if d))) if DATES else []

    clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name) 
    key_suffix = f"_lp_{waterbody}_{clean_index_name_for_key}"
    common_filename_prefix = f"{waterbody}_{index_name}_surface_map"

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
        return
        
    display_option_val = st.sidebar.radio("Εμφάνιση Μέσου Δείγματος:", 
                                        options=["Thresholded", "Original"], index=0, 
                                        key=f"display_opt{key_suffix}", horizontal=True)

    month_options_map = {i: datetime.datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
    
    default_months = st.session_state.get(f"sel_months{key_suffix}", list(month_options_map.keys()))
    selected_months_val = st.sidebar.multiselect("Επιλογή Μηνών:",
                                                options=list(month_options_map.keys()),
                                                format_func=lambda x: month_options_map[x],
                                                default=default_months,
                                                key=f"sel_months{key_suffix}")
    
    default_years = st.session_state.get(f"sel_years{key_suffix}", unique_years_avail)
    selected_years_val = st.sidebar.multiselect("Επιλογή Ετών:", 
                                                options=unique_years_avail,
                                                default=default_years,
                                                key=f"sel_years{key_suffix}")
    
    if refined_start_val and refined_end_val:
        start_dt_conv = datetime.datetime.combine(refined_start_val, datetime.time.min)
        end_dt_conv = datetime.datetime.combine(refined_end_val, datetime.time.max)

        indices_to_keep = [
            i for i, dt_obj in enumerate(DATES)
            if (start_dt_conv <= dt_obj <= end_dt_conv and
                (not selected_months_val or dt_obj.month in selected_months_val) and
                (not selected_years_val or dt_obj.year in selected_years_val))
        ]

        if not indices_to_keep:
            st.info("Δεν υπάρχουν δεδομένα για την επιλεγμένη περίοδο/μήνες/έτη. Παρακαλώ προσαρμόστε τα φίλτρα.")
            return

        with st.spinner("Επεξεργασία φιλτραρισμένων δεδομένων και δημιουργία γραφημάτων..."):
            stack_filt = STACK[indices_to_keep, :, :] if STACK is not None else None
            days_filt = DAYS[indices_to_keep] if DAYS is not None and indices_to_keep else None # Added check for DAYS
            filtered_dates_objects = [DATES[i] for i in indices_to_keep] if DATES is not None else []

            if stack_filt is None or days_filt is None:
                st.info("Δεν υπάρχουν επαρκή δεδομένα μετά το φιλτράρισμα για την επιλεγμένη περίοδο/μήνες/έτη.")
                return

            lower_t, upper_t = threshold_range_val
            in_range_bool_mask = np.logical_and(stack_filt >= lower_t, stack_filt <= upper_t)
            
            st.subheader("Ανάλυση Χαρτών")
            expander_col1, expander_col2 = st.columns(2)

            # Αυτές οι γραμμές υποθέτουμε ότι είναι ήδη σωστά στοιχισμένες μέσα στο
        # with st.spinner("Επεξεργασία φιλτραρισμένων δεδομένων και δημιουργία γραφημάτων..."):

        with expander_col1:
            with st.expander("Χάρτης: Ημέρες εντός Εύρους Τιμών", expanded=True):
                days_in_range_map = np.nansum(in_range_bool_mask, axis=0)
                fig_days = px.imshow(days_in_range_map, color_continuous_scale="plasma", labels={"color": "Ημέρες"})
                st.plotly_chart(fig_days, use_container_width=True, key=f"fig_days_map{key_suffix}")
                df_days_in_range = pd.DataFrame(days_in_range_map)
                add_excel_download_button(df_days_in_range, common_filename_prefix, "Days_in_Range_Map", f"excel_days_map{key_suffix}")
                st.caption("Δείχνει πόσες ημέρες κάθε pixel ήταν εντός του επιλεγμένου εύρους τιμών.")

        # Οι tick_vals_days και tick_text_days πρέπει να είναι στο ίδιο επίπεδο με τα with expander_colX
        # αν χρησιμοποιούνται και από το expander_col2, ή πιο μέσα αν είναι μόνο για το expander_col1
        # Ας υποθέσουμε ότι είναι γενικά για την ενότητα χαρτών, άρα στο ίδιο επίπεδο με τα expander_colX
        # Αν όμως το tick_vals_days και tick_text_days είναι ΕΞΩ από το `with expander_col1:`
        # τότε το `with expander_col2:` πρέπει να είναι στο ίδιο επίπεδο με το `with expander_col1:`

        # ΔΙΟΡΘΩΣΗ: Οι tick_vals_days και tick_text_days πρέπει να είναι έξω από το with expander_col1
        # και στο ίδιο επίπεδο με αυτό, αν χρησιμοποιούνται και από το expander_col2.
        # Αν δεν χρησιμοποιούνται από το expander_col2, μπορούν να μείνουν μέσα ή να μετακινηθούν.
        # Για ασφάλεια, ας τα βγάλουμε ένα επίπεδο έξω από το expander_col1 αλλά μέσα στο spinner.

    # Ας υποθέσουμε ότι οι tick_vals_days και tick_text_days ορίζονται εδώ,
    # στο ίδιο επίπεδο με τα st.subheader και st.columns
    tick_vals_days = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 365]
    tick_text_days = ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαΐ", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ", ""]

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
            df_mean_day_map = pd.DataFrame(mean_day_map)
            add_excel_download_button(df_mean_day_map, common_filename_prefix, "Mean_Day_Map", f"excel_mean_day_map{key_suffix}")
            st.caption("Δείχνει τη μέση ημέρα του έτους που ένα pixel ήταν εντός του εύρους τιμών.")

    st.subheader("Ανάλυση Δείγματος Εικόνας") # Στο ίδιο επίπεδο με το προηγούμενο st.subheader
    expander_col3, expander_col4 = st.columns(2) # Στο ίδιο επίπεδο

    # Εδώ είναι το διορθωμένο expander_col3
    with expander_col3: # Πρέπει να είναι στο ίδιο επίπεδο με το 'with expander_col1:'
        with st.expander("Χάρτης: Μέσο Δείγμα Εικόνας", expanded=True):
            average_sample_img_display = None  # Αρχικοποίηση

            # Αυτό είναι μέσα στο: with expander_col3:
            #                     with st.expander("Χάρτης: Μέσο Δείγμα Εικόνας", expanded=True):
            average_sample_img_display = None  # Αρχικοποίηση στην αρχή του expander

            if display_option_val.lower() == "thresholded":
                if 'stack_filt' in locals() and stack_filt is not None:
                    filtered_stack_for_avg = np.where(in_range_bool_mask, stack_filt, np.nan)
                    
                    # Έλεγχος αν υπάρχουν καθόλου δεδομένα και αν υπάρχει τουλάχιστον μία μη-NaN τιμή
                    if filtered_stack_for_avg.shape[0] > 0 and np.any(~np.isnan(filtered_stack_for_avg)):
                        average_sample_img_display = np.nanmean(filtered_stack_for_avg, axis=0) # Αυτή είναι η γραμμή 747 (ή κοντά)
                    else:
                        # Δεν υπάρχουν δεδομένα ή είναι όλα NaN
                        if 'STACK' in locals() and STACK is not None and STACK.ndim == 3:
                            average_sample_img_display = np.full(STACK.shape[1:], np.nan, dtype=float)
                        # (Το st.caption μπορεί να μπει εδώ ή μετά την εμφάνιση)
                else: # stack_filt δεν υπάρχει ή είναι None
                    if 'STACK' in locals() and STACK is not None and STACK.ndim == 3:
                        average_sample_img_display = np.full(STACK.shape[1:], np.nan, dtype=float)

            else:  # Original
                if 'stack_filt' in locals() and stack_filt is not None:
                    # Έλεγχος αν υπάρχουν καθόλου δεδομένα και αν υπάρχει τουλάχιστον μία μη-NaN τιμή
                    if stack_filt.shape[0] > 0 and np.any(~np.isnan(stack_filt)):
                        average_sample_img_display = np.nanmean(stack_filt, axis=0) # Αυτή είναι η γραμμή 747 (ή κοντά)
                    else:
                        # Δεν υπάρχουν δεδομένα ή είναι όλα NaN
                        if 'STACK' in locals() and STACK is not None and STACK.ndim == 3:
                            average_sample_img_display = np.full(STACK.shape[1:], np.nan, dtype=float)
                else: # stack_filt δεν υπάρχει ή είναι None
                    if 'STACK' in locals() and STACK is not None and STACK.ndim == 3:
                        average_sample_img_display = np.full(STACK.shape[1:], np.nan, dtype=float)

            # Ο υπόλοιπος κώδικας για την εμφάνιση (if average_sample_img_display is not None and not np.all(np.isnan(average_sample_img_display)): ...)
            # παραμένει όπως τον είχατε ή όπως τον διορθώσαμε προηγουμένως.
            # Έλεγχος και εμφάνιση του αποτελέσματος
            if average_sample_img_display is not None and not np.all(np.isnan(average_sample_img_display)):
                if average_sample_img_display.size > 0:
                    try:
                        avg_min_disp = float(np.nanmin(average_sample_img_display))
                        avg_max_disp = float(np.nanmax(average_sample_img_display))

                        if np.isnan(avg_min_disp) or np.isnan(avg_max_disp):
                            st.caption("Δεν υπάρχουν έγκυρες τιμές για την οπτικοποίηση του 'Μέσου Δείγματος Εικόνας'.")
                        else:
                            fig_sample_disp = px.imshow(average_sample_img_display, color_continuous_scale="jet",
                                                        range_color=[avg_min_disp, avg_max_disp] if avg_min_disp < avg_max_disp else None,
                                                        labels={"color": "Τιμή Pixel"})
                            st.plotly_chart(fig_sample_disp, use_container_width=True, key=f"fig_sample_map{key_suffix}")
                            df_avg_sample_display = pd.DataFrame(average_sample_img_display)
                            add_excel_download_button(df_avg_sample_display, common_filename_prefix, "Average_Sample_Map", f"excel_avg_sample_map{key_suffix}")
                            st.caption(f"Μέση τιμή pixel (εμφάνιση: {display_option_val}).")
                    except Exception as e:
                        st.caption(f"Σφάλμα κατά την προετοιμασία του γραφήματος 'Μέσου Δείγματος Εικόνας': {e}")
                else:
                    st.caption("Δεν υπάρχουν δεδομένα για το 'Μέσο Δείγμα Εικόνας' (κενό μέγεθος πίνακα).")
            else:
                st.caption("Δεν υπάρχουν δεδομένα για το 'Μέσο Δείγμα Εικόνας'.")

    # Ο κώδικας για το expander_col4 θα ακολουθήσει εδώ, στο ίδιο επίπεδο με το 'with expander_col3:'
    # with expander_col4:
    #     ...

        # Έλεγχος και εμφάνιση του αποτελέσματος
        if average_sample_img_display is not None and not np.all(np.isnan(average_sample_img_display)):
            # Έλεγχος αν το array έχει μη-NaN τιμές και δεν είναι απλά ένα άδειο array από το np.array([[]])
            if average_sample_img_display.size > 0 : # Εξασφαλίζει ότι δεν είναι shape (0,) ή παρόμοιο
                try:
                    avg_min_disp = float(np.nanmin(average_sample_img_display))
                    avg_max_disp = float(np.nanmax(average_sample_img_display))

                    # Επιπλέον έλεγχος για την περίπτωση που avg_min_disp == avg_max_disp (π.χ. σταθερή εικόνα)
                    # ή αν κάποιο από αυτά είναι NaN (αν και το np.all(np.isnan) θα έπρεπε να το έχει πιάσει)
                    if np.isnan(avg_min_disp) or np.isnan(avg_max_disp):
                         st.caption("Δεν υπάρχουν έγκυρες τιμές για την οπτικοποίηση του 'Μέσου Δείγματος Εικόνας'.")
                    else:
                        fig_sample_disp = px.imshow(average_sample_img_display, color_continuous_scale="jet",
                                                    range_color=[avg_min_disp, avg_max_disp] if avg_min_disp < avg_max_disp else None,
                                                    labels={"color": "Τιμή Pixel"})
                        st.plotly_chart(fig_sample_disp, use_container_width=True, key=f"fig_sample_map{key_suffix}")
                        df_avg_sample_display = pd.DataFrame(average_sample_img_display)
                        add_excel_download_button(df_avg_sample_display, common_filename_prefix, "Average_Sample_Map", f"excel_avg_sample_map{key_suffix}")
                        st.caption(f"Μέση τιμή pixel (εμφάνιση: {display_option_val}).")
                except Exception as e: # Πιάνει πιθανά σφάλματα από nanmin/nanmax αν το array είναι προβληματικό
                    st.caption(f"Σφάλμα κατά την προετοιμασία του γραφήματος 'Μέσου Δείγματος Εικόνας': {e}")
            else: # average_sample_img_display.size == 0
                 st.caption("Δεν υπάρχουν δεδομένα για το 'Μέσο Δείγμα Εικόνας' (κενό μέγεθος πίνακα).")
        else: # average_sample_img_display is None or all NaN
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
                    df_time_max_map = pd.DataFrame(time_max_map)
                    add_excel_download_button(df_time_max_map, common_filename_prefix, "Time_Max_Value_Map", f"excel_time_max_map{key_suffix}")
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
                        indices_for_month_all_years = [
                            i for i, dt_obj in enumerate(DATES)
                            if dt_obj.month == month_num and (not selected_years_val or dt_obj.year in selected_years_val)
                        ]
                        if indices_for_month_all_years:
                            monthly_sum_in_range = np.sum(stack_full_in_range[indices_for_month_all_years, :, :], axis=0)
                            month_name_disp = month_options_map[month_num]
                            fig_month_disp = px.imshow(monthly_sum_in_range, color_continuous_scale="plasma", title=month_name_disp, labels={"color": "Ημέρες"})
                            fig_month_disp.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=350)
                            fig_month_disp.update_coloraxes(showscale=False)
                            cols_monthly[col_idx_monthly].plotly_chart(fig_month_disp, use_container_width=True, key=f"fig_month_{month_num}{key_suffix}")
                            df_monthly_sum = pd.DataFrame(monthly_sum_in_range)
                            add_excel_download_button(df_monthly_sum, common_filename_prefix, f"Monthly_Dist_{month_name_disp}", f"excel_month_{month_num}{key_suffix}")
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
                        indices_for_year_selected_months = [
                            i for i, dt_obj in enumerate(DATES)
                            if dt_obj.year == year_val and (not selected_months_val or dt_obj.month in selected_months_val)
                        ]
                        if indices_for_year_selected_months:
                            yearly_sum_in_range = np.sum(stack_full_in_range[indices_for_year_selected_months, :, :], axis=0)
                            fig_year_disp = px.imshow(yearly_sum_in_range, color_continuous_scale="plasma", title=f"Έτος: {year_val}", labels={"color": "Ημέρες"})
                            fig_year_disp.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=350)
                            fig_year_disp.update_coloraxes(showscale=False)
                            cols_yearly[col_idx_yearly].plotly_chart(fig_year_disp, use_container_width=True, key=f"fig_year_{year_val}{key_suffix}")
                            df_yearly_sum = pd.DataFrame(yearly_sum_in_range)
                            add_excel_download_button(df_yearly_sum, common_filename_prefix, f"Yearly_Dist_Year_{year_val}", f"excel_year_{year_val}{key_suffix}")
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
    if current_idx >= len(sorted_date_strings): # Handle empty or out-of-bounds index
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
            try: # Use Streamlit's theme colors if available
                theme_bg = st.get_option("theme.backgroundColor")
                theme_text = st.get_option("theme.textColor")
                legend_fig = create_chl_legend_figure(orientation="horizontal", theme_bg_color=theme_bg, theme_text_color=theme_text)
            except: # Fallback if theme options are not accessible (e.g., older Streamlit version)
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
        try: date_obj = datetime.datetime(int(m.groups()[0]), int(m.groups()[1]), int(m.groups()[2]))
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
            if not df_tmp.empty and len(df_tmp.columns) >=2:
                df_h_d['Date']=pd.to_datetime(df_tmp.iloc[:,0],errors='coerce'); df_h_d['Height']=pd.to_numeric(df_tmp.iloc[:,1],errors='coerce')
                df_h_d.dropna(inplace=True); df_h_d.sort_values(by='Date',inplace=True)
        except Exception as e: st.warning(f"Σφάλμα ανάγνωσης στάθμης (dashboard): {e}")
            
    fig_colors_d=make_subplots(specs=[[{"secondary_y":True}]])
    pts_plot = selected_point_names_for_plot if selected_point_names_for_plot else [p[0] for p in sampling_points]
    pt_y_idx={n:i for i,n in enumerate(pts_plot)}

    for n_iter in pts_plot:
        if n_iter in results_colors_dash and results_colors_dash[n_iter]:
            dts,cols=zip(*sorted(results_colors_dash[n_iter],key=lambda x:x[0])) if results_colors_dash[n_iter] else ([],[])
            c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
            fig_colors_d.add_trace(go.Scatter(x=list(dts),y=[pt_y_idx.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
    if not df_h_d.empty: fig_colors_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='blue',width=2),legendgroup="h_grp"),secondary_y=True)
    fig_colors_d.update_layout(title='Χρώματα Pixel & Στάθμη',xaxis_title='Ημερομηνία',
                                yaxis=dict(title='Σημεία',tickmode='array',tickvals=list(pt_y_idx.values()),ticktext=list(pt_y_idx.keys()),showgrid=False),
                                yaxis2=dict(title='Στάθμη (m)',showgrid=True,gridcolor='rgba(128,128,128,0.2)'),showlegend=True,uirevision='dashboard_colors')

    all_mg_vals_date_d={};
    for p_n in pts_plot: 
        if p_n in results_mg_dash:
            for d_obj,val_mg in results_mg_dash[p_n]: all_mg_vals_date_d.setdefault(d_obj,[]).append(val_mg)
    s_dates_mg_d=sorted(all_mg_vals_date_d.keys()); avg_mg_d=[np.mean(all_mg_vals_date_d[d_obj]) for d_obj in s_dates_mg_d if all_mg_vals_date_d[d_obj]]
    
    fig_mg_d=go.Figure();
    if s_dates_mg_d and avg_mg_d: fig_mg_d.add_trace(go.Scatter(x=s_dates_mg_d,y=avg_mg_d,mode='lines+markers',name='Μέσο mg/m³',marker=dict(color=avg_mg_d,colorscale='Viridis',reversescale=True,colorbar=dict(title='mg/m³',thickness=15),size=10),line=dict(color='grey')))
    fig_mg_d.update_layout(title='Μέσο mg/m³ (Επιλεγμένα Σημεία)',xaxis_title='Ημερομηνία',yaxis_title='mg/m³',uirevision='dashboard_mg')

    fig_dual_d=make_subplots(specs=[[{"secondary_y":True}]])
    if not df_h_d.empty: 
        fig_dual_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='deepskyblue')),secondary_y=False)
    if s_dates_mg_d and avg_mg_d: 
        fig_dual_d.add_trace(go.Scatter(x=s_dates_mg_d,y=avg_mg_d,name='Μέσο mg/m³',mode='lines+markers',marker=dict(color=avg_mg_d,colorscale='Viridis',showscale=False)),secondary_y=True)
    
    fig_dual_d.update_layout(
        title='Στάθμη & Μέσο mg/m³',
        xaxis_title='Ημερομηνία',
        uirevision='dashboard_dual', 
        yaxis=dict(title=dict(text="Στάθμη (m)", font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"),side='left'),
        yaxis2=dict(title=dict(text="mg/m³", font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"),overlaying='y', side='right')
    )
    
    return fig_geo_d,fig_dual_d,fig_colors_d,fig_mg_d,results_colors_dash,results_mg_dash,df_h_d


def run_predictive_tools(authenticator):
    st.title("Εργαλεία Πρόβλεψης")
    # Initialize session state variables if not present
    if "defined_points" not in st.session_state: # Though likely already done by main_app
        st.session_state.defined_points = []
    if "selected_points_names_for_plot" not in st.session_state:
        st.session_state.selected_points_names_for_plot = []
    if "common_filename_prefix_pred" not in st.session_state: # Specific key for predictive tools
        st.session_state.common_filename_prefix_pred = "predict_export_data"
    if "current_index_name_pred" not in st.session_state:
        st.session_state.current_index_name_pred = "PredictionIndex"
    if "sampling_points_pred" not in st.session_state: # Specific sampling points for prediction
         st.session_state.sampling_points_pred = []


    res_c_data_pred: Dict[str, Any] = {} # Initialize
    res_m_data_pred: Dict[str, Any] = {} # Initialize
    fig_d_pred: Optional[go.Figure] = None # Initialize
    df_h_pred: Optional[pd.DataFrame] = None # Initialize, or get from session state if calculated elsewhere
    results_colors_pred: Dict[str, Any] = {} # Initialize
    results_mg_pred: Dict[str, Any] = {} # Initialize
    fig_geo_pred: Optional[go.Figure] = None # Initialize

    current_sel_pts_def_names_for_plot: List[str] = st.session_state.selected_points_names_for_plot
    common_filename_prefix_dash: str = st.session_state.common_filename_prefix_pred
    index_name: str = st.session_state.current_index_name_pred
    sampling_points: List[Any] = st.session_state.sampling_points_pred


    # --- ΒΗΜΑ 1: Φόρτωση και προετοιμασία δεδομένων πρόβλεψης ---
    # Θα προσθέσουμε μια νέα συνάρτηση για να φορτώσουμε τα δεδομένα πρόβλεψης από τον αντίστοιχο φάκελο.
    # Αυτή η συνάρτηση θα είναι παρόμοια με τη load_data_for_lake_processing, αλλά θα επικεντρώνεται μόνο στα δεδομένα πρόβλεψης.

    @st.cache_data
    def load_prediction_data(input_folder: str, shapefile_name="shapefile.xml") -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[Any]], Optional[Dict[str, Any]]]:
        debug_message(f"DEBUG: load_prediction_data για: {input_folder}")
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
            img_data, _ = read_image(fp_iter, lake_shape=lake_geom) # lake_geom can be None, read_image handles Optional
            if img_data is not None: images.append(img_data); days.append(day_yr); dates_list.append(date_obj)

        if not images:
            st.warning(f"Δεν φορτώθηκαν έγκυρες εικόνες από τον φάκελο: {input_folder}."); return None, None, None, None
        return np.stack(images, axis=0), np.array(days), dates_list, first_profile

    # --- ΒΗΜΑ 2: Εκτέλεση ανάλυσης με βάση τα δεδομένα πρόβλεψης ---
    # Θα προσθέσουμε μια νέα συνάρτηση ανάλυσης που θα χρησιμοποιεί τα δεδομένα που φορτώθηκαν από τη load_prediction_data.
    # Αυτή η συνάρτηση θα είναι παρόμοια με τη analyze_sampling_for_dashboard, αλλά θα επικεντρώνεται μόνο στα δεδομένα πρόβλεψης.

    def analyze_prediction_for_dashboard(sampling_points: list, first_image_data_rgb, first_image_transform,
                                        images_folder_path: str, lake_height_excel_path: str, 
                                        selected_point_names_for_plot: list | None = None):
        results_colors_pred, results_mg_pred = {n:[] for n,_,_ in sampling_points}, {n:[] for n,_,_ in sampling_points}
        if not os.path.isdir(images_folder_path):
            st.error(f"Ο φάκελος εικόνων '{images_folder_path}' δεν βρέθηκε για dashboard."); return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

        for filename in sorted(os.listdir(images_folder_path)):
            if not filename.lower().endswith(('.tif', '.tiff')): continue
            m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
            if not m: continue
            try: date_obj = datetime.datetime(int(m.groups()[0]), int(m.groups()[1]), int(m.groups()[2]))
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
                            results_mg_pred[name].append((date_obj, mg_v))
                            results_colors_pred[name].append((date_obj, (r/255.,g/255.,b/255.)))
            except Exception as e: debug_message(f"Σφάλμα {filename} για dashboard: {e}"); continue
            
        if first_image_data_rgb is None or first_image_transform is None:
            st.error("Δεδομένα εικόνας αναφοράς (first_image_data_rgb / first_image_transform) δεν είναι διαθέσιμα.")
            return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

        rgb_disp_data = first_image_data_rgb.transpose((1,2,0))
        if rgb_disp_data.max() > 1:
            rgb_disp_data = rgb_disp_data / 255.0
        rgb_disp_data = np.clip(rgb_disp_data, 0, 1)

        fig_geo_pred = px.imshow(rgb_disp_data, title='Εικόνα Αναφοράς & Σημεία Δειγματοληψίας')
        for n,lon,lat in sampling_points:
            col,row=_geographic_to_pixel(lon,lat,first_image_transform)
            fig_geo_pred.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text', marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right", hovertemplate=f'<b>{n}</b><br>Lon:{lon:.4f}<br>Lat:{lat:.4f}<extra></extra>'))
        fig_geo_pred.update_xaxes(visible=False); fig_geo_pred.update_yaxes(visible=False,scaleanchor="x",scaleratio=1); fig_geo_pred.update_layout(height=600,showlegend=True,legend_title_text="Σημεία",uirevision='dashboard_geo')

        df_h_pred = pd.DataFrame(columns=['Date', 'Height']) 
        if os.path.exists(str(lake_height_excel_path)):
            try:
                df_tmp=pd.read_excel(lake_height_excel_path)
                if not df_tmp.empty and len(df_tmp.columns) >=2:
                    df_h_pred['Date']=pd.to_datetime(df_tmp.iloc[:,0],errors='coerce'); df_h_pred['Height']=pd.to_numeric(df_tmp.iloc[:,1],errors='coerce')
                    df_h_pred.dropna(inplace=True); df_h_pred.sort_values(by='Date',inplace=True)
            except Exception as e: st.warning(f"Σφάλμα ανάγνωσης στάθμης (dashboard): {e}")
            
    fig_colors_pred=make_subplots(specs=[[{"secondary_y":True}]])
    pts_plot_pred = selected_point_names_for_plot if selected_point_names_for_plot else [p[0] for p in sampling_points]
    pt_y_idx_pred={n:i for i,n in enumerate(pts_plot_pred)}

    for n_iter in pts_plot_pred:
        if n_iter in results_colors_pred and results_colors_pred[n_iter]:
            dts,cols=zip(*sorted(results_colors_pred[n_iter],key=lambda x:x[0])) if results_colors_pred[n_iter] else ([],[])
            c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
            fig_colors_pred.add_trace(go.Scatter(x=list(dts),y=[pt_y_idx_pred.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
    if not df_h_pred.empty: fig_colors_pred.add_trace(go.Scatter(x=df_h_pred['Date'],y=df_h_pred['Height'],name='Στάθμη',mode='lines',line=dict(color='blue',width=2),legendgroup="h_grp"),secondary_y=True)
    fig_colors_pred.update_layout(title='Χρώματα Pixel & Στάθμη',xaxis_title='Ημερομηνία',
                                yaxis=dict(title='Σημεία',tickmode='array',tickvals=list(pt_y_idx_pred.values()),ticktext=list(pt_y_idx_pred.keys()),showgrid=False),
                                yaxis2=dict(title='Στάθμη (m)',showgrid=True,gridcolor='rgba(128,128,128,0.2)'),showlegend=True,uirevision='dashboard_colors')

    all_mg_vals_date_pred={};
    for p_n in pts_plot_pred: 
        if p_n in results_mg_pred:
            for d_obj,val_mg in results_mg_pred[p_n]: all_mg_vals_date_pred.setdefault(d_obj,[]).append(val_mg)
    s_dates_mg_pred=sorted(all_mg_vals_date_pred.keys()); avg_mg_pred=[np.mean(all_mg_vals_date_pred[d_obj]) for d_obj in s_dates_mg_pred if all_mg_vals_date_pred[d_obj]]
    
    fig_mg_pred=go.Figure();
    if s_dates_mg_pred and avg_mg_pred: fig_mg_pred.add_trace(go.Scatter(x=s_dates_mg_pred,y=avg_mg_pred,mode='lines+markers',name='Μέσο mg/m³',marker=dict(color=avg_mg_pred,colorscale='Viridis',reversescale=True,colorbar=dict(title='mg/m³',thickness=15),size=10),line=dict(color='grey')))
    fig_mg_pred.update_layout(title='Μέσο mg/m³ (Επιλεγμένα Σημεία)',xaxis_title='Ημερομηνία',yaxis_title='mg/m³',uirevision='dashboard_mg')

    fig_dual_pred=make_subplots(specs=[[{"secondary_y":True}]])
    if not df_h_pred.empty: 
        fig_dual_pred.add_trace(go.Scatter(x=df_h_pred['Date'],y=df_h_pred['Height'],name='Στάθμη',mode='lines',line=dict(color='deepskyblue')),secondary_y=False)
    if s_dates_mg_pred and avg_mg_pred: 
        fig_dual_pred.add_trace(go.Scatter(x=s_dates_mg_pred,y=avg_mg_pred,name='Μέσο mg/m³',mode='lines+markers',marker=dict(color=avg_mg_pred,colorscale='Viridis',showscale=False)),secondary_y=True)
    
    fig_dual_pred.update_layout(
        title='Στάθμη & Μέσο mg/m³',
        xaxis_title='Ημερομηνία',
        uirevision='dashboard_dual', 
        yaxis=dict(title=dict(text="Στάθμη (m)", font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"),side='left'),
        yaxis2=dict(title=dict(text="mg/m³", font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"),overlaying='y', side='right')
    )
    
    # --- ΒΗΜΑ 3: Εμφάνιση αποτελεσμάτων πρόβλεψης σε νέες καρτέλες (tabs) ---
    # Θα προσθέσουμε νέες καρτέλες για να εμφανίσουμε τα αποτελέσματα της ανάλυσης με προβλέψεις.
    # Οι καρτέλες θα είναι παρόμοιες με αυτές που χρησιμοποιούνται για την ανάλυση δειγματοληψίας,
    # αλλά θα περιέχουν τα αποτελέσματα από τη analyze_prediction_for_dashboard.

    tabs_pred_ctrl = st.tabs(["GeoTIFF","Εικόνες","Video/GIF","Χρώματα Pixel","Μέσο mg/m³","Συνδυασμένο","mg/m³ ανά Σημείο"])
    
    with tabs_pred_ctrl[0]: 
        st.plotly_chart(fig_geo_pred, use_container_width=True, key=f"geo_pred_chart_disp")
        if current_def_pts_list:
            points_to_export_df = pd.DataFrame(
                [pt for pt in current_def_pts_list if pt[0] in current_sel_pts_def_names_for_plot],
                columns=['PointName', 'Longitude', 'Latitude']
            ) if current_sel_pts_def_names_for_plot else pd.DataFrame(current_def_pts_list, columns=['PointName', 'Longitude', 'Latitude'])
            
            if not points_to_export_df.empty:
                add_excel_download_button(points_to_export_df, f"{common_filename_prefix_dash}_pred", "Sampling Points", f"excel_geo_pred")
        if index_name == "Χλωροφύλλη": 
            try:
                theme_bg = st.get_option("theme.backgroundColor")
                theme_text = st.get_option("theme.textColor")
                st.pyplot(create_chl_legend_figure(theme_bg_color=theme_bg, theme_text_color=theme_text))
            except:
                st.pyplot(create_chl_legend_figure())

    with tabs_pred_ctrl[1]: 
        image_navigation_ui(images_folder_path,available_tifs,SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF,f"nav_def_disp_{key_suffix_dash}",index_name=="Χλωροφύλλη",index_name)
    with tabs_pred_ctrl[2]: 
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

    with tabs_pred_ctrl[3]: 
        c1_disp,c2_disp=st.columns([.85,.15])
        c1_disp.plotly_chart(fig_colors_pred, use_container_width=True, key=f"colors_pred_chart_disp")
        excel_sheets_pred_colors = {}
        if isinstance(df_h_pred, pd.DataFrame) and not df_h_pred.empty:
            excel_sheets_pred_colors['LakeHeight'] = df_h_pred.copy()
        if res_c_data_pred: 
            for point_name_rc, data_list_rc in res_c_data_pred.items():
                if data_list_rc and (point_name_rc in current_sel_pts_def_names_for_plot):
                    df_pt_colors = pd.DataFrame(data_list_rc, columns=['Date', 'RGB_Normalized'])
                    df_pt_colors['R_norm'] = df_pt_colors['RGB_Normalized'].apply(lambda x: x[0])
                    df_pt_colors['G_norm'] = df_pt_colors['RGB_Normalized'].apply(lambda x: x[1])
                    df_pt_colors['B_norm'] = df_pt_colors['RGB_Normalized'].apply(lambda x: x[2])
                    if not df_pt_colors.empty:
                        excel_sheets_pred_colors[f"{point_name_rc}_Colors"] = df_pt_colors[['Date', 'R_norm', 'G_norm', 'B_norm']].sort_values(by=['Date'])
        if excel_sheets_pred_colors:
                add_excel_download_button(excel_sheets_pred_colors, f"{common_filename_prefix_dash}_pred", "Pixel Colors and Height", f"excel_colors_pred")
        if index_name=="Χλωροφύλλη": 
            try:
                theme_bg = st.get_option("theme.backgroundColor")
                theme_text = st.get_option("theme.textColor")
                c2_disp.pyplot(create_chl_legend_figure("vertical", theme_bg_color=theme_bg, theme_text_color=theme_text))
            except:
                c2_disp.pyplot(create_chl_legend_figure("vertical"))

    with tabs_pred_ctrl[4]: 
        st.plotly_chart(fig_mg_pred, use_container_width=True, key=f"mg_pred_chart_disp")
        temp_all_mg_by_d_loc = {} 
        for p_name_temp in current_sel_pts_def_names_for_plot:
            if p_name_temp in res_m_data_pred:
                for d_obj_temp, val_mg_temp in res_m_data_pred[p_name_temp]:
                    temp_all_mg_by_d_loc.setdefault(d_obj_temp, []).append(val_mg_temp)
        
        s_dts_mg_temp_loc = sorted(temp_all_mg_by_d_loc.keys())
        mean_mg_temp_loc = [np.mean(temp_all_mg_by_d_loc[d]) for d in s_dts_mg_temp_loc if temp_all_mg_by_d_loc[d]]
        st.session_state[f's_dts_mg_pred'] = s_dts_mg_temp_loc 
        st.session_state[f'mean_mg_pred'] = mean_mg_temp_loc

        if s_dts_mg_temp_loc and mean_mg_temp_loc:
            df_mean_mg = pd.DataFrame({'Date': s_dts_mg_temp_loc, 'Mean_mg_m3': mean_mg_temp_loc}).sort_values(by='Date')
            add_excel_download_button(df_mean_mg, f"{common_filename_prefix_dash}_pred", "Mean mg_m3 (Selected Points)", f"excel_mean_mg_pred")

    with tabs_pred_ctrl[5]: 
        st.plotly_chart(fig_d_pred, use_container_width=True, key=f"dual_pred_chart_disp")
        s_dts_mg_for_dual = st.session_state.get(f's_dts_mg_pred', []) 
        mean_mg_for_dual = st.session_state.get(f'mean_mg_pred', []) 
        df_mean_mg_for_dual = pd.DataFrame({'Date': s_dts_mg_for_dual, 'Mean_mg_m3': mean_mg_for_dual}) if s_dts_mg_for_dual and mean_mg_for_dual else pd.DataFrame(columns=['Date', 'Mean_mg_m3'])
        df_dual_export = pd.DataFrame()
        if isinstance(df_h_pred, pd.DataFrame) and not df_h_pred.empty:
            df_dual_export = df_h_pred.copy()
        if not df_mean_mg_for_dual.empty:
            if not df_dual_export.empty:
                df_dual_export = pd.merge(df_dual_export, df_mean_mg_for_dual, on='Date', how='outer')
            else:
                df_dual_export = df_mean_mg_for_dual
        if not df_dual_export.empty:
            df_dual_export.sort_values(by='Date', inplace=True, ignore_index=True)
            add_excel_download_button(df_dual_export, f"{common_filename_prefix_dash}_pred", "Height and Mean mg_m3", f"excel_dual_pred")

    with tabs_pred_ctrl[6]:
        point_options_for_detail = current_sel_pts_def_names_for_plot
        if not point_options_for_detail: 
                st.caption("Δεν έχουν επιλεγεί σημεία για εμφάνιση.")
        else:
            sel_pt_d_disp = st.selectbox("Σημείο για mg/m³:", point_options_for_detail, key=f"detail_d_sel_disp")
            if sel_pt_d_disp and res_m_data_pred.get(sel_pt_d_disp): 
                mg_d_p_list = sorted(res_m_data_pred[sel_pt_d_disp], key=lambda x: x[0])
                if mg_d_p_list: 
                    dts_detail, vals_detail = zip(*mg_d_p_list)
                    max_val_detail = max(vals_detail) if vals_detail else 1 
                    mk_cols_detail = px.colors.sample_colorscale("Viridis", [v/(max_val_detail if max_val_detail > 0 else 1) for v in vals_detail])
                    fig_det_d_disp = go.Figure(go.Scatter(x=list(dts_detail),y=list(vals_detail),mode='lines+markers',marker=dict(color=mk_cols_detail,size=10),line=dict(color="grey"),name=sel_pt_d_disp))
                    fig_det_d_disp.update_layout(title=f"mg/m³ για {sel_pt_d_disp}",xaxis_title="Ημερομηνία",yaxis_title="mg/m³")
                    st.plotly_chart(fig_det_d_disp,use_container_width=True, key=f"detail_d_chart_disp")

                    df_point_mg_detail = pd.DataFrame({'Date': list(dts_detail), f'mg_m3': list(vals_detail)}).sort_values(by="Date")
                    add_excel_download_button(df_point_mg_detail, f"{common_filename_prefix_dash}_pred_point_{sel_pt_d_disp}", f"mg_m3 for {sel_pt_d_disp}", f"excel_detail_mg_pred_{sel_pt_d_disp}")
                else: st.caption(f"Δεν υπάρχουν επεξεργασμένα δεδομένα mg/m³ για το σημείο '{sel_pt_d_disp}'.")
            elif sel_pt_d_disp: st.caption(f"Δεν βρέθηκαν δεδομένα mg/m³ για το σημείο '{sel_pt_d_disp}'.")
            else: st.caption("Παρακαλώ επιλέξτε ένα σημείο.")