#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI - Performance Enhanced)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET
import io
import gc # Garbage Collector interface
import psutil # For memory monitoring
import warnings

import numpy as np
import pandas as pd
import rasterio
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rasterio.errors import NotGeoreferencedWarning
from rasterio.enums import Resampling
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import streamlit_authenticator as stauth

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Υδάτων ΕΥΑΘ", page_icon="💧")
# --------------------------------------------------------------------

# --- Performance & Resource Management ---
def check_memory_usage(threshold=80.0):
    """Monitor memory usage and warn if high."""
    try:
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > threshold:
            st.warning(f"⚠️ Υψηλή χρήση μνήμης: {memory_percent:.1f}%. Η εφαρμογή μπορεί να επιβραδυνθεί.")
            return False
    except Exception as e:
        debug_message(f"DEBUG: Δεν ήταν δυνατός ο έλεγχος της μνήμης: {e}")
    return True

def periodic_gc_and_cache_clear():
    """Run garbage collection and clear cache periodically."""
    if 'run_counter' not in st.session_state:
        st.session_state.run_counter = 0
    st.session_state.run_counter += 1

    gc.collect() # Force GC on every run

    # Clear cache every 50 runs or so (adjust as needed)
    if st.session_state.run_counter % 50 == 0:
        st.cache_data.clear()
        st.cache_resource.clear()
        st.toast("🧹 Ο προσωρινός χώρος αποθήκευσης (cache) καθαρίστηκε για βελτιστοποίηση της μνήμης.")
        st.session_state.run_counter = 0

def safe_process_wrapper(func):
    """Decorator to handle memory errors gracefully."""
    def wrapper(*args, **kwargs):
        if not check_memory_usage():
            st.error("Ανεπαρκής μνήμη. Μειώστε το εύρος δεδομένων ή τα φίλτρα.")
            return None # Indicate failure
        try:
            result = func(*args, **kwargs)
            gc.collect() # Clean up after processing
            return result
        except MemoryError:
            st.error("Προέκυψε σφάλμα μνήμης. Δοκιμάστε με μικρότερο σύνολο δεδομένων.")
            gc.collect()
            return None
        except Exception as e:
            st.error(f"Προέκυψε σφάλμα κατά την επεξεργασία: {e}")
            debug_message(f"ERROR in {func.__name__}: {e}")
            gc.collect()
            return None
    return wrapper

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
    st.error("Σφάλμα: Οι λίστες ονομάτων, χρηστών και κωδικών πρέπει να έχουν το ίδιο μέγεθος.")
    st.stop()

authenticator = None
try:
    authenticator = stauth.Authenticate(
        credentials,
        "water_quality_app_cookie_v7", # Changed cookie name
        "a_very_random_secret_key_v7", # Changed key
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Σφάλμα αρχικοποίησης Authenticate: {e}")
    st.stop()
# --- END OF AUTHENTICATION SETUP ---

# --- Global Configuration & Constants ---
DEBUG = False # Set to True for verbose debug messages
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
LOGO_PATH = os.path.join(APP_BASE_DIR, "logo.jpg")

WATERBODY_FOLDERS = {
    "Γαδουρά": "Gadoura",
}

# Session keys (unchanged)
SESSION_KEY_WATERBODY = "waterbody_choice_main"
SESSION_KEY_INDEX = "index_choice_main"
SESSION_KEY_ANALYSIS = "analysis_choice_main"
SESSION_KEY_DEFAULT_RESULTS_DASHBOARD = "dashboard_default_sampling_results_light" # Renamed
SESSION_KEY_UPLOAD_RESULTS_DASHBOARD = "dashboard_upload_sampling_results_light" # Renamed
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF = "dash_def_current_image_idx"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL = "dash_upl_current_image_idx"

def debug_message(*args, **kwargs):
    if DEBUG:
        with st.expander("Debug Messages", expanded=False):
            st.write(*args, **kwargs)

def inject_custom_css():
    st.markdown("""
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
    """, unsafe_allow_html=True)

def add_excel_download_button(df_or_dict_of_dfs, filename_prefix: str, button_label_suffix: str, plot_key: str):
    """Generates and provides a download button for Excel files."""
    if df_or_dict_of_dfs is None: return
    is_empty_df = isinstance(df_or_dict_of_dfs, pd.DataFrame) and df_or_dict_of_dfs.empty
    is_empty_dict = isinstance(df_or_dict_of_dfs, dict) and (not df_or_dict_of_dfs or all(df.empty for df in df_or_dict_of_dfs.values() if isinstance(df, pd.DataFrame)))
    if is_empty_df or is_empty_dict: return

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
        excel_data = output.getvalue()
        if not excel_data: return

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
                - **Επιλογή Παραμέτρων:** Στην πλαϊνή μπάρα (αριστερά), επιλέξτε το υδάτινο σώμα, τον δείκτη ποιότητας και το είδος της ανάλυσης.
                - **Πλοήγηση:** Μετά την επιλογή, τα αποτελέσματα θα εμφανιστούν. Χρησιμοποιήστε τις καρτέλες (tabs).
                - **Προσαρμοσμένη Δειγματοληψία:** Ανεβάστε KML για ανάλυση σε συγκεκριμένα σημεία.
                - **Φίλτρα:** Χρησιμοποιήστε τα φίλτρα για να προσαρμόσετε τα αποτελέσματα.
                - **Επεξηγήσεις:** Κάντε κλικ στα ℹ️ για πληροφορίες.
                - **Ασφάλεια:** Τα δεδομένα επεξεργάζονται τοπικά.
                """)
        st.markdown('</div>', unsafe_allow_html=True)

def run_custom_sidebar_ui_custom():
    global authenticator
    if authenticator and st.session_state.get("authentication_status"):
        st.sidebar.success(f"Συνδεθήκατε ως: {st.session_state.get('name', 'N/A')}")
        authenticator.logout("Αποσύνδεση", "sidebar", key='unique_logout_button_key')
        st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    st.sidebar.markdown("<div class='nav-section'><h4>🛠️ Επιλογές Ανάλυσης</h4></div>", unsafe_allow_html=True)
    st.sidebar.info("❔ Επιλέξτε τις ρυθμίσεις σας!")

    waterbody = st.sidebar.selectbox("🌊 Υδάτινο σώμα", list(WATERBODY_FOLDERS.keys()), key=SESSION_KEY_WATERBODY)
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

@st.cache_data(ttl=3600) # Cache KML parsing for 1 hour
def parse_sampling_kml(kml_source) -> list:
    """Parses KML to extract LineString coordinates."""
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
                        points.append((f"LS{i_ls+1}_P{i_coord+1}", float(lon), float(lat)))
                    except ValueError: debug_message(f"Warning: KML: Παράλειψη '{coord_str}'")
        if not points: st.warning("Δεν βρέθηκαν σημεία LineString στο KML.")
        return points
    except FileNotFoundError: return []
    except Exception as e:
        st.error(f"Σφάλμα ανάλυσης KML: {e}")
        return []

@st.cache_data(ttl=3600) # Cache data folder path
def get_data_folder(waterbody: str, index_name: str) -> str | None:
    """Constructs and validates the data folder path."""
    waterbody_folder_name = WATERBODY_FOLDERS.get(waterbody)
    if not waterbody_folder_name: return None

    index_map = {"Πραγματικό": "Πραγματικό", "Χλωροφύλλη": "Chlorophyll", "Θολότητα": "Θολότητα"}
    index_specific_folder = index_map.get(index_name, index_name)

    data_folder = os.path.join(APP_BASE_DIR, waterbody_folder_name, index_specific_folder)
    return data_folder if os.path.isdir(data_folder) else None

@st.cache_data(ttl=86400) # Cache date extraction (long TTL)
def extract_date_from_filename(filename: str) -> tuple[int | None, datetime | None]:
    """Extracts date and day-of-year from a filename."""
    basename = os.path.basename(filename)
    match = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', basename)
    if match:
        try:
            date_obj = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return date_obj.timetuple().tm_yday, date_obj
        except ValueError: return None, None
    return None, None

@st.cache_data(ttl=86400) # Cache shapefile loading
def load_lake_shape_from_xml(xml_file_path: str, bounds: tuple = None,
                             xml_width: float = 518.0, xml_height: float = 505.0):
    """Loads lake boundary from XML."""
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        points_xml = [[float(p.get("x")), float(p.get("y"))] for p in root.findall("point") if p.get("x") and p.get("y")]
        if not points_xml: return None
        points_to_return = points_xml
        if bounds:
            minx, miny, maxx, maxy = bounds
            points_to_return = [[minx + (x/xml_width)*(maxx-minx), maxy - (y/xml_height)*(maxy-miny)] for x,y in points_xml]
        if points_to_return and (points_to_return[0] != points_to_return[-1]):
            points_to_return.append(points_to_return[0]) # Close polygon
        return {"type": "Polygon", "coordinates": [points_to_return]}
    except Exception as e:
        st.error(f"Σφάλμα φόρτωσης περιγράμματος XML: {e}"); return None

@st.cache_data(ttl=3600, show_spinner=False) # Cache image reading
def read_image(file_path: str, lake_shape: dict = None, downsample_factor: int = 1):
    """Reads a raster image, optionally masks it, and downsamples."""
    try:
        with rasterio.open(file_path) as src:
            out_shape = (
                src.count,
                int(src.height / downsample_factor),
                int(src.width / downsample_factor)
            )
            # Read (and downsample if factor > 1)
            img = src.read(out_shape=out_shape, resampling=Resampling.bilinear)
            
            # Get the transform for the potentially downsampled image
            transform = src.transform * src.transform.scale(
                (src.width / img.shape[-1]),
                (src.height / img.shape[-2])
            )

            # Use first band for float conversion and masking
            img_band1 = img[0].astype(np.float32)
            profile = src.profile.copy()
            profile.update(dtype="float32", width=img.shape[-1], height=img.shape[-2], transform=transform)

            if src.nodata is not None: img_band1 = np.where(img_band1 == src.nodata, np.nan, img_band1)
            img_band1 = np.where(img_band1 == 0, np.nan, img_band1)

            if lake_shape:
                from rasterio.features import geometry_mask
                # Ensure mask is created with the new transform and shape
                poly_mask = geometry_mask([lake_shape], transform=transform, invert=True, out_shape=(img.shape[-2], img.shape[-1]))
                img_band1 = np.where(poly_mask, img_band1, np.nan)
            
            # Return only the first band (assuming single-band analysis)
            # If multi-band is needed, adjust this. For 'Πραγματικό', we might need 3 bands.
            # Let's return all bands, but use the first for nan handling
            img_masked = img.astype(np.float32)
            for i in range(img_masked.shape[0]):
                 img_masked[i] = np.where(np.isnan(img_band1), np.nan, img_masked[i])

            return img_masked, profile # Return all (potentially downsampled) bands
    except Exception as e:
        st.warning(f"Σφάλμα ανάγνωσης {os.path.basename(file_path)}: {e}."); return None, None

@st.cache_data(ttl=3600) # Cache metadata loading
def load_image_metadata(input_folder: str, shapefile_name="shapefile.xml"):
    """Loads only metadata (paths, dates) and shapefile."""
    if not os.path.exists(input_folder): return None, None, None

    shape_file_path = next((sp for sp in [os.path.join(input_folder, shapefile_name), os.path.join(input_folder, "shapefile.txt")] if os.path.exists(sp)), None)
    tif_files = sorted([fp for fp in glob.glob(os.path.join(input_folder, "*.tif")) if os.path.basename(fp).lower() != "mask.tif"])
    if not tif_files: return None, None, None

    metadata, lake_geom, first_profile = [], None, None
    try:
        with rasterio.open(tif_files[0]) as src_first:
            first_profile = src_first.profile.copy()
            if shape_file_path: lake_geom = load_lake_shape_from_xml(shape_file_path, bounds=src_first.bounds)
    except Exception as e:
        st.error(f"Σφάλμα προετοιμασίας φόρτωσης: {e}"); return None, None, None

    for fp_iter in tif_files:
        day_yr, date_obj = extract_date_from_filename(fp_iter)
        if day_yr is not None:
            metadata.append({'path': fp_iter, 'day': day_yr, 'date': date_obj})
    return metadata, lake_geom, first_profile

@safe_process_wrapper # Use memory wrapper
def run_lake_processing_app(waterbody: str, index_name: str):
    """Processes and displays surface mapping analysis, optimized for memory."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Επιφανειακή Αποτύπωση: {waterbody} - {index_name}")

        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder:
            st.error(f"Ο φάκελος δεδομένων για '{waterbody} - {index_name}' δεν βρέθηκε."); st.markdown('</div>', unsafe_allow_html=True); return

        input_folder_geotiffs = os.path.join(data_folder, "GeoTIFFs")
        with st.spinner(f"Φόρτωση μετα-δεδομένων για {waterbody} - {index_name}..."):
            metadata, lake_geom, first_profile = load_image_metadata(input_folder_geotiffs)

        if not metadata or not first_profile:
            st.error("Δεν βρέθηκαν έγκυρα μετα-δεδομένα ή εικόνες."); st.markdown('</div>', unsafe_allow_html=True); return

        DATES = [m['date'] for m in metadata]
        st.sidebar.subheader(f"Φίλτρα Επεξεργασίας ({index_name})")
        min_avail_date, max_avail_date = min(DATES).date(), max(DATES).date()
        unique_years_avail = sorted(list(set(d.year for d in DATES)))

        key_suffix = f"_lp_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]', '', index_name)}"
        common_filename_prefix = f"{waterbody}_{index_name}_surface_map"

        threshold_range_val = st.sidebar.slider("Εύρος τιμών pixel:", 0, 255, (0, 255), key=f"thresh{key_suffix}")
        col_start_lp, col_end_lp = st.sidebar.columns(2)
        refined_start_val = col_start_lp.date_input("Έναρξη:", min_avail_date, min_value=min_avail_date, max_value=max_avail_date, key=f"refined_start{key_suffix}")
        refined_end_val = col_end_lp.date_input("Λήξη:", max_avail_date, min_value=min_avail_date, max_value=max_avail_date, key=f"refined_end{key_suffix}")

        if refined_start_val > refined_end_val:
            st.sidebar.error("Η έναρξη πρέπει να είναι πριν τη λήξη."); st.markdown('</div>', unsafe_allow_html=True); return

        display_option_val = st.sidebar.radio("Μέσο Δείγμα:", ["Thresholded", "Original"], 0, key=f"display_opt{key_suffix}", horizontal=True)
        month_options_map = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        selected_months_val = st.sidebar.multiselect("Μήνες:", list(month_options_map.keys()), format_func=lambda x: month_options_map[x], default=list(month_options_map.keys()), key=f"sel_months{key_suffix}")
        selected_years_val = st.sidebar.multiselect("Έτη:", unique_years_avail, default=unique_years_avail, key=f"sel_years{key_suffix}")

        start_dt_conv = datetime.combine(refined_start_val, datetime.min.time())
        end_dt_conv = datetime.combine(refined_end_val, datetime.max.time())

        filtered_metadata = [
            m for m in metadata if
            (start_dt_conv <= m['date'] <= end_dt_conv and
             (not selected_months_val or m['date'].month in selected_months_val) and
             (not selected_years_val or m['date'].year in selected_years_val))
        ]

        if not filtered_metadata:
            st.info("Δεν υπάρχουν δεδομένα για τα φίλτρα."); st.markdown('</div>', unsafe_allow_html=True); return

        # --- Iterative Processing ---
        with st.spinner("Επεξεργασία φιλτραρισμένων δεδομένων..."):
            check_memory_usage() # Check before starting
            
            # Use a downsampled version to determine shape if needed, or get from profile
            img_shape = (first_profile['height'], first_profile['width'])
            
            days_in_range_map = np.zeros(img_shape, dtype=np.int16)
            sum_days_in_range = np.zeros(img_shape, dtype=np.float32)
            average_sample_img_sum = np.zeros(img_shape, dtype=np.float64)
            average_sample_img_count = np.zeros(img_shape, dtype=np.int16)
            stack_for_time_max_val = np.full(img_shape, np.nan, dtype=np.float32)
            time_max_map = np.full(img_shape, np.nan, dtype=np.float32)

            monthly_sums = {m: np.zeros(img_shape, dtype=np.int16) for m in selected_months_val}
            yearly_sums = {y: np.zeros(img_shape, dtype=np.int16) for y in selected_years_val}

            lower_t, upper_t = threshold_range_val
            total_files = len(filtered_metadata)
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, meta in enumerate(filtered_metadata):
                img_data, _ = read_image(meta['path'], lake_shape) # Load one image
                if img_data is None: continue

                img_data = img_data[0] # Assume single band processing for now

                with np.errstate(invalid='ignore'): # Ignore warnings from nan comparisons
                    in_range_mask = np.logical_and(img_data >= lower_t, img_data <= upper_t)
                in_range_mask = np.nan_to_num(in_range_mask, nan=0).astype(bool)

                days_in_range_map += in_range_mask
                sum_days_in_range += meta['day'] * in_range_mask

                if display_option_val.lower() == "thresholded":
                    img_for_avg = np.where(in_range_mask, img_data, np.nan)
                else:
                    img_for_avg = img_data

                average_sample_img_sum += np.nan_to_num(img_for_avg, nan=0.0)
                average_sample_img_count += ~np.isnan(img_for_avg)

                # Time max (approximate - updates if current > previous max)
                current_max_mask = np.logical_and(in_range_mask, (img_data > stack_for_time_max_val) | np.isnan(stack_for_time_max_val))
                stack_for_time_max_val = np.where(current_max_mask, img_data, stack_for_time_max_val)
                time_max_map = np.where(current_max_mask, meta['day'], time_max_map)

                # Monthly/Yearly sums
                month = meta['date'].month
                year = meta['date'].year
                if month in monthly_sums: monthly_sums[month] += in_range_mask
                if year in yearly_sums: yearly_sums[year] += in_range_mask

                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f'Επεξεργασία: {i + 1}/{total_files} εικόνες')
                if i % 25 == 0: gc.collect() # Collect garbage every 25 images

            progress_bar.empty(); status_text.empty()
            check_memory_usage() # Check after processing

            # Final calculations
            with np.errstate(divide='ignore', invalid='ignore'):
                count_pixels_in_range = days_in_range_map.copy()
                mean_day_map = np.divide(sum_days_in_range, count_pixels_in_range, out=np.full(img_shape, np.nan), where=(count_pixels_in_range != 0))
                average_sample_img_display = np.divide(average_sample_img_sum, average_sample_img_count, out=np.full(img_shape, np.nan), where=(average_sample_img_count != 0))

        # --- Display Results ---
        st.subheader("Ανάλυση Χαρτών")
        expander_col1, expander_col2 = st.columns(2)

        with expander_col1, st.expander("Ημέρες εντός Εύρους", True):
            fig_days = px.imshow(days_in_range_map, color_continuous_scale="plasma", labels={"color": "Ημέρες"})
            st.plotly_chart(fig_days, use_container_width=True, key=f"fig_days_map{key_suffix}")
            add_excel_download_button(pd.DataFrame(days_in_range_map), common_filename_prefix, "Days_in_Range_Map", f"excel_days_map{key_suffix}")

        tick_vals_days = [1,32,60,91,121,152,182,213,244,274,305,335,365]
        tick_text_days = ["Ιαν","Φεβ","Μαρ","Απρ","Μαΐ","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ",""]
        with expander_col2, st.expander("Μέση Ημέρα Εμφάνισης", True):
            fig_mean_day = px.imshow(mean_day_map, color_continuous_scale="RdBu", labels={"color": "Μέση Ημέρα (1-365)"}, color_continuous_midpoint=182)
            fig_mean_day.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
            st.plotly_chart(fig_mean_day, use_container_width=True, key=f"fig_mean_day_map{key_suffix}")
            add_excel_download_button(pd.DataFrame(mean_day_map), common_filename_prefix, "Mean_Day_Map", f"excel_mean_day_map{key_suffix}")

        st.subheader("Ανάλυση Δείγματος Εικόνας")
        expander_col3, expander_col4 = st.columns(2)

        with expander_col3, st.expander("Μέσο Δείγμα Εικόνας", True):
            if not np.all(np.isnan(average_sample_img_display)):
                fig_sample_disp = px.imshow(average_sample_img_display, color_continuous_scale="jet", labels={"color": "Τιμή Pixel"})
                st.plotly_chart(fig_sample_disp, use_container_width=True, key=f"fig_sample_map{key_suffix}")
                add_excel_download_button(pd.DataFrame(average_sample_img_display), common_filename_prefix, "Average_Sample_Map", f"excel_avg_sample_map{key_suffix}")
            else: st.caption("Δεν υπάρχουν δεδομένα.")

        with expander_col4, st.expander("Χρόνος Μέγιστης Εμφάνισης", True):
            fig_time_max = px.imshow(time_max_map, color_continuous_scale="RdBu", labels={"color": "Ημέρα Μέγιστης (1-365)"}, color_continuous_midpoint=182, range_color=[1,365])
            fig_time_max.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
            st.plotly_chart(fig_time_max, use_container_width=True, key=f"fig_time_max_map{key_suffix}")
            add_excel_download_button(pd.DataFrame(time_max_map), common_filename_prefix, "Time_Max_Value_Map", f"excel_time_max_map{key_suffix}")

        st.subheader("Πρόσθετη Ανάλυση Κατανομής")
        num_cols_display = 3
        with st.expander("Μηνιαία Κατανομή", False):
            cols_monthly = st.columns(num_cols_display)
            col_idx_monthly = 0
            for month_num, monthly_sum in monthly_sums.items():
                month_name_disp = month_options_map[month_num]
                fig_month_disp = px.imshow(monthly_sum, color_continuous_scale="plasma", title=month_name_disp, labels={"color": "Ημέρες"})
                fig_month_disp.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=350, coloraxis_showscale=False)
                cols_monthly[col_idx_monthly].plotly_chart(fig_month_disp, use_container_width=True, key=f"fig_month_{month_num}{key_suffix}")
                add_excel_download_button(pd.DataFrame(monthly_sum), common_filename_prefix, f"Monthly_{month_name_disp}", f"excel_month_{month_num}{key_suffix}")
                col_idx_monthly = (col_idx_monthly + 1) % num_cols_display

        with st.expander("Ετήσια Κατανομή", False):
            cols_yearly = st.columns(num_cols_display)
            col_idx_yearly = 0
            for year_val, yearly_sum in yearly_sums.items():
                fig_year_disp = px.imshow(yearly_sum, color_continuous_scale="plasma", title=f"Έτος: {year_val}", labels={"color": "Ημέρες"})
                fig_year_disp.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=350, coloraxis_showscale=False)
                cols_yearly[col_idx_yearly].plotly_chart(fig_year_disp, use_container_width=True, key=f"fig_year_{year_val}{key_suffix}")
                add_excel_download_button(pd.DataFrame(yearly_sum), common_filename_prefix, f"Yearly_{year_val}", f"excel_year_{year_val}{key_suffix}")
                col_idx_yearly = (col_idx_yearly + 1) % num_cols_display

        st.markdown('</div>', unsafe_allow_html=True)
        gc.collect() # Final cleanup

# --- Plotting Helpers (Decimation & WebGL) ---
def create_decimated_plot(dates, values, title, y_axis_title, max_points=500, use_webgl=True):
    """Creates a time-series plot with data decimation and optional WebGL."""
    if not dates or not values: return go.Figure().update_layout(title=f"{title} (No Data)")
    
    if len(dates) > max_points:
        step = len(dates) // max_points
        dates = dates[::step]
        values = values[::step]

    fig = go.Figure()
    ScatterClass = go.Scattergl if use_webgl else go.Scatter
    
    fig.add_trace(ScatterClass(
        x=dates,
        y=values,
        mode='lines+markers',
        marker=dict(size=5, color=values, colorscale='Viridis', showscale=True, colorbar=dict(title=y_axis_title)),
        line=dict(width=1, color='grey'),
        name=y_axis_title
    ))
    fig.update_layout(
        title=title,
        xaxis_title='Ημερομηνία',
        yaxis_title=y_axis_title,
        height=450,
        uirevision=f"{title}_rev", # Helps maintain zoom
        hovermode='x unified'
    )
    return fig

def create_dual_axis_decimated_plot(df_h, dates_mg, values_mg, title, max_points=500, use_webgl=True):
    """Creates a dual-axis plot with decimation."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    ScatterClass = go.Scattergl if use_webgl else go.Scatter

    # Decimate Height data
    h_dates, h_values = (df_h['Date'], df_h['Height']) if not df_h.empty else ([], [])
    if len(h_dates) > max_points:
        step = len(h_dates) // max_points
        h_dates, h_values = h_dates[::step], h_values[::step]
        
    # Decimate MG data
    if len(dates_mg) > max_points:
        step = len(dates_mg) // max_points
        dates_mg, values_mg = dates_mg[::step], values_mg[::step]

    if not df_h.empty:
        fig.add_trace(ScatterClass(x=h_dates, y=h_values, name='Στάθμη', mode='lines', line=dict(color='deepskyblue')), secondary_y=False)
    if dates_mg and values_mg:
        fig.add_trace(ScatterClass(x=dates_mg, y=values_mg, name='Μέσο mg/m³', mode='lines+markers', marker=dict(color=values_mg, colorscale='Viridis', reversescale=True, size=5, showscale=False), line=dict(color='lightgreen')), secondary_y=True)

    fig.update_layout(
        title=title,
        xaxis_title='Ημερομηνία',
        uirevision='dual_rev',
        height=500,
        yaxis=dict(title="Στάθμη (m)", color="deepskyblue", side='left'),
        yaxis2=dict(title="mg/m³", color="lightgreen", overlaying='y', side='right'),
        hovermode='x unified'
    )
    return fig

@st.cache_resource # Cache legend figure
def create_chl_legend_figure(orientation="horizontal", theme_bg_color=None, theme_text_color=None):
    """Creates a Matplotlib legend for Chlorophyll."""
    levels = [0, 6, 12, 20, 30, 50]
    colors = ["#496FF2", "#82D35F", "#FEFD05", "#FD0004", "#8E2026", "#D97CF5"]
    cmap = mcolors.LinearSegmentedColormap.from_list("ChlLegend", list(zip(np.linspace(0, 1, len(levels)), colors)))
    norm = mcolors.Normalize(vmin=levels[0], vmax=levels[-1])

    figsize = (7, 1.2) if orientation == "horizontal" else (1.8, 6)
    fig, ax = plt.subplots(figsize=figsize)
    adjust_params = {'bottom': 0.45, 'top': 0.9, 'left': 0.05, 'right': 0.95} if orientation == "horizontal" else {'left': 0.3, 'right': 0.7, 'top': 0.95, 'bottom': 0.05}
    fig.subplots_adjust(**adjust_params)

    cbar = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=ax, orientation=orientation, ticks=levels, aspect=30 if orientation=="horizontal" else 20, shrink=0.95)
    label_text = "Συγκέντρωση Χλωροφύλλης-α (mg/m³)"
    tick_labels = [str(l) for l in levels]

    if orientation == "horizontal": ax.set_xlabel(label_text, fontsize=10); ax.set_xticklabels(tick_labels, fontsize=9)
    else: ax.set_ylabel(label_text, fontsize=10); ax.set_yticklabels(tick_labels, fontsize=9)
    
    # Apply theme colors
    if theme_bg_color: fig.patch.set_facecolor(theme_bg_color); ax.set_facecolor(theme_bg_color)
    if theme_text_color:
        ax.xaxis.label.set_color(theme_text_color); ax.yaxis.label.set_color(theme_text_color)
        ax.tick_params(axis='x', colors=theme_text_color); ax.tick_params(axis='y', colors=theme_text_color)
        cbar.ax.tick_params(colors=theme_text_color)
        cbar.ax.yaxis.label.set_color(theme_text_color); cbar.ax.xaxis.label.set_color(theme_text_color)

    plt.tight_layout(pad=0.5)
    return fig

# --- Dashboard & Sampling Analysis (Optimized) ---
@st.cache_data(ttl=3600, show_spinner="Ανάλυση σημείων δειγματοληψίας...")
def analyze_sampling_data(sampling_points: list, images_folder_path: str,
                           lake_height_excel_path: str,
                           date_min=None, date_max=None):
    """Analyzes sampling points iteratively, returning only data."""
    results_colors = {name: [] for name, _, _ in sampling_points}
    results_mg = {name: [] for name, _, _ in sampling_points}

    if not os.path.isdir(images_folder_path): return {}, {}, pd.DataFrame()

    tif_files = sorted(glob.glob(os.path.join(images_folder_path, "*.tif")))

    for filename in tif_files:
        _, date_obj = extract_date_from_filename(filename)
        if not date_obj: continue
        if (date_min and date_obj.date() < date_min) or \
           (date_max and date_obj.date() > date_max): continue

        try:
            with rasterio.open(os.path.join(images_folder_path, filename)) as src:
                if src.count < 3: continue
                for name, lon, lat in sampling_points:
                    try:
                        col, row = map(int, (~src.transform) * (lon, lat))
                        if 0 <= col < src.width and 0 <= row < src.height:
                            win = rasterio.windows.Window(col, row, 1, 1)
                            r, g, b = src.read(1, window=win)[0, 0], src.read(2, window=win)[0, 0], src.read(3, window=win)[0, 0]
                            mg_val = (g / 255.0) * 2.0  # Placeholder conversion
                            results_mg[name].append((date_obj, mg_val))
                            results_colors[name].append((date_obj, (r / 255., g / 255., b / 255.)))
                    except IndexError: debug_message(f"Σφάλμα Index για {name} στο {filename}.")
                    except Exception as e_inner: debug_message(f"Εσωτερικό σφάλμα {filename} / {name}: {e_inner}")
        except Exception as e: st.warning(f"Σφάλμα επεξεργασίας {filename}: {e}")
        gc.collect() # Collect garbage after processing each image

    df_h = pd.DataFrame(columns=['Date', 'Height'])
    if os.path.exists(str(lake_height_excel_path)):
        try:
            df_h_temp = pd.read_excel(lake_height_excel_path)
            if not df_h_temp.empty and len(df_h_temp.columns) >= 2:
                df_h['Date'] = pd.to_datetime(df_h_temp.iloc[:, 0], errors='coerce')
                df_h['Height'] = pd.to_numeric(df_h_temp.iloc[:, 1], errors='coerce')
                df_h.dropna(inplace=True); df_h.sort_values('Date', inplace=True)
        except Exception as e: st.warning(f"Σφάλμα ανάγνωσης Excel στάθμης: {e}")

    return results_colors, results_mg, df_h

@st.cache_data(ttl=600, show_spinner=False)
def get_image_preview(file_path: str, downsample_factor: int = 4):
    """Loads a downsampled preview image."""
    try:
        with rasterio.open(file_path) as src:
            if src.count < 3: return None, None
            data = src.read(
                [1, 2, 3], # Read RGB
                out_shape=(
                    3, # Read only 3 bands
                    int(src.height / downsample_factor),
                    int(src.width / downsample_factor)
                ),
                resampling=Resampling.bilinear # Use bilinear for smoother preview
            )
            transform = src.transform * src.transform.scale(
                (src.width / data.shape[-1]),
                (src.height / data.shape[-2])
            )
            rgb_disp = data.transpose((1, 2, 0))
            if rgb_disp.max() > 1.0: rgb_disp = rgb_disp / 255.0
            return np.clip(rgb_disp, 0, 1), transform
    except Exception as e:
        st.warning(f"Σφάλμα φόρτωσης προεπισκόπησης {os.path.basename(file_path)}: {e}")
        return None, None

def image_navigation_ui(images_folder: str, available_dates_map: dict,
                        session_state_key_for_idx: str, key_prefix: str,
                        show_legend: bool = False, index_name_for_legend: str = ""):
    """UI for navigating through images."""
    if not available_dates_map:
        st.info("Δεν υπάρχουν διαθέσιμες εικόνες."); return None

    sorted_date_strings = sorted(available_dates_map.keys())
    current_idx = st.session_state.setdefault(session_state_key_for_idx, 0)
    current_idx = min(max(0, current_idx), len(sorted_date_strings) - 1) # Ensure index is valid

    col_prev, col_select, col_next = st.columns([1, 2, 1])
    if col_prev.button("<< Προηγ.", key=f"{key_prefix}_prev", use_container_width=True):
        st.session_state[session_state_key_for_idx] = max(0, current_idx - 1); st.rerun()
    if col_next.button("Επόμ. >>", key=f"{key_prefix}_next", use_container_width=True):
        st.session_state[session_state_key_for_idx] = min(len(sorted_date_strings) - 1, current_idx + 1); st.rerun()

    def update_idx_from_select_nav():
        st.session_state[session_state_key_for_idx] = sorted_date_strings.index(st.session_state[f"{key_prefix}_select_nav"])

    col_select.selectbox("Επιλογή Ημερομηνίας:", options=sorted_date_strings, index=current_idx,
                         key=f"{key_prefix}_select_nav", on_change=update_idx_from_select_nav,
                         label_visibility="collapsed")

    actual_selected_date_str = sorted_date_strings[st.session_state[session_state_key_for_idx]]
    image_filename = available_dates_map[actual_selected_date_str]
    image_full_path = os.path.join(images_folder, image_filename)

    if os.path.exists(image_full_path):
        st.image(image_full_path, caption=f"{actual_selected_date_str} - {image_filename}", use_column_width=True)
        if show_legend and index_name_for_legend == "Χλωροφύλλη":
            st.pyplot(create_chl_legend_figure(orientation="horizontal"))
    else:
        st.error(f"Το αρχείο εικόνας δεν βρέθηκε: {image_full_path}")
    return image_full_path

def generate_dashboard_figures(sampling_points, results_colors, results_mg, df_h,
                               first_image_preview, first_transform_preview,
                               selected_point_names):
    """Generates Plotly figures from analysis data (lightweight)."""
    figures = {}

    # Geo Figure
    fig_geo = go.Figure()
    if first_image_preview is not None:
        fig_geo = px.imshow(first_image_preview, title='Εικόνα Αναφοράς & Σημεία')
        if first_transform_preview:
            for n, lon, lat in sampling_points:
                if n in selected_point_names:
                    col, row = map(int, (~first_transform_preview) * (lon, lat))
                    fig_geo.add_trace(go.Scattergl(x=[col], y=[row], mode='markers+text', marker=dict(color='red', size=10, symbol='x'), name=n, text=n, textposition="top right"))
        fig_geo.update_xaxes(visible=False); fig_geo.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig_geo.update_layout(height=600, uirevision='geo')
    figures['geo'] = fig_geo

    # Colors Figure
    fig_colors = make_subplots(specs=[[{"secondary_y": True}]])
    pt_y_map = {n: i for i, n in enumerate(selected_point_names)}
    for n_iter in selected_point_names:
        if n_iter in results_colors and results_colors[n_iter]:
            dts, cols = zip(*sorted(results_colors[n_iter], key=lambda x: x[0])) if results_colors[n_iter] else ([], [])
            c_rgb = [f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
            fig_colors.add_trace(go.Scattergl(x=list(dts), y=[pt_y_map.get(n_iter, -1)] * len(dts), mode='markers', marker=dict(color=c_rgb, size=10), name=n_iter), secondary_y=False)
    if not df_h.empty: fig_colors.add_trace(go.Scattergl(x=df_h['Date'], y=df_h['Height'], name='Στάθμη', mode='lines', line=dict(color='blue')), secondary_y=True)
    fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη', yaxis=dict(tickmode='array', tickvals=list(pt_y_map.values()), ticktext=list(pt_y_map.keys())), yaxis2=dict(title='Στάθμη (m)'), uirevision='colors', height=500, hovermode='x unified')
    figures['colors'] = fig_colors

    # MG Figure
    all_mg_by_d = {}
    for p_name in selected_point_names:
        if p_name in results_mg:
            for d, v in results_mg[p_name]: all_mg_by_d.setdefault(d, []).append(v)
    s_dts_mg = sorted(all_mg_by_d.keys())
    mean_mg = [np.mean(all_mg_by_d[d]) for d in s_dts_mg if all_mg_by_d[d]]
    figures['mg'] = create_decimated_plot(s_dts_mg, mean_mg, 'Μέσο mg/m³', 'mg/m³')
    figures['mg_data'] = (s_dts_mg, mean_mg) # Store decimated data

    # Dual Figure
    figures['dual'] = create_dual_axis_decimated_plot(df_h, s_dts_mg, mean_mg, 'Στάθμη & Μέσο mg/m³')

    return figures

@safe_process_wrapper
def run_water_quality_dashboard(waterbody: str, index_name: str):
    """Runs the Quality & Level Profile dashboard with optimizations."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Προφίλ Ποιότητας και Στάθμης: {waterbody} - {index_name}")

        key_suffix_dash = f"_dash_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]', '', index_name)}"
        common_filename_prefix_dash = f"{waterbody}_{index_name}"

        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder: st.error("Φάκελος δεδομένων δεν βρέθηκε."); st.markdown('</div>', unsafe_allow_html=True); return

        images_folder_path = os.path.join(data_folder, "GeoTIFFs")
        lake_height_excel_path = os.path.join(data_folder, "lake height.xlsx")
        default_sampling_kml_path = os.path.join(data_folder, "sampling.kml")
        vid_path = next((p for n in ["timelapse.mp4", "timelapse.gif"] for p in [os.path.join(data_folder, n), os.path.join(images_folder_path, n)] if os.path.exists(p)), None)

        available_tifs = {str(d.date()): fn for fn in (os.listdir(images_folder_path) if os.path.exists(images_folder_path) else []) if fn.lower().endswith(('.tif', '.tiff')) for _, d in [extract_date_from_filename(fn)] if d}
        if not available_tifs: st.error("Δεν βρέθηκαν GeoTIFFs."); st.markdown('</div>', unsafe_allow_html=True); return

        st.sidebar.subheader(f"Ρυθμίσεις ({index_name})")
        sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:", sorted(available_tifs.keys(), reverse=True), key=f"bg_date{key_suffix_dash}")
        
        first_img_preview, first_transform_preview = None, None
        if sel_bg_date:
            first_img_preview, first_transform_preview = get_image_preview(os.path.join(images_folder_path, available_tifs[sel_bg_date]))
        if first_img_preview is None: st.error("Απαιτείται έγκυρη εικόνα αναφοράς."); st.markdown('</div>', unsafe_allow_html=True); return

        tabs_ctrl = st.tabs(["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"])

        def display_dashboard_results(results_key, kml_points_key, selected_pts_key, tab_prefix, common_filename_prefix):
            """Helper to display results for a tab."""
            if results_key in st.session_state:
                res_data = st.session_state[results_key]
                figures = st.session_state[f"{results_key}_figs"]
                kml_points = st.session_state.get(kml_points_key, [])
                selected_pts = st.session_state.get(selected_pts_key, [p[0] for p in kml_points])

                if not res_data or not figures: st.info("Δεν υπάρχουν αποτελέσματα."); return

                results_colors, results_mg, df_h = res_data
                n_tabs_titles = ["GeoTIFF", "Εικόνες", "Video/GIF", "Χρώματα Pixel", "Μέσο mg/m³", "Συνδυασμένο", "mg/m³ ανά Σημείο"]
                n_tabs_display = st.tabs(n_tabs_titles)

                with n_tabs_display[0]:
                    st.plotly_chart(figures['geo'], use_container_width=True)
                    df_pts = pd.DataFrame([pt for pt in kml_points if pt[0] in selected_pts], columns=['PointName', 'Longitude', 'Latitude'])
                    add_excel_download_button(df_pts, common_filename_prefix, "Sampling Points", f"excel_geo_{tab_prefix}")
                    if index_name == "Χλωροφύλλη": st.pyplot(create_chl_legend_figure())

                with n_tabs_display[1]:
                    image_navigation_ui(images_folder_path, available_tifs, f"img_idx_{tab_prefix}", f"nav_{tab_prefix}", index_name == "Χλωροφύλλη", index_name)

                with n_tabs_display[2]:
                    if vid_path: st.video(vid_path) if vid_path.endswith(".mp4") else st.image(vid_path)
                    else: st.caption("Δεν βρέθηκε video/timelapse.")
                    if index_name == "Χλωροφύλλη" and vid_path: st.pyplot(create_chl_legend_figure())

                with n_tabs_display[3]:
                    c1, c2 = st.columns([.85, .15])
                    c1.plotly_chart(figures['colors'], use_container_width=True)
                    # Add excel download if needed (requires restructuring to pass data)
                    if index_name == "Χλωροφύλλη": c2.pyplot(create_chl_legend_figure("vertical"))

                with n_tabs_display[4]:
                    st.plotly_chart(figures['mg'], use_container_width=True)
                    s_dts, mean_mg = figures['mg_data']
                    df_mg = pd.DataFrame({'Date': s_dts, 'Mean_mg_m3': mean_mg})
                    add_excel_download_button(df_mg, common_filename_prefix, "Mean mg_m3", f"excel_mg_{tab_prefix}")

                with n_tabs_display[5]:
                    st.plotly_chart(figures['dual'], use_container_width=True)
                    # Add excel download if needed

                with n_tabs_display[6]:
                    sel_pt_d_disp = st.selectbox("Σημείο:", selected_pts, key=f"detail_sel_{tab_prefix}")
                    if sel_pt_d_disp and results_mg.get(sel_pt_d_disp):
                        dts, vals = zip(*sorted(results_mg[sel_pt_d_disp], key=lambda x: x[0]))
                        fig_det = create_decimated_plot(list(dts), list(vals), f"mg/m³ για {sel_pt_d_disp}", 'mg/m³', max_points=300)
                        st.plotly_chart(fig_det, use_container_width=True)
                        df_det = pd.DataFrame({'Date': dts, 'mg_m3': vals})
                        add_excel_download_button(df_det, common_filename_prefix, f"Point_{sel_pt_d_disp}", f"excel_det_{sel_pt_d_disp}_{tab_prefix}")


        with tabs_ctrl[0]: # Default KML
            st.markdown("##### Ανάλυση με Προεπιλεγμένα Σημεία")
            def_pts_list = parse_sampling_kml(default_sampling_kml_path) if os.path.exists(default_sampling_kml_path) else []
            st.session_state[f"def_pts_list{key_suffix_dash}"] = def_pts_list
            if def_pts_list:
                all_names = [n for n, _, _ in def_pts_list]
                sel_pts = st.multiselect("Σημεία:", all_names, default=all_names, key=f"sel_def{key_suffix_dash}")
                st.session_state[f"sel_pts_def_names{key_suffix_dash}"] = sel_pts
                if st.button("Εκτέλεση (Προεπιλογή)", key=f"run_def{key_suffix_dash}", type="primary"):
                    data = analyze_sampling_data(def_pts_list, images_folder_path, lake_height_excel_path)
                    st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD] = data
                    st.session_state[f"{SESSION_KEY_DEFAULT_RESULTS_DASHBOARD}_figs"] = generate_dashboard_figures(def_pts_list, *data, first_img_preview, first_transform_preview, sel_pts)
                    st.rerun() # Rerun to display
            else: st.caption("Δεν βρέθηκε προεπιλεγμένο KML.")
            display_dashboard_results(SESSION_KEY_DEFAULT_RESULTS_DASHBOARD, f"def_pts_list{key_suffix_dash}", f"sel_pts_def_names{key_suffix_dash}", f"def_{key_suffix_dash}", f"{common_filename_prefix_dash}_default")

        with tabs_ctrl[1]: # Upload KML
            st.markdown("##### Ανάλυση με Ανεβασμένο KML")
            upl_file = st.file_uploader("Ανέβασμα KML:", type="kml", key=f"upl_kml_{key_suffix_dash}")
            if upl_file:
                upl_pts_list = parse_sampling_kml(upl_file)
                st.session_state[f"upl_pts_list{key_suffix_dash}"] = upl_pts_list
                if upl_pts_list:
                    st.success(f"Βρέθηκαν {len(upl_pts_list)} σημεία.")
                    all_names = [n for n, _, _ in upl_pts_list]
                    sel_pts = st.multiselect("Σημεία:", all_names, default=all_names, key=f"sel_upl_{key_suffix_dash}")
                    st.session_state[f"sel_pts_upl_names{key_suffix_dash}"] = sel_pts
                    if st.button("Εκτέλεση (KML)", key=f"run_upl_{key_suffix_dash}", type="primary"):
                        data = analyze_sampling_data(upl_pts_list, images_folder_path, lake_height_excel_path)
                        st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD] = data
                        st.session_state[f"{SESSION_KEY_UPLOAD_RESULTS_DASHBOARD}_figs"] = generate_dashboard_figures(upl_pts_list, *data, first_img_preview, first_transform_preview, sel_pts)
                        st.rerun() # Rerun to display
                else: st.error("Το KML δεν περιείχε έγκυρα σημεία.")
            display_dashboard_results(SESSION_KEY_UPLOAD_RESULTS_DASHBOARD, f"upl_pts_list{key_suffix_dash}", f"sel_pts_upl_names{key_suffix_dash}", f"upl_{key_suffix_dash}", f"{common_filename_prefix_dash}_upload")

        st.markdown('</div>', unsafe_allow_html=True)
        gc.collect()

# --- Predictive Tools (Conceptual - Requires more work for full performance optimization) ---
# NOTE: Full parallel analysis can be very memory intensive.
# The `analyze_sampling_data` is already optimized, but running it 3 times might still be heavy.
# Consider running them sequentially or offering a "Run All" button with a strong warning.
# For now, we keep the structure but rely on the optimized `analyze_sampling_data`.

@safe_process_wrapper
def run_predictive_tools(waterbody: str, initial_selected_index: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Εργαλεία Πρόβλεψης & Έγκαιρης Ενημέρωσης: {waterbody}")
        st.info("Αυτή η ενότητα εκτελεί ανάλυση δειγματοληψίας για όλους τους δείκτες (Πραγματικό, Χλωροφύλλη, Θολότητα) χρησιμοποιώντας κοινά φίλτρα. **Προσοχή:** Μπορεί να απαιτήσει χρόνο και πόρους.")

        key_suffix_pred = f"_pred_{waterbody}"

        st.subheader("Κοινές Παράμετροι")
        col1, col2 = st.columns(2)
        date_min = col1.date_input("Από:", date(2020, 1, 1), key=f"date_min{key_suffix_pred}")
        date_max = col2.date_input("Έως:", date.today(), key=f"date_max{key_suffix_pred}")
        sampling_type = st.radio("Πηγή Σημείων:", ["Προεπιλογή", "Ανέβασμα KML"], key=f"stype{key_suffix_pred}", horizontal=True)

        sampling_points = []
        if sampling_type == "Προεπιλογή":
            # Try to find a default KML (e.g., from 'Πραγματικό')
            data_folder_def = get_data_folder(waterbody, "Πραγματικό")
            if data_folder_def:
                kml_path = os.path.join(data_folder_def, "sampling.kml")
                if os.path.exists(kml_path):
                    sampling_points = parse_sampling_kml(kml_path)
                    if sampling_points: st.caption(f"Χρήση {len(sampling_points)} προεπιλεγμένων σημείων.")
                else: st.warning("Δεν βρέθηκε προεπιλεγμένο KML.")
            else: st.warning("Δεν βρέθηκε φάκελος 'Πραγματικό' για KML.")
        else:
            upl_file = st.file_uploader("Ανέβασμα KML:", type="kml", key=f"kml_pred{key_suffix_pred}")
            if upl_file: sampling_points = parse_sampling_kml(upl_file)

        if not sampling_points:
            st.error("Πρέπει να οριστούν σημεία δειγματοληψίας."); st.markdown('</div>', unsafe_allow_html=True); return

        if st.button("Εκτέλεση Παράλληλης Ανάλυσης", key=f"run_pred{key_suffix_pred}", type="primary"):
            indices = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]
            results_all = {}
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, idx_name in enumerate(indices):
                status_text.text(f"Επεξεργασία: {idx_name}...")
                data_folder = get_data_folder(waterbody, idx_name)
                if data_folder:
                    images_folder = os.path.join(data_folder, "GeoTIFFs")
                    height_excel = os.path.join(data_folder, "lake height.xlsx")
                    results_all[idx_name] = analyze_sampling_data(sampling_points, images_folder, height_excel, date_min, date_max)
                else:
                    results_all[idx_name] = ({}, {}, pd.DataFrame()) # Empty results
                progress_bar.progress((i + 1) / len(indices))

            st.session_state[f"pred_results{key_suffix_pred}"] = results_all
            status_text.success("Η ανάλυση ολοκληρώθηκε!"); progress_bar.empty()
            gc.collect()

        if f"pred_results{key_suffix_pred}" in st.session_state:
            results_all = st.session_state[f"pred_results{key_suffix_pred}"]
            st.subheader("Συγκριτικά Αποτελέσματα")
            
            # Combine Lake Height Data (find first valid one)
            df_h_combined = next((res[2] for res in results_all.values() if not res[2].empty), pd.DataFrame())

            # Combine Mean MG Data
            fig_mg_combined = go.Figure()
            all_mg_dfs = {}
            for idx_name, (res_c, res_m, df_h) in results_all.items():
                all_mg_by_d = {}
                for p_name in [p[0] for p in sampling_points]:
                    if p_name in res_m:
                        for d, v in res_m[p_name]: all_mg_by_d.setdefault(d, []).append(v)
                s_dts_mg = sorted(all_mg_by_d.keys())
                mean_mg = [np.mean(all_mg_by_d[d]) for d in s_dts_mg if all_mg_by_d[d]]
                if s_dts_mg and mean_mg:
                    fig_mg_combined.add_trace(go.Scattergl(x=s_dts_mg, y=mean_mg, mode='lines', name=idx_name))
                    all_mg_dfs[f"{idx_name}_mg_m3"] = pd.DataFrame({'Date': s_dts_mg, 'Value': mean_mg})

            fig_mg_combined.update_layout(title="Συγκριτική Πορεία Μέσου mg/m³", xaxis_title="Ημερομηνία", yaxis_title="mg/m³", height=500, hovermode='x unified')
            st.plotly_chart(fig_mg_combined, use_container_width=True)
            if all_mg_dfs : add_excel_download_button(all_mg_dfs, f"{waterbody}_predictive", "All_Indices_Mean_mg_m3", "excel_pred_mg_all")

            st.markdown("---")
            st.markdown("#### Λεπτομέρειες ανά Δείκτη")
            tabs_pred = st.tabs(list(results_all.keys()))
            for i, idx_name in enumerate(results_all.keys()):
                with tabs_pred[i]:
                    res_c, res_m, df_h = results_all[idx_name]
                    if not res_m:
                        st.info(f"Δεν υπάρχουν δεδομένα για {idx_name}.")
                        continue

                    # Generate lightweight figures for this index
                    # Note: We don't have a 'first_image_preview' here, so Geo is skipped
                    s_dts_mg, mean_mg = [], []
                    all_mg_by_d = {}
                    for p_name in [p[0] for p in sampling_points]:
                        if p_name in res_m:
                            for d, v in res_m[p_name]: all_mg_by_d.setdefault(d, []).append(v)
                    s_dts_mg = sorted(all_mg_by_d.keys())
                    mean_mg = [np.mean(all_mg_by_d[d]) for d in s_dts_mg if all_mg_by_d[d]]

                    fig_mg_idx = create_decimated_plot(s_dts_mg, mean_mg, f'Μέσο mg/m³ ({idx_name})', 'mg/m³')
                    st.plotly_chart(fig_mg_idx, use_container_width=True)

                    fig_dual_idx = create_dual_axis_decimated_plot(df_h, s_dts_mg, mean_mg, f'Στάθμη & Μέσο mg/m³ ({idx_name})')
                    st.plotly_chart(fig_dual_idx, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
        gc.collect()

def main_app():
    """Main application logic."""
    inject_custom_css()
    check_memory_usage() # Check memory at the start
    periodic_gc_and_cache_clear() # Run cleanup tasks

    run_intro_page_custom()
    run_custom_sidebar_ui_custom()

    selected_wb = st.session_state.get(SESSION_KEY_WATERBODY)
    selected_idx = st.session_state.get(SESSION_KEY_INDEX)
    selected_an = st.session_state.get(SESSION_KEY_ANALYSIS)

    if not all([selected_wb, selected_idx, selected_an]):
        render_footer()
        return

    if selected_an == "Επιφανειακή Αποτύπωση":
        run_lake_processing_app(selected_wb, selected_idx)
    elif selected_an == "Προφίλ ποιότητας και στάθμης":
        run_water_quality_dashboard(selected_wb, selected_idx)
    elif selected_an == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
        run_predictive_tools(selected_wb, selected_idx)
    else:
        st.warning("Μη υποστηριζόμενη ανάλυση.")

    render_footer()

if __name__ == "__main__":
    if authenticator: # Ensure authenticator was initialized
        authenticator.login('main')
        auth_status = st.session_state.get("authentication_status")

        if auth_status:
            main_app()
        elif auth_status is False:
            st.error('Το όνομα χρήστη ή ο κωδικός πρόσβασης είναι λανθασμένος.')
        elif auth_status is None:
            st.warning('Παρακαλώ εισάγετε τα στοιχεία σας.')
    else:
        st.error("Σφάλμα συστήματος αυθεντικοποίησης. Επικοινωνήστε με τον διαχειριστή.")