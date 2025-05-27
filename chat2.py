#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI)
-----------------------------------------
Αυτή η έκδοση κρύβει τα μηνύματα αποσφαλμάτωσης εξ ορισμού και διαθέτει ένα
πολύ επαγγελματικό, φιλικό προς το χρήστη περιβάλλον.
Περιλαμβάνει εκτεταμένη αποσφαλμάτωση και χειρισμό σφαλμάτων.
"""

import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET
import traceback

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
# Also ignore numpy runtime warnings for now, but be aware of them
warnings.filterwarnings("ignore", category=RuntimeWarning, message='Mean of empty slice')
warnings.filterwarnings("ignore", category=RuntimeWarning, message='invalid value encountered in cast')


import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Global debug flag (set to True for extensive debugging output)
DEBUG = True # <-- Set to True to see detailed debug messages

def debug(*args, **kwargs):
    """Βοηθητική συνάρτηση για εμφάνιση μηνυμάτων αποσφαλμάτωσης, αν είναι ενεργοποιημένη."""
    if DEBUG:
        st.sidebar.caption(f"DEBUG: {' '.join(map(str, args))}")

# -------------------------------------------------------------------------
# Συνάρτηση Ελέγχου Πιστοποίησης
# -------------------------------------------------------------------------
def check_credentials():
    """Ελέγχει τα διαπιστευτήρια του χρήστη."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.sidebar.title("Login")
        username = st.sidebar.text_input("Username", key="username_input")
        password = st.sidebar.text_input("Password", type="password", key="password_input")

        if st.sidebar.button("Login"):
            if username == "Rhodes" and password == "123":
                st.session_state.authenticated = True
                st.rerun() # Rerun to hide login and show app
            else:
                st.sidebar.error("Incorrect username or password")
        return False
    return True

# -------------------------------------------------------------------------
# Διαμόρφωση σελίδας Streamlit
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="Ποιοτικά χαρακτηριστικά Επιφανειακού Ύδατος",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# -----------------------------------------------------------------------------
# Helper Function: Create Chlorophyll‑a Legend Figure
# -----------------------------------------------------------------------------
def create_chl_legend_figure():
    """Creates a horizontal legend for chlorophyll‑a."""
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
    fig.patch.set_facecolor('#1e1e1e') # Match card background
    ax.tick_params(colors='white')
    cbar.ax.xaxis.label.set_color('white')
    cbar.ax.tick_params(colors='white')

    return fig

# -----------------------------------------------------------------------------
# Βοηθητική Συνάρτηση για Επιλογή φακέλου δεδομένων
# -----------------------------------------------------------------------------
def get_data_folder(waterbody: str, index: str) -> str:
    """Finds the correct data folder."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_dir = os.getcwd()
    st.write(f"DEBUG: Base directory is: {base_dir}") # <-- DEBUG
    st.write(f"DEBUG: Content of base_dir: {os.listdir(base_dir)}") # <-- DEBUG

    waterbody_map = {"Γαδουρά": "Gadoura"}
    waterbody_folder = waterbody_map.get(waterbody, None)
    if waterbody_folder is None:
        st.error(f"Waterbody folder not found for {waterbody}")
        return None

    index_map = {
        "Χλωροφύλλη": "Chlorophyll",
        "Θολότητα": "Θολότητα", # Keep original if name matches
        "Πραγματικό": "Pragmatiko" # Assuming this map
    }
    # Handle special cases or use direct index if not mapped
    if index == "Χλωροφύλλη":
        index_folder_name = "Chlorophyll"
    elif index == "Θολότητα":
        index_folder_name = "Θολότητα"
    elif index == "Πραγματικό" and waterbody == "Κορώνεια": # As per original logic
        index_folder_name = "Pragmatiko"
    else:
        index_folder_name = index # Use index directly if not special

    data_folder = os.path.join(base_dir, waterbody_folder, index_folder_name)
    st.write(f"DEBUG: Attempting to use data folder: {data_folder}") # <-- DEBUG

    if not os.path.exists(data_folder):
        st.error(f"FATAL: Data folder does NOT exist: {data_folder}")
        st.error(f"DEBUG: Content of {os.path.join(base_dir, waterbody_folder)}: {os.listdir(os.path.join(base_dir, waterbody_folder)) if os.path.exists(os.path.join(base_dir, waterbody_folder)) else 'Does not exist'}") # <-- DEBUG
        return None

    st.write(f"DEBUG: Data folder exists: {data_folder}") # <-- DEBUG
    return data_folder

# -----------------------------------------------------------------------------
# Εξαγωγή ημερομηνίας από όνομα αρχείου
# -----------------------------------------------------------------------------
def extract_date_from_filename(filename: str):
    """Extracts date (YYYY-MM-DD) from filename using regex."""
    basename = os.path.basename(filename)
    match = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', basename) # More flexible
    if match:
        year, month, day = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            day_of_year = date_obj.timetuple().tm_yday
            return day_of_year, date_obj
        except Exception as e:
            debug(f"Date conversion error for {basename}: {e}")
            return None, None
    debug(f"No date match found in {basename}")
    return None, None

# -----------------------------------------------------------------------------
# Σελίδα Εισαγωγής
# -----------------------------------------------------------------------------
def run_intro_page():
    """Displays an intro card."""
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
                st.warning("DEBUG: logo.jpg not found.")
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
# Πλαϊνή Μπάρα Πλοήγησης
# -----------------------------------------------------------------------------
def run_custom_ui():
    """Creates the sidebar for navigation."""
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
# Βοηθητικές Συναρτήσεις Δεδομένων & Εικόνας
# -----------------------------------------------------------------------------
def load_lake_shape_from_xml(xml_file: str, bounds: tuple = None,
                             xml_width: float = 518.0, xml_height: float = 505.0):
    """Loads lake shape from XML, transforms if bounds given."""
    debug("Loading shape from:", xml_file)
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        points = []
        for point_elem in root.findall("point"):
            x_str = point_elem.get("x")
            y_str = point_elem.get("y")
            if x_str is not None and y_str is not None:
                points.append([float(x_str), float(y_str)])
        if not points:
            st.warning(f"No points found in XML: {xml_file}")
            return None
        if bounds:
            minx, miny, maxx, maxy = bounds
            points = [[minx + (x / xml_width) * (maxx - minx), maxy - (y / xml_height) * (maxy - miny)] for x, y in points]
        if points and (points[0] != points[-1]):
            points.append(points[0])
        debug("Loaded", len(points), "shape points.")
        return {"type": "Polygon", "coordinates": [points]}
    except Exception as e:
        st.error(f"Error loading shape from {xml_file}: {e}")
        return None

def read_image(file_path: str, lake_shape: dict = None):
    """Reads a GeoTIFF, applies mask if provided."""
    debug("Reading image:", file_path)
    try:
        with rasterio.open(file_path) as src:
            img = src.read(1).astype(np.float32)
            profile = src.profile.copy()
            profile.update(dtype="float32")
            no_data_value = src.nodata
            if no_data_value is not None:
                img = np.where(img == no_data_value, np.nan, img)
            img = np.where(img == 0, np.nan, img) # Treat 0 as NaN
            if lake_shape:
                from rasterio.features import geometry_mask
                # Ensure lake_shape is a list of geometries
                poly_mask = geometry_mask([lake_shape], transform=src.transform, invert=False, out_shape=img.shape)
                img = np.where(~poly_mask, img, np.nan)
            debug(f"Image {os.path.basename(file_path)} shape: {img.shape}, non-NaNs: {np.count_nonzero(~np.isnan(img))}")
            return img, profile
    except Exception as e:
        st.error(f"Error reading image {file_path}: {e}")
        return None, None

@st.cache_data # Cache the loaded data
def load_data(input_folder: str, shapefile_name="shapefile.xml"):
    """Loads all TIFs from a folder, masks, extracts dates."""
    st.write(f"DEBUG: `load_data` called with: {input_folder}")
    if not os.path.exists(input_folder):
        st.error(f"ERROR in `load_data`: Input folder not found: {input_folder}")
        raise FileNotFoundError(f"Input folder not found: {input_folder}")

    shapefile_path = os.path.join(input_folder, shapefile_name)
    lake_shape = None
    bounds = None

    all_tif_files = sorted(glob.glob(os.path.join(input_folder, "*.tif")))
    tif_files = [fp for fp in all_tif_files if os.path.basename(fp).lower() != "mask.tif"]
    st.write(f"DEBUG: Found {len(tif_files)} .tif files.")

    if not tif_files:
        st.error("ERROR in `load_data`: No GeoTIFF files found.")
        raise FileNotFoundError("No GeoTIFF files found.")

    try:
        with rasterio.open(tif_files[0]) as src:
            bounds = src.bounds
            st.write(f"DEBUG: Bounds from first TIF: {bounds}")
    except Exception as e:
        st.error(f"ERROR reading first TIF for bounds: {e}")
        raise

    if os.path.exists(shapefile_path):
        lake_shape = load_lake_shape_from_xml(shapefile_path, bounds=bounds)
        if lake_shape is None:
            st.warning("Could not load lake shape, proceeding without mask.")
    else:
        st.write(f"DEBUG: No shapefile found at {shapefile_path}. Proceeding without mask.")

    images, days, date_list = [], [], []
    for file_path in tif_files:
        day_of_year, date_obj = extract_date_from_filename(file_path)
        if day_of_year is not None:
            img, _ = read_image(file_path, lake_shape=lake_shape)
            if img is not None:
                images.append(img)
                days.append(day_of_year)
                date_list.append(date_obj)
            else:
                 st.warning(f"Skipping {file_path} due to read error.")
        else:
            st.warning(f"Skipping {file_path} - could not extract date.")


    if not images:
        st.error("ERROR in `load_data`: No valid images could be loaded/processed.")
        raise ValueError("No valid images found.")

    stack = np.stack(images, axis=0)
    st.write(f"DEBUG: `load_data` finished. Stack shape: {stack.shape}, Non-NaNs: {np.count_nonzero(~np.isnan(stack))}")
    return stack, np.array(days), date_list

# -----------------------------------------------------------------------------
# Επεξεργασία Λίμνης
# -----------------------------------------------------------------------------
def run_lake_processing_app(waterbody: str, index: str):
    """Main function for Lake Processing analysis."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title(f"Επεξεργασία Λίμνης ({waterbody} - {index})")

        data_folder = get_data_folder(waterbody, index)
        if data_folder is None:
            st.error("Cannot proceed: Data folder not found.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        input_folder = os.path.join(data_folder, "GeoTIFFs")
        st.write(f"DEBUG: Lake Processing using input folder: {input_folder}")

        try:
            STACK, DAYS, DATES = load_data(input_folder)
        except Exception as e:
            st.error(f"Σφάλμα φόρτωσης δεδομένων: {e}")
            st.error(traceback.format_exc())
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        if not DATES:
            st.error("Δεν υπάρχουν διαθέσιμες πληροφορίες ημερομηνίας.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        min_date = min(DATES).date() # Use .date() for slider
        max_date = max(DATES).date() # Use .date() for slider
        unique_years = sorted({d.year for d in DATES if d is not None})

        st.sidebar.header(f"Φίλτρα (Επεξεργασία Λίμνης: {waterbody})")
        threshold_range = st.sidebar.slider("Εύρος τιμών pixel", 0, 255, (0, 255), key="thresh_lp")
        # Ensure sliders use date objects
        refined_date_range_dt = st.sidebar.slider("Εξειδικευμένη περίοδος",
                                                min_value=min_date, max_value=max_date,
                                                value=(min_date, max_date), key="refined_date_lp")
        # Convert back to datetime for comparison
        start_dt = datetime.combine(refined_date_range_dt[0], datetime.min.time())
        end_dt = datetime.combine(refined_date_range_dt[1], datetime.max.time())

        display_option = st.sidebar.radio("Τρόπος εμφάνισης", options=["Thresholded", "Original"], index=0, key="display_lp")

        st.sidebar.markdown("### Επιλογή Μηνών/Ετών")
        month_options = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        selected_months = st.sidebar.multiselect("Μήνες", options=list(month_options.keys()),
                                                 format_func=lambda x: month_options[x],
                                                 default=list(month_options.keys()), key="months_lp")
        selected_years = st.sidebar.multiselect("Έτη", options=unique_years,
                                                default=unique_years, key="years_lp")

        selected_indices = [i for i, d in enumerate(DATES)
                             if start_dt <= d <= end_dt and d.month in selected_months and d.year in selected_years]

        st.write(f"DEBUG: Found {len(selected_indices)} images after filtering.")

        if not selected_indices:
            st.error("Δεν υπάρχουν δεδομένα για την επιλεγμένη περίοδο/μήνες/έτη.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        stack_filtered = STACK[selected_indices, :, :]
        days_filtered = np.array(DAYS)[selected_indices]
        filtered_dates = np.array(DATES)[selected_indices]
        st.write(f"DEBUG: Filtered stack shape: {stack_filtered.shape}, Non-NaNs: {np.count_nonzero(~np.isnan(stack_filtered))}")

        lower_thresh, upper_thresh = threshold_range
        in_range = np.logical_and(stack_filtered >= lower_thresh, stack_filtered <= upper_thresh)

        # Plot 1: Days in Range
        days_in_range = np.nansum(in_range, axis=0)
        if np.all(np.isnan(days_in_range)) or np.all(days_in_range == 0):
             st.warning("Διάγραμμα 'Ημέρες σε Εύρος': Δεν βρέθηκαν pixels εντός του εύρους.")
        else:
            fig_days = px.imshow(days_in_range, color_continuous_scale="plasma",
                                 title="Διάγραμμα: Ημέρες σε Εύρος", labels={"color": "Ημέρες σε Εύρος"})
            st.plotly_chart(fig_days, use_container_width=True, key="fig_days")

        # Plot 2: Mean Day
        tick_vals = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 365]
        tick_text = ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαΐ", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ", "Δεκ"]
        days_array = days_filtered.reshape((-1, 1, 1))
        sum_days = np.nansum(days_array * in_range, axis=0)
        count_in_range = np.nansum(in_range, axis=0)
        mean_day = np.divide(sum_days, count_in_range, out=np.full(sum_days.shape, np.nan), where=(count_in_range != 0))
        if np.all(np.isnan(mean_day)):
            st.warning("Διάγραμμα 'Μέση Ημέρα Εμφάνισης': Δεν βρέθηκαν pixels για υπολογισμό.")
        else:
            fig_mean = px.imshow(mean_day, color_continuous_scale="RdBu",
                                 title="Διάγραμμα: Μέση Ημέρα Εμφάνισης", labels={"color": "Μέση Ημέρα"})
            fig_mean.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text))
            st.plotly_chart(fig_mean, use_container_width=True, key="fig_mean")

        # Plot 3: Average Sample Image
        if display_option.lower() == "thresholded":
            current_stack_for_avg = np.where(in_range, stack_filtered, np.nan)
        else:
            current_stack_for_avg = stack_filtered
        average_sample_img = np.nanmean(current_stack_for_avg, axis=0) # This is the line 452!
        if np.all(np.isnan(average_sample_img)):
            st.warning("Διάγραμμα 'Μέσο Δείγμα Εικόνας': Δεν βρέθηκαν pixels για υπολογισμό μέσου όρου.")
        else:
            avg_min = float(np.nanmin(average_sample_img))
            avg_max = float(np.nanmax(average_sample_img))
            fig_sample = px.imshow(average_sample_img, color_continuous_scale="jet",
                                   range_color=[avg_min, avg_max],
                                   title="Διάγραμμα: Μέσο Δείγμα Εικόνας", labels={"color": "Τιμή Pixel"})
            st.plotly_chart(fig_sample, use_container_width=True, key="fig_sample")


        # Plot 4: Time Max
        filtered_day_of_year = np.array([d.timetuple().tm_yday for d in filtered_dates])
        def nanargmax_or_nan(arr):
            return np.nan if np.all(np.isnan(arr)) else np.nanargmax(arr)
        with warnings.catch_warnings(): # Suppress argmax warning if slice is all NaN
            warnings.simplefilter("ignore", category=RuntimeWarning)
            max_index = np.apply_along_axis(nanargmax_or_nan, 0, current_stack_for_avg) # Use same stack as avg
        time_max = np.full(max_index.shape, np.nan, dtype=float)
        valid_mask = ~np.isnan(max_index)
        max_index_int = max_index[valid_mask].astype(int)
        time_max[valid_mask] = filtered_day_of_year[max_index_int]

        if np.all(np.isnan(time_max)):
            st.warning("Διάγραμμα 'Χρόνος Μέγιστης Εμφάνισης': Δεν βρέθηκαν pixels για υπολογισμό.")
        else:
            fig_time = px.imshow(time_max, color_continuous_scale="RdBu", range_color=[1, 365],
                                 title="Διάγραμμα: Χρόνος Μέγιστης Εμφάνισης", labels={"color": "Ημέρα"})
            fig_time.update_layout(coloraxis_colorbar=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text))
            st.plotly_chart(fig_time, use_container_width=True, key="fig_time")

        # ... (Rest of the lake processing, monthly/yearly plots) ...
        # Add similar NaN checks for monthly/yearly plots if necessary.
        st.header("Μηνιαία Κατανομή")
        try:
            stack_full_in_range = (STACK >= lower_thresh) & (STACK <= upper_thresh)
            monthly_days_in_range = {}
            for m in range(1, 13):
                indices_m = [i for i, d in enumerate(DATES) if d is not None and d.month == m]
                if indices_m:
                    monthly_days_in_range[m] = np.sum(stack_full_in_range[indices_m, :, :], axis=0)
                else:
                    monthly_days_in_range[m] = None # Or np.full(STACK.shape[1:], np.nan)

            months_to_display = sorted([m for m in list(range(1, 13)) if m in selected_months])
            num_cols = 4 # Adjust columns for better layout
            cols = st.columns(num_cols)
            col_idx = 0
            for m in months_to_display:
                img = monthly_days_in_range[m]
                month_name = datetime(2000, m, 1).strftime('%B')
                if img is not None and not np.all(np.isnan(img)):
                    fig_month = px.imshow(img, color_continuous_scale="plasma", title=month_name, labels={"color": "Ημέρες"})
                    fig_month.update_layout(width=350, height=300, margin=dict(l=0, r=0, t=30, b=0))
                    fig_month.update_coloraxes(showscale=False)
                    cols[col_idx].plotly_chart(fig_month)
                    col_idx = (col_idx + 1) % num_cols
                # else: # Optionally show a placeholder or message
                #     cols[col_idx].info(f"No data {month_name}")
                #     col_idx = (col_idx + 1) % num_cols
        except Exception as e:
            st.error(f"Error during monthly analysis: {e}")


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
            st.error("Cannot proceed: Data folder not found.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        images_folder = os.path.join(data_folder, "GeoTIFFs")
        lake_height_path = os.path.join(data_folder, "lake height.xlsx")
        sampling_kml_path = os.path.join(data_folder, "sampling.kml")
        st.write(f"DEBUG: Dashboard using images_folder: {images_folder}")
        st.write(f"DEBUG: Dashboard using lake_height_path: {lake_height_path}")
        st.write(f"DEBUG: Dashboard using sampling_kml_path: {sampling_kml_path}")


        # ... (Rest of the Water Quality Dashboard code) ...
        # Add logging/error handling here as well, especially around:
        # - Finding TIF files
        # - Reading the background TIF
        # - Parsing KML
        # - Reading Excel
        # - `analyze_sampling` (especially rasterio reads inside it)
        st.info("Water Quality Dashboard is under construction / needs debugging.")

        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Placeholders
# -----------------------------------------------------------------------------
def run_burned_areas():
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title("Burned Areas (Placeholder)")
        st.info("Functionality not yet implemented.")
        st.markdown('</div>', unsafe_allow_html=True)

def run_water_level_profiles(waterbody: str, index: str):
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title(f"Προφίλ Ύψους ({waterbody}) [Placeholder]")
        st.info("Functionality not yet implemented.")
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main():
    """Main function to run the Streamlit app."""
    st.write("DEBUG: Starting main()")

    if not check_credentials():
        st.warning("Please log in to access the application.")
        st.stop()

    st.write("DEBUG: Credentials OK.")
    inject_custom_css()
    run_intro_page()
    run_custom_ui()

    wb = st.session_state.get("waterbody_choice", None)
    idx = st.session_state.get("index_choice", None)
    analysis = st.session_state.get("analysis_choice", None)
    st.write(f"DEBUG: Selections - WB: {wb}, Idx: {idx}, Analysis: {analysis}")

    if not all([wb, idx, analysis]):
        st.info("Please make selections in the sidebar.")
        st.stop()

    try:
        if idx in ["Χλωροφύλλη", "Πραγματικό", "Θολότητα"] and wb in ["Γαδουρά"]:
            if analysis == "Επιφανειακή Αποτύπωση":
                run_lake_processing_app(wb, idx)
            elif analysis == "Προφίλ ποιότητας και στάθμης":
                # Ensure this function is fully defined or use a placeholder
                run_water_quality_dashboard(wb, idx)
                # st.info("Προφίλ ποιότητας και στάθμης - Under Construction")
            elif analysis == "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":
                run_water_level_profiles(wb, idx)
            else:
                st.info("Παρακαλώ επιλέξτε ένα έγκυρο είδος ανάλυσης.")
        elif analysis == "Burned Areas":
            run_burned_areas()
        else:
            st.warning("Δεν υπάρχουν διαθέσιμα δεδομένα ή λειτουργίες για αυτόν τον συνδυασμό.")
    except FileNotFoundError as e:
         st.error(f"A required file or folder was not found: {e}. Please check your deployment and file paths.")
         st.error(traceback.format_exc())
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.error("Please check the logs for more details.")
        st.error(traceback.format_exc()) # Show full traceback in the app for debugging


if __name__ == "__main__":
    main()