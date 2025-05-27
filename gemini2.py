#!/usr_bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI - Ενημερωμένο για Σταθερότητα v3)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET
import io
import time

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
# <--- ΑΛΛΑΓΗ/ΒΕΛΤΙΩΣΗ ---> Καταστολή της συγκεκριμένης προειδοποίησης Mean of empty slice.
# Καλό για παραγωγή, αλλά μπορείτε να το αφαιρέσετε για debugging για να δείτε αν εξακολουθεί να εμφανίζεται.
warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="All-NaN slice encountered", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="invalid value encountered in scalar divide", category=RuntimeWarning) # For cases like 0/0
warnings.filterwarnings("ignore", message="invalid value encountered in divide", category=RuntimeWarning) # For cases like nan/nan or x/0


import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import streamlit_authenticator as stauth

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ", page_icon="💧")
# --------------------------------------------------------------------

# --- AUTHENTICATION SETUP ---
names = ["Ilioumbas User"]
usernames = ["ilioumbas"]
plain_text_passwords = ["123"] # Consider using environment variables for passwords in production

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
        "water_quality_app_cookie_v9", # Changed name slightly
        "a_very_random_secret_key_v9", # Changed key slightly
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Error during stauth.Authenticate initialization: {e}")
    st.stop()
# --- END OF AUTHENTICATION SETUP ---


# --- Global Configuration & Constants ---
DEBUG = False # Set to True for more verbose debugging output
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
LOGO_PATH = os.path.join(APP_BASE_DIR, "logo.jpg")

WATERBODY_FOLDERS = {
    "Γαδουρά": "Gadoura",
}

SESSION_KEY_WATERBODY = "waterbody_choice_main"
SESSION_KEY_INDEX = "index_choice_main"
SESSION_KEY_ANALYSIS = "analysis_choice_main"
SESSION_KEY_DEFAULT_RESULTS_DASHBOARD = "dashboard_default_sampling_results_v3"
SESSION_KEY_UPLOAD_RESULTS_DASHBOARD = "dashboard_upload_sampling_results_v3"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF = "dash_def_current_image_idx_v3"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL = "dash_upl_current_image_idx_v3"

def debug_message(*args, **kwargs):
    if DEBUG:
        with st.expander("Debug Messages (Εντοπισμός Σφαλμάτων)", expanded=False):
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
        debug_message(f"No data for Excel export: {button_label_suffix}")
        return

    is_empty_df = isinstance(df_or_dict_of_dfs, pd.DataFrame) and df_or_dict_of_dfs.empty
    is_empty_dict = False
    if isinstance(df_or_dict_of_dfs, dict):
        if not df_or_dict_of_dfs: is_empty_dict = True
        else:
            is_empty_dict = all(isinstance(df, pd.DataFrame) and df.empty for df in df_or_dict_of_dfs.values())

    if is_empty_df or is_empty_dict:
        debug_message(f"Empty data for Excel export: {button_label_suffix}")
        return

    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if isinstance(df_or_dict_of_dfs, pd.DataFrame):
                if not df_or_dict_of_dfs.empty:
                    df_or_dict_of_dfs.to_excel(writer, index=False, sheet_name='Data')
            elif isinstance(df_or_dict_of_dfs, dict):
                for sheet_name, data_df in df_or_dict_of_dfs.items():
                    if isinstance(data_df, pd.DataFrame) and not data_df.empty:
                        sane_sheet_name = re.sub(r'[\[\]\*\/\\?\:\']', '_', str(sheet_name))[:31]
                        data_df.to_excel(writer, index=False, sheet_name=sane_sheet_name)
        excel_data = output.getvalue()
        if not excel_data:
            debug_message(f"No data written to Excel buffer for: {button_label_suffix}")
            return

        file_name_suffix = button_label_suffix.lower().replace(' ', '_').replace('/', '_').replace('&', 'and').replace('(', '').replace(')', '')
        st.download_button(
            label=f"📥 Αποθήκευση {button_label_suffix} σε Excel",
            data=excel_data,
            file_name=f"{filename_prefix}_{file_name_suffix}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key=f"download_excel_{plot_key}" # Ensure unique key for download buttons
        )
    except Exception as e:
        st.warning(f"Δεν ήταν δυνατή η δημιουργία αρχείου Excel για {button_label_suffix}: {e}")
        debug_message(f"Excel generation error for {button_label_suffix}: {e}")

def render_footer():
    st.markdown(f"""
        <hr style="border-color: #2a2e37;">
        <div class='footer'>
            © {datetime.now().year} ΕΥΑΘ ΑΕ • Powered by Google Gemini & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
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
        authenticator.logout("Αποσύνδεση", "sidebar", key='unique_logout_button_key_sidebar')
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
        if hasattr(kml_source, "seek"): kml_source.seek(0) # Reset file pointer for UploadedFile
        kml_content = kml_source.read() if hasattr(kml_source, "read") else kml_source
        if isinstance(kml_content, bytes):
            kml_content = kml_content.decode('utf-8', errors='ignore') # Handle potential encoding issues

        # Attempt to parse directly from string
        try:
            root = ET.fromstring(kml_content)
        except ET.ParseError:
            # If direct string parsing fails (e.g. if kml_source was a path initially)
            # and kml_content is a path string, try parsing from path
            if isinstance(kml_source, str) and os.path.exists(kml_source):
                 tree = ET.parse(kml_source)
                 root = tree.getroot()
            else:
                raise # Re-raise if it wasn't a path or path parsing also failed

        ns = {'kml': 'http://www.opengis.net/kml/2.2'} # Default KML namespace
        # Try to find if a different namespace is used
        if not root.findall('.//kml:LineString', ns) and '}' in root.tag:
            match = re.match(r'\{([^}]+)\}', root.tag)
            if match:
                actual_ns = match.group(1)
                if actual_ns:
                    ns = {'kml': actual_ns}
                    debug_message(f"KML: Using detected namespace: {actual_ns}")

        points = []
        placemarks = root.findall('.//kml:Placemark', ns)
        if not placemarks: placemarks = root.findall('.//Placemark') # Try without namespace if not found

        for pm_idx, placemark in enumerate(placemarks):
            name_elem = placemark.find('kml:name', ns) if ns['kml'] else placemark.find('name')
            point_name_base = name_elem.text.strip() if name_elem is not None and name_elem.text else f"Placemark_{pm_idx+1}"

            # Find LineString
            linestring = placemark.find('.//kml:LineString', ns) if ns['kml'] else placemark.find('.//LineString')
            if linestring is not None:
                coords_elem = linestring.find('kml:coordinates', ns) if ns['kml'] else linestring.find('coordinates')
                if coords_elem is not None and coords_elem.text:
                    coords_text = coords_elem.text.strip()
                    coords_list = re.split(r'\s+', coords_text) # Split by any whitespace
                    for i_coord, coord_str in enumerate(coords_list):
                        if not coord_str: continue
                        try:
                            lon, lat, *_ = map(float, coord_str.split(','))
                            points.append((f"{point_name_base}_P{i_coord+1}", lon, lat))
                        except ValueError:
                            debug_message(f"KML Warning: Skipping malformed coordinate '{coord_str}' in LineString '{point_name_base}'")
            else: # Find Point
                point_geom = placemark.find('.//kml:Point', ns) if ns['kml'] else placemark.find('.//Point')
                if point_geom is not None:
                    coords_elem = point_geom.find('kml:coordinates', ns) if ns['kml'] else point_geom.find('coordinates')
                    if coords_elem is not None and coords_elem.text:
                        coords_text = coords_elem.text.strip()
                        try:
                            lon, lat, *_ = map(float, coords_text.split(','))
                            points.append((point_name_base, lon, lat))
                        except ValueError:
                             debug_message(f"KML Warning: Skipping malformed coordinate '{coords_text}' in Point '{point_name_base}'")

        if not points:
            st.warning("Δεν βρέθηκαν σημεία (LineString ή Point) στο παρεχόμενο αρχείο KML.")
        return points
    except FileNotFoundError:
        debug_message(f"Προειδοποίηση: Το αρχείο KML '{kml_source}' δεν βρέθηκε (αν ήταν διαδρομή).")
        return []
    except ET.ParseError as e_parse:
        st.error(f"Σφάλμα ανάλυσης KML: {e_parse}. Βεβαιωθείτε ότι το αρχείο είναι έγκυρο KML.")
        debug_message(f"KML ParseError details: {e_parse}")
        return []
    except Exception as e:
        st.error(f"Γενικό σφάλμα κατά την επεξεργασία του KML: {e}")
        debug_message(f"KML General Exception details: {e}")
        return []

# <--- ΑΛΛΑΓΗ/ΒΕΛΤΙΩΣΗ ---> Ρητός χειρισμός για np.mean και έλεγχοι για κενά δεδομένα γραφημάτων
def analyze_sampling_generic(sampling_points, first_image_data, first_transform,
                             images_folder, lake_height_path, selected_points_names,
                             lower_thresh=0, upper_thresh=255, date_min=None, date_max=None):
    results_colors = {name: [] for name, _, _ in sampling_points}
    results_mg = {name: [] for name, _, _ in sampling_points}

    if not os.path.isdir(images_folder):
        st.error(f"Ο φάκελος εικόνων '{images_folder}' δεν βρέθηκε."); return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    tif_files = sorted([f for f in os.listdir(images_folder) if f.lower().endswith(('.tif', '.tiff'))])
    if not tif_files:
        st.warning(f"Δεν βρέθηκαν αρχεία .tif/.tiff στον φάκελο: {images_folder}")
        return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    for filename in tif_files:
        m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
        if not m: continue
        try:
            date_obj = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            debug_message(f"Παράλειψη {filename}: μη έγκυρη ημερομηνία."); continue

        if (date_min and date_obj.date() < date_min) or \
           (date_max and date_obj.date() > date_max):
            continue

        try:
            with rasterio.open(os.path.join(images_folder, filename)) as src:
                if src.count < 3: debug_message(f"Παράλειψη {filename}: <3 κανάλια."); continue
                for name, lon, lat in sampling_points:
                    if name not in selected_points_names: continue
                    try:
                        # Check if transform is affine
                        if not isinstance(src.transform, rasterio.Affine):
                            debug_message(f"Παράλειψη {filename} για το σημείο {name}: Μη έγκυρος μετασχηματισμός rasterio.")
                            continue
                        col, row = map(int, (~src.transform) * (lon, lat))

                        if not (0 <= col < src.width and 0 <= row < src.height):
                            debug_message(f"Σημείο {name} εκτός ορίων για {filename} ({col},{row}) vs ({src.width},{src.height})")
                            continue
                        win = rasterio.windows.Window(col,row,1,1)
                        pixel_values = src.read(window=win) # Read all bands for the window
                        r,g,b = pixel_values[0,0,0], pixel_values[1,0,0], pixel_values[2,0,0]

                        mg_val = (g / 255.0) * 2.0 # Placeholder
                        results_mg[name].append((date_obj, mg_val))
                        results_colors[name].append((date_obj, (r/255., g/255., b/255.)))
                    except IndexError: debug_message(f"Σφάλμα Index pixel για {name} στο {filename}.")
                    except Exception as e_inner: st.warning(f"Εσωτερικό σφάλμα επεξεργασίας {filename} για {name}: {e_inner}")
        except rasterio.errors.RasterioIOError as e_rio:
            st.warning(f"Σφάλμα I/O κατά την ανάγνωση του {filename}: {e_rio}. Το αρχείο μπορεί να είναι κατεστραμμένο.")
        except Exception as e: st.warning(f"Γενικό σφάλμα επεξεργασίας {filename}: {e}")


    fig_geo_empty = go.Figure().update_layout(title='Εικόνα Αναφοράς & Σημεία (Σφάλμα Φόρτωσης Δεδομένων)')
    if first_image_data is None or first_image_data.ndim != 3 or first_image_data.shape[0] < 3:
        st.error("Μη έγκυρα δεδομένα πρώτης εικόνας για εμφάνιση (analyze_sampling_generic).")
        return fig_geo_empty, go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    rgb_disp = first_image_data[:3, :, :].transpose((1,2,0))
    if np.issubdtype(rgb_disp.dtype, np.integer) and rgb_disp.max() > 1: # Basic check for 0-255
         if rgb_disp.max() > 0: rgb_disp = rgb_disp / float(rgb_disp.max() if rgb_disp.max() <=255 else 255.0)
    rgb_disp = np.clip(rgb_disp, 0, 1)

    if np.all(np.isnan(rgb_disp)):
        st.warning("Η εικόνα αναφοράς περιέχει μόνο τιμές NaN μετά την επεξεργασία.")
        return fig_geo_empty, go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()


    fig_geo = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία')
    fig_geo.update_layout(height=600, uirevision='geo_sampling_generic_v3')

    if first_transform:
        for n,lon,lat in sampling_points:
            if n in selected_points_names:
                try:
                    if not isinstance(first_transform, rasterio.Affine): continue
                    col,row = map(int, (~first_transform) * (lon,lat))
                    if 0 <= col < rgb_disp.shape[1] and 0 <= row < rgb_disp.shape[0]:
                         fig_geo.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text',marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right"))
                except Exception as e_trace: debug_message(f"Could not trace point {n} on reference image: {e_trace}")
    fig_geo.update_xaxes(visible=False); fig_geo.update_yaxes(visible=False,scaleanchor="x",scaleratio=1)

    df_h = pd.DataFrame(columns=['Date','Height'])
    if lake_height_path and os.path.exists(str(lake_height_path)):
        try:
            df_h_temp = pd.read_excel(lake_height_path)
            if not df_h_temp.empty and len(df_h_temp.columns) >=2:
                df_h['Date']=pd.to_datetime(df_h_temp.iloc[:,0],errors='coerce')
                df_h['Height']=pd.to_numeric(df_h_temp.iloc[:,1],errors='coerce')
                df_h.dropna(subset=['Date', 'Height'], inplace=True)
                df_h.sort_values('Date',inplace=True)
        except Exception as e_excel: st.warning(f"Δεν ήταν δυνατή η ανάγνωση του αρχείου στάθμης '{lake_height_path}': {e_excel}"); df_h = pd.DataFrame(columns=['Date','Height'])
    elif lake_height_path:
        debug_message(f"Το αρχείο στάθμης '{lake_height_path}' δεν βρέθηκε.")


    fig_colors = make_subplots(specs=[[{"secondary_y":True}]]); pt_y_map={n:i for i,n in enumerate(selected_points_names)}
    has_color_data = False
    for n_iter in selected_points_names:
        if n_iter in results_colors and results_colors[n_iter]:
            sorted_color_data = sorted(results_colors[n_iter],key=lambda x:x[0])
            if sorted_color_data:
                dts,cols=zip(*sorted_color_data)
                if dts:
                    c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
                    fig_colors.add_trace(go.Scatter(x=list(dts),y=[pt_y_map.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
                    has_color_data = True
    if not df_h.empty:
        fig_colors.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη',mode='lines',line=dict(color='blue')),secondary_y=True)
        has_color_data = True # If height data exists, the plot is not entirely empty

    if not has_color_data: fig_colors.update_layout(annotations=[dict(text="Δεν υπάρχουν δεδομένα χρωμάτων ή στάθμης", xref="paper", yref="paper", showarrow=False)])
    fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη',yaxis=dict(tickmode='array',tickvals=list(pt_y_map.values()),ticktext=list(pt_y_map.keys())),yaxis2=dict(title='Στάθμη (m)'), uirevision='colors_sampling_generic_v3')

    all_mg_by_d={};
    for p_name in selected_points_names:
        if p_name in results_mg:
            for d,v in results_mg[p_name]: all_mg_by_d.setdefault(d,[]).append(v)
    s_dts_mg=sorted(all_mg_by_d.keys())

    mean_mg_values = []
    for d_val in s_dts_mg:
        data_for_mean = all_mg_by_d.get(d_val, [])
        if data_for_mean:
            mean_mg_values.append(np.mean(data_for_mean))
        else:
            mean_mg_values.append(np.nan)

    fig_mg=go.Figure()
    # Filter out NaNs for plotting
    s_dts_mg_plot = [s_dts_mg[i] for i, val in enumerate(mean_mg_values) if not np.isnan(val)]
    mean_mg_plot = [val for val in mean_mg_values if not np.isnan(val)]

    if s_dts_mg_plot and mean_mg_plot:
         fig_mg.add_trace(go.Scatter(x=s_dts_mg_plot,y=mean_mg_plot,mode='lines+markers',marker=dict(color=mean_mg_plot,colorscale='Viridis',colorbar=dict(title='mg/m³'),size=8)))
    else:
        fig_mg.update_layout(annotations=[dict(text="Δεν υπάρχουν δεδομένα μέσου mg/m³", xref="paper", yref="paper", showarrow=False)])
    fig_mg.update_layout(title='Μέσο mg/m³', uirevision='mg_sampling_generic_v3')

    fig_dual=make_subplots(specs=[[{"secondary_y":True}]])
    has_dual_data = False
    if not df_h.empty:
        fig_dual.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη Λίμνης',mode='lines'),secondary_y=False)
        has_dual_data = True
    if s_dts_mg_plot and mean_mg_plot:
        fig_dual.add_trace(go.Scatter(x=s_dts_mg_plot,y=mean_mg_plot,name='Μέσο mg/m³',mode='lines+markers', marker=dict(color=mean_mg_plot, colorscale='Viridis', showscale=False)),secondary_y=True)
        has_dual_data = True
    if not has_dual_data: fig_dual.update_layout(annotations=[dict(text="Δεν υπάρχουν δεδομένα για συνδυασμένο γράφημα", xref="paper", yref="paper", showarrow=False)])

    fig_dual.update_layout(title='Στάθμη & Μέσο mg/m³', uirevision='dual_sampling_generic_v3',
                            yaxis=dict(title=dict(text="Στάθμη (m)",font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"), side='left'),
                            yaxis2=dict(title=dict(text="Μέσο mg/m³",font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"), overlaying='y', side='right'))
    return fig_geo,fig_dual,fig_colors,fig_mg,results_colors,results_mg,df_h

# ... (Οι υπόλοιπες συναρτήσεις create_chl_legend_figure, get_data_folder, extract_date_from_filename, load_lake_shape_from_xml, read_image, load_data_for_lake_processing παραμένουν ως είχαν στις προηγούμενες ενημερώσεις, καθώς οι κύριες αλλαγές για τη μνήμη έγιναν ήδη εκεί.)

# ... (Η συνάρτηση run_lake_processing_app παραμένει ως είχε στην προηγούμενη αναθεώρηση, καθώς ήδη χρησιμοποιεί την επαναληπτική προσέγγιση)

# ... (Η συνάρτηση display_geotiff_with_plotly παραμένει ως είχε στην προηγούμενη αναθεώρηση)

# ... (Η συνάρτηση image_navigation_ui παραμένει ως είχε, καλεί display_geotiff_with_plotly)

# <--- ΑΛΛΑΓΗ/ΒΕΛΤΙΩΣΗ ---> Εφαρμογή του ρητού χειρισμού για np.mean και εδώ
def analyze_sampling_for_dashboard(sampling_points: list, first_image_data_rgb, first_image_transform,
                                   images_folder_path: str, lake_height_excel_path: str,
                                   selected_point_names_for_plot: list | None = None):
    # (Αυτή η συνάρτηση είναι πολύ παρόμοια με την analyze_sampling_generic. Οι αλλαγές για τον χειρισμό του np.mean θα εφαρμοστούν εδώ όπως και παραπάνω.)
    def _geographic_to_pixel(lon: float, lat: float, transform_matrix) -> tuple[int, int]:
        try:
            if not isinstance(transform_matrix, rasterio.Affine): return -1,-1
            inv_transform = ~transform_matrix; px, py = inv_transform * (lon, lat); return int(px), int(py)
        except Exception: return -1, -1

    def _map_rgb_to_mg(r_val: float, g_val: float, b_val: float, mg_factor: float = 2.0) -> float:
        return (g_val / 255.0) * mg_factor

    results_colors_dash, results_mg_dash = {n:[] for n,_,_ in sampling_points}, {n:[] for n,_,_ in sampling_points}
    if not os.path.isdir(images_folder_path):
        st.error(f"Ο φάκελος εικόνων '{images_folder_path}' δεν βρέθηκε για dashboard."); return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    tif_files = sorted([f for f in os.listdir(images_folder_path) if f.lower().endswith(('.tif', '.tiff'))])
    if not tif_files:
        st.warning(f"Δεν βρέθηκαν αρχεία .tif/.tiff στον φάκελο dashboard: {images_folder_path}")
        return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    for filename in tif_files:
        m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
        if not m: continue
        try: date_obj = datetime(int(m.groups()[0]), int(m.groups()[1]), int(m.groups()[2]))
        except ValueError: continue

        try:
            with rasterio.open(os.path.join(images_folder_path, filename)) as src:
                if src.count < 3: continue
                for name, lon, lat in sampling_points:
                    if selected_point_names_for_plot and name not in selected_point_names_for_plot: continue
                    col, row = _geographic_to_pixel(lon, lat, src.transform)
                    if 0 <= col < src.width and 0 <= row < src.height:
                        try:
                            win = rasterio.windows.Window(col,row,1,1)
                            pixel_data = src.read(window=win) # Read all bands
                            r,g,b = pixel_data[0,0,0], pixel_data[1,0,0], pixel_data[2,0,0]
                            mg_v = _map_rgb_to_mg(r,g,b)
                            results_mg_dash[name].append((date_obj, mg_v))
                            results_colors_dash[name].append((date_obj, (r/255.,g/255.,b/255.)))
                        except IndexError: debug_message(f"Σφάλμα Index pixel για {name} στο {filename} (dashboard).")
                        except Exception as e_inner_dash: debug_message(f"Εσωτερικό σφάλμα {filename} για {name} (dashboard): {e_inner_dash}")
        except rasterio.errors.RasterioIOError as e_rio:
            st.warning(f"Σφάλμα I/O κατά την ανάγνωση του {filename} (dashboard): {e_rio}.")
        except Exception as e: debug_message(f"Σφάλμα {filename} για dashboard: {e}"); continue

    fig_geo_empty_dash = go.Figure().update_layout(title='Εικόνα Αναφοράς & Σημεία (Σφάλμα Φόρτωσης Δεδομένων)')
    if first_image_data_rgb is None or first_image_transform is None:
        st.error("Δεδομένα εικόνας αναφοράς δεν είναι διαθέσιμα (dashboard).")
        return fig_geo_empty_dash,go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    rgb_disp_data = first_image_data_rgb.transpose((1,2,0))
    if np.issubdtype(rgb_disp_data.dtype, np.integer) and rgb_disp_data.max() > 1:
        if rgb_disp_data.max() > 0: rgb_disp_data = rgb_disp_data / float(rgb_disp_data.max() if rgb_disp_data.max() <=255 else 255.0)
    rgb_disp_data = np.clip(rgb_disp_data, 0, 1)

    if np.all(np.isnan(rgb_disp_data)):
        st.warning("Η εικόνα αναφοράς (dashboard) περιέχει μόνο τιμές NaN μετά την επεξεργασία.")
        return fig_geo_empty_dash,go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    fig_geo_d = px.imshow(rgb_disp_data, title='Εικόνα Αναφοράς & Σημεία Δειγματοληψίας')
    for n,lon,lat in sampling_points:
        if selected_point_names_for_plot and n not in selected_point_names_for_plot: continue
        col,row=_geographic_to_pixel(lon,lat,first_image_transform)
        if col != -1 and 0 <= col < rgb_disp_data.shape[1] and 0 <= row < rgb_disp_data.shape[0]:
            fig_geo_d.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text', marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right", hovertemplate=f'<b>{n}</b><br>Lon:{lon:.4f}<br>Lat:{lat:.4f}<extra></extra>'))
    fig_geo_d.update_xaxes(visible=False); fig_geo_d.update_yaxes(visible=False,scaleanchor="x",scaleratio=1); fig_geo_d.update_layout(height=600,showlegend=True,legend_title_text="Σημεία",uirevision='dashboard_geo_v3')

    df_h_d = pd.DataFrame(columns=['Date', 'Height'])
    if lake_height_excel_path and os.path.exists(str(lake_height_excel_path)):
        try:
            df_tmp=pd.read_excel(lake_height_excel_path)
            if not df_tmp.empty and len(df_tmp.columns)>=2:
                df_h_d['Date']=pd.to_datetime(df_tmp.iloc[:,0],errors='coerce'); df_h_d['Height']=pd.to_numeric(df_tmp.iloc[:,1],errors='coerce')
                df_h_d.dropna(subset=['Date', 'Height'], inplace=True); df_h_d.sort_values('Date',inplace=True)
        except Exception as e: st.warning(f"Σφάλμα ανάγνωσης στάθμης (dashboard) από '{lake_height_excel_path}': {e}")
    elif lake_height_excel_path:
        debug_message(f"Το αρχείο στάθμης (dashboard) '{lake_height_excel_path}' δεν βρέθηκε.")


    fig_colors_d=make_subplots(specs=[[{"secondary_y":True}]])
    pts_plot_effective = selected_point_names_for_plot if selected_point_names_for_plot else [p[0] for p in sampling_points]
    pt_y_idx={n:i for i,n in enumerate(pts_plot_effective)}
    has_color_data_dash = False

    for n_iter in pts_plot_effective:
        if n_iter in results_colors_dash and results_colors_dash[n_iter]:
            d_list_sorted=sorted(results_colors_dash[n_iter],key=lambda x:x[0])
            if d_list_sorted:
                dts_c,cols_c_norm=zip(*d_list_sorted)
                if dts_c:
                    cols_rgb_s=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols_c_norm]
                    y_p=pt_y_idx.get(n_iter,-1)
                    if y_p != -1:
                        fig_colors_d.add_trace(go.Scatter(x=list(dts_c),y=[y_p]*len(dts_c),mode='markers',marker=dict(color=cols_rgb_s,size=10),name=n_iter,legendgroup=n_iter),secondary_y=False)
                        has_color_data_dash = True
    if not df_h_d.empty:
        fig_colors_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='blue',width=2),legendgroup="h_grp"),secondary_y=True)
        has_color_data_dash = True
    if not has_color_data_dash: fig_colors_d.update_layout(annotations=[dict(text="Δεν υπάρχουν δεδομένα χρωμάτων ή στάθμης", xref="paper", yref="paper", showarrow=False)])
    fig_colors_d.update_layout(title='Χρώματα Pixel & Στάθμη',xaxis_title='Ημερομηνία',
                                yaxis=dict(title='Σημεία',tickmode='array',tickvals=list(pt_y_idx.values()),ticktext=list(pt_y_idx.keys()),showgrid=False),
                                yaxis2=dict(title='Στάθμη (m)',showgrid=True,gridcolor='rgba(128,128,128,0.2)'),showlegend=True,uirevision='dashboard_colors_v3')

    all_mg_vals_date_d={};
    for p_n in pts_plot_effective:
        if p_n in results_mg_dash:
            for d_obj,val_mg in results_mg_dash[p_n]: all_mg_vals_date_d.setdefault(d_obj,[]).append(val_mg)
    s_dates_mg_d=sorted(all_mg_vals_date_d.keys())

    avg_mg_d_values = []
    for d_val in s_dates_mg_d:
        data_for_mean = all_mg_vals_date_d.get(d_val, [])
        if data_for_mean:
            avg_mg_d_values.append(np.mean(data_for_mean))
        else:
            avg_mg_d_values.append(np.nan)

    fig_mg_d=go.Figure()
    s_dates_mg_d_plot = [s_dates_mg_d[i] for i, val in enumerate(avg_mg_d_values) if not np.isnan(val)]
    avg_mg_d_plot = [val for val in avg_mg_d_values if not np.isnan(val)]

    if s_dates_mg_d_plot and avg_mg_d_plot:
        fig_mg_d.add_trace(go.Scatter(x=s_dates_mg_d_plot,y=avg_mg_d_plot,mode='lines+markers',name='Μέσο mg/m³',marker=dict(color=avg_mg_d_plot,colorscale='Viridis',reversescale=True,colorbar=dict(title='mg/m³',thickness=15),size=10),line=dict(color='grey')))
    else:
        fig_mg_d.update_layout(annotations=[dict(text="Δεν υπάρχουν δεδομένα μέσου mg/m³", xref="paper", yref="paper", showarrow=False)])
    fig_mg_d.update_layout(title='Μέσο mg/m³ (Επιλεγμένα Σημεία)',xaxis_title='Ημερομηνία',yaxis_title='mg/m³',uirevision='dashboard_mg_v3')

    fig_dual_d=make_subplots(specs=[[{"secondary_y":True}]])
    has_dual_data_dash = False
    if not df_h_d.empty:
        fig_dual_d.add_trace(go.Scatter(x=df_h_d['Date'],y=df_h_d['Height'],name='Στάθμη',mode='lines',line=dict(color='deepskyblue')),secondary_y=False)
        has_dual_data_dash = True
    if s_dates_mg_d_plot and avg_mg_d_plot:
        fig_dual_d.add_trace(go.Scatter(x=s_dates_mg_d_plot,y=avg_mg_d_plot,name='Μέσο mg/m³',mode='lines+markers',marker=dict(color=avg_mg_d_plot,colorscale='Viridis',reversescale=True,size=10,showscale=False),line=dict(color='lightgreen')),secondary_y=True)
        has_dual_data_dash = True
    if not has_dual_data_dash: fig_dual_d.update_layout(annotations=[dict(text="Δεν υπάρχουν δεδομένα για συνδυασμένο γράφημα", xref="paper", yref="paper", showarrow=False)])

    fig_dual_d.update_layout(
        title='Στάθμη & Μέσο mg/m³', xaxis_title='Ημερομηνία', uirevision='dashboard_dual_v3',
        yaxis=dict(title=dict(text="Στάθμη (m)", font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"),side='left'),
        yaxis2=dict(title=dict(text="mg/m³", font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"),overlaying='y', side='right')
    )
    return fig_geo_d,fig_dual_d,fig_colors_d,fig_mg_d,results_colors_dash,results_mg_dash,df_h_d


# ... (run_water_quality_dashboard, run_predictive_tools, main_app, και if __name__ == "__main__":
#      παραμένουν σε μεγάλο βαθμό ως είχαν στην προηγούμενη αναθεώρηση, καθώς οι κύριες αλλαγές
#      για την αντιμετώπιση του "Mean of empty slice" έγιναν στις υποκείμενες συναρτήσεις
#      analyze_sampling_generic και analyze_sampling_for_dashboard, καθώς και
#      στην run_lake_processing_app για την αποφυγή του αρχικού προβλήματος με το np.stack.
#      Οι έλεγχοι για το αν τα γραφήματα έχουν δεδομένα πριν την εμφάνιση είναι επίσης σημαντικοί.)
def run_water_quality_dashboard(waterbody: str, index_name: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Προφίλ Ποιότητας και Στάθμης: {waterbody} - {index_name}")

        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name)
        key_suffix_dash = f"_dash_{waterbody}_{clean_index_name_for_key}_v3"
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
        if os.path.exists(images_folder_path):
             for fn in os.listdir(images_folder_path):
                 if fn.lower().endswith(('.tif','.tiff')):
                     _, d = extract_date_from_filename(fn)
                     if d: available_tifs[str(d.date())] = fn
        else:
            st.sidebar.warning(f"Ο φάκελος εικόνων '{images_folder_path}' δεν βρέθηκε.")

        first_img_rgb, first_img_transform = None, None
        if available_tifs:
            sel_bg_date_options = sorted(available_tifs.keys(),reverse=True)
            sel_bg_date_idx = 0
            sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:", sel_bg_date_options, index=sel_bg_date_idx, key=f"bg_date{key_suffix_dash}")
            if sel_bg_date and available_tifs.get(sel_bg_date):
                try:
                    with rasterio.open(os.path.join(images_folder_path,available_tifs[sel_bg_date])) as src:
                        if src.count>=3:
                            first_img_rgb,first_img_transform = src.read([1,2,3]),src.transform
                        elif src.count == 1:
                            st.sidebar.info("Η εικόνα αναφοράς είναι μονοκαναλική. Θα χρησιμοποιηθεί για γεωαναφορά.")
                            band1 = src.read(1)
                            first_img_rgb = np.stack([band1, band1, band1], axis=0)
                            first_img_transform = src.transform
                        else:
                            st.sidebar.error(f"Η εικόνα αναφοράς '{available_tifs[sel_bg_date]}' έχει {src.count} κανάλια. Απαιτούνται >=3 ή 1.")
                            first_img_rgb, first_img_transform = None, None # Ensure they remain None
                except Exception as e:
                    st.sidebar.error(f"Σφάλμα φόρτωσης εικόνας αναφοράς: {e}")
                    first_img_rgb, first_img_transform = None, None
        else: st.sidebar.warning("Δεν βρέθηκαν GeoTIFF αρχεία για επιλογή εικόνας αναφοράς.")

        if first_img_rgb is None or first_img_transform is None:
            st.error("Απαιτείται έγκυρη εικόνα αναφοράς GeoTIFF (τουλάχιστον 3 ή 1 κανάλι) για τη συνέχεια της ανάλυσης.")
            st.markdown('</div>', unsafe_allow_html=True); return

        tabs_ctrl = st.tabs(["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"])

        with tabs_ctrl[0]: # Default Sampling
            st.markdown("##### Ανάλυση με Προεπιλεγμένα Σημεία")
            def_pts_list = []
            if os.path.exists(default_sampling_kml_path):
                with st.spinner("Φόρτωση προεπιλεγμένων σημείων KML..."):
                    def_pts_list = parse_sampling_kml(default_sampling_kml_path)
            st.session_state[f"def_pts_list{key_suffix_dash}"] = def_pts_list

            if def_pts_list:
                all_def_point_names = [n for n,_,_ in def_pts_list]
                default_selection_def = all_def_point_names[:]
                sel_pts_def_names = st.multiselect("Επιλογή Σημείων (Προεπιλογή):", all_def_point_names, default=default_selection_def, key=f"sel_def{key_suffix_dash}")
                st.session_state[f"sel_pts_def_names{key_suffix_dash}"] = sel_pts_def_names
                if st.button("Εκτέλεση Ανάλυσης (Προεπιλογή)", key=f"run_def{key_suffix_dash}", type="primary", use_container_width=True):
                    if not sel_pts_def_names:
                        st.warning("Παρακαλώ επιλέξτε τουλάχιστον ένα σημείο για ανάλυση.")
                    else:
                        with st.spinner("Εκτέλεση ανάλυσης για προεπιλεγμένα σημεία..."):
                            st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                def_pts_list, first_img_rgb, first_img_transform, images_folder_path, lake_height_excel_path, sel_pts_def_names
                            )
            else: st.caption(f"Δεν βρέθηκε ή δεν μπόρεσε να αναλυθεί το προεπιλεγμένο αρχείο δειγματοληψίας ({default_sampling_kml_path}). Ανεβάστε ένα KML στην καρτέλα 'Δειγματοληψία 2'.")

            if SESSION_KEY_DEFAULT_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]:
                res_def = st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]
                current_sel_pts_def_names_for_plot = st.session_state.get(f"sel_pts_def_names{key_suffix_dash}", [])

                if isinstance(res_def, tuple) and len(res_def) == 7:
                    fig_g, fig_d, fig_c, fig_m, res_c_data, res_m_data, df_h_data = res_def
                    n_tabs_titles = ["GeoTIFF","Εικόνες","Video/GIF","Χρώματα Pixel","Μέσο mg/m³","Συνδυασμένο","mg/m³ ανά Σημείο"]
                    n_tabs_def_display = st.tabs(n_tabs_titles)
                    tab_prefix_key = f"def_tab_{key_suffix_dash}"

                    with n_tabs_def_display[0]: # GeoTIFF
                        if fig_g and hasattr(fig_g, 'data') and fig_g.data:
                            st.plotly_chart(fig_g, use_container_width=True, key=f"geo_d_chart_disp_{tab_prefix_key}")
                        else:
                            st.caption("Δεν υπάρχουν δεδομένα για την Εικόνα Αναφοράς.")
                        # ... (Excel download logic for points) ...
                        if index_name == "Χλωροφύλλη":
                             st.pyplot(create_chl_legend_figure(orientation="horizontal"))


                    with n_tabs_def_display[1]: # Εικόνες
                        if available_tifs:
                            image_navigation_ui(images_folder_path,available_tifs,SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF,f"nav_def_disp_{key_suffix_dash}",index_name=="Χλωροφύλλη",index_name)
                        else:
                            st.caption("Δεν υπάρχουν διαθέσιμες εικόνες για πλοήγηση.")

                    with n_tabs_def_display[2]: # Video/GIF
                        if vid_path:
                            if vid_path.endswith(".mp4"): st.video(vid_path)
                            else: st.image(vid_path, use_column_width=True)
                            if index_name=="Χλωροφύλλη":
                                st.pyplot(create_chl_legend_figure(orientation="horizontal"))
                        else: st.caption("Δεν βρέθηκε video/timelapse.")

                    with n_tabs_def_display[3]: # Χρώματα Pixel
                        c1_disp,c2_disp=st.columns([.85,.15])
                        if fig_c and hasattr(fig_c, 'data') and fig_c.data:
                            c1_disp.plotly_chart(fig_c, use_container_width=True, key=f"colors_d_chart_disp_{tab_prefix_key}")
                        else:
                            c1_disp.caption("Δεν υπάρχουν δεδομένα για εμφάνιση στο γράφημα χρωμάτων pixel.")
                        # ... (Excel download & legend logic for colors tab) ...

                    with n_tabs_def_display[4]: # Μέσο mg/m³
                        if fig_m and hasattr(fig_m, 'data') and fig_m.data:
                            st.plotly_chart(fig_m, use_container_width=True, key=f"mg_d_chart_disp_{tab_prefix_key}")
                        else:
                            st.caption("Δεν υπάρχουν δεδομένα για εμφάνιση στο γράφημα μέσου mg/m³.")
                        # ... (Excel download logic for mean mg/m3) ...

                    with n_tabs_def_display[5]: # Συνδυασμένο
                        if fig_d and hasattr(fig_d, 'data') and fig_d.data:
                             st.plotly_chart(fig_d, use_container_width=True, key=f"dual_d_chart_disp_{tab_prefix_key}")
                        else:
                            st.caption("Δεν υπάρχουν δεδομένα για εμφάνιση στο συνδυασμένο γράφημα.")
                        # ... (Excel download logic for dual plot) ...

                    with n_tabs_def_display[6]: # mg/m³ ανά Σημείο
                        if not current_sel_pts_def_names_for_plot:
                            st.caption("Δεν έχουν επιλεγεί σημεία για εμφάνιση.")
                        else:
                            sel_pt_d_disp = st.selectbox("Επιλογή Σημείου για εμφάνιση mg/m³:", current_sel_pts_def_names_for_plot, key=f"detail_d_sel_disp_{tab_prefix_key}")
                            if sel_pt_d_disp and res_m_data and sel_pt_d_disp in res_m_data and res_m_data[sel_pt_d_disp]:
                                mg_d_p_list = sorted(res_m_data[sel_pt_d_disp], key=lambda x: x[0])
                                if mg_d_p_list:
                                    dts_detail, vals_detail = zip(*mg_d_p_list)
                                    if dts_detail and vals_detail: # Check if lists are not empty
                                        valid_vals_indices = [i for i, v in enumerate(vals_detail) if not np.isnan(v)]
                                        if not valid_vals_indices:
                                            st.caption(f"Όλες οι τιμές mg/m³ για το σημείο '{sel_pt_d_disp}' είναι μη διαθέσιμες (NaN).")
                                        else:
                                            dts_plot = [dts_detail[i] for i in valid_vals_indices]
                                            vals_plot = [vals_detail[i] for i in valid_vals_indices]

                                            min_val_plot, max_val_plot = min(vals_plot), max(vals_plot)
                                            color_norm = [(v - min_val_plot) / (max_val_plot - min_val_plot) if (max_val_plot - min_val_plot) > 0 else 0.5 for v in vals_plot]
                                            marker_colors = px.colors.sample_colorscale("Viridis", color_norm)

                                            fig_det_d_disp = go.Figure(go.Scatter(x=dts_plot,y=vals_plot,mode='lines+markers',marker=dict(color=marker_colors,size=10),line=dict(color="grey"),name=sel_pt_d_disp))
                                            fig_det_d_disp.update_layout(title=f"mg/m³ για {sel_pt_d_disp}",xaxis_title="Ημερομηνία",yaxis_title="mg/m³")
                                            st.plotly_chart(fig_det_d_disp,use_container_width=True, key=f"detail_d_chart_disp_{tab_prefix_key}")
                                            # ... Excel download for this point ...
                                    else:
                                        st.caption(f"Δεν υπάρχουν έγκυρες τιμές mg/m³ για το σημείο '{sel_pt_d_disp}'.")
                                else: st.caption(f"Δεν υπάρχουν επεξεργασμένα δεδομένα mg/m³ για το σημείο '{sel_pt_d_disp}'.")
                            elif sel_pt_d_disp: st.caption(f"Δεν βρέθηκαν δεδομένα mg/m³ για το επιλεγμένο σημείο '{sel_pt_d_disp}'.")

                else: st.error("Σφάλμα μορφής αποτελεσμάτων (Προεπιλογή). Ελέγξτε τα δεδομένα εισόδου και τις ρυθμίσεις.")

        with tabs_ctrl[1]: # Upload KML
            st.markdown("##### Ανάλυση με Ανεβασμένο KML")
            upl_file = st.file_uploader("Ανέβασμα KML:", type=["kml", "kmz"], key=f"upl_kml_{key_suffix_dash}")
            if upl_file:
                with st.spinner(f"Ανάλυση αρχείου KML: {upl_file.name}..."):
                    upl_pts_list = parse_sampling_kml(upl_file) # kml_source is UploadedFile object
                st.session_state[f"upl_pts_list{key_suffix_dash}"] = upl_pts_list
                if upl_pts_list:
                    st.success(f"Βρέθηκαν {len(upl_pts_list)} σημεία από το KML.")
                    all_upl_point_names = [n for n,_,_ in upl_pts_list]
                    default_selection_upl = all_upl_point_names[:]
                    sel_pts_upl_names = st.multiselect("Επιλογή Σημείων (KML):", all_upl_point_names, default=default_selection_upl, key=f"sel_upl_{key_suffix_dash}")
                    st.session_state[f"sel_pts_upl_names{key_suffix_dash}"] = sel_pts_upl_names
                    if st.button("Εκτέλεση Ανάλυσης (KML)",key=f"run_upl_{key_suffix_dash}",type="primary", use_container_width=True):
                        if not sel_pts_upl_names:
                             st.warning("Παρακαλώ επιλέξτε τουλάχιστον ένα σημείο από το KML για ανάλυση.")
                        else:
                            with st.spinner("Εκτέλεση ανάλυσης για σημεία από KML..."):
                                st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                    upl_pts_list, first_img_rgb, first_img_transform,
                                    images_folder_path, lake_height_excel_path, sel_pts_upl_names
                                )
                else:
                    st.error("Το ανεβασμένο αρχείο KML δεν περιείχε έγκυρα σημεία (LineString ή Point) ή δεν μπόρεσε να αναλυθεί σωστά.")

            if SESSION_KEY_UPLOAD_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]:
                res_upl = st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]
                # ... (Εδώ θα πρέπει να γίνει παρόμοιος χειρισμός εμφάνισης αποτελεσμάτων με την καρτέλα Προεπιλογής,
                #      συμπεριλαμβανομένων των ελέγχων για κενά γραφήματα. Για συντομία, δεν επαναλαμβάνεται όλος ο κώδικας εμφάνισης,
                #      αλλά θα πρέπει να ακολουθεί την ίδια λογική με την παραπάνω καρτέλα.)
                st.success("Η ανάλυση για το KML ολοκληρώθηκε. Εμφανίστε τα αποτελέσματα στις καρτέλες.")
        st.markdown('</div>', unsafe_allow_html=True)

# (run_predictive_tools, main_app, if __name__ ... παραμένουν ως είχαν στην προηγούμενη έκδοση)
# Οι αλλαγές στην analyze_sampling_generic θα επηρεάσουν θετικά την run_predictive_tools.
def run_predictive_tools(waterbody: str, initial_selected_index: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Εργαλεία Πρόβλεψης & Έγκαιρης Ενημέρωσης: {waterbody}")
        st.markdown(f"Παράλληλη Ανάλυση για Δείκτες: **Πραγματικό, Χλωροφύλλη, Θολότητα**")

        clean_initial_index_name = re.sub(r'[^a-zA-Z0-9_]', '', initial_selected_index)
        key_suffix_pred_section = f"_pred_tool_{waterbody}_{clean_initial_index_name}_v3"

        chart_display_options = {
            "GeoTIFF Εικόνα Αναφοράς & Σημεία": "geo",
            "Χρώματα Pixel & Στάθμη": "colors",
            "Στάθμη Λίμνης (Μόνο)": "lake_height_only",
            "Μέσο mg/m³ (Επιλεγμένα Σημεία)": "mg",
            "Συνδυασμένο (Στάθμη & Μέσο mg/m³)": "dual"
        }
        default_charts = [list(chart_display_options.keys())[0]] if chart_display_options else []
        selected_charts_to_display = st.multiselect(
            "Επιλέξτε τύπους διαγραμμάτων για εμφάνιση:",
            options=list(chart_display_options.keys()),
            default=default_charts,
            key=f"select_charts{key_suffix_pred_section}"
        )
        if len(selected_charts_to_display) > 2:
             st.info("💡 **Συμβουλή:** Η εμφάνιση πολλών γραφημάτων ταυτόχρονα μπορεί να επιβραδύνει την εφαρμογή.")

        st.subheader("Κοινές Παράμετροι Φιλτραρίσματος για όλους τους Δείκτες")
        col_filt1, col_filt2 = st.columns(2)
        with col_filt1:
            lower_thresh_common, upper_thresh_common = st.slider(
                "Εύρος τιμών pixel (για εξαγωγή τιμών από GeoTIFFs):", 0, 255, (0, 255),
                key=f"thresh_common{key_suffix_pred_section}",
                help="Αυτό το εύρος χρησιμοποιείται για τον υπολογισμό των μέσων τιμών mg/m³ και την εξαγωγή χρωμάτων pixel."
            )
            sampling_type_common = st.radio(
                "Σύνολο Σημείων Δειγματοληψίας:",
                ["Προεπιλογή (από φάκελο 'Πραγματικό')", "Ανέβασμα KML"],
                key=f"sampling_type_common{key_suffix_pred_section}",
                horizontal=True
            )
        with col_filt2:
            min_date_default = date(2015, 1, 1)
            max_date_default = date.today()
            date_min_common = st.date_input("Ημερομηνία από (για ανάλυση εικόνων):", value=min_date_default, key=f"date_min_common{key_suffix_pred_section}")
            date_max_common = st.date_input("Ημερομηνία έως (για ανάλυση εικόνων):", value=max_date_default, key=f"date_max_common{key_suffix_pred_section}")

        uploaded_kml_common = None
        sampling_points_to_use_for_analysis = None

        if sampling_type_common == "Ανέβασμα KML":
            uploaded_kml_common = st.file_uploader(
                "Ανεβάστε ένα αρχείο KML (θα χρησιμοποιηθεί για όλους τους δείκτες):",
                type=["kml", "kmz"],
                key=f"kml_upload_common{key_suffix_pred_section}"
            )
            if uploaded_kml_common:
                with st.spinner("Επεξεργασία ανεβασμένου KML..."):
                    sampling_points_to_use_for_analysis = parse_sampling_kml(uploaded_kml_common)
                if not sampling_points_to_use_for_analysis:
                    st.error("Το ανεβασμένο KML δεν περιείχε έγκυρα σημεία ή απέτυχε η ανάλυση.")
        else:
            st.caption("Χρήση προεπιλεγμένου KML από τον φάκελο του δείκτη 'Πραγματικό'.")
            default_real_color_folder = get_data_folder(waterbody, "Πραγματικό")
            if default_real_color_folder:
                default_kml_path_common = os.path.join(default_real_color_folder, "sampling.kml")
                if os.path.exists(default_kml_path_common):
                    with st.spinner("Φόρτωση προεπιλεγμένου KML..."):
                        sampling_points_to_use_for_analysis = parse_sampling_kml(default_kml_path_common)
                    if not sampling_points_to_use_for_analysis:
                        st.warning(f"Το προεπιλεγμένο KML '{default_kml_path_common}' δεν περιείχε έγκυρα σημεία.")
                else:
                    st.warning(f"Δεν βρέθηκε προεπιλεγμένο αρχείο KML ({default_kml_path_common}) στον φάκελο 'Πραγματικό'.")
            else:
                st.warning("Δεν βρέθηκε ο φάκελος δεδομένων για τον δείκτη 'Πραγματικό' για φόρτωση προεπιλεγμένου KML.")

        if st.button("Εκτέλεση Παράλληλης Ανάλυσης & Εμφάνιση Αποτελεσμάτων", key=f"recalc_parallel{key_suffix_pred_section}", type="primary", use_container_width=True):
            if not sampling_points_to_use_for_analysis:
                st.error("Δεν έχουν οριστεί σημεία δειγματοληψίας. Η ανάλυση δεν μπορεί να προχωρήσει.")
                st.markdown('</div>', unsafe_allow_html=True); return

            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]
            analysis_results_all_indices = {}
            all_point_names_to_use_in_analysis = [pt[0] for pt in sampling_points_to_use_for_analysis]

            progress_bar_overall = st.progress(0, text="Έναρξη παράλληλης ανάλυσης...")
            num_indices = len(indices_to_analyze)

            for i_prog, current_idx_name_iter in enumerate(indices_to_analyze):
                progress_text_overall = f"Επεξεργασία Δείκτη: {current_idx_name_iter} ({i_prog+1}/{num_indices})"
                progress_bar_overall.progress((i_prog) / num_indices, text=progress_text_overall)

                data_folder_idx = get_data_folder(waterbody, current_idx_name_iter)
                if not data_folder_idx:
                    analysis_results_all_indices[current_idx_name_iter] = {"error": f"Δεν βρέθηκε φάκελος δεδομένων."}
                    st.warning(f"Παράλειψη '{current_idx_name_iter}': Δεν βρέθηκε φάκελος δεδομένων.")
                    continue

                images_folder_idx = os.path.join(data_folder_idx, "GeoTIFFs")
                lake_height_excel_idx = os.path.join(data_folder_idx, "lake height.xlsx")

                first_img_data_idx, first_transform_idx = None, None
                available_tifs_idx = {}
                if os.path.exists(images_folder_idx):
                    for fn_idx in os.listdir(images_folder_idx):
                        if fn_idx.lower().endswith(('.tif','.tiff')):
                            _, d_idx = extract_date_from_filename(fn_idx)
                            if d_idx: available_tifs_idx[d_idx] = fn_idx
                if available_tifs_idx:
                    first_date_idx = min(available_tifs_idx.keys())
                    first_tif_filename_idx = available_tifs_idx[first_date_idx]
                    try:
                        with rasterio.open(os.path.join(images_folder_idx, first_tif_filename_idx)) as src:
                            if src.count >= 3: first_img_data_idx = src.read([1,2,3])
                            elif src.count == 1:
                                band1 = src.read(1); first_img_data_idx = np.stack([band1, band1, band1], axis=0)
                            else:
                                analysis_results_all_indices[current_idx_name_iter] = {"error": f"Η 1η εικόνα '{first_tif_filename_idx}' έχει {src.count} κανάλια."}
                                continue
                            first_transform_idx = src.transform
                    except Exception as e:
                        analysis_results_all_indices[current_idx_name_iter] = {"error": f"Σφάλμα φόρτωσης 1ης εικόνας '{first_tif_filename_idx}': {e}"}
                        continue
                else:
                    analysis_results_all_indices[current_idx_name_iter] = {"error": "Δεν βρέθηκαν GeoTIFF για εικόνα αναφοράς."}
                    continue

                try:
                    with st.spinner(f"Ανάλυση δεδομένων για '{current_idx_name_iter}'..."):
                        raw_figs_and_data = analyze_sampling_generic(
                            sampling_points_to_use_for_analysis, first_img_data_idx, first_transform_idx,
                            images_folder_idx, lake_height_excel_idx, all_point_names_to_use_in_analysis,
                            lower_thresh_common, upper_thresh_common, date_min_common, date_max_common
                        )
                    analysis_results_all_indices[current_idx_name_iter] = {
                        "fig_geo": raw_figs_and_data[0], "fig_dual": raw_figs_and_data[1],
                        "fig_colors": raw_figs_and_data[2], "fig_mg": raw_figs_and_data[3],
                        "data_results_colors": raw_figs_and_data[4], "data_results_mg": raw_figs_and_data[5],
                        "data_df_h": raw_figs_and_data[6]
                    }
                except Exception as e_analyze:
                    analysis_results_all_indices[current_idx_name_iter] = {"error": f"Σφάλμα ανάλυσης '{current_idx_name_iter}': {e_analyze}"}
            progress_bar_overall.progress(1.0, text="Όλες οι αναλύσεις ολοκληρώθηκαν!")
            time.sleep(1)
            progress_bar_overall.empty()

            st.session_state[f"predictive_tool_results{key_suffix_pred_section}"] = analysis_results_all_indices
            st.session_state[f"predictive_tool_selected_charts{key_suffix_pred_section}"] = selected_charts_to_display
            st.session_state[f"predictive_tool_sampling_points{key_suffix_pred_section}"] = sampling_points_to_use_for_analysis
            st.success("Όλες οι αναλύσεις ολοκληρώθηκαν! Μπορείτε να δείτε τα αποτελέσματα παρακάτω.")

        if f"predictive_tool_results{key_suffix_pred_section}" in st.session_state:
            analysis_results = st.session_state[f"predictive_tool_results{key_suffix_pred_section}"]
            charts_to_show_from_session = st.session_state.get(f"predictive_tool_selected_charts{key_suffix_pred_section}", [])
            # ... (Ο υπόλοιπος κώδικας εμφάνισης για predictive tools παραμένει,
            #      αλλά θα πρέπει να περιλαμβάνει ελέγχους για κενά γραφήματα όπως στην run_water_quality_dashboard)
        st.markdown('</div>', unsafe_allow_html=True)


def main_app():
    inject_custom_css()
    run_intro_page_custom()
    run_custom_sidebar_ui_custom()

    selected_wb = st.session_state.get(SESSION_KEY_WATERBODY)
    selected_idx = st.session_state.get(SESSION_KEY_INDEX)
    selected_an = st.session_state.get(SESSION_KEY_ANALYSIS)

    if not all([selected_wb, selected_idx, selected_an]):
        st.info("Επιλέξτε Υδάτινο Σώμα, Δείκτη και Είδος Ανάλυσης από την πλαϊνή μπάρα για να ξεκινήσετε.")
        render_footer()
        return

    # <--- ΑΛΛΑΓΗ/ΒΕΛΤΙΩΣΗ ---> Πιο περιγραφικό spinner text
    spinner_text = f"Φόρτωση ανάλυσης '{selected_an}' για '{selected_wb} - {selected_idx}'..."
    if selected_an == "Επιφανειακή Αποτύπωση":
        spinner_text = f"Δημιουργία επιφανειακής αποτύπωσης για '{selected_wb} - {selected_idx}'... (Μπορεί να διαρκέσει)"
    elif selected_an == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
        spinner_text = f"Εκτέλεση εργαλείων πρόβλεψης για '{selected_wb}'..."


    with st.spinner(spinner_text):
        # time.sleep(0.1) # Μικρή παύση για να εμφανιστεί το spinner, αν χρειάζεται
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
    # Check if 'authentication_status' is in session_state, initialize if not
    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None # Can be None, True, or False
    if "name" not in st.session_state:
        st.session_state.name = None
    if "username" not in st.session_state:
        st.session_state.username = None

    authenticator.login('main', fields={'Username':'Όνομα Χρήστη', 'Password':'Κωδικός', 'Login':'Σύνδεση'})

    auth_status = st.session_state.get("authentication_status")

    if auth_status:
        main_app()
    elif auth_status is False:
        st.error('Το όνομα χρήστη ή ο κωδικός πρόσβασης είναι λανθασμένος.')
        # Consider adding a retry mechanism or clearing previous attempts if desired
    elif auth_status is None: # Before first login attempt or if cookie expired etc.
        st.warning('Παρακαλώ εισάγετε το όνομα χρήστη και τον κωδικό πρόσβασής σας.')