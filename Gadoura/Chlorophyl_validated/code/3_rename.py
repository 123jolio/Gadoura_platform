import os
import pandas as pd

# ======================================================================
# ===== MODIFIED CODE IS HERE ==========================================
# ======================================================================
# Get the directory where the python script is running
run_dir = os.getcwd()

# Define the path for the 'jpgs' subfolder where the images are
folder_path = os.path.join(run_dir, "jpgs")

# Define the path for the ocr_results.xlsx file, expecting it next to the script
excel_path = os.path.join(run_dir, "ocr_results.xlsx")
# ======================================================================

# Check if the necessary files and folders exist before starting
if not os.path.exists(excel_path):
    print(f"ERROR: The file 'ocr_results.xlsx' was not found in this directory: {run_dir}")
    exit()

if not os.path.exists(folder_path):
    print(f"ERROR: The subfolder 'jpgs' was not found in this directory: {run_dir}")
    exit()

# Read the Excel file
df = pd.read_excel(excel_path)

# Clean up column names by removing extra spaces
df.columns = df.columns.str.strip()

print("Excel file loaded. Starting file renaming process...")

# Loop through the Excel rows to rename the files
for index, row in df.iterrows():
    try:
        # Check that the necessary columns exist and are not empty
        if 'File Number' not in df.columns or 'Year' not in df.columns or 'Month' not in df.columns or 'Day' not in df.columns:
            print("ERROR: Excel file is missing one of the required columns: 'File Number', 'Year', 'Month', 'Day'")
            break
        if pd.isna(row['Year']) or pd.isna(row['Month']) or pd.isna(row['Day']):
            print(f"Skipping row {index + 2} due to missing date information.")
            continue

        # ======================================================================
        # ===== THIS IS THE UPDATED LINE =======================================
        # ======================================================================
        # Construct the old filename (e.g., frame_0.jpg)
        old_name = f"frame_{int(row['File Number'])}.jpg"
        
        # Construct the new filename (e.g., 2024_07_11.jpg)
        # zfill(2) ensures month and day are two digits (e.g., 07 instead of 7)
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
        else:
            print(f"WARNING: File not found and could not be renamed: {old_name}")
            
    except KeyError as e:
        print(f"ERROR: A required column is missing from the Excel file: {e}")
        break
    except Exception as e:
        print(f"An unexpected error occurred at row {index + 2}")

print("\nRenaming process complete.")