import os
import json
import rasterio
from rasterio.transform import from_bounds
from PIL import Image
import numpy as np
from pathlib import Path

def load_coordinates_from_file(filepath):
    """
    Reads a JSON file containing polygon coordinates and returns the bounding box.

    Args:
        filepath (Path): The path to the dimensions.txt file.

    Returns:
        dict: A dictionary with north, south, east, and west keys, or None on error.
    """
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

# ======================================================================
# --- Script Configuration ---
# This script requires the 'rasterio' and 'Pillow' libraries.
# Install them with: pip install rasterio Pillow numpy
# ======================================================================

# Get the directory where the python script is running
run_dir = Path.cwd()

# Define paths relative to the script's location
input_folder = run_dir / "jpgs"
output_folder = run_dir / "GeoTIFFs"
dimensions_file_path = run_dir / "dimensions.txt"

# Load the coordinates from the text file
polygon_coords = load_coordinates_from_file(dimensions_file_path)

# If coordinates failed to load, stop the script
if polygon_coords is None:
    exit()

# Check if the input folder exists
if not input_folder.is_dir():
    print(f"ERROR: The input folder 'jpgs' was not found in this directory: {run_dir}")
    exit()

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)
print("Output will be saved to: GeoTIFFs folder")

# Find all JPG files to process
image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".jpg")]

if not image_files:
    print(f"WARNING: No .jpg files found in the '{input_folder}' folder.")
else:
    print(f"Found {len(image_files)} JPG files. Starting GeoTIFF conversion...")
    # Process each image
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
            
            # print(f"GeoTIFF created: {tiff_path}") # Optional: uncomment for detailed output

        except Exception as e:
            print(f"ERROR: Failed to process {filename}. Error: {e}")

    print("\nGeoTIFF creation process completed.")
