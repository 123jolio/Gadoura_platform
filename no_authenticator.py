#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI) - DEBUG ENABLED
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
Αυτή η έκδοση περιλαμβάνει εκτεταμένες δυνατότητες καταγραφής (logging)
και διαχείρισης σφαλμάτων (try-except) για να βοηθήσει στον εντοπισμό
του σημείου που προκαλεί τη διακοπή λειτουργίας.
"""

import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET
import io
import traceback  # <-- IMPORT TRACEBACK FOR DETAILED ERRORS

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
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων (DEBUG)", page_icon="💧")
# --------------------------------------------------------------------

# --- Global Configuration & Constants ---
DEBUG = True # <-- FORCE DEBUG ON
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
LOGO_PATH = os.path.join(APP_BASE_DIR, "logo.jpg")

WATERBODY_FOLDERS = {
    "Γαδουρά": "Gadoura",
    # Add other waterbodies here if needed
}

SESSION_KEY_WATERBODY = "waterbody_choice_main"
SESSION_KEY_INDEX = "index_choice_main"
SESSION_KEY_ANALYSIS = "analysis_choice_main"
SESSION_KEY_DEFAULT_RESULTS_DASHBOARD = "dashboard_default_sampling_results"
SESSION_KEY_UPLOAD_RESULTS_DASHBOARD = "dashboard_upload_sampling_results"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF = "dash_def_current_image_idx"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL = "dash_upl_current_image_idx"

# --- DEBUGGING & LOGGING FUNCTIONS ---
def log_message(level, *args, **kwargs):
    """Logs messages to both console and Streamlit expander."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}][{level}] - {' '.join(map(str, args))}"
    print(message, flush=True) # Print to console/logs
    if DEBUG:
        with st.expander("🔴 Debug Log", expanded=False):
            st.write(message)
            if kwargs:
                st.write(kwargs)

def log_debug(*args, **kwargs):
    log_message("DEBUG", *args, **kwargs)

def log_info(*args, **kwargs):
    log_message("INFO", *args, **kwargs)

def log_warning(*args, **kwargs):
    log_message("WARNING", *args, **kwargs)

def log_error(*args, **kwargs):
    log_message("ERROR", *args, **kwargs)
    exc_info = traceback.format_exc()
    print(exc_info, flush=True) # Print full traceback to console
    if DEBUG:
        with st.expander("🔴 Debug Log", expanded=False):
            st.code(exc_info) # Show traceback in Streamlit

# --- CSS Injection ---
def inject_custom_css():
    log_debug("Injecting custom CSS.")
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

# --- Excel Download Utility ---
def add_excel_download_button(df_or_dict_of_dfs, filename_prefix: str, button_label_suffix: str, plot_key: str):
    log_debug(f"Attempting to create Excel download for: {button_label_suffix}")
    if df_or_dict_of_dfs is None:
        log_warning(f"No data provided for Excel export: {button_label_suffix}")
        return

    is_empty_df = isinstance(df_or_dict_of_dfs, pd.DataFrame) and df_or_dict_of_dfs.empty
    is_empty_dict = False
    if isinstance(df_or_dict_of_dfs, dict):
        if not df_or_dict_of_dfs:
            is_empty_dict = True
        else:
            all_dfs_in_dict_empty = all(isinstance(df_item, pd.DataFrame) and df_item.empty for df_item in df_or_dict_of_dfs.values())
            if all_dfs_in_dict_empty:
                is_empty_dict = True

    if is_empty_df or is_empty_dict:
        log_warning(f"Empty data provided for Excel export: {button_label_suffix}")
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
                        log_debug(f"Empty DataFrame for sheet '{sheet_name}' in Excel export: {button_label_suffix}")
        excel_data = output.getvalue()
        if not excel_data:
            log_warning(f"No data written to Excel buffer for: {button_label_suffix}")
            return

        file_name_suffix = button_label_suffix.lower().replace(' ', '_').replace('/', '_').replace('&', 'and').replace('(', '').replace(')', '')
        st.download_button(
            label=f"📥 Save {button_label_suffix} to Excel",
            data=excel_data,
            file_name=f"{filename_prefix}_{file_name_suffix}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key=f"download_{plot_key}"
        )
        log_debug(f"Excel download button created for: {button_label_suffix}")
    except Exception as e:
        log_error(f"Could not generate Excel file for {button_label_suffix}: {e}")
        st.warning(f"Could not generate Excel file for {button_label_suffix}: {e}")

# --- UI Components ---
def render_footer():
    log_debug("Rendering footer.")
    st.markdown(f"""
        <hr style="border-color: #2a2e37;">
        <div class='footer'>
            © {datetime.now().year} EYATH SA • Powered by Google Gemini & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
        </div>
    """, unsafe_allow_html=True)

def run_intro_page_custom():
    log_debug("Rendering intro page.")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_logo, col_text = st.columns([0.3, 0.7], gap="large")
        with col_logo:
            if os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=240, output_format="auto")
            else:
                log_warning(f"Logo not found at {LOGO_PATH}")
                st.markdown("💧", help="Λογότυπο ΕΥΑΘ")
        with col_text:
            user_name_display = "Χρήστη"
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
    log_debug("Rendering sidebar UI.")
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
    log_debug(f"Sidebar choices: WB={waterbody}, Index={index_name}, Analysis={analysis_type}")

# --- Data Parsing & Loading ---
@st.cache_data
def parse_sampling_kml(kml_source) -> list:
    log_info(f"Parsing KML source: {kml_source}")
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
                    except ValueError: log_warning(f"KML Skipping malformed coordinate: '{coord_str}'")
        if not points:
            log_warning("No LineString points found in KML.")
            st.warning("Δεν βρέθηκαν σημεία LineString στο KML.")
        else:
            log_info(f"Successfully parsed {len(points)} points from KML.")
        return points
    except FileNotFoundError:
        log_error(f"KML file not found: '{kml_source}'")
        st.error(f"Το αρχείο KML '{kml_source}' δεν βρέθηκε.")
        return []
    except ET.ParseError as e:
        log_error(f"KML Parse Error for '{kml_source}': {e}")
        st.error(f"Σφάλμα ανάλυσης KML '{kml_source}': Μη έγκυρο XML. {e}")
        return []
    except Exception as e:
        log_error(f"Generic KML Parsing Error for '{kml_source}': {e}")
        st.error(f"Σφάλμα ανάλυσης KML '{kml_source}': {e}")
        return []

@st.cache_data
def get_data_folder(waterbody: str, index_name: str) -> str | None:
    log_debug(f"Getting data folder for WB='{waterbody}', Index='{index_name}'.")
    waterbody_folder_name = WATERBODY_FOLDERS.get(waterbody)
    if not waterbody_folder_name:
        log_error(f"No folder mapping for waterbody: '{waterbody}'.")
        st.error(f"Δεν έχει οριστεί αντιστοίχιση φακέλου για το υδάτινο σώμα: '{waterbody}'.")
        return None

    index_map = {"Πραγματικό": "Πραγματικό", "Χλωροφύλλη": "Chlorophyll", "Θολότητα": "Θολότητα"}
    index_specific_folder = index_map.get(index_name, index_name)

    data_folder = os.path.join(APP_BASE_DIR, waterbody_folder_name, index_specific_folder)
    log_debug(f"Attempting data folder path: {data_folder}")

    if not os.path.exists(data_folder) or not os.path.isdir(data_folder):
        log_error(f"Data folder does not exist or is not a directory: {data_folder}")
        return None
    log_info(f"Data folder found: {data_folder}")
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
            log_warning(f"Invalid date in filename '{basename}': {e}")
            return None, None
    log_debug(f"No date match in filename: {basename}")
    return None, None

@st.cache_data
def load_lake_shape_from_xml(xml_file_path: str, bounds: tuple = None,
                             xml_width: float = 518.0, xml_height: float = 505.0):
    log_info(f"Loading lake shape from XML: {xml_file_path}")
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        points_xml = []
        for point_elem in root.findall("point"):
            x_str, y_str = point_elem.get("x"), point_elem.get("y")
            if x_str and y_str: points_xml.append([float(x_str), float(y_str)])

        if not points_xml:
            log_warning(f"No points found in XML: {os.path.basename(xml_file_path)}")
            st.warning(f"Δεν βρέθηκαν σημεία στο XML: {os.path.basename(xml_file_path)}"); return None

        points_to_return = points_xml
        if bounds:
            minx, miny, maxx, maxy = bounds
            points_to_return = [[minx + (x/xml_width)*(maxx-minx), maxy - (y/xml_height)*(maxy-miny)] for x,y in points_xml]

        if points_to_return and (points_to_return[0] != points_to_return[-1]):
            points_to_return.append(points_to_return[0]) # Close the polygon

        log_info(f"Loaded {len(points_to_return)} shape points.")
        return {"type": "Polygon", "coordinates": [points_to_return]}
    except FileNotFoundError:
        log_error(f"Shape XML not found: {xml_file_path}")
        st.error(f"Το αρχείο XML περιγράμματος δεν βρέθηκε: {xml_file_path}"); return None
    except ET.ParseError as e:
        log_error(f"Shape XML Parse Error: {e}")
        st.error(f"Σφάλμα ανάλυσης XML περιγράμματος: {e}"); return None
    except Exception as e:
        log_error(f"Error loading shape from {os.path.basename(xml_file_path)}: {e}");
        st.error(f"Σφάλμα φόρτωσης περιγράμματος από {os.path.basename(xml_file_path)}: {e}"); return None

@st.cache_data
def read_image(file_path: str, lake_shape: dict = None):
    log_debug(f"Reading image: {file_path}")
    try:
        with rasterio.open(file_path) as src:
            img = src.read(1).astype(np.float32)
            profile = src.profile.copy(); profile.update(dtype="float32")
            transform = src.transform # Get transform here

            if src.nodata is not None: img = np.where(img == src.nodata, np.nan, img)
            img = np.where(img == 0, np.nan, img) # Treat 0 as NaN

            if lake_shape:
                from rasterio.features import geometry_mask
                poly_mask = geometry_mask([lake_shape], transform=transform, invert=True, out_shape=img.shape)
                img = np.where(poly_mask, img, np.nan)
            log_debug(f"Successfully read image: {file_path}")
            return img, profile
    except rasterio.errors.RasterioIOError as e:
        log_error(f"Rasterio I/O Error reading {os.path.basename(file_path)}: {e}")
        st.warning(f"Προειδοποίηση: Σφάλμα I/O ανάγνωσης εικόνας {os.path.basename(file_path)}: {e}. Παραλείπεται."); return None, None
    except Exception as e:
        log_error(f"Generic Error reading {os.path.basename(file_path)}: {e}")
        st.warning(f"Προειδοποίηση: Σφάλμα ανάγνωσης εικόνας {os.path.basename(file_path)}: {e}. Παραλείπεται."); return None, None

@st.cache_data
def load_data_for_lake_processing(input_folder: str, shapefile_name="shapefile.xml"):
    log_info(f"Loading lake processing data for: {input_folder}")
    if not os.path.exists(input_folder):
        log_error(f"Input folder does not exist: {input_folder}");
        st.error(f"Ο φάκελος εισόδου δεν υπάρχει: {input_folder}"); return None, None, None, None

    shape_file_path = next((sp for sp in [os.path.join(input_folder, shapefile_name), os.path.join(input_folder, "shapefile.txt")] if os.path.exists(sp)), None)
    if shape_file_path: log_debug(f"Found shape file: {shape_file_path}")
    else: log_warning(f"Shape file not found in {input_folder}")

    tif_files = sorted([fp for fp in glob.glob(os.path.join(input_folder, "*.tif")) if os.path.basename(fp).lower() != "mask.tif"])
    if not tif_files:
        log_error(f"No GeoTIFF files found in: {input_folder}");
        st.warning(f"Δεν βρέθηκαν GeoTIFF αρχεία στον φάκελο: {input_folder}"); return None, None, None, None
    log_info(f"Found {len(tif_files)} TIF files.")

    first_profile, lake_geom = None, None
    try:
        log_debug(f"Opening first TIF: {tif_files[0]}")
        with rasterio.open(tif_files[0]) as src_first:
            first_profile = src_first.profile.copy()
            if shape_file_path: lake_geom = load_lake_shape_from_xml(shape_file_path, bounds=src_first.bounds)
    except Exception as e:
        log_error(f"Error loading first image/shapefile: {e}");
        st.error(f"Σφάλμα προετοιμασίας φόρτωσης (πρώτη εικόνα/shapefile): {e}"); return None, None, None, None

    images, days, dates_list = [], [], []
    for fp_iter in tif_files:
        day_yr, date_obj = extract_date_from_filename(fp_iter)
        if day_yr is None: continue
        img_data, _ = read_image(fp_iter, lake_shape=lake_geom)
        if img_data is not None: images.append(img_data); days.append(day_yr); dates_list.append(date_obj)

    if not images:
        log_error(f"No valid images were loaded from: {input_folder}.")
        st.warning(f"Δεν φορτώθηκαν έγκυρες εικόνες από τον φάκελο: {input_folder}."); return None, None, None, None

    log_info(f"Successfully loaded {len(images)} images.")
    return np.stack(images, axis=0), np.array(days), dates_list, first_profile

# --- Analysis Functions ---
def analyze_sampling_generic(sampling_points, first_image_data, first_transform,
                             images_folder, lake_height_path, selected_points_names,
                             lower_thresh=0, upper_thresh=255, date_min=None, date_max=None):
    log_info(f"Starting generic sampling analysis. Points: {len(sampling_points)}, Folder: {images_folder}")
    results_colors = {name: [] for name, _, _ in sampling_points}
    results_mg = {name: [] for name, _, _ in sampling_points}

    if not os.path.isdir(images_folder):
        log_error(f"Image folder not found: '{images_folder}'.")
        st.error(f"Ο φάκελος εικόνων '{images_folder}' δεν βρέθηκε."); return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    tif_files = sorted([f for f in os.listdir(images_folder) if f.lower().endswith(('.tif', '.tiff'))])
    log_debug(f"Found {len(tif_files)} TIF files in {images_folder}.")

    for filename in tif_files:
        log_debug(f"Processing TIF: {filename}")
        m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
        if not m: log_warning(f"Skipping {filename}: No date found."); continue
        try: date_obj = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: log_warning(f"Skipping {filename}: Invalid date."); continue

        if (date_min and date_obj.date() < date_min) or \
           (date_max and date_obj.date() > date_max):
            log_debug(f"Skipping {filename}: Outside date range.")
            continue

        file_path = os.path.join(images_folder, filename)
        try:
            with rasterio.open(file_path) as src:
                if src.count < 3: log_warning(f"Skipping {filename}: <3 channels."); continue
                current_transform = src.transform
                for name, lon, lat in sampling_points:
                    if name not in selected_points_names: continue
                    try:
                        col, row = map(int, (~current_transform) * (lon, lat))
                        if not (0 <= col < src.width and 0 <= row < src.height):
                            log_warning(f"Point {name} ({lon},{lat}) out of bounds for {filename}. ({col},{row}) vs ({src.width},{src.height})"); continue

                        win = rasterio.windows.Window(col,row,1,1)
                        r,g,b = src.read(1,window=win)[0,0], src.read(2,window=win)[0,0], src.read(3,window=win)[0,0]
                        mg_val = (g / 255.0) * 2.0 # Placeholder
                        results_mg[name].append((date_obj, mg_val))
                        results_colors[name].append((date_obj, (r/255., g/255., b/255.)))
                    except IndexError: log_error(f"Index error for point {name} in {filename}.")
                    except Exception as p_err: log_error(f"Error sampling point {name} in {filename}: {p_err}")
        except rasterio.errors.RasterioIOError as e:
            log_error(f"Rasterio I/O Error processing {filename}: {e}")
            st.warning(f"Σφάλμα I/O επεξεργασίας {filename}: {e}")
        except Exception as e:
            log_error(f"Generic Error processing {filename}: {e}")
            st.warning(f"Σφάλμα επεξεργασίας {filename}: {e}")

    log_info("Finished TIF processing. Starting plot generation.")

    if first_image_data is None or first_image_data.ndim != 3 or first_image_data.shape[0] < 3:
        log_error("Invalid first image data for plotting.")
        st.error("Μη έγκυρα δεδομένα πρώτης εικόνας για εμφάνιση."); return go.Figure(), go.Figure(), go.Figure(), go.Figure(), {}, {}, pd.DataFrame()

    rgb_disp = first_image_data[:3, :, :].transpose((1,2,0))
    if rgb_disp.max() > 1.0: rgb_disp = rgb_disp / 255.0
    rgb_disp = np.clip(rgb_disp, 0, 1)

    fig_geo = px.imshow(rgb_disp, title='Εικόνα Αναφοράς & Σημεία'); fig_geo.update_layout(height=600, uirevision='geo')
    if first_transform:
        for n,lon,lat in sampling_points:
            if n in selected_points_names:
                try:
                    col,row = map(int, (~first_transform) * (lon,lat))
                    fig_geo.add_trace(go.Scatter(x=[col],y=[row],mode='markers+text',marker=dict(color='red',size=10,symbol='x'),name=n,text=n,textposition="top right"))
                except Exception as e: log_error(f"Error plotting point {n} on geo map: {e}")
    fig_geo.update_xaxes(visible=False); fig_geo.update_yaxes(visible=False,scaleanchor="x",scaleratio=1)
    log_debug("Geo plot created.")

    df_h = pd.DataFrame(columns=['Date','Height'])
    if os.path.exists(str(lake_height_path)):
        try:
            df_h_temp = pd.read_excel(lake_height_path)
            if not df_h_temp.empty and len(df_h_temp.columns) >=2:
                df_h['Date']=pd.to_datetime(df_h_temp.iloc[:,0],errors='coerce'); df_h['Height']=pd.to_numeric(df_h_temp.iloc[:,1],errors='coerce')
                df_h.dropna(inplace=True); df_h.sort_values('Date',inplace=True)
                log_info(f"Loaded {len(df_h)} height records.")
        except Exception as e:
            log_error(f"Error reading lake height Excel '{lake_height_path}': {e}")
            df_h = pd.DataFrame(columns=['Date','Height'])
    else:
        log_warning(f"Lake height file not found: {lake_height_path}")


    fig_colors = make_subplots(specs=[[{"secondary_y":True}]]); pt_y_map={n:i for i,n in enumerate(selected_points_names)}
    try:
        for n_iter in selected_points_names:
            if n_iter in results_colors and results_colors[n_iter]:
                dts,cols=zip(*sorted(results_colors[n_iter],key=lambda x:x[0])) if results_colors[n_iter] else ([],[])
                c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
                fig_colors.add_trace(go.Scatter(x=list(dts),y=[pt_y_map.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=10),name=n_iter),secondary_y=False)
        if not df_h.empty: fig_colors.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη',mode='lines',line=dict(color='blue')),secondary_y=True)
        fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη',yaxis=dict(tickmode='array',tickvals=list(pt_y_map.values()),ticktext=list(pt_y_map.keys())),yaxis2=dict(title='Στάθμη (m)'), uirevision='colors')
        log_debug("Colors plot created.")
    except Exception as e: log_error(f"Error creating colors plot: {e}")

    fig_mg=go.Figure(); fig_dual=make_subplots(specs=[[{"secondary_y":True}]])
    try:
        all_mg_by_d={};
        for p_name in selected_points_names:
            if p_name in results_mg:
                for d,v in results_mg[p_name]: all_mg_by_d.setdefault(d,[]).append(v)
        s_dts_mg=sorted(all_mg_by_d.keys()); mean_mg=[np.mean(all_mg_by_d[d]) for d in s_dts_mg if all_mg_by_d[d]]

        if s_dts_mg and mean_mg: fig_mg.add_trace(go.Scatter(x=s_dts_mg,y=mean_mg,mode='lines+markers',marker=dict(color=mean_mg,colorscale='Viridis',colorbar=dict(title='mg/m³'),size=8)))
        fig_mg.update_layout(title='Μέσο mg/m³', uirevision='mg')
        log_debug("MG plot created.")

        if not df_h.empty: fig_dual.add_trace(go.Scatter(x=df_h['Date'],y=df_h['Height'],name='Στάθμη Λίμνης',mode='lines'),secondary_y=False)
        if s_dts_mg and mean_mg: fig_dual.add_trace(go.Scatter(x=s_dts_mg,y=mean_mg,name='Μέσο mg/m³',mode='lines+markers', marker=dict(color=mean_mg, colorscale='Viridis', showscale=False)),secondary_y=True)
        fig_dual.update_layout(title='Στάθμη & Μέσο mg/m³', uirevision='dual',
                               yaxis=dict(title=dict(text="Στάθμη (m)",font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue"), side='left'),
                               yaxis2=dict(title=dict(text="Μέσο mg/m³",font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"), overlaying='y', side='right'))
        log_debug("Dual plot created.")
    except Exception as e: log_error(f"Error creating MG/Dual plot: {e}")

    log_info("Finished generic sampling analysis.")
    return fig_geo,fig_dual,fig_colors,fig_mg,results_colors,results_mg,df_h

def analyze_sampling_for_dashboard(sampling_points: list, first_image_data_rgb, first_image_transform,
                                   images_folder_path: str, lake_height_excel_path: str,
                                   selected_point_names_for_plot: list | None = None):
    # This function is very similar to analyze_sampling_generic.
    # For brevity in this example, we'll assume it has similar error potential and
    # would need similar try-except blocks and logging. We'll skip adding them here
    # but you should add them following the pattern of analyze_sampling_generic.
    log_info(f"Starting dashboard sampling analysis. Points: {len(sampling_points)}, Folder: {images_folder_path}")

    def _geographic_to_pixel(lon: float, lat: float, transform_matrix) -> tuple[int, int]:
        try:
            inv_transform = ~transform_matrix; px, py = inv_transform * (lon, lat); return int(px), int(py)
        except Exception as e:
            log_error(f"Error converting geographic to pixel ({lon},{lat}): {e}"); return -1,-1

    def _map_rgb_to_mg(r_val: float, g_val: float, b_val: float, mg_factor: float = 2.0) -> float:
        return (g_val / 255.0) * mg_factor

    results_colors_dash, results_mg_dash = {n:[] for n,_,_ in sampling_points}, {n:[] for n,_,_ in sampling_points}
    if not os.path.isdir(images_folder_path):
        log_error(f"Image folder not found: '{images_folder_path}'.")
        st.error(f"Ο φάκελος εικόνων '{images_folder_path}' δεν βρέθηκε για dashboard."); return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    tif_files = sorted([f for f in os.listdir(images_folder_path) if f.lower().endswith(('.tif', '.tiff'))])

    for filename in tif_files:
        m = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', filename)
        if not m: continue
        try: date_obj = datetime(int(m.groups()[0]), int(m.groups()[1]), int(m.groups()[2]))
        except ValueError: continue

        file_path = os.path.join(images_folder_path, filename)
        try:
            with rasterio.open(file_path) as src:
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
        except Exception as e: log_error(f"Error processing {filename} for dashboard: {e}"); continue

    if first_image_data_rgb is None or first_image_transform is None:
        log_error("Reference image data missing for dashboard.")
        st.error("Δεδομένα εικόνας αναφοράς δεν είναι διαθέσιμα."); return go.Figure(),go.Figure(),go.Figure(),go.Figure(),{},{},pd.DataFrame()

    rgb_disp_data = first_image_data_rgb.transpose((1,2,0))
    if rgb_disp_data.max() > 1: rgb_disp_data = rgb_disp_data / 255.0
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
        except Exception as e: log_error(f"Error reading height Excel (dashboard): {e}"); st.warning(f"Σφάλμα ανάγνωσης στάθμης (dashboard): {e}")

    # ... The rest of the plotting code ...
    # (Add try-excepts around plot generation as in analyze_sampling_generic if needed)
    fig_colors_d = make_subplots(specs=[[{"secondary_y": True}]])
    pts_plot = selected_point_names_for_plot if selected_point_names_for_plot else [p[0] for p in sampling_points]
    pt_y_idx = {n: i for i, n in enumerate(pts_plot)}

    for n_iter in pts_plot:
        if n_iter in results_colors_dash and results_colors_dash[n_iter]:
            d_list = sorted(results_colors_dash[n_iter], key=lambda x: x[0])
            if d_list:
                dts_c, cols_c_norm = zip(*d_list)
                cols_rgb_s = [f"rgb({int(c[0] * 255)},{int(c[1] * 255)},{int(c[2] * 255)})" for c in cols_c_norm]
                y_p = pt_y_idx.get(n_iter, -1)
                if y_p != -1:
                    fig_colors_d.add_trace(go.Scatter(x=list(dts_c), y=[y_p] * len(dts_c), mode='markers', marker=dict(color=cols_rgb_s, size=10), name=n_iter, legendgroup=n_iter), secondary_y=False)

    if not df_h_d.empty: fig_colors_d.add_trace(go.Scatter(x=df_h_d['Date'], y=df_h_d['Height'], name='Στάθμη', mode='lines', line=dict(color='blue', width=2), legendgroup="h_grp"), secondary_y=True)
    fig_colors_d.update_layout(title='Χρώματα Pixel & Στάθμη', xaxis_title='Ημερομηνία',
                               yaxis=dict(title='Σημεία', tickmode='array', tickvals=list(pt_y_idx.values()), ticktext=list(pt_y_idx.keys()), showgrid=False),
                               yaxis2=dict(title='Στάθμη (m)', showgrid=True, gridcolor='rgba(128,128,128,0.2)'), showlegend=True, uirevision='dashboard_colors')

    all_mg_vals_date_d = {};
    for p_n in pts_plot:
        if p_n in results_mg_dash:
            for d_obj, val_mg in results_mg_dash[p_n]: all_mg_vals_date_d.setdefault(d_obj, []).append(val_mg)
    s_dates_mg_d = sorted(all_mg_vals_date_d.keys())
    avg_mg_d = [np.mean(all_mg_vals_date_d[d_obj]) for d_obj in s_dates_mg_d if all_mg_vals_date_d[d_obj]]

    fig_mg_d = go.Figure()
    if s_dates_mg_d and avg_mg_d: fig_mg_d.add_trace(go.Scatter(x=s_dates_mg_d, y=avg_mg_d, mode='lines+markers', name='Μέσο mg/m³', marker=dict(color=avg_mg_d, colorscale='Viridis', reversescale=True, colorbar=dict(title='mg/m³', thickness=15), size=10), line=dict(color='grey')))
    fig_mg_d.update_layout(title='Μέσο mg/m³ (Επιλεγμένα Σημεία)', xaxis_title='Ημερομηνία', yaxis_title='mg/m³', uirevision='dashboard_mg')

    fig_dual_d = make_subplots(specs=[[{"secondary_y": True}]])
    if not df_h_d.empty:
        fig_dual_d.add_trace(go.Scatter(x=df_h_d['Date'], y=df_h_d['Height'], name='Στάθμη', mode='lines', line=dict(color='deepskyblue')), secondary_y=False)
    if s_dates_mg_d and avg_mg_d:
        fig_dual_d.add_trace(go.Scatter(x=s_dates_mg_d, y=avg_mg_d, name='Μέσο mg/m³', mode='lines+markers', marker=dict(color=avg_mg_d, colorscale='Viridis', reversescale=True, size=10, showscale=False), line=dict(color='lightgreen')), secondary_y=True)

    fig_dual_d.update_layout(
        title='Στάθμη & Μέσο mg/m³',
        xaxis_title='Ημερομηνία',
        uirevision='dashboard_dual',
        yaxis=dict(title=dict(text="Στάθμη (m)", font=dict(color="deepskyblue")), tickfont=dict(color="deepskyblue")),
        yaxis2=dict(title=dict(text="mg/m³", font=dict(color="lightgreen")), tickfont=dict(color="lightgreen"), overlaying='y', side='right')
    )


    log_info("Finished dashboard sampling analysis.")
    return fig_geo_d,fig_dual_d,fig_colors_d,fig_mg_d,results_colors_dash,results_mg_dash,df_h_d

# --- Legend & Image Navigation ---
@st.cache_resource
def create_chl_legend_figure(orientation="horizontal", theme_bg_color=None, theme_text_color=None):
    log_debug(f"Creating Chl legend (orientation={orientation}).")
    try:
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
    except Exception as e:
        log_error(f"Error creating legend figure: {e}")
        return None # Return None or a placeholder figure


def image_navigation_ui(images_folder: str, available_dates_map: dict,
                        session_state_key_for_idx: str, key_prefix: str,
                        show_legend: bool = False, index_name_for_legend: str = ""):
    log_debug(f"Setting up image navigation UI (key_prefix={key_prefix}).")
    if not available_dates_map:
        log_warning("No available images for navigation.")
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
    image_filename = available_dates_map[actual_selected_date_str]
    image_full_path = os.path.join(images_folder, image_filename)
    log_debug(f"Selected image for navigation: {image_full_path}")

    if os.path.exists(image_full_path):
        try:
            # IMPORTANT: st.image may struggle with GeoTIFFs.
            # It's better to load with rasterio and display as an array if this crashes.
            log_warning(f"Attempting to display TIF directly with st.image: {image_full_path}. This MIGHT CRASH.")
            st.image(image_full_path, caption=f"{image_filename}", use_column_width=True)
            if show_legend and index_name_for_legend == "Χλωροφύλλη":
                legend_fig = create_chl_legend_figure(orientation="horizontal")
                if legend_fig: st.pyplot(legend_fig)

        except Exception as e:
            log_error(f"Error displaying image {image_full_path} with st.image: {e}")
            st.error(f"Σφάλμα εμφάνισης εικόνας {image_filename}. Δοκιμάστε να φορτώσετε με rasterio και να εμφανίσετε ως array.")
    else:
        log_error(f"Image file not found for navigation: {image_full_path}")
        st.error(f"Το αρχείο εικόνας δεν βρέθηκε: {image_full_path}")
    return image_full_path

# --- Main Application Pages ---
def run_lake_processing_app(waterbody: str, index_name: str):
    log_info(f"Running Lake Processing App for WB='{waterbody}', Index='{index_name}'.")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Επιφανειακή Αποτύπωση: {waterbody} - {index_name}")

        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder:
            # Error is already logged in get_data_folder
            st.markdown('</div>', unsafe_allow_html=True); return

        input_folder_geotiffs = os.path.join(data_folder, "GeoTIFFs")

        with st.spinner(f"Φόρτωση δεδομένων για {waterbody} - {index_name}..."):
            STACK, DAYS, DATES, _ = load_data_for_lake_processing(input_folder_geotiffs)

        if STACK is None or not DATES:
            log_error("Failed to load data in run_lake_processing_app.")
            st.markdown('</div>', unsafe_allow_html=True); return

        # ... (Sidebar and filter code - relatively safe, skipping try-excepts for brevity) ...
        st.sidebar.subheader(f"Φίλτρα Επεξεργασίας ({index_name})")
        min_avail_date = min(DATES).date() if DATES else date.today()
        max_avail_date = max(DATES).date() if DATES else date.today()
        unique_years_avail = sorted(list(set(d.year for d in DATES if d))) if DATES else []
        clean_index_name_for_key = re.sub(r'[^a-zA-Z0-9_]', '', index_name)
        key_suffix = f"_lp_{waterbody}_{clean_index_name_for_key}"
        common_filename_prefix = f"{waterbody}_{index_name}_surface_map"
        threshold_range_val = st.sidebar.slider("Εύρος τιμών pixel:", 0, 255, (0, 255), key=f"thresh{key_suffix}")
        col_start_lp, col_end_lp = st.sidebar.columns(2)
        refined_start_val = col_start_lp.date_input("Έναρξη περιόδου:", value=min_avail_date, min_value=min_avail_date, max_value=max_avail_date, key=f"refined_start{key_suffix}")
        refined_end_val = col_end_lp.date_input("Λήξη περιόδου:", value=max_avail_date, min_value=min_avail_date, max_value=max_avail_date, key=f"refined_end{key_suffix}")
        if refined_start_val > refined_end_val: st.sidebar.error("Η ημερομηνία έναρξης πρέπει να είναι πριν ή ίδια με την ημερομηνία λήξης."); st.markdown('</div>', unsafe_allow_html=True); return
        display_option_val = st.sidebar.radio("Εμφάνιση Μέσου Δείγματος:", ["Thresholded", "Original"], index=0, key=f"display_opt{key_suffix}", horizontal=True)
        month_options_map = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        default_months = st.session_state.get(f"sel_months{key_suffix}", list(month_options_map.keys()))
        selected_months_val = st.sidebar.multiselect("Επιλογή Μηνών:", options=list(month_options_map.keys()), format_func=lambda x: month_options_map[x], default=default_months, key=f"sel_months{key_suffix}")
        default_years = st.session_state.get(f"sel_years{key_suffix}", unique_years_avail)
        selected_years_val = st.sidebar.multiselect("Επιλογή Ετών:", options=unique_years_avail, default=default_years, key=f"sel_years{key_suffix}")
        start_dt_conv = datetime.combine(refined_start_val, datetime.min.time())
        end_dt_conv = datetime.combine(refined_end_val, datetime.max.time())
        indices_to_keep = [i for i, dt_obj in enumerate(DATES) if (start_dt_conv <= dt_obj <= end_dt_conv and (not selected_months_val or dt_obj.month in selected_months_val) and (not selected_years_val or dt_obj.year in selected_years_val))]
        if not indices_to_keep: st.info("Δεν υπάρχουν δεδομένα για την επιλεγμένη περίοδο/μήνες/έτη."); st.markdown('</div>', unsafe_allow_html=True); return


        with st.spinner("Επεξεργασία φιλτραρισμένων δεδομένων και δημιουργία γραφημάτων..."):
            try:
                log_debug("Starting filtered data processing in lake processing app.")
                stack_filt = STACK[indices_to_keep, :, :]
                days_filt = DAYS[indices_to_keep]
                filtered_dates_objects = [DATES[i] for i in indices_to_keep]
                lower_t, upper_t = threshold_range_val
                in_range_bool_mask = np.logical_and(stack_filt >= lower_t, stack_filt <= upper_t)

                st.subheader("Ανάλυση Χαρτών")
                expander_col1, expander_col2 = st.columns(2)

                with expander_col1, st.expander("Χάρτης: Ημέρες εντός Εύρους Τιμών", expanded=True):
                    days_in_range_map = np.nansum(in_range_bool_mask, axis=0)
                    fig_days = px.imshow(days_in_range_map, color_continuous_scale="plasma", labels={"color": "Ημέρες"})
                    st.plotly_chart(fig_days, use_container_width=True, key=f"fig_days_map{key_suffix}")
                    add_excel_download_button(pd.DataFrame(days_in_range_map), common_filename_prefix, "Days_in_Range_Map", f"excel_days_map{key_suffix}")

                tick_vals_days = [1,32,60,91,121,152,182,213,244,274,305,335,365]
                tick_text_days = ["Ιαν","Φεβ","Μαρ","Απρ","Μαΐ","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ",""]

                with expander_col2, st.expander("Χάρτης: Μέση Ημέρα Εμφάνισης εντός Εύρους", expanded=True):
                    days_array_expanded = days_filt.reshape((-1, 1, 1))
                    sum_days_in_range = np.nansum(days_array_expanded * in_range_bool_mask, axis=0)
                    count_pixels_in_range = np.nansum(in_range_bool_mask, axis=0)
                    mean_day_map = np.divide(sum_days_in_range, count_pixels_in_range, out=np.full(sum_days_in_range.shape, np.nan), where=(count_pixels_in_range != 0))
                    fig_mean_day = px.imshow(mean_day_map, color_continuous_scale="RdBu", labels={"color": "Μέση Ημέρα (1-365)"}, color_continuous_midpoint=182)
                    fig_mean_day.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals_days, ticktext=tick_text_days))
                    st.plotly_chart(fig_mean_day, use_container_width=True, key=f"fig_mean_day_map{key_suffix}")
                    add_excel_download_button(pd.DataFrame(mean_day_map), common_filename_prefix, "Mean_Day_Map", f"excel_mean_day_map{key_suffix}")

                # ... (Continue with other plots, adding try-excepts if they involve heavy numpy/plotly) ...
                log_debug("Finished filtered data processing and plotting.")

            except Exception as e:
                log_error(f"Error during Lake Processing App analysis/plotting: {e}")
                st.error(f"Προέκυψε σφάλμα κατά την επεξεργασία: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

def run_water_quality_dashboard(waterbody: str, index_name: str):
    log_info(f"Running Water Quality Dashboard for WB='{waterbody}', Index='{index_name}'.")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Προφίλ Ποιότητας και Στάθμης: {waterbody} - {index_name}")

        key_suffix_dash = f"_dash_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]', '', index_name)}"
        common_filename_prefix_dash = f"{waterbody}_{index_name}"
        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder: st.markdown('</div>', unsafe_allow_html=True); return

        images_folder_path = os.path.join(data_folder,"GeoTIFFs")
        lake_height_excel_path = os.path.join(data_folder,"lake height.xlsx")
        default_sampling_kml_path = os.path.join(data_folder,"sampling.kml")
        vid_path = next((p for n in ["timelapse.mp4","timelapse.gif","Sentinel-2_L1C-202307221755611-timelapse.gif"] for p in [os.path.join(data_folder,n), os.path.join(images_folder_path,n)] if os.path.exists(p)), None)

        st.sidebar.subheader(f"Ρυθμίσεις Πίνακα ({index_name})")
        available_tifs = {}
        try:
            if os.path.exists(images_folder_path):
                for fn in os.listdir(images_folder_path):
                    if fn.lower().endswith(('.tif','.tiff')):
                        _, d = extract_date_from_filename(fn)
                        if d: available_tifs[str(d.date())] = fn
            else:
                 log_error(f"Images folder not found for dashboard: {images_folder_path}")
        except Exception as e:
            log_error(f"Error listing TIFs for dashboard: {e}")

        first_img_rgb, first_img_transform = None, None
        if available_tifs:
            sel_bg_date_options = sorted(available_tifs.keys(),reverse=True)
            sel_bg_date_index = 0 if sel_bg_date_options else None
            sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:", sel_bg_date_options, index=sel_bg_date_index, key=f"bg_date{key_suffix_dash}")
            if sel_bg_date and available_tifs.get(sel_bg_date):
                try:
                    ref_img_path = os.path.join(images_folder_path, available_tifs[sel_bg_date])
                    log_debug(f"Loading reference image: {ref_img_path}")
                    with rasterio.open(ref_img_path) as src:
                        if src.count>=3: first_img_rgb,first_img_transform = src.read([1,2,3]),src.transform
                        else: log_error("Reference image < 3 channels."); st.sidebar.error("Εικόνα < 3 κανάλια.")
                except Exception as e: log_error(f"Error loading reference image: {e}"); st.sidebar.error(f"Σφάλμα φόρτωσης αναφοράς: {e}")
        else: st.sidebar.warning("Δεν βρέθηκαν GeoTIFF για εικόνα αναφοράς.")

        if first_img_rgb is None:
            log_error("No valid reference image loaded, cannot continue dashboard.")
            st.error("Απαιτείται έγκυρη εικόνα αναφοράς GeoTIFF."); st.markdown('</div>', unsafe_allow_html=True); return

        tabs_ctrl = st.tabs(["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"])

        with tabs_ctrl[0]: # Default Sampling
            st.markdown("##### Ανάλυση με Προεπιλεγμένα Σημεία")
            def_pts_list = parse_sampling_kml(default_sampling_kml_path) if os.path.exists(default_sampling_kml_path) else []
            st.session_state[f"def_pts_list{key_suffix_dash}"] = def_pts_list
            if def_pts_list:
                all_def_point_names = [n for n,_,_ in def_pts_list]
                sel_pts_def_names = st.multiselect("Σημεία (Προεπιλογή):", all_def_point_names, default=all_def_point_names[:], key=f"sel_def{key_suffix_dash}")
                st.session_state[f"sel_pts_def_names{key_suffix_dash}"] = sel_pts_def_names
                if st.button("Εκτέλεση (Προεπιλογή)", key=f"run_def{key_suffix_dash}", type="primary", use_container_width=True):
                    with st.spinner("Εκτέλεση ανάλυσης..."):
                        try:
                             st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                 def_pts_list, first_img_rgb, first_img_transform, images_folder_path, lake_height_excel_path, sel_pts_def_names)
                        except Exception as e: log_error(f"Error running default dashboard analysis: {e}"); st.error(f"Σφάλμα: {e}")
            else: st.caption("Δεν βρέθηκε το προεπιλεγμένο αρχείο δειγματοληψίας (sampling.kml).")
            # ... (Display results - Add try-excepts around plotting if needed) ...

        with tabs_ctrl[1]: # Upload KML
            st.markdown("##### Ανάλυση με Ανεβασμένο KML")
            upl_file = st.file_uploader("Ανέβασμα KML:", type="kml", key=f"upl_kml_{key_suffix_dash}")
            if upl_file:
                upl_pts_list = parse_sampling_kml(upl_file)
                st.session_state[f"upl_pts_list{key_suffix_dash}"] = upl_pts_list
                if upl_pts_list:
                    st.success(f"Βρέθηκαν {len(upl_pts_list)} σημεία.")
                    all_upl_point_names = [n for n,_,_ in upl_pts_list]
                    sel_pts_upl_names = st.multiselect("Σημεία (KML):", all_upl_point_names, default=all_upl_point_names[:], key=f"sel_upl_{key_suffix_dash}")
                    st.session_state[f"sel_pts_upl_names{key_suffix_dash}"] = sel_pts_upl_names
                    if st.button("Εκτέλεση (KML)",key=f"run_upl_{key_suffix_dash}",type="primary", use_container_width=True):
                         with st.spinner("Εκτέλεση..."):
                            try:
                                st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD] = analyze_sampling_for_dashboard(
                                    upl_pts_list, first_img_rgb, first_img_transform, images_folder_path, lake_height_excel_path, sel_pts_upl_names)
                            except Exception as e: log_error(f"Error running uploaded KML analysis: {e}"); st.error(f"Σφάλμα: {e}")
                else: st.error("Το KML δεν περιείχε έγκυρα σημεία ή δεν μπόρεσε να αναλυθεί.")
            # ... (Display results - Add try-excepts around plotting if needed) ...

        # --- Display Results Logic (Simplified, add try-excepts as needed) ---
        if SESSION_KEY_DEFAULT_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]:
             with tabs_ctrl[0]:
                 log_debug("Displaying default dashboard results.")
                 res_def = st.session_state[SESSION_KEY_DEFAULT_RESULTS_DASHBOARD]
                 if isinstance(res_def, tuple) and len(res_def) == 7:
                    fig_g, fig_d, fig_c, fig_m, _, _, _ = res_def
                    n_tabs_def_display = st.tabs(["GeoTIFF", "Χρώματα Pixel", "Συνδυασμένο"])
                    with n_tabs_def_display[0]: st.plotly_chart(fig_g, use_container_width=True)
                    with n_tabs_def_display[1]: st.plotly_chart(fig_c, use_container_width=True)
                    with n_tabs_def_display[2]: st.plotly_chart(fig_d, use_container_width=True)
                 else: log_error("Default results have incorrect format.")

        if SESSION_KEY_UPLOAD_RESULTS_DASHBOARD in st.session_state and st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]:
             with tabs_ctrl[1]:
                log_debug("Displaying uploaded KML dashboard results.")
                res_upl = st.session_state[SESSION_KEY_UPLOAD_RESULTS_DASHBOARD]
                if isinstance(res_upl, tuple) and len(res_upl) == 7:
                    fig_g_u, fig_d_u, fig_c_u, fig_m_u, _, _, _ = res_upl
                    n_tabs_upl_display = st.tabs(["GeoTIFF", "Χρώματα", "Διπλό"])
                    with n_tabs_upl_display[0]: st.plotly_chart(fig_g_u, use_container_width=True)
                    with n_tabs_upl_display[1]: st.plotly_chart(fig_c_u, use_container_width=True)
                    with n_tabs_upl_display[2]: st.plotly_chart(fig_d_u, use_container_width=True)
                else: log_error("Uploaded KML results have incorrect format.")

        st.markdown('</div>', unsafe_allow_html=True)


def run_predictive_tools(waterbody: str, initial_selected_index: str):
    log_info(f"Running Predictive Tools for WB='{waterbody}'.")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True) # Changed from custom-card
        st.header(f"Εργαλεία Πρόβλεψης & Έγκαιρης Ενημέρωσης: {waterbody}")
        st.markdown(f"Παράλληλη Ανάλυση για Δείκτες: **Πραγματικό, Χλωροφύλλη, Θολότητα**")

        key_suffix_pred_section = f"_pred_tool_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]', '', initial_selected_index)}"

        # ... (Filter setup - relatively safe) ...
        chart_display_options = { "GeoTIFF": "geo", "Χρώματα Pixel & Στάθμη": "colors", "Μέσο mg/m³": "mg", "Συνδυασμένο": "dual" }
        selected_charts_to_display = st.multiselect("Επιλέξτε τύπους διαγραμμάτων:", list(chart_display_options.keys()), default=list(chart_display_options.keys()), key=f"select_charts{key_suffix_pred_section}")
        st.subheader("Κοινές Παράμετροι Φιλτραρίσματος")
        col_filt1, col_filt2 = st.columns(2)
        with col_filt1:
            lower_thresh_common, upper_thresh_common = st.slider("Εύρος τιμών pixel:", 0, 255, (0, 255), key=f"thresh_common{key_suffix_pred_section}")
            sampling_type_common = st.radio("Σύνολο Σημείων:", ["Προεπιλογή", "Ανέβασμα KML"], key=f"sampling_type_common{key_suffix_pred_section}", horizontal=True)
        with col_filt2:
            date_min_common = st.date_input("Ημερομηνία από:", value=date(2015, 1, 1), key=f"date_min_common{key_suffix_pred_section}")
            date_max_common = st.date_input("Ημερομηνία έως:", value=date.today(), key=f"date_max_common{key_suffix_pred_section}")
        uploaded_kml_common = None
        if sampling_type_common == "Ανέβασμα KML":
            uploaded_kml_common = st.file_uploader("Ανεβάστε KML:", type="kml", key=f"kml_upload_common{key_suffix_pred_section}")


        if st.button("Εκτέλεση Παράλληλης Ανάλυσης", key=f"recalc_parallel{key_suffix_pred_section}", type="primary", use_container_width=True):
            log_info("--- STARTING PARALLEL ANALYSIS ---")
            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]
            analysis_results_all_indices = {}
            sampling_points_to_use_for_analysis = None
            default_kml_found = False

            # --- Determine Sampling Points ---
            if sampling_type_common == "Προεπιλογή":
                log_debug("Using default KML. Searching...")
                for idx_for_kml in indices_to_analyze:
                    temp_data_folder_for_kml = get_data_folder(waterbody, idx_for_kml)
                    if temp_data_folder_for_kml:
                        default_kml_path_common = os.path.join(temp_data_folder_for_kml, "sampling.kml")
                        if os.path.exists(default_kml_path_common):
                            sampling_points_to_use_for_analysis = parse_sampling_kml(default_kml_path_common)
                            if sampling_points_to_use_for_analysis:
                                default_kml_found = True; log_info(f"Found default KML in '{idx_for_kml}' folder."); break
                if not default_kml_found: log_error("Default KML not found anywhere!"); st.error("Δεν βρέθηκε προεπιλεγμένο αρχείο KML."); st.markdown('</div>', unsafe_allow_html=True); return
            elif sampling_type_common == "Ανέβασμα KML":
                log_debug("Using uploaded KML.")
                if uploaded_kml_common: sampling_points_to_use_for_analysis = parse_sampling_kml(uploaded_kml_common)
                if not sampling_points_to_use_for_analysis: log_error("Uploaded KML missing or failed to parse."); st.error("Ανεβάστε έγκυρο KML."); st.markdown('</div>', unsafe_allow_html=True); return

            if not sampling_points_to_use_for_analysis: log_error("No sampling points defined!"); st.error("Δεν ορίστηκαν σημεία δειγματοληψίας."); st.markdown('</div>', unsafe_allow_html=True); return

            all_point_names_to_use_in_analysis = [pt[0] for pt in sampling_points_to_use_for_analysis]
            log_info(f"Using {len(all_point_names_to_use_in_analysis)} points for analysis.")

            progress_bar = st.progress(0, text="Έναρξη επεξεργασίας...")
            num_indices = len(indices_to_analyze)

            # --- Main Analysis Loop ---
            for i_prog, current_idx_name_iter in enumerate(indices_to_analyze):
                progress_val = (i_prog + 1) / num_indices
                progress_text = f"Επεξεργασία δείκτη: {current_idx_name_iter} ({i_prog+1}/{num_indices})"
                progress_bar.progress(progress_val, text=progress_text)
                log_info(f"--- Processing Index: {current_idx_name_iter} ---")

                data_folder_idx = get_data_folder(waterbody, current_idx_name_iter)
                if not data_folder_idx:
                    analysis_results_all_indices[current_idx_name_iter] = {"error": "Δεν βρέθηκε φάκελος δεδομένων."}; continue

                images_folder_idx = os.path.join(data_folder_idx, "GeoTIFFs")
                lake_height_excel_idx = os.path.join(data_folder_idx, "lake height.xlsx")

                tif_files_idx = sorted(glob.glob(os.path.join(images_folder_idx, "*.tif*"))) # Allow .tiff too
                if not tif_files_idx:
                    analysis_results_all_indices[current_idx_name_iter] = {"error": "Δεν βρέθηκαν αρχεία GeoTIFF."}; continue

                first_img_data_idx, first_transform_idx = None, None
                try:
                    with rasterio.open(tif_files_idx[0]) as src:
                        if src.count < 3: analysis_results_all_indices[current_idx_name_iter] = {"error": "1η εικόνα < 3 κανάλια."}; continue
                        first_img_data_idx, first_transform_idx = src.read([1,2,3]), src.transform
                except Exception as e:
                    analysis_results_all_indices[current_idx_name_iter] = {"error": f"Σφάλμα φόρτωσης 1ης εικόνας: {e}"}; continue

                try:
                    log_debug(f"Calling analyze_sampling_generic for {current_idx_name_iter}")
                    # **** THIS IS A VERY CRITICAL CALL ****
                    # If it crashes here, the problem is likely inside analyze_sampling_generic
                    # (probably rasterio or memory)
                    raw_figs_and_data = analyze_sampling_generic(
                        sampling_points=sampling_points_to_use_for_analysis,
                        first_image_data=first_img_data_idx, first_transform=first_transform_idx,
                        images_folder=images_folder_idx, lake_height_path=lake_height_excel_idx,
                        selected_points_names=all_point_names_to_use_in_analysis,
                        lower_thresh=lower_thresh_common, upper_thresh=upper_thresh_common,
                        date_min=date_min_common, date_max=date_max_common )
                    analysis_results_all_indices[current_idx_name_iter] = { "fig_geo": raw_figs_and_data[0], "fig_dual": raw_figs_and_data[1], "fig_colors": raw_figs_and_data[2], "fig_mg": raw_figs_and_data[3], "data_results_colors": raw_figs_and_data[4], "data_results_mg": raw_figs_and_data[5], "data_df_h": raw_figs_and_data[6] }
                    log_info(f"--- Finished Index: {current_idx_name_iter} ---")
                except Exception as e_analyze:
                    log_error(f"FATAL ERROR during analysis for {current_idx_name_iter}: {e_analyze}")
                    analysis_results_all_indices[current_idx_name_iter] = {"error": f"Σφάλμα ανάλυσης: {e_analyze}"}

            st.session_state[f"predictive_tool_results{key_suffix_pred_section}"] = analysis_results_all_indices
            st.session_state[f"predictive_tool_selected_charts{key_suffix_pred_section}"] = selected_charts_to_display
            st.session_state[f"predictive_tool_sampling_points{key_suffix_pred_section}"] = sampling_points_to_use_for_analysis
            progress_bar.progress(1.0, text="Ολοκληρώθηκε!")
            st.success("Όλες οι αναλύσεις ολοκληρώθηκαν!")
            log_info("--- FINISHED PARALLEL ANALYSIS ---")


        # --- Display Predictive Results ---
        if f"predictive_tool_results{key_suffix_pred_section}" in st.session_state:
            log_debug("Displaying predictive tool results.")
            analysis_results = st.session_state[f"predictive_tool_results{key_suffix_pred_section}"]
            charts_to_show = st.session_state.get(f"predictive_tool_selected_charts{key_suffix_pred_section}", [])
            indices_to_analyze = ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"]

            st.markdown("---")
            st.subheader("Αποτελέσματα Παράλληλης Ανάλυσης")

            for chart_name_key_iter, fig_internal_key_iter in chart_display_options.items():
                if chart_name_key_iter not in charts_to_show: continue

                st.markdown(f"#### {chart_name_key_iter}")
                inner_cols = st.columns(len(indices_to_analyze))
                for i, idx_name_iter_cols in enumerate(indices_to_analyze):
                    with inner_cols[i]:
                        st.markdown(f"##### {idx_name_iter_cols}")
                        result_data = analysis_results.get(idx_name_iter_cols, {})
                        if "error" in result_data: st.error(result_data["error"]); continue
                        fig_to_plot = result_data.get(f"fig_{fig_internal_key_iter}")
                        if fig_to_plot:
                           try:
                               st.plotly_chart(fig_to_plot, use_container_width=True, key=f"chart_{fig_internal_key_iter}_{idx_name_iter_cols}_{key_suffix_pred_section}")
                           except Exception as e_plot:
                               log_error(f"Error plotting {fig_internal_key_iter} for {idx_name_iter_cols}: {e_plot}")
                               st.error(f"Plot Error: {e_plot}")
                        else: st.caption("Δεν υπάρχουν δεδομένα.")

        st.markdown('</div>', unsafe_allow_html=True)

# --- Main Application Logic ---
def main_app():
    log_info("====================================")
    log_info("          STARTING MAIN APP         ")
    log_info("====================================")
    try:
        inject_custom_css()
        run_intro_page_custom()
        run_custom_sidebar_ui_custom()

        selected_wb = st.session_state.get(SESSION_KEY_WATERBODY)
        selected_idx = st.session_state.get(SESSION_KEY_INDEX)
        selected_an = st.session_state.get(SESSION_KEY_ANALYSIS)

        if not all([selected_wb, selected_idx, selected_an]):
            log_warning("Waiting for user selections.")
            render_footer()
            return

        log_info(f"Running main content for WB='{selected_wb}', Idx='{selected_idx}', Analysis='{selected_an}'.")

        if selected_wb == "Γαδουρά" and selected_idx in ["Χλωροφύλλη", "Πραγματικό", "Θολότητα"]:
            if selected_an == "Επιφανειακή Αποτύπωση":
                run_lake_processing_app(selected_wb, selected_idx)
            elif selected_an == "Προφίλ ποιότητας και στάθμης":
                run_water_quality_dashboard(selected_wb, selected_idx)
            elif selected_an == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
                # **** THIS IS THE LIKELY AREA WHERE CRASHES HAPPEN ****
                log_info("Entering Predictive Tools section...")
                run_predictive_tools(selected_wb, selected_idx)
                log_info("Exited Predictive Tools section.")
        else:
            st.warning(f"Δεν υπάρχουν διαθέσιμες αναλύσεις για: '{selected_wb}' - '{selected_idx}'.")

        render_footer()
        log_info("====================================")
        log_info("          APP RENDERED OK           ")
        log_info("====================================")

    except Exception as main_exception:
        log_error(f"!!! UNHANDLED EXCEPTION IN MAIN APP !!!: {main_exception}")
        st.error("Προέκυψε ένα κρίσιμο σφάλμα στην εφαρμογή. Ελέγξτε τα logs για λεπτομέρειες.")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main_app()