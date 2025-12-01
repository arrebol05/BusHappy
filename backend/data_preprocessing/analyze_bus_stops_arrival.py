"""
Bus Stop Analysis - Door Events & Arrival Time Calculation

This script:
1. Detects door open/close events from cleaned GPS data
2. Matches GPS locations to bus stops and routes
3. Calculates arrival times for each bus at each stop
4. Generates comprehensive arrival time data for all routes
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class BusStopAnalyzer:
    """Analyze bus stops, door events, and calculate arrival times"""
    
    def __init__(self, 
                 gps_data_dir: str = 'Bus_route_data/raw_GPS/cleaned',
                 route_data_dir: str = 'Bus_route_data/HCMC_bus_routes',
                 stops_data_file: str = 'Bus_route_data/all_bus_stops_ag_old_adr.csv',
                 output_dir: str = 'Bus_route_data/arrival_times'):
        
        self.gps_data_dir = Path(gps_data_dir)
        self.route_data_dir = Path(route_data_dir)
        self.stops_data_file = Path(stops_data_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Parameters for stop detection
        self.STOP_RADIUS_METERS = 50  # Distance threshold to match GPS to stop
        self.MIN_STOP_DURATION_SECONDS = 10  # Minimum time at stop to consider it valid
        self.DOOR_EVENT_WINDOW_SECONDS = 30  # Time window to look for door events
        self.MAX_SPEED_AT_STOP = 5  # Max speed (km/h) to consider vehicle stopped
        
        # Load bus stops data
        print("Loading bus stops data...")
        self.stops_df = pd.read_csv(self.stops_data_file)
        print(f"✓ Loaded {len(self.stops_df)} bus stops")
        
        # Load all route data
        print("\nLoading route data...")
        self.routes_data = self._load_all_routes()
        print(f"✓ Loaded {len(self.routes_data)} routes")
    
    def _load_all_routes(self) -> Dict:
        """Load all route and stop information"""
        routes = {}
        
        for route_dir in sorted(self.route_data_dir.iterdir()):
            if not route_dir.is_dir():
                continue
                
            route_num = route_dir.name
            
            try:
                # Load route variants (directions)
                vars_file = route_dir / 'vars_by_route.csv'
                if not vars_file.exists():
                    continue
                    
                vars_df = pd.read_csv(vars_file)
                
                # Load stops for this route
                stops_file = route_dir / 'stops_by_var.csv'
                if not stops_file.exists():
                    continue
                    
                stops_df = pd.read_csv(stops_file)
                
                routes[route_num] = {
                    'variants': vars_df,
                    'stops': stops_df
                }
                
            except Exception as e:
                print(f"  Warning: Could not load route {route_num}: {e}")
                continue
        
        return routes
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two GPS coordinates"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def _detect_door_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect door open/close events for each vehicle"""
        df = df.sort_values(['anonymized_vehicle', 'datetime']).copy()
        
        # Detect door state changes
        df['door_opened'] = False
        df['door_closed'] = False
        
        for vehicle in df['anonymized_vehicle'].unique():
            vehicle_mask = df['anonymized_vehicle'] == vehicle
            vehicle_data = df[vehicle_mask].copy()
            
            # Detect door_up changes (boarding)
            door_up_changes = vehicle_data['door_up'].ne(vehicle_data['door_up'].shift())
            df.loc[vehicle_mask & door_up_changes & vehicle_data['door_up'], 'door_opened'] = True
            
            # Detect door_down changes (alighting)
            door_down_changes = vehicle_data['door_down'].ne(vehicle_data['door_down'].shift())
            df.loc[vehicle_mask & door_down_changes & vehicle_data['door_down'], 'door_opened'] = True
            
            # Detect when doors close
            any_door_open = vehicle_data['door_up'] | vehicle_data['door_down']
            door_close_events = any_door_open.ne(any_door_open.shift()) & ~any_door_open
            df.loc[vehicle_mask & door_close_events, 'door_closed'] = True
        
        return df
    
    def _match_gps_to_stops(self, df: pd.DataFrame, route_stops: pd.DataFrame) -> pd.DataFrame:
        """Match GPS coordinates to nearest bus stops within threshold"""
        df['matched_stop_id'] = None
        df['matched_stop_name'] = None
        df['distance_to_stop'] = np.inf
        
        # Create a copy for efficiency
        stops_coords = route_stops[['StopId', 'Name', 'Lat', 'Lng']].values
        
        for idx, row in df.iterrows():
            if pd.isna(row['lat']) or pd.isna(row['lng']):
                continue
            
            # Calculate distances to all stops
            distances = np.array([
                self._haversine_distance(row['lat'], row['lng'], stop[2], stop[3])
                for stop in stops_coords
            ])
            
            min_dist_idx = np.argmin(distances)
            min_dist = distances[min_dist_idx]
            
            if min_dist <= self.STOP_RADIUS_METERS:
                df.at[idx, 'matched_stop_id'] = int(stops_coords[min_dist_idx][0])
                df.at[idx, 'matched_stop_name'] = stops_coords[min_dist_idx][1]
                df.at[idx, 'distance_to_stop'] = min_dist
        
        return df
    
    def _identify_route_variant(self, df: pd.DataFrame, route_num: str) -> pd.DataFrame:
        """Identify which route variant (direction) the vehicle is following"""
        df['route_variant'] = None
        
        if route_num not in self.routes_data:
            return df
        
        route_info = self.routes_data[route_num]
        variants = route_info['variants']
        
        for vehicle in df['anonymized_vehicle'].unique():
            vehicle_mask = df['anonymized_vehicle'] == vehicle
            vehicle_stops = df[vehicle_mask & df['matched_stop_id'].notna()]['matched_stop_id'].unique()
            
            if len(vehicle_stops) < 2:
                continue
            
            # Try to match to a variant based on stop sequence
            best_variant = None
            best_match_score = 0
            
            for _, variant in variants.iterrows():
                variant_id = variant['RouteVarId']
                variant_stops = route_info['stops']
                
                # Count matching stops in sequence
                match_score = len(set(vehicle_stops))
                
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_variant = variant_id
            
            if best_variant:
                df.loc[vehicle_mask, 'route_variant'] = best_variant
        
        return df
    
    def _calculate_stop_arrivals(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate arrival times at each stop for each vehicle trip"""
        arrivals = []
        
        # Group by vehicle
        for vehicle, vehicle_df in df.groupby('anonymized_vehicle'):
            vehicle_df = vehicle_df.sort_values('datetime')
            
            # Identify stops (low speed + door events or proximity to stop)
            at_stop_mask = (
                (vehicle_df['speed'] <= self.MAX_SPEED_AT_STOP) &
                (vehicle_df['matched_stop_id'].notna())
            ) | (
                vehicle_df['door_opened'] | vehicle_df['door_closed']
            )
            
            stop_events = vehicle_df[at_stop_mask].copy()
            
            if len(stop_events) == 0:
                continue
            
            # Group consecutive records at same stop
            stop_events['stop_group'] = (
                (stop_events['matched_stop_id'] != stop_events['matched_stop_id'].shift()) |
                (stop_events['datetime'] - stop_events['datetime'].shift() > timedelta(minutes=5))
            ).cumsum()
            
            for stop_group, group_df in stop_events.groupby('stop_group'):
                if len(group_df) == 0:
                    continue
                
                arrival_time = group_df['datetime'].min()
                departure_time = group_df['datetime'].max()
                stop_duration = (departure_time - arrival_time).total_seconds()
                
                # Only record if stop duration meets minimum threshold
                if stop_duration < self.MIN_STOP_DURATION_SECONDS:
                    continue
                
                stop_id = group_df['matched_stop_id'].mode()[0] if len(group_df['matched_stop_id'].mode()) > 0 else group_df['matched_stop_id'].iloc[0]
                stop_name = group_df['matched_stop_name'].mode()[0] if len(group_df['matched_stop_name'].mode()) > 0 else group_df['matched_stop_name'].iloc[0]
                
                arrival_record = {
                    'vehicle_id': vehicle,
                    'stop_id': int(stop_id) if pd.notna(stop_id) else None,
                    'stop_name': stop_name,
                    'arrival_time': arrival_time,
                    'departure_time': departure_time,
                    'stop_duration_seconds': stop_duration,
                    'had_door_event': group_df['door_opened'].any() or group_df['door_closed'].any(),
                    'avg_distance_to_stop': group_df['distance_to_stop'].mean(),
                    'route_variant': group_df['route_variant'].mode()[0] if len(group_df['route_variant'].mode()) > 0 else None
                }
                
                arrivals.append(arrival_record)
        
        return arrivals
    
    def analyze_date(self, date_str: str, route_num: str = None) -> pd.DataFrame:
        """
        Analyze bus stop arrivals for a specific date
        
        Args:
            date_str: Date in format 'YYYY-MM-DD'
            route_num: Specific route to analyze (optional, analyzes all if None)
        
        Returns:
            DataFrame with arrival time records
        """
        print(f"\n{'='*80}")
        print(f"Analyzing date: {date_str}")
        print(f"{'='*80}")
        
        # Load GPS data
        gps_file = self.gps_data_dir / f'cleaned_anonymized_raw_{date_str}.csv'
        if not gps_file.exists():
            print(f"❌ GPS data file not found: {gps_file}")
            return pd.DataFrame()
        
        print(f"\n📥 Loading GPS data from {gps_file.name}...")
        df = pd.read_csv(gps_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        print(f"✓ Loaded {len(df):,} GPS records for {df['anonymized_vehicle'].nunique()} vehicles")
        
        # Detect door events
        print(f"\n🚪 Detecting door events...")
        df = self._detect_door_events(df)
        door_opens = df['door_opened'].sum()
        door_closes = df['door_closed'].sum()
        print(f"✓ Detected {door_opens:,} door open events, {door_closes:,} door close events")
        
        all_arrivals = []
        
        # Process each route
        routes_to_process = [route_num] if route_num else list(self.routes_data.keys())
        
        for route in routes_to_process:
            if route not in self.routes_data:
                print(f"\n⚠️  Route {route} not found in route data")
                continue
            
            print(f"\n📍 Processing Route {route}...")
            
            route_stops = self.routes_data[route]['stops']
            print(f"  Route has {len(route_stops)} stops")
            
            # Match GPS to stops
            df_route = self._match_gps_to_stops(df.copy(), route_stops)
            matched_count = df_route['matched_stop_id'].notna().sum()
            print(f"  ✓ Matched {matched_count:,} GPS points to stops")
            
            # Identify route variants
            df_route = self._identify_route_variant(df_route, route)
            
            # Calculate arrivals
            route_arrivals = self._calculate_stop_arrivals(df_route)
            print(f"  ✓ Calculated {len(route_arrivals)} stop arrivals")
            
            # Add route number to each record
            for arrival in route_arrivals:
                arrival['route_num'] = route
                arrival['date'] = date_str
            
            all_arrivals.extend(route_arrivals)
        
        # Convert to DataFrame
        if len(all_arrivals) == 0:
            print(f"\n⚠️  No arrivals detected")
            return pd.DataFrame()
        
        arrivals_df = pd.DataFrame(all_arrivals)
        
        print(f"\n{'='*80}")
        print(f"✓ Analysis Complete!")
        print(f"  Total arrivals: {len(arrivals_df):,}")
        print(f"  Unique vehicles: {arrivals_df['vehicle_id'].nunique()}")
        print(f"  Unique stops: {arrivals_df['stop_id'].nunique()}")
        print(f"{'='*80}")
        
        return arrivals_df
    
    def analyze_date_range(self, start_date: str, end_date: str, route_num: str = None) -> pd.DataFrame:
        """
        Analyze multiple dates
        
        Args:
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            route_num: Specific route (optional)
        
        Returns:
            Combined DataFrame for all dates
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_results = []
        current = start
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            result = self.analyze_date(date_str, route_num)
            
            if len(result) > 0:
                all_results.append(result)
            
            current += timedelta(days=1)
        
        if len(all_results) == 0:
            return pd.DataFrame()
        
        combined = pd.concat(all_results, ignore_index=True)
        return combined
    
    def save_results(self, arrivals_df: pd.DataFrame, filename: str = None):
        """Save arrival times to CSV"""
        if len(arrivals_df) == 0:
            print("No data to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bus_stop_arrivals_{timestamp}.csv'
        
        output_file = self.output_dir / filename
        arrivals_df.to_csv(output_file, index=False)
        print(f"\n💾 Saved results to: {output_file}")
        
        # Also save summary statistics
        summary_file = self.output_dir / filename.replace('.csv', '_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("BUS STOP ARRIVAL ANALYSIS SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total Records: {len(arrivals_df):,}\n")
            f.write(f"Date Range: {arrivals_df['date'].min()} to {arrivals_df['date'].max()}\n")
            f.write(f"Routes: {arrivals_df['route_num'].nunique()}\n")
            f.write(f"Vehicles: {arrivals_df['vehicle_id'].nunique()}\n")
            f.write(f"Unique Stops: {arrivals_df['stop_id'].nunique()}\n\n")
            
            f.write("Records by Route:\n")
            f.write("-" * 80 + "\n")
            route_summary = arrivals_df.groupby('route_num').agg({
                'vehicle_id': 'nunique',
                'stop_id': 'nunique',
                'arrival_time': 'count'
            }).rename(columns={
                'vehicle_id': 'Vehicles',
                'stop_id': 'Stops',
                'arrival_time': 'Arrivals'
            })
            f.write(route_summary.to_string())
            f.write("\n\n")
            
            f.write("Average Stop Duration by Route:\n")
            f.write("-" * 80 + "\n")
            duration_by_route = arrivals_df.groupby('route_num')['stop_duration_seconds'].agg(['mean', 'median', 'std'])
            f.write(duration_by_route.to_string())
            f.write("\n")
        
        print(f"💾 Saved summary to: {summary_file}")
        
        return output_file


def main():
    """Main execution function"""
    print("="*80)
    print("BUS STOP ARRIVAL TIME ANALYZER")
    print("="*80)
    
    # Initialize analyzer
    analyzer = BusStopAnalyzer()
    
    # Example: Analyze a single date for all routes
    date = '2025-04-01'
    arrivals_df = analyzer.analyze_date(date)
    
    if len(arrivals_df) > 0:
        # Save results
        analyzer.save_results(arrivals_df, f'arrivals_{date}.csv')
        
        # Display sample results
        print("\n📊 Sample Results:")
        print("-" * 80)
        print(arrivals_df.head(10).to_string(index=False))
        
        # Display statistics
        print("\n📈 Statistics:")
        print("-" * 80)
        print(f"Average stop duration: {arrivals_df['stop_duration_seconds'].mean():.1f} seconds")
        print(f"Median stop duration: {arrivals_df['stop_duration_seconds'].median():.1f} seconds")
        print(f"Stops with door events: {arrivals_df['had_door_event'].sum():,} ({arrivals_df['had_door_event'].sum()/len(arrivals_df)*100:.1f}%)")
    
    # Example: Analyze specific route for date range
    # arrivals_df = analyzer.analyze_date_range('2025-04-01', '2025-04-07', route_num='1')
    # analyzer.save_results(arrivals_df, 'arrivals_route_1_week1.csv')


if __name__ == '__main__':
    main()
