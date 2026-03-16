import os
import json
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
# Get the directory where the python script is running
run_dir = Path.cwd()

# Define the path for the 'jpgs' subfolder where the images are
folder_path = run_dir / "jpgs"

# Define the path for the KML output file
kml_file_path = run_dir / "All_Images_Overlay.kml"

# Define the path for the coordinates input file
dimensions_file_path = run_dir / "dimensions.txt"
# ======================================================================

# Load the coordinates from the text file
polygon_coords = load_coordinates_from_file(dimensions_file_path)

# If coordinates failed to load, stop the script
if polygon_coords is None:
    exit()

# Check if the 'jpgs' subfolder exists before starting
if not folder_path.is_dir():
    print(f"ERROR: The subfolder 'jpgs' was not found in this directory: {run_dir}")
    print("Please make sure your JPG files are inside a 'jpgs' subfolder.")
    exit()

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
    print(f"WARNING: No .jpg files found in the '{folder_path}' folder.")
else:
    print(f"Found {len(image_files)} JPG files. Generating KML...")
    for filename in image_files:
        # Get the name of the image without the .jpg extension
        image_name = os.path.splitext(filename)[0]
        
        # Create the KML block for a single image overlay
        # Note: The <href> must be a relative path for the KML to work correctly
        # when the folder is moved.
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
    print(f"\nKML file created successfully: All_Images_Overlay.kml")
except Exception as e:
    print(f"ERROR: An error occurred while saving the file: {e}")

