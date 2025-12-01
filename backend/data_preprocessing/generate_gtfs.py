"""
Generate GTFS (General Transit Feed Specification) files from HCMC bus route data.
GTFS format enables quick access to route and stop data for transit applications.
"""

import os
import csv
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd


class GTFSGenerator:
    def __init__(self, base_path: str, output_path: str):
        """Initialize GTFS generator."""
        self.base_path = Path(base_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        self.all_stops_old = pd.read_csv(self.base_path / "all_bus_stops_ag_old_adr.csv")
        self.all_stops_new = pd.read_csv(self.base_path / "all_bus_stops_ag_new_adr.csv")
        
        self.all_stops = self.all_stops_old.merge(
            self.all_stops_new[['StopId', 'Ward', 'AddressNo', 'Street']], 
            on='StopId', 
            how='left',
            suffixes=('_old', '_new')
        )
        
        self.route_folders = [
            d for d in (self.base_path / "HCMC_bus_routes").iterdir() 
            if d.is_dir()
        ]
        
    def generate_agency_txt(self):
        """Generate agency.txt - Transit agency information."""
        agency_data = [{
            'agency_id': 'HCMC_BUS',
            'agency_name': 'Ho Chi Minh City Public Transport',
            'agency_url': 'http://www.buyttphcm.com.vn',
            'agency_timezone': 'Asia/Ho_Chi_Minh',
            'agency_lang': 'vi'
        }]
        
        with open(self.output_path / 'agency.txt', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=agency_data[0].keys())
            writer.writeheader()
            writer.writerows(agency_data)
        
        print("✓ Generated agency.txt")
    
    def generate_stops_txt(self):
        """Generate stops.txt - All bus stop information with directional route data."""
        stops_data = []
        
        for _, stop in self.all_stops.iterrows():
            desc_parts = []
            
            old_address_parts = []
            if pd.notna(stop['AddressNo_old']) and str(stop['AddressNo_old']).strip():
                old_address_parts.append(str(stop['AddressNo_old']).strip())
            if pd.notna(stop['Street_old']) and str(stop['Street_old']).strip():
                if old_address_parts:
                    old_address_parts[0] += ' ' + str(stop['Street_old']).strip()
                else:
                    old_address_parts.append(str(stop['Street_old']).strip())
            
            if pd.notna(stop['Ward_old']) and str(stop['Ward_old']).strip():
                old_address_parts.append(str(stop['Ward_old']).strip())
            
            if pd.notna(stop['Zone']) and str(stop['Zone']).strip():
                old_address_parts.append(str(stop['Zone']).strip())
            
            if old_address_parts:
                old_address = ", ".join(old_address_parts)
                desc_parts.append(f"Old: {old_address}")
            
            new_address_parts = []
            if pd.notna(stop['AddressNo_new']) and str(stop['AddressNo_new']).strip():
                new_address_parts.append(str(stop['AddressNo_new']).strip())
            if pd.notna(stop['Street_new']) and str(stop['Street_new']).strip():
                if new_address_parts:
                    new_address_parts[0] += ' ' + str(stop['Street_new']).strip()
                else:
                    new_address_parts.append(str(stop['Street_new']).strip())
            
            if pd.notna(stop['Ward_new']) and str(stop['Ward_new']).strip():
                new_address_parts.append(str(stop['Ward_new']).strip())
            
            if new_address_parts:
                new_address = ", ".join(new_address_parts)
                desc_parts.append(f"New: {new_address}")
            
            route_info = []
            if pd.notna(stop['Routes_Outbound']) and str(stop['Routes_Outbound']).strip():
                route_info.append(f"Outbound: {str(stop['Routes_Outbound']).strip()}")
            if pd.notna(stop['Routes_Inbound']) and str(stop['Routes_Inbound']).strip():
                route_info.append(f"Inbound: {str(stop['Routes_Inbound']).strip()}")
            
            if route_info:
                desc_parts.append(" | ".join(route_info))
            
            stops_data.append({
                'stop_id': int(stop['StopId']),
                'stop_code': stop['Code'],
                'stop_name': stop['Name'],
                'stop_desc': " | ".join(desc_parts) if desc_parts else '',
                'stop_lat': stop['Lat'],
                'stop_lon': stop['Lng'],
                'zone_id': stop['Zone'],
                'stop_url': '',
                'location_type': '0',
                'wheelchair_boarding': '1' if stop['SupportDisability'] == 'Có' else '2'
            })
        
        with open(self.output_path / 'stops.txt', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=stops_data[0].keys())
            writer.writeheader()
            writer.writerows(stops_data)
        
        print(f"✓ Generated stops.txt ({len(stops_data)} stops)")
    
    def generate_routes_txt(self):
        """Generate routes.txt - All bus route information."""
        routes_data = []
        
        for route_folder in sorted(self.route_folders, key=lambda x: self._natural_sort_key(x.name)):
            route_file = route_folder / "route_by_id.csv"
            if not route_file.exists():
                continue
            
            route_df = pd.read_csv(route_file)
            if route_df.empty:
                continue
            
            route = route_df.iloc[0]
            routes_data.append({
                'route_id': int(route['RouteId']),
                'agency_id': 'HCMC_BUS',
                'route_short_name': int(route['RouteNo']),
                'route_long_name': route['RouteName'],
                'route_desc': f"{route['OutBoundName']} ↔ {route['InBoundName']}",
                'route_type': '3',
                'route_url': '',
                'route_color': route['Color'].replace('#', '') if pd.notna(route['Color']) else 'FFFFFF',
                'route_text_color': '000000'
            })
        
        with open(self.output_path / 'routes.txt', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=routes_data[0].keys())
            writer.writeheader()
            writer.writerows(routes_data)
        
        print(f"✓ Generated routes.txt ({len(routes_data)} routes)")
        return routes_data
    
    def generate_calendar_txt(self):
        """Generate calendar.txt - Service schedule (operates every day)."""
        calendar_data = [{
            'service_id': 'DAILY',
            'monday': '1',
            'tuesday': '1',
            'wednesday': '1',
            'thursday': '1',
            'friday': '1',
            'saturday': '1',
            'sunday': '1',
            'start_date': '20250101',
            'end_date': '20251231'
        }]
        
        with open(self.output_path / 'calendar.txt', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=calendar_data[0].keys())
            writer.writeheader()
            writer.writerows(calendar_data)
        
        print("✓ Generated calendar.txt")
    
    def generate_trips_and_stop_times(self):
        """Generate trips.txt and stop_times.txt - Trip and stop sequence information."""
        trips_data = []
        stop_times_data = []
        trip_counter = 0
        
        for route_folder in sorted(self.route_folders, key=lambda x: self._natural_sort_key(x.name)):
            route_file = route_folder / "route_by_id.csv"
            vars_file = route_folder / "vars_by_route.csv"
            stops_file = route_folder / "stops_by_var.csv"
            rev_stops_file = route_folder / "rev_stops_by_var.csv"
            
            if not all([route_file.exists(), vars_file.exists()]):
                continue
            
            route_df = pd.read_csv(route_file)
            vars_df = pd.read_csv(vars_file)
            
            if route_df.empty or vars_df.empty:
                continue
            
            route = route_df.iloc[0]
            route_id = str(route['RouteId'])
            
            for _, var in vars_df.iterrows():
                trip_counter += 1
                trip_id = f"T{trip_counter:06d}"
                
                is_outbound = var['Outbound']
                direction_id = '0' if is_outbound else '1'
                trip_headsign = var['RouteVarShortName']
                
                trips_data.append({
                    'route_id': route_id,
                    'service_id': 'DAILY',
                    'trip_id': trip_id,
                    'trip_headsign': trip_headsign,
                    'direction_id': direction_id,
                    'block_id': '',
                    'shape_id': '',
                    'wheelchair_accessible': '1'
                })
                
                if is_outbound and stops_file.exists():
                    stops_df = pd.read_csv(stops_file)
                elif not is_outbound and rev_stops_file.exists():
                    stops_df = pd.read_csv(rev_stops_file)
                else:
                    continue
                
                running_time_minutes = int(var['RunningTime']) if pd.notna(var['RunningTime']) else 60
                num_stops = len(stops_df)
                
                if num_stops == 0:
                    continue
                
                time_interval = running_time_minutes / max(num_stops - 1, 1)
                start_time = datetime.strptime("05:00:00", "%H:%M:%S")
                
                for stop_sequence, (_, stop) in enumerate(stops_df.iterrows(), start=1):
                    time_offset = timedelta(minutes=time_interval * (stop_sequence - 1))
                    arrival_time = start_time + time_offset
                    departure_time = arrival_time + timedelta(seconds=30)
                    
                    stop_times_data.append({
                        'trip_id': trip_id,
                        'arrival_time': arrival_time.strftime("%H:%M:%S"),
                        'departure_time': departure_time.strftime("%H:%M:%S"),
                        'stop_id': int(stop['StopId']),
                        'stop_sequence': str(stop_sequence),
                        'stop_headsign': '',
                        'pickup_type': '0',
                        'drop_off_type': '0',
                        'shape_dist_traveled': ''
                    })
        
        with open(self.output_path / 'trips.txt', 'w', encoding='utf-8', newline='') as f:
            if trips_data:
                writer = csv.DictWriter(f, fieldnames=trips_data[0].keys())
                writer.writeheader()
                writer.writerows(trips_data)
        
        print(f"✓ Generated trips.txt ({len(trips_data)} trips)")
        
        with open(self.output_path / 'stop_times.txt', 'w', encoding='utf-8', newline='') as f:
            if stop_times_data:
                writer = csv.DictWriter(f, fieldnames=stop_times_data[0].keys())
                writer.writeheader()
                writer.writerows(stop_times_data)
        
        print(f"✓ Generated stop_times.txt ({len(stop_times_data)} stop times)")
    
    def generate_feed_info_txt(self):
        """Generate feed_info.txt - GTFS feed metadata."""
        feed_info = [{
            'feed_publisher_name': 'BusHappy',
            'feed_publisher_url': 'https://github.com/PenguAKAuseless/BusHappy',
            'feed_lang': 'vi',
            'feed_start_date': '20250101',
            'feed_end_date': '20251231',
            'feed_version': datetime.now().strftime('%Y%m%d')
        }]
        
        with open(self.output_path / 'feed_info.txt', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=feed_info[0].keys())
            writer.writeheader()
            writer.writerows(feed_info)
        
        print(f"✓ Generated feed_info.txt")
    
    def _natural_sort_key(self, s):
        """Natural sort key for route numbers."""
        import re
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', str(s))]
    
    def generate_all(self):
        """Generate all GTFS files."""
        print("\n🚌 Generating GTFS files for HCMC Bus Routes...")
        print(f"Output directory: {self.output_path}\n")
        
        self.generate_agency_txt()
        self.generate_stops_txt()
        self.generate_routes_txt()
        self.generate_calendar_txt()
        self.generate_trips_and_stop_times()
        self.generate_feed_info_txt()
        
        print("\n✅ GTFS generation complete!")
        print(f"\nGTFS files are ready in: {self.output_path}")
        print("\nGenerated files:")
        for gtfs_file in sorted(self.output_path.glob('*.txt')):
            file_size = gtfs_file.stat().st_size / 1024  # KB
            print(f"  • {gtfs_file.name} ({file_size:.1f} KB)")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent.parent
    
    base_path = script_dir / "Bus_route_data"
    output_path = script_dir / "gtfs"
    
    # Check if base path exists
    if not base_path.exists():
        print(f"❌ Error: Bus_route_data directory not found at {base_path}")
        return
    
    # Generate GTFS
    generator = GTFSGenerator(str(base_path), str(output_path))
    generator.generate_all()


if __name__ == "__main__":
    main()
