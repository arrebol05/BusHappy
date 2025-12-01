"""
Aggregate all bus stops from route data files.
This script reads all stops_by_var.csv (outbound) and rev_stops_by_var.csv (inbound) files
from all route folders and creates a comprehensive file with all unique bus stops,
tracking which routes access each stop in both directions.
"""

import os
import pandas as pd
from collections import defaultdict

def aggregate_bus_stops():
    """Aggregate all bus stops from all routes with directional information."""
    
    base_path = os.path.join(os.path.dirname(__file__), "..", "Bus_route_data", "HCMC_bus_routes")
    
    route_folders = []
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            route_folders.append((item, item_path))
    
    route_folders.sort(key=lambda x: int(x[0]) if x[0].isdigit() else float('inf'))
    
    print(f"Found {len(route_folders)} route folders")
    
    all_stops = {}
    total_outbound_stops = 0
    total_inbound_stops = 0
    routes_processed = 0
    
    for route_num, route_path in route_folders:
        outbound_file = os.path.join(route_path, "stops_by_var.csv")
        inbound_file = os.path.join(route_path, "rev_stops_by_var.csv")
        
        route_has_data = False
        
        if os.path.exists(outbound_file):
            try:
                df_outbound = pd.read_csv(outbound_file)
                total_outbound_stops += len(df_outbound)
                
                for _, row in df_outbound.iterrows():
                    stop_id = str(row['StopId'])
                    
                    if stop_id not in all_stops:
                        all_stops[stop_id] = {
                            'StopId': stop_id,
                            'Code': row['Code'],
                            'Name': row['Name'],
                            'StopType': row['StopType'],
                            'Zone': row['Zone'],
                            'Ward': row.get('Ward', ''),
                            'AddressNo': row.get('AddressNo', ''),
                            'Street': row['Street'],
                            'SupportDisability': row['SupportDisability'],
                            'Status': row['Status'],
                            'Lng': row['Lng'],
                            'Lat': row['Lat'],
                            'Search': row['Search'],
                            'routes_outbound': set(),
                            'routes_inbound': set()
                        }
                    
                    all_stops[stop_id]['routes_outbound'].add(route_num)
                    route_has_data = True
                    
            except Exception as e:
                print(f"  Warning: Error reading outbound file for route {route_num}: {e}")
        
        if os.path.exists(inbound_file):
            try:
                df_inbound = pd.read_csv(inbound_file)
                total_inbound_stops += len(df_inbound)
                
                for _, row in df_inbound.iterrows():
                    stop_id = str(row['StopId'])
                    
                    if stop_id not in all_stops:
                        all_stops[stop_id] = {
                            'StopId': stop_id,
                            'Code': row['Code'],
                            'Name': row['Name'],
                            'StopType': row['StopType'],
                            'Zone': row['Zone'],
                            'Ward': row.get('Ward', ''),
                            'AddressNo': row.get('AddressNo', ''),
                            'Street': row['Street'],
                            'SupportDisability': row['SupportDisability'],
                            'Status': row['Status'],
                            'Lng': row['Lng'],
                            'Lat': row['Lat'],
                            'Search': row['Search'],
                            'routes_outbound': set(),
                            'routes_inbound': set()
                        }
                    
                    all_stops[stop_id]['routes_inbound'].add(route_num)
                    route_has_data = True
                    
            except Exception as e:
                print(f"  Warning: Error reading inbound file for route {route_num}: {e}")
        
        if route_has_data:
            routes_processed += 1
            print(f"  Processed route {route_num}")
    
    print(f"\nStatistics:")
    print(f"  Routes processed: {routes_processed}")
    print(f"  Total outbound stop entries: {total_outbound_stops}")
    print(f"  Total inbound stop entries: {total_inbound_stops}")
    print(f"  Unique bus stops: {len(all_stops)}")
    
    output_data = []
    for stop_id, stop_info in all_stops.items():
        routes_outbound = sorted(stop_info['routes_outbound'], 
                                key=lambda x: int(x) if x.isdigit() else float('inf'))
        routes_inbound = sorted(stop_info['routes_inbound'], 
                               key=lambda x: int(x) if x.isdigit() else float('inf'))
        
        output_data.append({
            'StopId': stop_info['StopId'],
            'Code': stop_info['Code'],
            'Name': stop_info['Name'],
            'StopType': stop_info['StopType'],
            'Zone': stop_info['Zone'],
            'Ward': stop_info['Ward'],
            'AddressNo': stop_info['AddressNo'],
            'Street': stop_info['Street'],
            'SupportDisability': stop_info['SupportDisability'],
            'Status': stop_info['Status'],
            'Lng': stop_info['Lng'],
            'Lat': stop_info['Lat'],
            'Search': stop_info['Search'],
            'Routes_Outbound': ', '.join(routes_outbound) if routes_outbound else '',
            'Routes_Inbound': ', '.join(routes_inbound) if routes_inbound else '',
            'Total_Routes': len(routes_outbound) + len(routes_inbound),
            'Both_Directions': 'Yes' if (routes_outbound and routes_inbound) else 'No'
        })
    
    df_output = pd.DataFrame(output_data)
    df_output = df_output.sort_values('StopId')
    
    output_file = os.path.join(os.path.dirname(__file__), "..", "Bus_route_data", "all_bus_stops_aggregated.csv")
    df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\nOutput saved to: {output_file}")
    print(f"\nSample statistics:")
    print(f"  Stops with both directions: {len(df_output[df_output['Both_Directions'] == 'Yes'])}")
    print(f"  Stops with only outbound: {len(df_output[(df_output['Routes_Outbound'] != '') & (df_output['Routes_Inbound'] == '')])})")
    print(f"  Stops with only inbound: {len(df_output[(df_output['Routes_Outbound'] == '') & (df_output['Routes_Inbound'] != '')])})")
    
    print(f"\nTop 5 stops with most routes:")
    top_stops = df_output.nlargest(5, 'Total_Routes')[['StopId', 'Name', 'Total_Routes', 'Routes_Outbound', 'Routes_Inbound']]
    for idx, row in top_stops.iterrows():
        print(f"  {row['Name']} (ID: {row['StopId']}): {row['Total_Routes']} routes")
        if row['Routes_Outbound']:
            print(f"    Outbound: {row['Routes_Outbound']}")
        if row['Routes_Inbound']:
            print(f"    Inbound: {row['Routes_Inbound']}")
    
    return df_output

if __name__ == "__main__":
    print("=" * 80)
    print("Bus Stop Aggregation Script")
    print("=" * 80)
    print()
    
    df = aggregate_bus_stops()
    
    print(f"\n{'=' * 80}")
    print("Aggregation Complete!")
    print(f"{'=' * 80}")
