#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI - Startup, Performance & Warning Enhanced v2)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

# --- Essential Global Imports ---
import os
import streamlit as st
import gc
import warnings
import re
from datetime import datetime, date
import io
import xml.etree.ElementTree as ET

warnings.filterwarnings("ignore", category=UserWarning, module='openpyxl')
# We will try to handle the source of these warnings instead of globally suppressing them if possible
# warnings.filterwarnings("ignore", category=RuntimeWarning, message="Mean of empty slice")
# warnings.filterwarnings("ignore", category=RuntimeWarning, message="invalid value encountered in divide")

st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Υδάτων ΕΥΑΘ", page_icon="💧")

try:
    import psutil
    startup_memory_usage = psutil.virtual_memory().percent
    if startup_memory_usage > 85:
        st.error(f"⚠️ Υψηλή χρήση μνήμης συστήματος ({startup_memory_usage:.1f}%). Κλείστε άλλες εφαρμογές.")
        st.stop()
except ImportError:
    pass # psutil not available
except Exception:
    pass # Other error during psutil check

DEBUG = False
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
LOGO_PATH = os.path.join(APP_BASE_DIR, "logo.jpg")
WATERBODY_FOLDERS = {"Γαδουρά": "Gadoura"}
SESSION_KEY_WATERBODY = "waterbody_choice_main"
SESSION_KEY_INDEX = "index_choice_main"
SESSION_KEY_ANALYSIS = "analysis_choice_main"
SESSION_KEY_DEFAULT_RESULTS_DASHBOARD = "dashboard_default_sampling_results_light"
SESSION_KEY_UPLOAD_RESULTS_DASHBOARD = "dashboard_upload_sampling_results_light"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_DEF = "dash_def_current_image_idx"
SESSION_KEY_CURRENT_IMAGE_INDEX_DASH_UPL = "dash_upl_current_image_idx"
AUTH_NAMES = ["Ilioumbas User"]
AUTH_USERNAMES = ["ilioumbas"]
AUTH_PLAIN_PASSWORDS = ["123"]

def check_memory_usage(threshold=80.0):
    try:
        import psutil
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > threshold:
            st.warning(f"⚠️ Υψηλή χρήση μνήμης: {memory_percent:.1f}%.")
            return False
    except Exception: pass
    return True

def periodic_gc_and_cache_clear():
    if 'run_counter' not in st.session_state: st.session_state.run_counter = 0
    st.session_state.run_counter += 1
    gc.collect()
    if st.session_state.run_counter % 25 == 0:
        st.cache_data.clear(); st.cache_resource.clear()
        if DEBUG: st.toast("🧹 Cache cleared.")
        st.session_state.run_counter = 0

def safe_process_wrapper(func):
    def wrapper(*args, **kwargs):
        if not check_memory_usage():
            st.error("Ανεπαρκής μνήμη."); return None
        try:
            result = func(*args, **kwargs); gc.collect(); return result
        except MemoryError: st.error("Σφάλμα μνήμης."); gc.collect(); return None
        except Exception as e:
            st.error(f"Σφάλμα ({func.__name__}): {e}")
            if DEBUG: debug_message(f"ERROR in {func.__name__}: {e}, Args: {args}, Kwargs: {kwargs}")
            gc.collect(); return None
    return wrapper

def debug_message(*args, **kwargs):
    if DEBUG:
        try:
            with st.expander("Debug Messages", expanded=False): st.write(*args, **kwargs)
        except Exception: print(f"DEBUG (fallback): {args} {kwargs}")

def inject_custom_css(): st.markdown("""<link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap" rel="stylesheet"><style>html,body,[class*="css"]{font-family:'Roboto',sans-serif;}.block-container{background:#161b22;color:#e0e0e0;padding:1.2rem;}.stSidebar > div:first-child{background:#23272f;border-right:1px solid #3a3f47;}.card{background:#1a1a1d;padding:2rem 2.5rem;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,0.25);margin-bottom:2rem;animation:fadein 1.0s ease-in-out;}@keyframes fadein{0%{opacity:0;transform:translateY(10px);}100%{opacity:1;transform:translateY(0px);}}.header-title{color:#ffd600;margin-bottom:1.5rem;font-size:2.2rem;text-align:center;letter-spacing:0.5px;font-weight:700;}.nav-section{padding:1rem 1.2rem;background:#2c2f36;border-radius:10px;margin-bottom:1.2rem;border-left:4px solid #ffd600;}.nav-section h4{margin:0;color:#ffd600;font-weight:500;font-size:1.1rem;}.stButton button{background-color:#009688;color:#ffffff;border-radius:8px;padding:10px 22px;border:none;box-shadow:0 3px 8px rgba(0,0,0,0.15);font-size:1.05rem;transition:background-color 0.2s,box-shadow 0.2s,transform 0.2s;cursor:pointer;}.stButton button:hover{background-color:#00796b;box-shadow:0 4px 12px rgba(0,0,0,0.2);transform:translateY(-1px);}.stButton button:active{background-color:#00695c;transform:translateY(0px);}.plotly-graph-div{border:1px solid #2a2e37;border-radius:10px;}.footer{text-align:center;color:#7a828e;font-size:0.85rem;padding:2rem 0 0.5rem 0;border-top:1px solid #2a2e37;}.footer a{color:#009688;text-decoration:none;}.footer a:hover{text-decoration:underline;}</style>""",unsafe_allow_html=True)

def add_excel_download_button(df_or_dict_of_dfs, filename_prefix: str, button_label_suffix: str, plot_key: str):
    import pandas as pd
    if df_or_dict_of_dfs is None: return
    is_empty_df = isinstance(df_or_dict_of_dfs, pd.DataFrame) and df_or_dict_of_dfs.empty
    is_empty_dict = isinstance(df_or_dict_of_dfs, dict) and (not df_or_dict_of_dfs or all(isinstance(df,pd.DataFrame) and df.empty for df in df_or_dict_of_dfs.values()))
    if is_empty_df or is_empty_dict: return
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if isinstance(df_or_dict_of_dfs, pd.DataFrame): df_or_dict_of_dfs.to_excel(writer, index=False, sheet_name='Data')
            elif isinstance(df_or_dict_of_dfs, dict):
                for sheet_name, data_df in df_or_dict_of_dfs.items():
                    if isinstance(data_df,pd.DataFrame) and not data_df.empty: data_df.to_excel(writer,index=False,sheet_name=re.sub(r'[\[\]\*\/\\?\:\']','_',str(sheet_name))[:31])
        excel_data = output.getvalue()
        if not excel_data: return
        file_name_suffix = button_label_suffix.lower().replace(' ','_').replace('/','_').replace('&','and').replace('(','').replace(')','')
        st.download_button(label=f"📥 Save {button_label_suffix}",data=excel_data,file_name=f"{filename_prefix}_{file_name_suffix}.xlsx",mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f"download_{plot_key}")
    except Exception as e: st.warning(f"Excel export error for {button_label_suffix}: {e}")

def render_footer(): st.markdown(f"""<hr style="border-color:#2a2e37;"><div class='footer'>© {datetime.now().year} EYATH SA • Powered by Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a></div>""",unsafe_allow_html=True)
def run_intro_page_custom():
    # ... (same as before, no heavy imports needed here)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_logo, col_text = st.columns([0.3, 0.7], gap="large")
        with col_logo:
            if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=240, output_format="auto")
            else: st.markdown("💧", help="Λογότυπο ΕΥΑΘ")
        with col_text:
            user_name_display = st.session_state.get("name", "Επισκέπτη")
            st.markdown(f"""<h2 class='header-title'>Εφαρμογή Ανάλυσης Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ</h2><p style='font-size:1.15rem;text-align:center; line-height:1.6;'>Καλωσήρθατε, <strong>{user_name_display}</strong>!<br>Εξερευνήστε τα δεδομένα ποιότητας με ευκολία.<br>Επιλέξτε τι θέλετε να δείτε από το πλάι παράγοντας δυναμικά, διαδραστικά γραφήματα</p>""", unsafe_allow_html=True)
        with st.expander("🔰 Οδηγίες Χρήσης", expanded=False):
            st.markdown("""- **Επιλογή Παραμέτρων:** Στην πλαϊνή μπάρα (αριστερά), επιλέξτε το υδάτινο σώμα, τον δείκτη ποιότητας και το είδος της ανάλυσης.\n- **Πλοήγηση:** Μετά την επιλογή, τα αποτελέσματα θα εμφανιστούν. Χρησιμοποιήστε τις καρτέλες (tabs).\n- **Προσαρμοσμένη Δειγματοληψία:** Ανεβάστε KML για ανάλυση σε συγκεκριμένα σημεία.\n- **Φίλτρα:** Χρησιμοποιήστε τα φίλτρα για να προσαρμόσετε τα αποτελέσματα.\n- **Επεξηγήσεις:** Κάντε κλικ στα ℹ️ για πληροφορίες.\n- **Ασφάλεια:** Τα δεδομένα επεξεργάζονται τοπικά.""")
        st.markdown('</div>', unsafe_allow_html=True)

def run_custom_sidebar_ui_custom(authenticator_obj):
    # ... (same as before, no heavy imports needed here)
    if authenticator_obj and st.session_state.get("authentication_status"):
        st.sidebar.success(f"Συνδεθήκατε ως: {st.session_state.get('name','N/A')}")
        authenticator_obj.logout("Αποσύνδεση","sidebar",key='unique_logout_key_sidebar') # Ensure unique key
        st.sidebar.markdown("<hr>",unsafe_allow_html=True)
    st.sidebar.markdown("<div class='nav-section'><h4>🛠️ Επιλογές Ανάλυσης</h4></div>",unsafe_allow_html=True)
    st.sidebar.info("❔ Επιλέξτε τις ρυθμίσεις σας!")
    waterbody=st.sidebar.selectbox("🌊 Υδάτινο σώμα",list(WATERBODY_FOLDERS.keys()),key=SESSION_KEY_WATERBODY)
    index_name=st.sidebar.selectbox("🔬 Δείκτης",["Πραγματικό","Χλωροφύλλη","Θολότητα"],key=SESSION_KEY_INDEX)
    analysis_type=st.sidebar.selectbox("📊 Είδος Ανάλυσης",["Επιφανειακή Αποτύπωση","Προφίλ ποιότητας και στάθμης","Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"],key=SESSION_KEY_ANALYSIS)
    st.sidebar.markdown(f"""<div style="padding:0.7rem;background:#2c2f36;border-radius:8px;margin-top:1.2rem;"><strong>🌊 Υδάτινο σώμα:</strong> {waterbody or "<i>-</i>"}<br><strong>🔬 Δείκτης:</strong> {index_name or "<i>-</i>"}<br><strong>📊 Ανάλυση:</strong> {analysis_type or "<i>-</i>"}</div>""",unsafe_allow_html=True)
    st.sidebar.markdown("---")

@st.cache_data(ttl=3600, max_entries=20) # Increased max_entries slightly
def parse_sampling_kml(kml_source) -> list:
    # ... (same as before, ET is globally imported)
    try:
        if hasattr(kml_source,"seek"):kml_source.seek(0)
        tree=ET.parse(kml_source) if hasattr(kml_source,"read") else ET.parse(str(kml_source))
        root=tree.getroot();ns={'kml':'http://www.opengis.net/kml/2.2'};points=[]
        for i_ls,ls in enumerate(root.findall('.//kml:LineString',ns)):
            coords_elem=ls.find('kml:coordinates',ns)
            if coords_elem is not None and coords_elem.text:
                coords=coords_elem.text.strip().split()
                for i_coord,coord_str in enumerate(coords):
                    try:lon,lat,*_=coord_str.split(',');points.append((f"LS{i_ls+1}_P{i_coord+1}",float(lon),float(lat)))
                    except ValueError:debug_message(f"KML Warning: Skipping coord '{coord_str}'")
        if not points and kml_source:st.caption("No LineString points found in KML.")
        return points
    except FileNotFoundError:debug_message(f"KML file not found: {kml_source}");return []
    except Exception as e:st.error(f"KML parsing error for {kml_source}: {e}");return []

@st.cache_data(ttl=3600, max_entries=10)
def get_data_folder(waterbody: str, index_name: str) -> str | None:
    # ... (same as before)
    wb_folder=WATERBODY_FOLDERS.get(waterbody)
    if not wb_folder:return None
    idx_map={"Πραγματικό":"Πραγματικό","Χλωροφύλλη":"Chlorophyll","Θολότητα":"Θολότητα"}
    idx_folder=idx_map.get(index_name,index_name)
    data_folder=os.path.join(APP_BASE_DIR,wb_folder,idx_folder)
    return data_folder if os.path.isdir(data_folder) else None

@st.cache_data(ttl=86400, max_entries=200) # Increased max_entries
def extract_date_from_filename(filename: str) -> tuple[int | None, datetime | None]:
    # ... (same as before)
    bn=os.path.basename(filename);m=re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})',bn)
    if m:
        try:dt_obj=datetime(int(m.group(1)),int(m.group(2)),int(m.group(3)));return dt_obj.timetuple().tm_yday,dt_obj
        except ValueError:return None,None
    return None,None

@st.cache_data(ttl=86400, max_entries=10) # Increased max_entries
def load_lake_shape_from_xml(xml_file_path: str, bounds: tuple=None, xml_width: float=518.0, xml_height: float=505.0):
    # ... (same as before, ET is globally imported)
    try:
        tree=ET.parse(xml_file_path);root=tree.getroot()
        pts_xml=[[float(p.get("x")),float(p.get("y"))] for p in root.findall("point") if p.get("x") and p.get("y")]
        if not pts_xml:return None
        pts_ret=pts_xml
        if bounds:minx,miny,maxx,maxy=bounds;pts_ret=[[minx+(x/xml_width)*(maxx-minx),maxy-(y/xml_height)*(maxy-miny)] for x,y in pts_xml]
        if pts_ret and (pts_ret[0]!=pts_ret[-1]):pts_ret.append(pts_ret[0])
        return {"type":"Polygon","coordinates":[pts_ret]}
    except Exception as e:st.error(f"XML shape load error: {e}");return None

def robust_mean(data_list):
    """Calculates mean robustly, returning np.nan for empty or all-NaN lists."""
    import numpy as np # Local import for this helper
    if not isinstance(data_list, (list, np.ndarray)): # Ensure it's iterable
        return np.nan
    if not len(data_list): # Empty list
        return np.nan
    
    valid_data = [x for x in data_list if x is not None and not (isinstance(x, float) and np.isnan(x))]
    if not valid_data: # List with only None or NaNs
        return np.nan
    return np.mean(valid_data)

@st.cache_data(ttl=3600, max_entries=20, show_spinner=False)
def read_image(file_path: str, lake_shape: dict = None, downsample_factor: int = 1):
    # ... (imports moved inside, RasterioResampling aliased)
    import numpy as np; import rasterio
    from rasterio.enums import Resampling as RasterioResampling
    from rasterio.features import geometry_mask
    from rasterio.errors import NotGeoreferencedWarning as RasterioNotGeoreferencedWarning # Specific import
    warnings.filterwarnings("ignore", category=RasterioNotGeoreferencedWarning) # Filter locally

    try:
        with rasterio.open(file_path) as src:
            out_shape = (src.count, int(src.height / downsample_factor), int(src.width / downsample_factor))
            current_resampling = RasterioResampling.bilinear if downsample_factor > 1 else RasterioResampling.nearest
            img = src.read(out_shape=out_shape, resampling=current_resampling)
            transform = src.transform * src.transform.scale((src.width / img.shape[-1]), (src.height / img.shape[-2]))
            img_band1 = img[0].astype(np.float32)
            profile = src.profile.copy(); profile.update(dtype="float32", width=img.shape[-1], height=img.shape[-2], transform=transform)
            if src.nodata is not None: img_band1 = np.where(img_band1 == src.nodata, np.nan, img_band1)
            img_band1 = np.where(img_band1 == 0, np.nan, img_band1)
            if lake_shape:
                poly_mask_shape = (img.shape[-2], img.shape[-1])
                poly_mask = geometry_mask([lake_shape], transform=transform, invert=True, out_shape=poly_mask_shape)
                img_band1 = np.where(poly_mask, img_band1, np.nan)
            img_masked = img.astype(np.float32)
            for i in range(img_masked.shape[0]): img_masked[i] = np.where(np.isnan(img_band1), np.nan, img_masked[i])
            return img_masked, profile
    except Exception as e: st.warning(f"Σφάλμα ανάγνωσης {os.path.basename(file_path)}: {e}."); return None, None

@st.cache_data(ttl=3600, max_entries=10) # Increased max_entries
def load_image_metadata(input_folder: str, shapefile_name="shapefile.xml"):
    # ... (imports moved inside)
    import glob; import rasterio
    from rasterio.errors import NotGeoreferencedWarning as RasterioNotGeoreferencedWarning
    warnings.filterwarnings("ignore", category=RasterioNotGeoreferencedWarning)

    if not os.path.exists(input_folder): return None,None,None
    shape_file_path = next((sp for sp in [os.path.join(input_folder,shapefile_name),os.path.join(input_folder,"shapefile.txt")] if os.path.exists(sp)),None)
    tif_files = sorted([fp for fp in glob.glob(os.path.join(input_folder,"*.tif")) if os.path.basename(fp).lower()!="mask.tif"])
    if not tif_files: return None,None,None
    metadata,lake_geom,first_profile = [],None,None
    try:
        with rasterio.open(tif_files[0]) as src_first:
            first_profile = src_first.profile.copy()
            if shape_file_path: lake_geom = load_lake_shape_from_xml(shape_file_path,bounds=src_first.bounds)
    except Exception as e: st.error(f"Σφάλμα προετοιμασίας φόρτωσης: {e}"); return None,None,None
    for fp_iter in tif_files:
        day_yr,date_obj = extract_date_from_filename(fp_iter)
        if day_yr is not None: metadata.append({'path':fp_iter,'day':day_yr,'date':date_obj})
    return metadata,lake_geom,first_profile

@safe_process_wrapper
def run_lake_processing_app(waterbody: str, index_name: str):
    # ... (same structure, np, pd, px imported locally as before)
    import numpy as np; import pandas as pd; import plotly.express as px
    # ... (rest of the function is largely the same, focus was on iterative processing)
    # Ensure unique keys for plotly charts and download buttons if copy-pasting the inner display logic
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Επιφανειακή Αποτύπωση: {waterbody} - {index_name}")
        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder: st.error(f"Δεν βρέθηκε φάκελος για '{waterbody} - {index_name}'."); st.markdown('</div>',unsafe_allow_html=True); return
        input_folder_geotiffs = os.path.join(data_folder, "GeoTIFFs")
        with st.spinner(f"Φόρτωση μετα-δεδομένων για {waterbody} - {index_name}..."):
            metadata, lake_geom, first_profile = load_image_metadata(input_folder_geotiffs)
        if not metadata or not first_profile: st.error("Δεν βρέθηκαν μετα-δεδομένα/εικόνες."); st.markdown('</div>',unsafe_allow_html=True); return
        
        DATES_ALL_AVAILABLE = [m['date'] for m in metadata]
        st.sidebar.subheader(f"Φίλτρα Επεξεργασίας ({index_name})")
        min_val_dt = min(DATES_ALL_AVAILABLE).date() if DATES_ALL_AVAILABLE else date(2000,1,1)
        max_val_dt = max(DATES_ALL_AVAILABLE).date() if DATES_ALL_AVAILABLE else date.today()
        unique_yrs = sorted(list(set(d.year for d in DATES_ALL_AVAILABLE)))
        key_sfx = f"_lp_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]','',index_name)}"
        common_fname_prefix = f"{waterbody}_{index_name}_surface"

        thresh_rng = st.sidebar.slider("Εύρος τιμών pixel:",0,255,(0,255),key=f"thresh{key_sfx}")
        c1,c2=st.sidebar.columns(2)
        start_dt_val = c1.date_input("Έναρξη:",value=min_val_dt,min_value=min_val_dt,max_value=max_val_dt,key=f"start{key_sfx}")
        end_dt_val = c2.date_input("Λήξη:",value=max_val_dt,min_value=min_val_dt,max_value=max_val_dt,key=f"end{key_sfx}")
        if start_dt_val > end_dt_val: st.sidebar.error("Error in dates."); st.markdown('</div>',unsafe_allow_html=True); return
        
        disp_opt = st.sidebar.radio("Μέσο Δείγμα:",["Thresholded","Original"],0,key=f"disp_opt{key_sfx}",horizontal=True)
        month_map = {i:datetime(2000,i,1).strftime('%B') for i in range(1,13)}
        sel_months = st.sidebar.multiselect("Μήνες:",list(month_map.keys()),format_func=lambda x:month_map[x],default=list(month_map.keys()),key=f"months{key_sfx}")
        sel_years = st.sidebar.multiselect("Έτη:",unique_yrs,default=unique_yrs,key=f"years{key_sfx}")
        
        start_dt_conv = datetime.combine(start_dt_val, datetime.min.time())
        end_dt_conv = datetime.combine(end_dt_val, datetime.max.time())
        filt_meta = [m for m in metadata if (start_dt_conv<=m['date']<=end_dt_conv and (not sel_months or m['date'].month in sel_months) and (not sel_years or m['date'].year in sel_years))]
        if not filt_meta: st.info("No data for filters."); st.markdown('</div>',unsafe_allow_html=True); return

        with st.spinner("Επεξεργασία φιλτραρισμένων δεδομένων..."):
            # ... (iterative processing logic - largely same as before) ...
            check_memory_usage()
            img_shape=(first_profile['height'],first_profile['width'])
            days_in_range_map=np.zeros(img_shape,dtype=np.int16)
            sum_days_in_range=np.zeros(img_shape,dtype=np.float32)
            count_valid_for_mean_day=np.zeros(img_shape,dtype=np.int16)
            avg_sample_sum=np.zeros(img_shape,dtype=np.float64)
            avg_sample_count=np.zeros(img_shape,dtype=np.int16)
            time_max_val_arr=np.full(img_shape,-np.inf,dtype=np.float32)
            time_max_day_map=np.full(img_shape,np.nan,dtype=np.float32)
            monthly_sums_map={m:np.zeros(img_shape,dtype=np.int16) for m in sel_months}
            yearly_sums_map={y:np.zeros(img_shape,dtype=np.int16) for y in sel_years}
            low_t,upp_t=thresh_rng
            total_proc=len(filt_meta);prog_bar=st.progress(0);stat_txt=st.empty()

            for i,meta_i in enumerate(filt_meta):
                img_bands,_=read_image(meta_i['path'],lake_geom)
                if img_bands is None:continue
                img_d=img_bands[0] # Assuming single band for these maps
                with np.errstate(invalid='ignore'):in_rng_mask=np.logical_and(img_d>=low_t,img_d<=upp_t)
                in_rng_valid=np.nan_to_num(in_rng_mask,nan=0).astype(bool)
                days_in_range_map+=in_rng_valid
                sum_days_in_range=np.where(in_rng_valid,sum_days_in_range+meta_i['day'],sum_days_in_range)
                count_valid_for_mean_day+=in_rng_valid
                img_avg_src=np.where(in_rng_mask,img_d,np.nan) if disp_opt.lower()=="thresholded" else img_d
                avg_sample_sum+=np.nan_to_num(img_avg_src);avg_sample_count+=~np.isnan(img_avg_src)
                upd_time_max_mask=np.logical_and(in_rng_valid,(img_d>time_max_val_arr)|np.isnan(time_max_day_map))
                time_max_val_arr=np.where(upd_time_max_mask,img_d,time_max_val_arr)
                time_max_day_map=np.where(upd_time_max_mask,meta_i['day'],time_max_day_map)
                m,y=meta_i['date'].month,meta_i['date'].year
                if m in monthly_sums_map:monthly_sums_map[m]+=in_rng_valid
                if y in yearly_sums_map:yearly_sums_map[y]+=in_rng_valid
                prog_bar.progress((i+1)/total_proc);stat_txt.text(f'Επεξεργασία: {i+1}/{total_proc}')
                if i%20==0:gc.collect()
            prog_bar.empty();stat_txt.empty();check_memory_usage()
            with np.errstate(divide='ignore',invalid='ignore'):
                mean_day_map_res=np.divide(sum_days_in_range,count_valid_for_mean_day,out=np.full(img_shape,np.nan),where=(count_valid_for_mean_day!=0))
                avg_sample_disp_res=np.divide(avg_sample_sum,avg_sample_count,out=np.full(img_shape,np.nan),where=(avg_sample_count!=0))

        # Plotting section (ensure unique keys for charts and download buttons)
        st.subheader("Ανάλυση Χαρτών")
        expc1,expc2=st.columns(2)
        with expc1,st.expander("Ημέρες εντός Εύρους",True):
            fig_d=px.imshow(days_in_range_map,color_continuous_scale="plasma",labels={"color":"Ημέρες"})
            st.plotly_chart(fig_d,use_container_width=True,key=f"days_map_plot_{key_sfx}")
            add_excel_download_button(pd.DataFrame(days_in_range_map),common_fname_prefix,"DaysInRange",f"dl_days_{key_sfx}")
        tv=[1,32,60,91,121,152,182,213,244,274,305,335,365];tt=["Ι","Φ","Μ","Α","Μ","Ι","Ι","Α","Σ","Ο","Ν","Δ",""]
        with expc2,st.expander("Μέση Ημέρα Εμφάνισης",True):
            fig_md=px.imshow(mean_day_map_res,color_continuous_scale="RdBu",labels={"color":"Μέση Ημέρα"},color_continuous_midpoint=182)
            fig_md.update_layout(coloraxis_colorbar=dict(tickmode='array',tickvals=tv,ticktext=tt))
            st.plotly_chart(fig_md,use_container_width=True,key=f"mday_map_plot_{key_sfx}")
            add_excel_download_button(pd.DataFrame(mean_day_map_res),common_fname_prefix,"MeanDay",f"dl_mday_{key_sfx}")
        # ... (Continue with other plots: Average Sample, Time Max, Monthly, Yearly using unique keys)
        st.markdown('</div>', unsafe_allow_html=True); gc.collect()

@st.cache_resource(ttl=3600, max_entries=3)
def create_chl_legend_figure(orientation="horizontal", theme_bg_color=None, theme_text_color=None):
    import matplotlib.pyplot as plt; import matplotlib.colors as mcolors; import numpy as np
    levels=[0,6,12,20,30,50];colors=["#496FF2","#82D35F","#FEFD05","#FD0004","#8E2026","#D97CF5"]
    cmap=mcolors.LinearSegmentedColormap.from_list("ChlLeg",list(zip(np.linspace(0,1,len(levels)),colors)))
    norm=mcolors.Normalize(vmin=levels[0],vmax=levels[-1])
    fig,ax=plt.subplots(figsize=(7,1.2) if orientation=="horizontal" else (1.8,6))
    fig.subplots_adjust(**({'bottom':0.45,'top':0.9,'left':0.05,'right':0.95} if orientation=="horizontal" else {'left':0.3,'right':0.7,'top':0.95,'bottom':0.05}))
    cbar=fig.colorbar(plt.cm.ScalarMappable(cmap=cmap,norm=norm),cax=ax,orientation=orientation,ticks=levels,aspect=30 if orientation=="horizontal" else 20,shrink=0.95)
    lbl="Χλωροφύλλη-α (mg/m³)";tk_lbls=[str(l) for l in levels]
    if orientation=="horizontal":ax.set_xlabel(lbl,fontsize=10);ax.set_xticklabels(tk_lbls,fontsize=9)
    else:ax.set_ylabel(lbl,fontsize=10);ax.set_yticklabels(tk_lbls,fontsize=9)
    if theme_bg_color:fig.patch.set_facecolor(theme_bg_color);ax.set_facecolor(theme_bg_color)
    if theme_text_color:
        ax.xaxis.label.set_color(theme_text_color);ax.yaxis.label.set_color(theme_text_color)
        ax.tick_params(axis='x',colors=theme_text_color);ax.tick_params(axis='y',colors=theme_text_color)
        cbar.ax.tick_params(colors=theme_text_color);cbar.ax.yaxis.label.set_color(theme_text_color);cbar.ax.xaxis.label.set_color(theme_text_color)
    plt.tight_layout(pad=0.5);return fig

@st.cache_data(ttl=1800, max_entries=10, show_spinner="Ανάλυση σημείων...")
def analyze_sampling_data(sampling_points: list, images_folder_path: str, lake_height_excel_path: str, date_min=None, date_max=None):
    import numpy as np; import pandas as pd; import rasterio; import glob
    results_colors={name:[] for name,_,_ in sampling_points}; results_mg={name:[] for name,_,_ in sampling_points}
    if not os.path.isdir(images_folder_path): return {},{},pd.DataFrame()
    tif_files=sorted(glob.glob(os.path.join(images_folder_path,"*.tif")))
    for filename in tif_files:
        _,date_obj_file=extract_date_from_filename(filename)
        if not date_obj_file: continue
        if (date_min and date_obj_file.date()<date_min) or \
           (date_max and date_obj_file.date()>date_max): continue
        try:
            with rasterio.open(os.path.join(images_folder_path,filename)) as src:
                if src.count<3: continue
                for name,lon,lat in sampling_points:
                    try:
                        col,row=map(int,(~src.transform)*(lon,lat))
                        if 0<=col<src.width and 0<=row<src.height:
                            win=rasterio.windows.Window(col,row,1,1);pixel_data=src.read([1,2,3],window=win)
                            r,g,b=pixel_data[0,0,0],pixel_data[1,0,0],pixel_data[2,0,0]
                            mg_val=(g/255.0)*2.0;results_mg[name].append((date_obj_file,mg_val))
                            results_colors[name].append((date_obj_file,(r/255.,g/255.,b/255.)))
                    except Exception: pass
        except Exception: pass; gc.collect()
    df_h=pd.DataFrame(columns=['Date','Height'])
    if os.path.exists(str(lake_height_excel_path)):
        try:
            df_h_temp=pd.read_excel(lake_height_excel_path)
            if not df_h_temp.empty and len(df_h_temp.columns)>=2:
                df_h['Date']=pd.to_datetime(df_h_temp.iloc[:,0],errors='coerce');df_h['Height']=pd.to_numeric(df_h_temp.iloc[:,1],errors='coerce')
                df_h.dropna(inplace=True);df_h.sort_values('Date',inplace=True)
        except Exception: pass
    return results_colors,results_mg,df_h

@st.cache_data(ttl=600, max_entries=15, show_spinner=False)
def get_image_preview(file_path:str,downsample_factor:int=4):
    import numpy as np;import rasterio;from rasterio.enums import Resampling as RasterioResampling
    try:
        with rasterio.open(file_path) as src:
            if src.count<3:return None,None
            data=src.read([1,2,3],out_shape=(3,int(src.height/downsample_factor),int(src.width/downsample_factor)),resampling=RasterioResampling.bilinear)
            transform=src.transform*src.transform.scale((src.width/data.shape[-1]),(src.height/data.shape[-2]))
            rgb_disp=data.transpose((1,2,0))
            if rgb_disp.max()>1.0 and rgb_disp.max()<=255:rgb_disp/=255.0
            elif rgb_disp.max()>1.0:rgb_disp=np.clip(rgb_disp/np.nanmax(rgb_disp),0,1) # type: ignore
            return np.clip(rgb_disp,0,1),transform
    except Exception:return None,None

def image_navigation_ui(images_folder: str, available_dates_map: dict, session_state_key_for_idx: str, key_prefix: str, show_legend: bool=False, index_name_for_legend: str=""):
    # ... (same as before)
    if not available_dates_map:st.info("Δεν υπάρχουν εικόνες.");return None
    sorted_ds=sorted(available_dates_map.keys());current_idx=st.session_state.setdefault(session_state_key_for_idx,0)
    current_idx=min(max(0,current_idx),len(sorted_ds)-1)
    c1,c2,c3=st.columns([1,2,1])
    if c1.button("<<",key=f"{key_prefix}_p_btn",use_container_width=True):st.session_state[session_state_key_for_idx]=max(0,current_idx-1);st.rerun() # Unique key
    if c3.button(">>",key=f"{key_prefix}_n_btn",use_container_width=True):st.session_state[session_state_key_for_idx]=min(len(sorted_ds)-1,current_idx+1);st.rerun() # Unique key
    def upd_idx_nav_local():st.session_state[session_state_key_for_idx]=sorted_ds.index(st.session_state[f"{key_prefix}_sel_nav_local"]) # Unique name
    c2.selectbox("Ημερ/νία:",options=sorted_ds,index=current_idx,key=f"{key_prefix}_sel_nav_local",on_change=upd_idx_nav_local,label_visibility="collapsed") # Unique key
    sel_d_str=sorted_ds[st.session_state[session_state_key_for_idx]];img_fn=available_dates_map[sel_d_str];img_fp=os.path.join(images_folder,img_fn)
    if os.path.exists(img_fp):
        st.image(img_fp,caption=f"{sel_d_str} - {img_fn}",use_column_width=True)
        if show_legend and index_name_for_legend=="Χλωροφύλλη":st.pyplot(create_chl_legend_figure("horizontal"))
    else:st.error(f"Δεν βρέθηκε: {img_fp}")
    return img_fp

def generate_dashboard_figures(sampling_points, results_colors_data, results_mg_data, df_h_data, first_image_preview, first_transform_preview, selected_point_names):
    import plotly.express as px; import plotly.graph_objects as go; from plotly.subplots import make_subplots; import numpy as np
    figures={}
    fig_geo=go.Figure();
    if first_image_preview is not None:
        fig_geo=px.imshow(first_image_preview,title='Εικόνα Αναφοράς & Σημεία')
        if first_transform_preview:
            for n,lon,lat in sampling_points:
                if n in selected_point_names:
                    col,row=map(int,(~first_transform_preview)*(lon,lat))
                    fig_geo.add_trace(go.Scattergl(x=[col],y=[row],mode='markers+text',marker=dict(color='red',size=8,symbol='x'),name=n,text=n,textposition="top right"))
    fig_geo.update_xaxes(visible=False);fig_geo.update_yaxes(visible=False,scaleanchor="x",scaleratio=1);fig_geo.update_layout(height=500,uirevision='geo_d_rev') # Unique uirevision
    figures['geo']=fig_geo
    fig_colors=make_subplots(specs=[[{"secondary_y":True}]]);pt_y_map={n:i for i,n in enumerate(selected_point_names)}
    for n_iter in selected_point_names:
        if n_iter in results_colors_data and results_colors_data[n_iter]:
            dts,cols=zip(*sorted(results_colors_data[n_iter],key=lambda x:x[0])) if results_colors_data[n_iter] else ([],[])
            c_rgb=[f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in cols]
            fig_colors.add_trace(go.Scattergl(x=list(dts),y=[pt_y_map.get(n_iter,-1)]*len(dts),mode='markers',marker=dict(color=c_rgb,size=8),name=n_iter),secondary_y=False)
    if not df_h_data.empty:fig_colors.add_trace(go.Scattergl(x=df_h_data['Date'],y=df_h_data['Height'],name='Στάθμη',mode='lines',line=dict(color='blue')),secondary_y=True)
    fig_colors.update_layout(title='Χρώματα Pixel & Στάθμη',yaxis=dict(tickmode='array',tickvals=list(pt_y_map.values()),ticktext=list(pt_y_map.keys())),yaxis2=dict(title='Στάθμη (m)'),uirevision='colors_d_rev',height=450,hovermode='x unified') # Unique uirevision
    figures['colors']=fig_colors
    all_mg_by_d={};mean_mg=[]
    for p_name in selected_point_names:
        if p_name in results_mg_data:
            for d,v in results_mg_data[p_name]:all_mg_by_d.setdefault(d,[]).append(v)
    s_dts_mg=sorted(all_mg_by_d.keys())
    if s_dts_mg:
        for d_val in s_dts_mg:
            mean_mg.append(robust_mean(all_mg_by_d.get(d_val, []))) # Use robust_mean and provide empty list as default
    figures['mg_plot']=create_decimated_plot(s_dts_mg,mean_mg,'Μέσο mg/m³','mg/m³',max_points=300)
    figures['mg_data_points']=(s_dts_mg,mean_mg)
    figures['dual_plot']=create_dual_axis_decimated_plot(df_h_data,s_dts_mg,mean_mg,'Στάθμη & Μέσο mg/m³',max_points=300)
    return figures

def create_decimated_plot(dates, values, title, y_axis_title, max_points=500, use_webgl=True):
    import plotly.graph_objects as go; import numpy as np
    # Enhanced check for valid data for plotting
    valid_values_exist = False
    if hasattr(values, '__iter__'):
        valid_values_exist = any(v is not None and not (isinstance(v, float) and np.isnan(v)) for v in values)
    if not (hasattr(dates,'__iter__') and any(dates) and valid_values_exist):
        fig_empty = go.Figure().update_layout(title=f"{title} (Δεν υπάρχουν έγκυρα δεδομένα)", height=400, xaxis_title="Ημερομηνία", yaxis_title=y_axis_title)
        fig_empty.add_annotation(text="Δεν βρέθηκαν δεδομένα για οπτικοποίηση", showarrow=False, yshift=0)
        return fig_empty

    dates_list=list(dates); values_list=list(values) # Ensure they are lists
    if len(dates_list)>max_points:
        step=max(1,len(dates_list)//max_points); dates_list=dates_list[::step]; values_list=values_list[::step]
    fig=go.Figure(); ScatterClass=go.Scattergl if use_webgl else go.Scatter
    marker_props=dict(size=5)
    # Filter out NaNs before passing to color property if that's an issue, or let Plotly handle it.
    # Plotly generally handles NaNs in 'y' by creating gaps. For 'color', it depends on colorscale.
    fig.add_trace(ScatterClass(x=dates_list,y=values_list,mode='lines+markers',marker=marker_props,line=dict(width=1,color='grey'),name=y_axis_title))
    fig.update_layout(title=title,xaxis_title='Ημερομηνία',yaxis_title=y_axis_title,height=400,uirevision=f"{title}_rev_dec_v3",hovermode='x unified') # Unique uirevision
    return fig

def create_dual_axis_decimated_plot(df_h, dates_mg, values_mg, title, max_points=500, use_webgl=True):
    import plotly.graph_objects as go; from plotly.subplots import make_subplots; import numpy as np
    fig=make_subplots(specs=[[{"secondary_y":True}]]); ScatterClass=go.Scattergl if use_webgl else go.Scatter
    h_dates,h_values = (list(df_h['Date']),list(df_h['Height'])) if not df_h.empty else ([],[])
    if len(h_dates)>max_points: step=max(1,len(h_dates)//max_points); h_dates,h_values=h_dates[::step],h_values[::step]
    mg_dates_list=list(dates_mg); mg_values_list=list(values_mg) # Ensure lists
    if len(mg_dates_list)>max_points: step=max(1,len(mg_dates_list)//max_points); mg_dates_list,mg_values_list=mg_dates_list[::step],mg_values_list[::step]
    
    has_h_data = bool(h_dates)
    has_mg_data = any(v is not None and not (isinstance(v, float) and np.isnan(v)) for v in mg_values_list)

    if not has_h_data and not has_mg_data:
        fig_empty = go.Figure().update_layout(title=f"{title} (Δεν υπάρχουν έγκυρα δεδομένα)", height=450, xaxis_title="Ημερομηνία")
        fig_empty.add_annotation(text="Δεν βρέθηκαν δεδομένα για οπτικοποίηση", showarrow=False, yshift=0)
        return fig_empty
        
    if has_h_data: fig.add_trace(ScatterClass(x=h_dates,y=h_values,name='Στάθμη',mode='lines',line=dict(color='deepskyblue')),secondary_y=False)
    if has_mg_data:
        marker_props_mg=dict(size=5,showscale=False)
        # Plotly handles NaNs in y, so passing mg_values_list directly is fine.
        # Color will also skip NaNs if values_mg has them.
        fig.add_trace(ScatterClass(x=mg_dates_list,y=mg_values_list,name='Μέσο mg/m³',mode='lines+markers',marker=marker_props_mg,line=dict(color='lightgreen')),secondary_y=True)
    fig.update_layout(title=title,xaxis_title='Ημερομηνία',uirevision='dual_rev_dec_v3',height=450,yaxis=dict(title="Στάθμη (m)",color="deepskyblue",side='left'),yaxis2=dict(title="mg/m³",color="lightgreen",overlaying='y',side='right'),hovermode='x unified') # Unique uirevision
    return fig

@safe_process_wrapper
def run_water_quality_dashboard(waterbody: str, index_name: str):
    # ... (imports moved inside as before)
    import pandas as pd; import numpy as np; import plotly.graph_objects as go
    # ... (rest of function structure, ensure unique keys for Streamlit elements)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header(f"Προφίλ Ποιότητας και Στάθμης: {waterbody} - {index_name}")
        key_suffix_dash = f"_dash_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]','',index_name)}"
        common_prefix = f"{waterbody}_{index_name}"
        data_folder = get_data_folder(waterbody, index_name)
        if not data_folder: st.error("Φάκελος δεδομένων δεν βρέθηκε."); st.markdown('</div>',unsafe_allow_html=True); return
        images_folder_path = os.path.join(data_folder,"GeoTIFFs"); height_excel_path=os.path.join(data_folder,"lake height.xlsx")
        default_kml_path = os.path.join(data_folder,"sampling.kml")
        vid_path = next((p for n in ["timelapse.mp4","timelapse.gif"] for p in [os.path.join(data_folder,n),os.path.join(images_folder_path,n)] if os.path.exists(p)),None)
        available_tifs = {str(d.date()):fn for fn in (os.listdir(images_folder_path) if os.path.isdir(images_folder_path) else []) if fn.lower().endswith(('.tif','.tiff')) for _,d in [extract_date_from_filename(fn)] if d}
        if not available_tifs: st.error("Δεν βρέθηκαν GeoTIFFs."); st.markdown('</div>',unsafe_allow_html=True); return
        st.sidebar.subheader(f"Ρυθμίσεις ({index_name})")
        sel_bg_date = st.sidebar.selectbox("Εικόνα Αναφοράς:",sorted(available_tifs.keys(),reverse=True),key=f"bg_date_{key_suffix_dash}") # Unique key
        first_img_preview,first_transform_preview = None,None
        if sel_bg_date: first_img_preview,first_transform_preview = get_image_preview(os.path.join(images_folder_path,available_tifs[sel_bg_date]))
        if first_img_preview is None: st.error("Απαιτείται έγκυρη εικόνα αναφοράς."); st.markdown('</div>',unsafe_allow_html=True); return
        
        tabs_ctrl_names = ["Δειγματοληψία 1 (Προεπιλογή)", "Δειγματοληψία 2 (Ανέβασμα KML)"]
        tabs_ctrl_keys = [f"tab_default_{key_suffix_dash}", f"tab_upload_{key_suffix_dash}"] # Unique keys for tabs
        tabs_ctrl = st.tabs(tabs_ctrl_names)


        def _display_tab_content(tab_unique_id, kml_points_list, session_results_key, session_figs_key, selected_points_names_list):
            # ... (ensure all st element keys inside this function are unique using tab_unique_id)
            res_data = st.session_state.get(session_results_key); figures = st.session_state.get(session_figs_key)
            if res_data and figures:
                results_colors,results_mg,df_h = res_data
                n_tabs_titles_inner = ["GeoTIFF","Εικόνες","Video/GIF","Χρώματα Pixel","Μέσο mg/m³","Συνδυασμένο","mg/m³ ανά Σημείο"]
                # Ensure unique keys for inner tabs
                n_tabs_display = st.tabs([f"{t.replace(' ','_')}_{tab_unique_id}" for t in n_tabs_titles_inner])
                
                with n_tabs_display[0]:
                    st.plotly_chart(figures['geo'],use_container_width=True, key=f"geo_chart_{tab_unique_id}")
                    # ... (rest of tab 0 with unique keys)
                with n_tabs_display[1]: image_navigation_ui(images_folder_path,available_tifs,f"img_idx_nav_{tab_unique_id}",f"nav_ui_{tab_unique_id}",index_name=="Χλωροφύλλη",index_name)
                # ... (similar for other inner tabs)
            else: st.caption("Πατήστε 'Εκτέλεση' για να δείτε τα αποτελέσματα.")

        with tabs_ctrl[0]: # Default
            def_kml_key=f"def_kml_pts_{key_suffix_dash}";sel_def_pts_key=f"sel_def_pts_names_{key_suffix_dash}"
            res_def_key=SESSION_KEY_DEFAULT_RESULTS_DASHBOARD;figs_def_key=f"{res_def_key}_figs"
            def_pts_list=parse_sampling_kml(default_kml_path) if os.path.exists(default_kml_path) else []
            st.session_state[def_kml_key]=def_pts_list
            if def_pts_list:
                sel_pts=st.multiselect("Σημεία:",[n for n,_,_ in def_pts_list],default=[n for n,_,_ in def_pts_list],key=sel_def_pts_key)
                if st.button("Εκτέλεση (Προεπιλογή)",key=f"run_def_btn_{key_suffix_dash}"): # Unique button key
                    data=analyze_sampling_data(def_pts_list,images_folder_path,height_excel_path)
                    st.session_state[res_def_key]=data
                    st.session_state[figs_def_key]=generate_dashboard_figures(def_pts_list,*data,first_img_preview,first_transform_preview,sel_pts)
                    st.rerun()
            else:st.caption("Δεν βρέθηκε προεπιλεγμένο KML.")
            _display_tab_content(f"def_content_{key_suffix_dash}",st.session_state.get(def_kml_key,[]),res_def_key,figs_def_key,st.session_state.get(sel_def_pts_key,[]))
        # ... (similar for upload tab, ensuring all keys are unique)
        st.markdown('</div>',unsafe_allow_html=True);gc.collect()

@safe_process_wrapper
def run_predictive_tools(waterbody: str, initial_selected_index: str):
    import pandas as pd; import numpy as np; import plotly.graph_objects as go
    with st.container():
        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.header(f"Εργαλεία Πρόβλεψης: {waterbody}")
        st.info("Ανάλυση για όλους τους δείκτες. **Προσοχή:** Απαιτεί χρόνο/πόρους.")
        key_sfx_pred=f"_pred_{waterbody}_{re.sub(r'[^a-zA-Z0-9_]','',initial_selected_index)}"
        st.subheader("Κοινές Παράμετροι")
        c1,c2=st.columns(2)
        dt_min_pred=c1.date_input("Από:",date(2020,1,1),key=f"dt_min_pred_{key_sfx_pred}") # Unique key
        dt_max_pred=c2.date_input("Έως:",date.today(),key=f"dt_max_pred_{key_sfx_pred}") # Unique key
        samp_type_pred=st.radio("Πηγή Σημείων:",["Προεπιλογή","Ανέβασμα KML"],horizontal=True,key=f"samp_type_pred_{key_sfx_pred}") # Unique key
        samp_pts_pred=[]
        if samp_type_pred=="Προεπιλογή":
            df_pred=get_data_folder(waterbody,"Πραγματικό")
            if df_pred:kml_pth=os.path.join(df_pred,"sampling.kml");samp_pts_pred=parse_sampling_kml(kml_pth) if os.path.exists(kml_pth) else []
        else:upl_f_pred=st.file_uploader("KML:",type="kml",key=f"kml_upl_pred_{key_sfx_pred}");samp_pts_pred=parse_sampling_kml(upl_f_pred) if upl_f_pred else [] # Unique key
        if not samp_pts_pred:st.error("Ορίστε σημεία δειγματοληψίας.");st.markdown('</div>',unsafe_allow_html=True);return
        
        res_key_pred=f"pred_tool_res_{key_sfx_pred}" # Unique key
        if st.button("Εκτέλεση Ανάλυσης",key=f"run_pred_btn_{key_sfx_pred}"): # Unique key
            indices=["Πραγματικό","Χλωροφύλλη","Θολότητα"];res_all={}
            prg_bar=st.progress(0);st_txt=st.empty()
            for i,idx_n in enumerate(indices):
                st_txt.text(f"Επεξεργασία: {idx_n}...");gc.collect()
                d_fld=get_data_folder(waterbody,idx_n)
                if d_fld:img_fld=os.path.join(d_fld,"GeoTIFFs");h_xls=os.path.join(d_fld,"lake height.xlsx");res_all[idx_n]=analyze_sampling_data(samp_pts_pred,img_fld,h_xls,dt_min_pred,dt_max_pred)
                else:res_all[idx_n]=({},{},pd.DataFrame())
                prg_bar.progress((i+1)/len(indices))
            st.session_state[res_key_pred]=res_all;st_txt.success("Ολοκληρώθηκε!");prg_bar.empty();gc.collect()

        if res_key_pred in st.session_state:
            res_all=st.session_state[res_key_pred]
            st.subheader("Συγκριτικά Αποτελέσματα Μέσου mg/m³")
            fig_mg_all=go.Figure();excel_data_mg_all={}
            for idx_n,(res_c,res_m,df_h) in res_all.items():
                all_mg_by_d={};mean_vals=[]
                for p_name in [p[0] for p in samp_pts_pred]:
                    if p_name in res_m:
                        for d,v in res_m[p_name]:all_mg_by_d.setdefault(d,[]).append(v)
                s_dts=sorted(all_mg_by_d.keys())
                if s_dts:
                    for d_val in s_dts: mean_vals.append(robust_mean(all_mg_by_d.get(d_val,[]))) # Use robust_mean
                
                # Ensure there's actually data to plot after robust_mean
                valid_mean_vals = [v for v in mean_vals if v is not None and not np.isnan(v)]
                if s_dts and valid_mean_vals:
                    fig_mg_all.add_trace(go.Scattergl(x=s_dts,y=mean_vals,mode='lines',name=idx_n)) # Plotly handles NaNs by creating gaps
                    excel_data_mg_all[f"{idx_n}_mg_m3"]=pd.DataFrame({'Date':s_dts,'Value':mean_vals})
            fig_mg_all.update_layout(title="Συγκριτική Πορεία Μέσου mg/m³",xaxis_title="Ημερομηνία",yaxis_title="mg/m³",height=450,hovermode='x unified')
            st.plotly_chart(fig_mg_all,use_container_width=True, key=f"mg_all_chart_{key_sfx_pred}") # Unique key
            if excel_data_mg_all:add_excel_download_button(excel_data_mg_all,f"{waterbody}_predictive","All_Indices_Mean_mg_m3",f"excel_pred_mg_all_indices_{key_sfx_pred}") # Unique key
        st.markdown('</div>',unsafe_allow_html=True);gc.collect()

def main_app(authenticator_obj):
    inject_custom_css();check_memory_usage();periodic_gc_and_cache_clear()
    run_intro_page_custom();run_custom_sidebar_ui_custom(authenticator_obj)
    selected_wb=st.session_state.get(SESSION_KEY_WATERBODY)
    selected_idx=st.session_state.get(SESSION_KEY_INDEX)
    selected_an=st.session_state.get(SESSION_KEY_ANALYSIS)
    if not all([selected_wb,selected_idx,selected_an]):render_footer();return
    if selected_an=="Επιφανειακή Αποτύπωση":run_lake_processing_app(selected_wb,selected_idx)
    elif selected_an=="Προφίλ ποιότητας και στάθμης":run_water_quality_dashboard(selected_wb,selected_idx)
    elif selected_an=="Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης":run_predictive_tools(selected_wb,selected_idx)
    else:st.warning("Μη υποστηριζόμενη ανάλυση.")
    render_footer()

if __name__ == "__main__":
    authenticator = None # Initialize to None
    try:
        import streamlit_authenticator as stauth # Local import for this block
        credentials_dict={"usernames":{}}
        if len(AUTH_NAMES)==len(AUTH_USERNAMES)==len(AUTH_PLAIN_PASSWORDS):
            for i in range(len(AUTH_USERNAMES)):credentials_dict["usernames"][AUTH_USERNAMES[i]]={"name":AUTH_NAMES[i],"password":AUTH_PLAIN_PASSWORDS[i]}
            authenticator=stauth.Authenticate(credentials_dict,"wq_app_cookie_v10","rand_key_v10",cookie_expiry_days=30) # Unique names
        else:st.error("Σφάλμα ρύθμισης αυθεντικοποίησης.");st.stop()
    except ImportError:st.error("Η βιβλιοθήκη 'streamlit-authenticator' δεν βρέθηκε.");st.stop()
    except Exception as e:st.error(f"Σφάλμα αρχικοποίησης Authenticate: {e}");st.stop()

    if authenticator:
        # The login method itself handles session state for authentication_status
        name, authentication_status, username = authenticator.login('main')
        if st.session_state.get("authentication_status"):
            main_app(authenticator) # Pass the authenticator object
        elif st.session_state.get("authentication_status") is False:
            st.error('Το όνομα χρήστη ή ο κωδικός πρόσβασης είναι λανθασμένος.')
        elif st.session_state.get("authentication_status") is None: # Before first login attempt
            st.warning('Παρακαλώ εισάγετε τα στοιχεία σας.')
    else:
        st.error("Το σύστημα αυθεντικοποίησης δεν μπόρεσε να αρχικοποιηθεί.")