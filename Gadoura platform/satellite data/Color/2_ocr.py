import cv2
import numpy as np
import pytesseract
import re
from datetime import datetime
from openpyxl import Workbook
from pathlib import Path

# ======================================================================
# ===== CONFIGURATION ==================================================
# ======================================================================
# Set the full path to the Tesseract executable.
# UPDATE THIS PATH if Tesseract is installed elsewhere on your system.
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\ilioumbas\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
# ======================================================================


def preprocess_image(roi):
    """Preprocessing optimized for satellite/aerial images."""
    # Convert to grayscale if needed
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi.copy()
    
    # Resize image to make text larger (helps OCR significantly)
    height, width = gray.shape
    scale_factor = 3  # Make image 3x larger
    resized = cv2.resize(gray, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)
    
    # Apply stronger noise reduction for textured backgrounds
    denoised = cv2.medianBlur(resized, 3)
    
    # Enhance contrast more aggressively
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(denoised)
    
    return enhanced


def strategy_adaptive_threshold_fast(image):
    """Fast adaptive thresholding - most reliable method."""
    enhanced = preprocess_image(image)
    thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return thresh


def strategy_hsv_mask_fast(image):
    """HSV masking optimized for white text on colored backgrounds."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Wider range for white/light text on any colored background
    lower_white = np.array([0, 0, 150])  # Lower brightness threshold
    upper_white = np.array([180, 50, 255])  # Allow some saturation
    mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # Clean up the mask with morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    return cv2.bitwise_not(mask)


def strategy_satellite_optimized(image):
    """Strategy optimized for satellite/aerial imagery with textured backgrounds."""
    enhanced = preprocess_image(image)
    
    # Use morphological top-hat to isolate bright text from textured background
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    tophat = cv2.morphologyEx(enhanced, cv2.MORPH_TOPHAT, kernel)
    
    # Apply aggressive thresholding to isolate bright pixels
    _, thresh = cv2.threshold(tophat, 30, 255, cv2.THRESH_BINARY)
    
    # Clean up with morphological operations
    clean_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, clean_kernel)
    
    return cleaned


def strategy_simple_threshold(image):
    """Simple but effective thresholding."""
    enhanced = preprocess_image(image)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def parse_date_string_fast(text):
    """Fast and accurate date parsing with essential corrections."""
    if not text or not text.strip():
        return None
    
    # Essential character corrections only
    text = text.strip()
    corrections = {'O': '0', 'o': '0', 'S': '5', 'I': '1', 'l': '1', 'Z': '2', 'B': '8'}
    for old, new in corrections.items():
        text = text.replace(old, new)
    
    # Clean separators
    text = re.sub(r'[^\d]+', '-', text).strip('-')
    
    # Look for date patterns
    patterns = [
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY or MM-DD-YYYY
        r'(\d{4})(\d{2})(\d{2})',        # YYYYMMDD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                parts = [int(x) for x in match.groups()]
                
                # Determine year, month, day based on pattern
                if len(match.group(1)) == 4:  # YYYY-MM-DD
                    year, month, day = parts
                elif len(match.group(3)) == 4:  # DD-MM-YYYY (assume European format)
                    day, month, year = parts
                else:  # YYYYMMDD
                    year, month, day = parts
                
                # Validate
                if 1900 <= year <= datetime.now().year + 5 and 1 <= month <= 12 and 1 <= day <= 31:
                    try:
                        return datetime(year, month, day)
                    except ValueError:
                        continue
            except (ValueError, TypeError):
                continue
    
    return None


def extract_date(image_path):
    """Streamlined date extraction with best strategies only."""
    try:
        img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None

        height, width, _ = img.shape
        
        # Try 3 most likely regions only
        regions = [
            img[0:int(0.15 * height), int(0.75 * width):width],  # Top-right (original)
            img[0:int(0.2 * height), 0:width],                   # Full top
            img[int(0.8 * height):height, int(0.75 * width):width]  # Bottom-right
        ]
        
        # 4 best strategies for satellite imagery
        strategies = [
            {'name': 'Satellite', 'func': strategy_satellite_optimized},
            {'name': 'Adaptive', 'func': strategy_adaptive_threshold_fast},
            {'name': 'HSV', 'func': strategy_hsv_mask_fast},
            {'name': 'Threshold', 'func': strategy_simple_threshold},
        ]
        
        # 2 best Tesseract configs only
        configs = [
            '--psm 7 -c tessedit_char_whitelist=0123456789-/.',
            '--psm 6 -c tessedit_char_whitelist=0123456789-/.'
        ]
        
        for region_idx, roi in enumerate(regions):
            if roi.size == 0:
                continue
                
            for strategy in strategies:
                try:
                    processed_img = strategy['func'](roi)
                    
                    for config in configs:
                        text = pytesseract.image_to_string(processed_img, config=config)
                        if text.strip():
                            date_obj = parse_date_string_fast(text)
                            if date_obj:
                                print(f"SUCCESS {image_path.name}: {date_obj.strftime('%Y-%m-%d')} ({strategy['name']}, R{region_idx+1})")
                                return date_obj
                except:
                    continue
        
        print(f"FAILED {image_path.name}: No date found")
        return None

    except Exception as e:
        print(f"ERROR {image_path.name}: Error - {e}")
        return None


def extract_number(filename):
    match = re.search(r'frame_(\d+)', filename.name, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def main():
    run_directory = Path.cwd()
    folder_path = run_directory / 'jpgs'
    output_path = run_directory / 'ocr_results.xlsx'

    if not folder_path.is_dir():
        print(f"Error: The input folder '{folder_path}' does not exist.")
        exit(1)

    image_files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in ('.png', '.jpg', '.jpeg')], key=extract_number)
    if not image_files:
        print(f"Error: No image files found in '{folder_path}'.")
        exit(1)

    print(f"Processing {len(image_files)} images...")
    
    data = []
    successful = 0
    
    for i, image_path in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] ", end="")
        date_obj = extract_date(image_path)
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
    
    print(f"\nComplete: {successful}/{len(image_files)} successful ({successful/len(image_files)*100:.1f}%)")
    print(f"Results saved to: ocr_results.xlsx")


if __name__ == "__main__":
    main()