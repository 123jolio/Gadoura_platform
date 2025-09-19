#!/usr/bin/env python3
"""
Complete Pipeline Script for Satellite Image Processing
Combines all 5 sequential scripts into a single execution:
1. Convert GIF to JPG frames
2. OCR to extract dates from images
3. Rename files based on extracted dates
4. Create KML with georeferenced overlays
5. Convert to GeoTIFF files
"""

import os
import json
import cv2
import numpy as np
import pytesseract
import re
import rasterio
from rasterio.transform import from_bounds
from PIL import Image
import pandas as pd
from datetime import datetime
from openpyxl import Workbook
from pathlib import Path

# ======================================================================
# ===== CONFIGURATION ==================================================
# ======================================================================

# Set the full path to the Tesseract executable
# UPDATE THIS PATH if Tesseract is installed elsewhere on your system
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\ilioumbas\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# ======================================================================
# ===== STEP 1: CONVERT GIF TO JPG =====================================
# ======================================================================

def gif_to_jpgs(gif_path):
    """Convert GIF file to individual JPG frames."""
    print("Step 1: Converting GIF to JPG frames...")
    
    current_dir = os.getcwd()
    output_folder = os.path.join(current_dir, 'jpgs')
    
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Load the GIF and extract frames
    with Image.open(gif_path) as img:
        i = 0
        while True:
            try:
                img.seek(i)  # Move to the next frame
                frame = img.convert('RGB')  # Convert the frame to RGB
                frame.save(os.path.join(output_folder, f'frame_{i}.jpg'), 'JPEG')
                i += 1
            except EOFError:
                break  # No more frames
    
    print(f"GIF converted successfully. {i} frames saved in: jpgs folder")
    return i

# ======================================================================
# ===== STEP 2: OCR DATE EXTRACTION (IMPROVED) =========================
# ======================================================================

def preprocess_image(roi):
    """Preprocessing optimized for satellite/aerial images."""
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi.copy()
    
    # Avoid making already large images excessively big
    height, width = gray.shape
    if width < 500: # Only scale up if the region is small
        scale_factor = 3
        resized = cv2.resize(gray, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)
    else:
        resized = gray
    
    denoised = cv2.medianBlur(resized, 3)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(denoised)
    
    return enhanced

def strategy_adaptive_threshold(image):
    """Fast adaptive thresholding."""
    enhanced = preprocess_image(image)
    thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    return thresh

def strategy_hsv_mask(image):
    """HSV masking optimized for white text."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 150])
    upper_white = np.array([180, 50, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    return mask

def strategy_satellite_optimized(image):
    """Strategy using morphological top-hat for bright text on textured backgrounds."""
    enhanced = preprocess_image(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    tophat = cv2.morphologyEx(enhanced, cv2.MORPH_TOPHAT, kernel)
    _, thresh = cv2.threshold(tophat, 30, 255, cv2.THRESH_BINARY)
    return thresh

def strategy_simple_threshold(image):
    """Simple but effective Otsu's thresholding."""
    enhanced = preprocess_image(image)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return thresh
    
def strategy_grayscale_only(image):
    """A strategy that only preprocesses to grayscale without binarization."""
    return preprocess_image(image)

def parse_and_validate_date(text):
    """
    More robustly parses a string to find and validate a date object.
    Returns a datetime object or None.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return None

    # --- Step 1: Pre-processing and Corrections ---
    text = text.strip()
    corrections = {'O': '0', 'o': '0', 'S': '5', 'I': '1', 'l': '1', 'Z': '2', 'B': '8', 'G': '6'}
    for old, new in corrections.items():
        text = text.replace(old, new)

    # Replace common separators with a standard one, but keep the numbers
    text = re.sub(r'[\s/.-]+', '-', text)

    # --- Step 2: Regex Matching ---
    patterns = [
        # YYYY-MM-DD (e.g., 2023-09-15)
        r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})',
        # DD-MM-YYYY (e.g., 15-09-2023)
        r'(?P<day>\d{1,2})-(?P<month>\d{1,2})-(?P<year>\d{4})',
        # YYYYMMDD (e.g., 20230915)
        r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                parts = match.groupdict()
                year, month, day = int(parts['year']), int(parts['month']), int(parts['day'])
                
                # --- Step 3: Validation ---
                if 1900 <= year <= datetime.now().year + 5:
                    return datetime(year, month, day) # Let datetime handle month/day validation
            except (ValueError, KeyError):
                continue # If parsing or validation fails, try the next pattern
    
    return None

def find_best_date(image_path):
    """
    Applies multiple strategies to find the most likely date in an image
    based on OCR confidence scores.
    """
    try:
        img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None: return None

        height, width, _ = img.shape
        
        # Define regions of interest
        regions = {
            "Top-Right": img[0:int(0.15 * height), int(0.70 * width):width],
            "Top-Full": img[0:int(0.2 * height), 0:width],
            "Bottom-Right": img[int(0.8 * height):height, int(0.70 * width):width]
        }
        
        # Define image processing strategies
        strategies = {
            "Satellite": strategy_satellite_optimized,
            "Adaptive": strategy_adaptive_threshold,
            "HSV": strategy_hsv_mask,
            "Grayscale": strategy_grayscale_only,
            "Simple": strategy_simple_threshold,
        }
        
        # Tesseract configurations
        configs = [
            '--psm 6 -c tessedit_char_whitelist=0123456789-/.', # Assume a single uniform block of text.
            '--psm 7 -c tessedit_char_whitelist=0123456789-/.', # Treat the image as a single text line.
        ]
        
        candidate_dates = []

        # Iterate through all combinations
        for region_name, roi in regions.items():
            if roi.size == 0: continue
            
            for strategy_name, strategy_func in strategies.items():
                try:
                    processed_img = strategy_func(roi)
                    
                    for config in configs:
                        # Use image_to_data to get confidence scores
                        ocr_data = pytesseract.image_to_data(processed_img, config=config, output_type=pytesseract.Output.DATAFRAME)
                        ocr_data = ocr_data[ocr_data.conf > 40] # Filter out low-confidence words

                        if not ocr_data.empty:
                            full_text = " ".join(ocr_data['text'].astype(str))
                            avg_conf = ocr_data['conf'].mean()

                            date_obj = parse_and_validate_date(full_text)
                            if date_obj:
                                candidate_dates.append({
                                    "date": date_obj, 
                                    "confidence": avg_conf,
                                    "source": f"{strategy_name} @ {region_name}"
                                })
                except Exception:
                    continue
        
        # Select the best candidate date
        if not candidate_dates:
            print(f"FAILED {image_path.name}: No date found")
            return None
        
        # Sort by confidence score in descending order
        best_candidate = sorted(candidate_dates, key=lambda x: x['confidence'], reverse=True)[0]
        
        print(f"SUCCESS {image_path.name}: Found {best_candidate['date'].strftime('%Y-%m-%d')} "
              f"(Conf: {best_candidate['confidence']:.1f}%, Source: {best_candidate['source']})")
        return best_candidate['date']

    except Exception as e:
        print(f"ERROR {image_path.name}: An exception occurred - {e}")
        return None

def extract_number(filename):
    match = re.search(r'frame_(\d+)', filename.name, re.IGNORECASE)
    return int(match.group(1)) if match else 0

def perform_ocr():
    """Perform OCR on all JPG images and extract the most likely dates."""
    print("\nStep 2: Performing OCR to extract dates (Improved Method)...")
    
    run_directory = Path.cwd()
    folder_path = run_directory / 'jpgs'
    output_path = run_directory / 'ocr_results.xlsx'

    if not folder_path.is_dir():
        print(f"ERROR: The input folder 'jpgs' does not exist.")
        return False

    image_files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in ('.png', '.jpg', '.jpeg')], key=extract_number)
    if not image_files:
        print(f"ERROR: No image files found in 'jpgs' folder.")
        return False

    print(f"Processing {len(image_files)} images...")
    
    data = []
    successful = 0
    
    for i, image_path in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] ", end="")
        date_obj = find_best_date(image_path) # Use the new improved function
        file_number = extract_number(image_path)
        
        if date_obj:
            data.append((file_number, date_obj.year, date_obj.month, date_obj.day))
            successful += 1
        else:
            data.append((file_number, 'Not Found', 'Not Found', 'Not Found'))

    # Create Excel file
    wb = Workbook()
    ws = wb.active
    ws.title = "OCR_Dates"
    ws.append(['File Number', 'Year', 'Month', 'Day'])
    for row_data in data:
        ws.append(row_data)
    wb.save(str(output_path))
    
    if len(image_files) > 0:
        success_rate = (successful / len(image_files)) * 100
        print(f"\nOCR Complete: {successful}/{len(image_files)} successful ({success_rate:.1f}%)")
    else:
        print("\nOCR Complete: No images to process.")
        
    print(f"Results saved to: ocr_results.xlsx")
    return successful > 0
# ======================================================================
# ===== STEP 3: RENAME FILES ===========================================
# ======================================================================

def rename_files():
    """Rename JPG files based on OCR results."""
    print("\nStep 3: Renaming files based on extracted dates...")
    
    run_dir = os.getcwd()
    folder_path = os.path.join(run_dir, "jpgs")
    excel_path = os.path.join(run_dir, "ocr_results.xlsx")

    # Check if the necessary files and folders exist
    if not os.path.exists(excel_path):
        print(f"ERROR: The file 'ocr_results.xlsx' was not found.")
        return False

    if not os.path.exists(folder_path):
        print(f"ERROR: The subfolder 'jpgs' was not found.")
        return False

    # Read the Excel file
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()

    print("Excel file loaded. Starting file renaming process...")

    renamed_count = 0
    for index, row in df.iterrows():
        try:
            # Check that the necessary columns exist and are not empty
            if 'File Number' not in df.columns or 'Year' not in df.columns or 'Month' not in df.columns or 'Day' not in df.columns:
                print("ERROR: Excel file is missing required columns.")
                return False
            if pd.isna(row['Year']) or pd.isna(row['Month']) or pd.isna(row['Day']):
                print(f"Skipping row {index + 2} due to missing date information.")
                continue

            # Construct the old filename
            old_name = f"frame_{int(row['File Number'])}.jpg"
            
            # Construct the new filename
            new_name = f"{int(row['Year'])}_{str(int(row['Month'])).zfill(2)}_{str(int(row['Day'])).zfill(2)}.jpg"
            
            # Create the full old and new file paths
            old_path = os.path.join(folder_path, old_name)
            new_path = os.path.join(folder_path, new_name)
            
            # Check if the original file exists before trying to rename it
            if os.path.exists(old_path):
                # If the target file already exists, remove it first
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(old_path, new_path)
                print(f"Renamed: {old_name} -> {new_name}")
                renamed_count += 1
            else:
                print(f"WARNING: File not found and could not be renamed: {old_name}")
                
        except KeyError as e:
            print(f"ERROR: A required column is missing from the Excel file: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred at row {index + 2}")

    print(f"\nRenaming process complete. {renamed_count} files renamed.")
    return renamed_count > 0

# ======================================================================
# ===== STEP 4: CREATE KML ============================================
# ======================================================================

def load_coordinates_from_file(filepath):
    """Read coordinates from JSON file and return bounding box."""
    try:
        print("Reading coordinates from dimensions.txt...")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract the list of [longitude, latitude] pairs
        coords_list = data['coordinates'][0]
        
        # Separate longitudes and latitudes
        longitudes = [p[0] for p in coords_list]
        latitudes = [p[1] for p in coords_list]
        
        # Calculate the bounding box
        bounds = {
            "north": max(latitudes),
            "south": min(latitudes),
            "east": max(longitudes),
            "west": min(longitudes)
        }
        print(f"Coordinates loaded successfully: {bounds}")
        return bounds
        
    except FileNotFoundError:
        print(f"ERROR: The coordinates file was not found at {filepath}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"ERROR: The coordinates file is not in the correct JSON format. Details: {e}")
        return None

def create_kml():
    """Create KML file with georeferenced image overlays."""
    print("\nStep 4: Creating KML with georeferenced overlays...")
    
    run_dir = Path.cwd()
    folder_path = run_dir / "jpgs"
    kml_file_path = run_dir / "All_Images_Overlay.kml"
    dimensions_file_path = run_dir / "dimensions.txt"

    # Load the coordinates from the text file
    polygon_coords = load_coordinates_from_file(dimensions_file_path)
    if polygon_coords is None:
        return False

    # Check if the 'jpgs' subfolder exists
    if not folder_path.is_dir():
        print(f"ERROR: The subfolder 'jpgs' was not found.")
        return False

    # Create the basic KML content structure
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>All Images Overlay</name>
'''

    kml_footer = '''
  </Document>
</kml>
'''

    # A string to gather all the GroundOverlay elements
    ground_overlays = ""

    # Find all JPG files in the 'jpgs' folder
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")]

    if not image_files:
        print(f"WARNING: No .jpg files found in the 'jpgs' folder.")
        return False
    else:
        print(f"Found {len(image_files)} JPG files. Generating KML...")
        for filename in image_files:
            # Get the name of the image without the .jpg extension
            image_name = os.path.splitext(filename)[0]
            
            # Create the KML block for a single image overlay
            ground_overlay = f'''
    <GroundOverlay>
      <name>{image_name}</name>
      <Icon>
        <href>jpgs/{filename}</href>
      </Icon>
      <LatLonBox>
        <north>{polygon_coords["north"]}</north>
        <south>{polygon_coords["south"]}</south>
        <east>{polygon_coords["east"]}</east>
        <west>{polygon_coords["west"]}</west>
        <rotation>0</rotation>
      </LatLonBox>
    </GroundOverlay>
'''
            ground_overlays += ground_overlay

    # Combine the header, all the overlays, and the footer
    kml_content = kml_header + ground_overlays + kml_footer

    # Save the final KML file
    try:
        with open(kml_file_path, 'w', encoding='utf-8') as file:
            file.write(kml_content)
        print(f"KML file created successfully: All_Images_Overlay.kml")
        return True
    except Exception as e:
        print(f"ERROR: An error occurred while saving the file: {e}")
        return False

# ======================================================================
# ===== STEP 5: CREATE GEOTIFF =========================================
# ======================================================================

def create_geotiff():
    """Convert JPG files to georeferenced GeoTIFF files."""
    print("\nStep 5: Creating GeoTIFF files...")
    
    run_dir = Path.cwd()
    input_folder = run_dir / "jpgs"
    output_folder = run_dir / "GeoTIFFs"
    dimensions_file_path = run_dir / "dimensions.txt"

    # Load the coordinates from the text file
    polygon_coords = load_coordinates_from_file(dimensions_file_path)
    if polygon_coords is None:
        return False

    # Check if the input folder exists
    if not input_folder.is_dir():
        print(f"ERROR: The input folder 'jpgs' was not found.")
        return False

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    print("Output will be saved to: GeoTIFFs folder")

    # Find all JPG files to process
    image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".jpg")]

    if not image_files:
        print(f"WARNING: No .jpg files found in the 'jpgs' folder.")
        return False
    else:
        print(f"Found {len(image_files)} JPG files. Starting GeoTIFF conversion...")
        processed_count = 0
        
        for filename in image_files:
            img_path = input_folder / filename
            tiff_path = output_folder / filename.replace('.jpg', '.tif')
            
            try:
                # Open the image and convert to a numpy array
                with Image.open(img_path) as img:
                    img_rgb = img.convert('RGB')
                    img_array = np.array(img_rgb)
                
                # Get image dimensions
                height, width = img_array.shape[:2]

                # Create the affine transform for georeferencing
                transform = from_bounds(
                    west=polygon_coords["west"],
                    south=polygon_coords["south"],
                    east=polygon_coords["east"],
                    north=polygon_coords["north"],
                    width=width,
                    height=height
                )
                
                # Write the GeoTIFF file with georeferencing information
                with rasterio.open(
                    tiff_path,
                    'w',
                    driver='GTiff',
                    height=height,
                    width=width,
                    count=3,  # RGB has 3 bands
                    dtype=img_array.dtype,
                    crs='EPSG:4326',  # WGS84 Coordinate System
                    transform=transform
                ) as dst:
                    # Rasterio expects bands in (bands, height, width) order
                    # The numpy array is (height, width, bands), so we transpose it
                    dst.write(np.transpose(img_array, (2, 0, 1)))
                
                processed_count += 1

            except Exception as e:
                print(f"ERROR: Failed to process {filename}. Error: {e}")

        print(f"\nGeoTIFF creation process completed. {processed_count} files created.")
        return processed_count > 0

# ======================================================================
# ===== MAIN FUNCTION ==================================================
# ======================================================================

def main():
    """Main function to run the complete pipeline."""
    print("=" * 60)
    print("COMPLETE SATELLITE IMAGE PROCESSING PIPELINE")
    print("=" * 60)
    
    # Check if required input files exist
    run_dir = Path.cwd()
    gif_files = [f for f in os.listdir(run_dir) if f.lower().endswith('.gif')]
    dimensions_file = run_dir / "dimensions.txt"
    
    if not gif_files:
        print("ERROR: No GIF file found in the current directory.")
        return
    
    if not dimensions_file.exists():
        print("ERROR: dimensions.txt file not found.")
        return
    
    gif_path = os.path.join(run_dir, gif_files[0])
    print(f"Processing GIF file: {gif_files[0]}")
    
    try:
        # Step 1: Convert GIF to JPG
        frame_count = gif_to_jpgs(gif_path)
        if frame_count == 0:
            print("ERROR: Failed to convert GIF to JPG frames.")
            return
        
        # Step 2: Perform OCR
        if not perform_ocr():
            print("ERROR: OCR processing failed.")
            return
        
        # Step 3: Rename files
        if not rename_files():
            print("ERROR: File renaming failed.")
            return
        
        # Step 4: Create KML
        if not create_kml():
            print("ERROR: KML creation failed.")
            return
        
        # Step 5: Create GeoTIFF
        if not create_geotiff():
            print("ERROR: GeoTIFF creation failed.")
            return
        
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("Summary of created files:")
        print("- JPG frames: jpgs/ folder")
        print("- OCR results: ocr_results.xlsx")
        print("- KML file: All_Images_Overlay.kml")
        print("- GeoTIFF files: GeoTIFFs/ folder")
        
    except Exception as e:
        print(f"\nERROR: Pipeline failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
