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

@st.cache_data
def read_image(file_path: str, lake_shape: dict = None):
    debug_message(f"DEBUG: Ανάγνωση εικόνας: {file_path}")
    try:
        with rasterio.open(file_path) as src:
            img = src.read(1).astype(np.float32)
            profile = src.profile.copy()
            profile.update(dtype="float32")

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

        if STACK is None or not DATES:
            st.markdown('</div>', unsafe_allow_html=True); return

        st.sidebar.subheader(f"Φίλτρα Επεξεργασίας ({index_name})")
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
            st.markdown('</div>', unsafe_allow_html=True); return
            
        display_option_val = st.sidebar.radio("Εμφάνιση Μέσου Δείγματος:", 
                                            options=["Thresholded", "Original"], index=0, 
                                            key=f"display_opt{key_suffix}", horizontal=True)

        month_options_map = {i: datetime(2000, i, 1).strftime('%B') for i in range(1, 13)}
        
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
                    df_days_in_range = pd.DataFrame(days_in_range_map)
                    add_excel_download_button(df_days_in_range, common_filename_prefix, "Days_in_Range_Map", f"excel_days_map{key_suffix}")
                    st.caption("Δείχνει πόσες ημέρες κάθε pixel ήταν εντός του επιλεγμένου εύρους τιμών.")

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
                    st.caption("Δείχνει τη μέση ημέρα του έτους που κάθε pixel ήταν εντός του επιλεγμένου εύρους τιμών.")

        st.markdown('</div>', unsafe_allow_html=True)

# Main app execution
if __name__ == "__main__":
    inject_custom_css()
    run_intro_page_custom()
    run_custom_sidebar_ui_custom()
    
    waterbody = st.session_state.get(SESSION_KEY_WATERBODY)
    index_name = st.session_state.get(SESSION_KEY_INDEX)
    analysis_type = st.session_state.get(SESSION_KEY_ANALYSIS)
    
    if waterbody and index_name and analysis_type:
        if analysis_type == "Επιφανειακή Αποτύπωση":
            run_lake_processing_app(waterbody, index_name)
        # Additional analysis types can be added here
    
    render_footer()
