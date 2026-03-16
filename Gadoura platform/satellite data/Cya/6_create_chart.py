import os
import re
from datetime import datetime
from pathlib import Path
import rasterio
import matplotlib.pyplot as plt
import pandas as pd
import xml.etree.ElementTree as ET


def parse_sampling_kml(kml_file):
    tree = ET.parse(kml_file)
    root = tree.getroot()
    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
    points = []
    for linestring in root.findall('.//kml:LineString', namespace):
        coord_text = linestring.find('kml:coordinates', namespace).text.strip()
        coords = coord_text.split()
        for idx, coord in enumerate(coords):
            lon_str, lat_str, *_ = coord.split(',')
            points.append((f"Point {idx + 1}", float(lon_str), float(lat_str)))
    return points


def geographic_to_pixel(lon, lat, transform):
    from affine import Affine
    inverse_transform = ~transform
    col, row = inverse_transform * (lon, lat)
    return int(col), int(row)


def resolve_input_file(run_dir, filename):
    local_path = run_dir / filename
    if local_path.exists():
        return local_path

    for candidate in run_dir.parent.rglob(filename):
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(f"Could not find '{filename}' in {run_dir} or its parent folders.")


def main():
    run_dir = Path.cwd()
    images_folder = run_dir / 'GeoTIFFs'
    sampling_kml_path = resolve_input_file(run_dir, 'sampling.kml')
    lake_height_path = resolve_input_file(run_dir, 'lake height.xlsx')
    chart_output_path = run_dir / 'lake_sampling_chart.png'
    overlay_output_path = run_dir / 'first_geotiff_sampling_points.png'

    if not images_folder.is_dir():
        raise FileNotFoundError(f"Could not find GeoTIFF folder: {images_folder}")

    sampling_points = parse_sampling_kml(sampling_kml_path)
    results = {name: [] for name, _, _ in sampling_points}

    first_image_path = None
    first_transform = None
    first_image_data = None

    for filename in sorted(os.listdir(images_folder)):
        if filename.lower().endswith('.tif') or filename.lower().endswith('.tiff'):
            match = re.search(r'(\d{4}_\d{2}_\d{2})', filename)
            if not match:
                continue
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, '%Y_%m_%d')
            except ValueError as ve:
                print(f"Error parsing date from filename {filename}: {ve}")
                continue

            image_path = images_folder / filename

            try:
                with rasterio.open(image_path) as src:
                    transform = src.transform
                    width, height = src.width, src.height
                    if src.count >= 3:
                        if first_image_path is None:
                            first_image_path = image_path
                            first_transform = transform
                            first_image_data = src.read([1, 2, 3])

                        for name, lon, lat in sampling_points:
                            col, row = geographic_to_pixel(lon, lat, transform)
                            if 0 <= col < width and 0 <= row < height:
                                try:
                                    window = rasterio.windows.Window(col, row, 1, 1)
                                    r = src.read(1, window=window)[0, 0]
                                    g = src.read(2, window=window)[0, 0]
                                    b = src.read(3, window=window)[0, 0]
                                    pixel_color = (r / 255, g / 255, b / 255)
                                except Exception as e:
                                    print(f"Error reading pixel at {lon}, {lat} in {filename}: {e}")
                                    pixel_color = (0, 0, 0)
                            else:
                                print(f"Sampling point ({lon}, {lat}) out of bounds in {filename}.")
                                pixel_color = (0, 0, 0)
                            results[name].append((date_obj, pixel_color))
                    else:
                        print(f"Image {filename} does not have enough bands for RGB.")
            except Exception as e:
                print(f"Error opening image {filename}: {e}")

    lake_data = pd.read_excel(lake_height_path)
    lake_data['Date'] = pd.to_datetime(lake_data.iloc[:, 0])
    lake_data.sort_values('Date', inplace=True)

    fig, (ax_lake, ax) = plt.subplots(2, 1, figsize=(12, 12), gridspec_kw={'height_ratios': [1, 2]}, sharex=True)
    plt.subplots_adjust(left=0.1, bottom=0.2)

    chart_square_size = 25
    sampling_point_size = 5

    ax_lake.plot(lake_data['Date'], lake_data.iloc[:, 1], color='blue')
    ax_lake.set_title('Lake Height Over Time')
    ax_lake.set_ylabel('Height')
    ax_lake.grid(True)

    for idx, (point_name, data) in enumerate(results.items()):
        if not data:
            print(f"No data collected for {point_name}.")
            continue
        data.sort(key=lambda x: x[0])
        dates = [d[0] for d in data]
        colors = [d[1] for d in data]
        ax.scatter(dates, [idx] * len(dates), color=colors, s=chart_square_size, marker='s')

    ax.set_xlabel('Date')
    ax.set_yticks(range(len(results)))
    ax.set_yticklabels(results.keys())
    ax.set_ylabel('Sampling Points')
    ax.set_title('Pixel Colors at Sampling Points Over Time')
    ax.grid(True)

    # Add the first GeoTIFF image with sampling points at the bottom
    if first_image_data is not None:
        fig_img, ax_img = plt.subplots(figsize=(12, 6))
        rgb_image = first_image_data.transpose((1, 2, 0)) / 255.0
        ax_img.imshow(rgb_image)
        ax_img.set_title('First GeoTIFF Image with Sampling Points')
        ax_img.axis('off')

        for name, lon, lat in sampling_points:
            col, row = geographic_to_pixel(lon, lat, first_transform)
            ax_img.scatter(col, row, color='red', s=sampling_point_size, marker='s')

    # Set x-axis limits from 2015 to 2025
    ax_lake.set_xlim(datetime(2015, 1, 1), datetime(2025, 12, 31))

    plt.tight_layout()
    fig.savefig(chart_output_path, dpi=200, bbox_inches='tight')
    print(f"Saved chart to: {chart_output_path}")

    if first_image_data is not None:
        fig_img.savefig(overlay_output_path, dpi=200, bbox_inches='tight')
        print(f"Saved sampling overlay to: {overlay_output_path}")
        plt.close(fig_img)

    plt.close(fig)


if __name__ == '__main__':
    main()
