import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
from math import radians, cos, sin, asin, sqrt
import os

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6371 * c
    return km

def calculate_speed(row_current, row_previous):
    """Calculate speed in km/h based on GPS coordinates and time difference."""
    if row_previous is None:
        return 0
    
    distance = haversine(
        row_previous['lng'], row_previous['lat'],
        row_current['lng'], row_current['lat']
    )
    
    time_diff = (row_current['datetime'] - row_previous['datetime']).total_seconds() / 3600
    
    if time_diff == 0:
        return 0
    
    speed = distance / time_diff
    
    if speed < 1:
        return 0
    
    if speed > 100:
        return 100
    
    return speed

def clean_gps_file(input_path, output_path):
    """Clean a single GPS file: remove duplicates, sort chronologically, drop driver column, calculate speed."""
    print(f"\nProcessing: {input_path.name}")
    
    print("  Reading file...")
    df = pd.read_csv(input_path)
    
    print(f"  Original records: {len(df)}")
    
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    print("  Sorting chronologically...")
    df = df.sort_values(['anonymized_vehicle', 'datetime']).reset_index(drop=True)
    
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        print(f"  Found {duplicates} duplicates, removing...")
        df = df.drop_duplicates().reset_index(drop=True)
    
    print("  Dropping driver column...")
    if 'anonymized_driver' in df.columns:
        df = df.drop(columns=['anonymized_driver'])
    
    print("  Calculating speed...")
    speeds = []
    grouped = df.groupby('anonymized_vehicle')
    
    for vehicle_id, group in tqdm(grouped, desc="  Vehicles", unit="vehicle"):
        vehicle_speeds = []
        prev_row = None
        
        for idx, row in group.iterrows():
            if prev_row is None:
                vehicle_speeds.append((idx, 0))
            else:
                speed = calculate_speed(row, prev_row)
                vehicle_speeds.append((idx, speed))
            
            prev_row = row
        
        speeds.extend(vehicle_speeds)
    
    speeds.sort(key=lambda x: x[0])
    df['speed'] = [s[1] for s in speeds]
    
    print(f"  Final records: {len(df)}")
    print(f"  Speed stats - Mean: {df['speed'].mean():.2f} km/h, Max: {df['speed'].max():.2f} km/h")
    
    # Save to cleaned directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  Saved to: {output_path.name}")

def clean_all_gps_files(start=0):
    """Clean all raw GPS files in the raw_GPS directory."""
    script_dir = Path(__file__).parent.parent
    raw_gps_dir = script_dir / "Bus_route_data" / "raw_GPS"
    cleaned_dir = raw_gps_dir / "cleaned"
    
    csv_files = [f for f in raw_gps_dir.glob("*.csv") 
                 if f.is_file() and 'cleaned' not in str(f.parent)][start:]
    
    if not csv_files:
        print("No CSV files found in raw_GPS directory!")
        return
    
    print(f"Found {len(csv_files)} files to process")
    print("=" * 60)
    
    for csv_file in csv_files:
        output_file = cleaned_dir / f"cleaned_{csv_file.name}"
        
        try:
            clean_gps_file(csv_file, output_file)
        except Exception as e:
            print(f"  ERROR processing {csv_file.name}: {str(e)}")
            continue
    
    print("\n" + "=" * 60)
    print("Cleaning complete!")

if __name__ == "__main__":
    clean_all_gps_files()
