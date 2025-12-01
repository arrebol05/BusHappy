"""
Bus Route Matching & Arrival Time Generation

This script:
1. Parses all cleaned GPS data files
2. Matches each bus vehicle to its most likely route using trajectory analysis
3. Calculates and stores arrival times at each stop for each route
4. Generates comprehensive arrival time database for the transit system

Author: BusHappy Team
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from collections import defaultdict
import warnings
from tqdm import tqdm
warnings.filterwarnings('ignore')

# GPU support
try:
    import cupy as cp
    GPU_AVAILABLE = cp.cuda.is_available()
    if GPU_AVAILABLE:
        print("🚀 GPU detected! Using CuPy for accelerated computations")
        xp = cp  # Use CuPy for array operations
    else:
        print("💻 No GPU detected, using CPU (NumPy)")
        xp = np
except ImportError:
    print("💻 CuPy not installed, using CPU (NumPy)")
    GPU_AVAILABLE = False
    xp = np
    cp = None


class BusRouteMapper:
    """Maps bus vehicles to routes and calculates arrival times"""
    
    def __init__(self,
                 gps_data_dir: str = 'Bus_route_data/raw_GPS/cleaned',
                 route_data_dir: str = 'Bus_route_data/HCMC_bus_routes',
                 stops_data_file: str = 'Bus_route_data/all_bus_stops_aggregated.csv',
                 output_dir: str = 'Bus_route_data/arrival_times',
                 use_gpu: bool = True,
                 batch_size: int = 10000):
        
        self.gps_data_dir = Path(gps_data_dir)
        self.route_data_dir = Path(route_data_dir)
        self.stops_data_file = Path(stops_data_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # GPU settings
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.batch_size = batch_size
        
        if self.use_gpu:
            print(f"⚡ GPU acceleration enabled (batch size: {batch_size:,})")
        
        # Matching parameters
        self.STOP_RADIUS_METERS = 50  # Distance to match GPS to stop
        self.MIN_STOPS_FOR_ROUTE_MATCH = 3  # Minimum stops to confirm route
        self.MAX_SPEED_AT_STOP = 5  # km/h - max speed when at stop
        self.MIN_STOP_DURATION = 10  # seconds - minimum time at stop
        self.TRIP_SEPARATION_MINUTES = 30  # Gap between trips
        self.CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for route match
        
        print("🚌 Initializing Bus Route Mapper...")
        print("=" * 80)
        
        # Load bus stops
        print(f"\n📍 Loading bus stops from {self.stops_data_file.name}...")
        self.stops_df = pd.read_csv(self.stops_data_file)
        print(f"✓ Loaded {len(self.stops_df):,} bus stops")
        
        # Pre-convert stops to GPU if available
        if self.use_gpu:
            self.stops_lat_gpu = cp.array(self.stops_df['Lat'].values, dtype=cp.float32)
            self.stops_lng_gpu = cp.array(self.stops_df['Lng'].values, dtype=cp.float32)
            print(f"✓ Loaded stops data to GPU memory")
        
        # Load all routes
        print(f"\n🗺️  Loading route data from {self.route_data_dir}...")
        self.routes_data = self._load_all_routes()
        print(f"✓ Loaded {len(self.routes_data)} routes")
        
        # Create route-stop lookup
        self._build_route_stop_lookup()
        
        print(f"\n✓ Initialization complete!")
        print("=" * 80)
    
    def _load_all_routes(self) -> Dict:
        """Load all route information and stop sequences"""
        routes = {}
        
        route_dirs = [d for d in self.route_data_dir.iterdir() if d.is_dir()]
        
        for route_dir in tqdm(sorted(route_dirs), desc="Loading routes", unit="route"):
            route_num = route_dir.name
            
            try:
                # Load route info
                route_info_file = route_dir / 'route_by_id.csv'
                if not route_info_file.exists():
                    continue
                
                route_info = pd.read_csv(route_info_file)
                
                # Load variants (directions)
                vars_file = route_dir / 'vars_by_route.csv'
                if vars_file.exists():
                    variants = pd.read_csv(vars_file)
                else:
                    variants = pd.DataFrame()
                
                # Load stops (both forward and reverse directions)
                stops_file = route_dir / 'stops_by_var.csv'
                rev_stops_file = route_dir / 'rev_stops_by_var.csv'
                
                stops_list = []
                
                if stops_file.exists():
                    stops_forward = pd.read_csv(stops_file)
                    stops_list.append(stops_forward)
                
                if rev_stops_file.exists():
                    stops_reverse = pd.read_csv(rev_stops_file)
                    stops_list.append(stops_reverse)
                
                if not stops_list:
                    continue
                
                # Combine forward and reverse stops
                stops = pd.concat(stops_list, ignore_index=True)
                # Remove duplicates (some stops may be in both directions)
                stops = stops.drop_duplicates(subset=['StopId'])
                
                routes[route_num] = {
                    'info': route_info,
                    'variants': variants,
                    'stops': stops,
                    'stop_ids': set(stops['StopId'].unique())
                }
                
            except Exception as e:
                print(f"  ⚠️  Warning: Could not load route {route_num}: {e}")
                continue
        
        return routes
    
    def _build_route_stop_lookup(self):
        """Build lookup table: stop_id -> list of routes"""
        self.stop_to_routes = defaultdict(list)
        
        total_stops = 0
        for route_num, route_data in self.routes_data.items():
            num_stops = len(route_data['stop_ids'])
            total_stops += num_stops
            for stop_id in route_data['stop_ids']:
                self.stop_to_routes[stop_id].append(route_num)
        
        print(f"✓ Built stop-to-route lookup for {len(self.stop_to_routes)} unique stops")
        print(f"  (Total route-stop combinations: {total_stops})")
    
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
    
    def _match_point_to_stop(self, lat: float, lng: float) -> Tuple[Optional[int], Optional[str], float]:
        """Match a GPS point to the nearest bus stop (vectorized)"""
        if pd.isna(lat) or pd.isna(lng):
            return None, None, np.inf
        
        # Vectorized distance calculation
        lat1_rad = np.radians(lat)
        lat2_rad = np.radians(self.stops_df['Lat'].values)
        delta_lat = np.radians(self.stops_df['Lat'].values - lat)
        delta_lon = np.radians(self.stops_df['Lng'].values - lng)
        
        a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        distances = 6371000 * c  # Earth radius in meters
        
        min_idx = np.argmin(distances)
        min_dist = distances[min_idx]
        
        if min_dist <= self.STOP_RADIUS_METERS:
            return (
                int(self.stops_df.iloc[min_idx]['StopId']),
                self.stops_df.iloc[min_idx]['Name'],
                min_dist
            )
        
        return None, None, min_dist
    
    def _batch_match_points_to_stops_gpu(self, lats: np.ndarray, lngs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        GPU-accelerated batch matching of GPS points to stops
        
        Args:
            lats: Array of latitudes
            lngs: Array of longitudes
            
        Returns:
            (stop_indices, distances) - Arrays of closest stop indices and distances
        """
        if not self.use_gpu:
            return self._batch_match_points_to_stops_cpu(lats, lngs)
        
        # Transfer GPS points to GPU
        lats_gpu = cp.asarray(lats, dtype=cp.float32)
        lngs_gpu = cp.asarray(lngs, dtype=cp.float32)
        
        n_points = len(lats)
        n_stops = len(self.stops_lat_gpu)
        
        # Process in chunks to avoid memory overflow
        chunk_size = min(self.batch_size, n_points)
        all_stop_indices = []
        all_distances = []
        
        for i in range(0, n_points, chunk_size):
            end_idx = min(i + chunk_size, n_points)
            chunk_lats = lats_gpu[i:end_idx]
            chunk_lngs = lngs_gpu[i:end_idx]
            
            # Reshape for broadcasting: (chunk_size, 1) vs (n_stops,)
            chunk_lats_2d = chunk_lats[:, cp.newaxis]
            chunk_lngs_2d = chunk_lngs[:, cp.newaxis]
            
            # Haversine formula on GPU
            lat1_rad = cp.radians(chunk_lats_2d)
            lat2_rad = cp.radians(self.stops_lat_gpu)
            delta_lat = cp.radians(self.stops_lat_gpu - chunk_lats_2d)
            delta_lon = cp.radians(self.stops_lng_gpu - chunk_lngs_2d)
            
            a = cp.sin(delta_lat/2)**2 + cp.cos(lat1_rad) * cp.cos(lat2_rad) * cp.sin(delta_lon/2)**2
            c = 2 * cp.arctan2(cp.sqrt(a), cp.sqrt(1-a))
            distances = 6371000 * c  # Earth radius in meters
            
            # Find minimum distance for each point
            min_indices = cp.argmin(distances, axis=1)
            min_distances = cp.min(distances, axis=1)
            
            all_stop_indices.append(cp.asnumpy(min_indices))
            all_distances.append(cp.asnumpy(min_distances))
        
        return np.concatenate(all_stop_indices), np.concatenate(all_distances)
    
    def _batch_match_points_to_stops_cpu(self, lats: np.ndarray, lngs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        CPU-based batch matching of GPS points to stops
        
        Args:
            lats: Array of latitudes
            lngs: Array of longitudes
            
        Returns:
            (stop_indices, distances) - Arrays of closest stop indices and distances
        """
        stops_lat = self.stops_df['Lat'].values
        stops_lng = self.stops_df['Lng'].values
        
        # Reshape for broadcasting
        lats_2d = lats[:, np.newaxis]
        lngs_2d = lngs[:, np.newaxis]
        
        # Haversine formula
        lat1_rad = np.radians(lats_2d)
        lat2_rad = np.radians(stops_lat)
        delta_lat = np.radians(stops_lat - lats_2d)
        delta_lon = np.radians(stops_lng - lngs_2d)
        
        a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        distances = 6371000 * c
        
        # Find minimum distance for each point
        min_indices = np.argmin(distances, axis=1)
        min_distances = np.min(distances, axis=1)
        
        return min_indices, min_distances
    
    def _match_vehicle_to_route(self, stop_sequence: List[int]) -> Tuple[Optional[str], float, Dict]:
        """
        Match a sequence of stops to the most likely route
        
        Returns:
            (route_num, confidence_score, match_details)
        """
        if len(stop_sequence) < self.MIN_STOPS_FOR_ROUTE_MATCH:
            return None, 0.0, {}
        
        # Get candidate routes (routes that contain any of these stops)
        candidate_routes = set()
        for stop_id in stop_sequence:
            if stop_id in self.stop_to_routes:
                candidate_routes.update(self.stop_to_routes[stop_id])
        
        if not candidate_routes:
            return None, 0.0, {}
        
        # Score each candidate route
        best_route = None
        best_score = 0.0
        best_details = {}
        
        for route_num in candidate_routes:
            route_stops = list(self.routes_data[route_num]['stop_ids'])
            
            # Calculate match score
            matched_stops = [s for s in stop_sequence if s in route_stops]
            
            if len(matched_stops) < self.MIN_STOPS_FOR_ROUTE_MATCH:
                continue
            
            # Score based on:
            # 1. Percentage of stops matched
            # 2. Sequence order preservation
            coverage_score = len(matched_stops) / len(route_stops)
            sequence_score = len(matched_stops) / len(stop_sequence)
            
            # Check sequence order
            order_score = 0.0
            if len(matched_stops) >= 2:
                ordered_count = 0
                for i in range(len(matched_stops) - 1):
                    try:
                        idx1 = route_stops.index(matched_stops[i])
                        idx2 = route_stops.index(matched_stops[i + 1])
                        if idx2 > idx1:  # Correct order
                            ordered_count += 1
                    except ValueError:
                        continue
                
                order_score = ordered_count / (len(matched_stops) - 1) if len(matched_stops) > 1 else 0
            
            # Combined score
            total_score = (coverage_score * 0.3 + sequence_score * 0.3 + order_score * 0.4)
            
            if total_score > best_score:
                best_score = total_score
                best_route = route_num
                best_details = {
                    'matched_stops': len(matched_stops),
                    'total_route_stops': len(route_stops),
                    'coverage': coverage_score,
                    'sequence_match': sequence_score,
                    'order_preservation': order_score
                }
        
        return best_route, best_score, best_details
    
    def _segment_into_trips(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """Segment vehicle GPS data into individual trips"""
        trips = []
        
        if len(df) == 0:
            return trips
        
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Find trip boundaries (large time gaps)
        df['time_gap'] = df['datetime'].diff().dt.total_seconds() / 60  # minutes
        
        trip_starts = [0] + list(df[df['time_gap'] > self.TRIP_SEPARATION_MINUTES].index)
        trip_starts.append(len(df))
        
        for i in range(len(trip_starts) - 1):
            start_idx = trip_starts[i]
            end_idx = trip_starts[i + 1]
            
            trip_df = df.iloc[start_idx:end_idx].copy()
            
            if len(trip_df) > 10:  # Minimum records for valid trip
                trips.append(trip_df)
        
        return trips
    
    def _detect_stop_arrivals(self, trip_df: pd.DataFrame) -> List[Dict]:
        """Detect when a vehicle arrives at each stop during a trip (GPU-accelerated)"""
        arrivals = []
        
        trip_df = trip_df.sort_values('datetime').reset_index(drop=True)
        
        # Extract coordinates
        lats = trip_df['lat'].values
        lngs = trip_df['lng'].values
        
        # Remove NaN values
        valid_mask = ~(pd.isna(lats) | pd.isna(lngs))
        if not valid_mask.any():
            return arrivals
        
        # Batch match GPS points to stops (GPU or CPU)
        stop_indices, distances = self._batch_match_points_to_stops_gpu(
            lats[valid_mask], 
            lngs[valid_mask]
        )
        
        # Map back to full dataframe
        trip_df['stop_id'] = None
        trip_df['stop_name'] = None
        trip_df['distance_to_stop'] = np.inf
        
        valid_indices = np.where(valid_mask)[0]
        for i, (stop_idx, dist) in enumerate(zip(stop_indices, distances)):
            df_idx = valid_indices[i]
            if dist <= self.STOP_RADIUS_METERS:
                trip_df.at[df_idx, 'stop_id'] = int(self.stops_df.iloc[stop_idx]['StopId'])
                trip_df.at[df_idx, 'stop_name'] = self.stops_df.iloc[stop_idx]['Name']
                trip_df.at[df_idx, 'distance_to_stop'] = dist
        
        # Group consecutive points at same stop
        trip_df['at_stop'] = (
            (trip_df['speed'] <= self.MAX_SPEED_AT_STOP) &
            (trip_df['stop_id'].notna())
        )
        
        trip_df['stop_group'] = (
            (trip_df['stop_id'] != trip_df['stop_id'].shift()) |
            (~trip_df['at_stop'])
        ).cumsum()
        
        # Extract arrival events
        for stop_group, group_df in trip_df[trip_df['at_stop']].groupby('stop_group'):
            if len(group_df) == 0:
                continue
            
            arrival_time = group_df['datetime'].min()
            departure_time = group_df['datetime'].max()
            duration = (departure_time - arrival_time).total_seconds()
            
            if duration < self.MIN_STOP_DURATION:
                continue
            
            stop_id = group_df['stop_id'].mode()[0] if len(group_df) > 0 else group_df['stop_id'].iloc[0]
            stop_name = group_df['stop_name'].mode()[0] if len(group_df) > 0 else group_df['stop_name'].iloc[0]
            
            arrival = {
                'stop_id': int(stop_id) if pd.notna(stop_id) else None,
                'stop_name': stop_name,
                'arrival_time': arrival_time,
                'departure_time': departure_time,
                'duration_seconds': duration,
                'avg_distance_meters': group_df['distance_to_stop'].mean(),
                'had_door_event': group_df[['door_up', 'door_down']].any().any()
            }
            
            arrivals.append(arrival)
        
        return arrivals
    
    def process_gps_file(self, gps_file: Path) -> pd.DataFrame:
        """
        Process a single GPS data file
        
        Returns:
            DataFrame with columns: vehicle_id, trip_id, route_num, stop_id, arrival_time, etc.
        """
        print(f"\n📂 Processing: {gps_file.name}")
        print("-" * 80)
        
        # Load GPS data
        try:
            df = pd.read_csv(gps_file)
            df['datetime'] = pd.to_datetime(df['datetime'])
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return pd.DataFrame()
        
        print(f"  Loaded {len(df):,} GPS records for {df['anonymized_vehicle'].nunique()} vehicles")
        
        all_arrivals = []
        
        vehicle_groups = list(df.groupby('anonymized_vehicle'))
        
        # Process each vehicle with progress bar
        for vehicle_id, vehicle_df in tqdm(vehicle_groups, desc=f"  Vehicles", unit="vehicle", leave=False):
            # Segment into trips
            trips = self._segment_into_trips(vehicle_df)
            
            for trip_idx, trip_df in enumerate(trips):
                # Detect stop arrivals
                arrivals = self._detect_stop_arrivals(trip_df)
                
                if len(arrivals) < self.MIN_STOPS_FOR_ROUTE_MATCH:
                    continue
                
                # Extract stop sequence
                stop_sequence = [a['stop_id'] for a in arrivals if a['stop_id'] is not None]
                
                # Match to route
                route_num, confidence, match_details = self._match_vehicle_to_route(stop_sequence)
                
                if route_num is None or confidence < self.CONFIDENCE_THRESHOLD:
                    continue
                
                # Record arrivals with route info
                trip_start_time = trip_df['datetime'].min()
                
                for arrival in arrivals:
                    if arrival['stop_id'] is None:
                        continue
                    
                    arrival_record = {
                        'date': gps_file.stem.replace('cleaned_anonymized_raw_', ''),
                        'vehicle_id': vehicle_id,
                        'trip_id': f"{vehicle_id}_{trip_idx}_{trip_start_time.strftime('%H%M')}",
                        'route_num': route_num,
                        'route_confidence': confidence,
                        'stop_id': arrival['stop_id'],
                        'stop_name': arrival['stop_name'],
                        'arrival_time': arrival['arrival_time'],
                        'departure_time': arrival['departure_time'],
                        'stop_duration_seconds': arrival['duration_seconds'],
                        'distance_to_stop_meters': arrival['avg_distance_meters'],
                        'had_door_event': arrival['had_door_event'],
                        'time_of_day': arrival['arrival_time'].strftime('%H:%M:%S'),
                        'hour': arrival['arrival_time'].hour,
                        'day_of_week': arrival['arrival_time'].strftime('%A')
                    }
                    
                    all_arrivals.append(arrival_record)
        
        if len(all_arrivals) == 0:
            print(f"  ⚠️  No valid arrivals detected")
            return pd.DataFrame()
        
        arrivals_df = pd.DataFrame(all_arrivals)
        
        print(f"\n  ✓ Processed {len(arrivals_df):,} arrivals")
        print(f"    Routes detected: {arrivals_df['route_num'].nunique()}")
        print(f"    Stops visited: {arrivals_df['stop_id'].nunique()}")
        print(f"    Avg confidence: {arrivals_df['route_confidence'].mean():.2%}")
        
        return arrivals_df
    
    def process_all_files(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Process all cleaned GPS files
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
        
        Returns:
            Combined DataFrame of all arrivals
        """
        print("\n" + "=" * 80)
        print("PROCESSING ALL GPS DATA FILES")
        print("=" * 80)
        
        # Get all cleaned GPS files
        gps_files = sorted(self.gps_data_dir.glob('cleaned_anonymized_raw_*.csv'))
        
        if start_date:
            gps_files = [f for f in gps_files if f.stem.replace('cleaned_anonymized_raw_', '') >= start_date]
        if end_date:
            gps_files = [f for f in gps_files if f.stem.replace('cleaned_anonymized_raw_', '') <= end_date]
        
        print(f"\nFound {len(gps_files)} files to process")
        
        if len(gps_files) == 0:
            print("❌ No files found!")
            return pd.DataFrame()
        
        all_results = []
        
        # Process files with progress bar
        for gps_file in tqdm(gps_files, desc="Processing GPS files", unit="file"):
            result = self.process_gps_file(gps_file)
            
            if len(result) > 0:
                all_results.append(result)
        
        if len(all_results) == 0:
            print("\n❌ No valid data processed!")
            return pd.DataFrame()
        
        # Combine all results
        print("\n" + "=" * 80)
        print("COMBINING RESULTS...")
        print("=" * 80)
        
        combined_df = pd.concat(all_results, ignore_index=True)
        
        print(f"\n✓ Combined data from {len(all_results)} files")
        print(f"  Total arrivals: {len(combined_df):,}")
        print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"  Unique routes: {combined_df['route_num'].nunique()}")
        print(f"  Unique stops: {combined_df['stop_id'].nunique()}")
        print(f"  Unique vehicles: {combined_df['vehicle_id'].nunique()}")
        print(f"  Unique trips: {combined_df['trip_id'].nunique()}")
        
        return combined_df
    
    def save_arrivals(self, arrivals_df: pd.DataFrame, filename: str = None):
        """Save arrival data in hierarchical structure for efficient querying"""
        if len(arrivals_df) == 0:
            print("❌ No data to save!")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print("\n💾 Saving arrivals in hierarchical structure...")
        print("=" * 80)
        
        # 1. Save complete dataset (for backward compatibility)
        if filename is None:
            filename = f'bus_arrivals_all_routes_{timestamp}.csv'
        main_file = self.output_dir / filename
        arrivals_df.to_csv(main_file, index=False)
        print(f"✓ Saved complete dataset: {main_file}")
        
        # 2. Save by DATE -> ROUTE structure (optimized for date-based queries)
        print("\n📅 Organizing by date...")
        by_date_dir = self.output_dir / 'by_date'
        by_date_dir.mkdir(exist_ok=True)
        
        for date, date_df in tqdm(arrivals_df.groupby('date'), desc="  Dates", unit="date"):
            date_dir = by_date_dir / str(date)
            date_dir.mkdir(exist_ok=True)
            
            # Save metadata for the date
            date_metadata = {
                'date': date,
                'total_arrivals': len(date_df),
                'routes': sorted(date_df['route_num'].unique().tolist()),
                'vehicles': date_df['vehicle_id'].nunique(),
                'trips': date_df['trip_id'].nunique(),
                'stops': date_df['stop_id'].nunique(),
                'generated_at': datetime.now().isoformat()
            }
            
            with open(date_dir / 'metadata.json', 'w') as f:
                json.dump(date_metadata, f, indent=2)
            
            # Save each route within the date
            for route_num, route_df in date_df.groupby('route_num'):
                route_dir = date_dir / f'route_{str(route_num)}'
                route_dir.mkdir(exist_ok=True)
                
                route_df.to_csv(route_dir / 'arrivals.csv', index=False)
                
                # Save route-specific metadata
                route_metadata = {
                    'route_num': route_num,
                    'date': date,
                    'total_arrivals': len(route_df),
                    'trips': route_df['trip_id'].nunique(),
                    'vehicles': route_df['vehicle_id'].nunique(),
                    'stops': sorted(route_df['stop_id'].unique().tolist()),
                    'avg_confidence': float(route_df['route_confidence'].mean()),
                    'time_range': {
                        'first_arrival': route_df['arrival_time'].min(),
                        'last_arrival': route_df['arrival_time'].max()
                    }
                }
                
                with open(route_dir / 'metadata.json', 'w') as f:
                    json.dump(route_metadata, f, indent=2, default=str)
        
        print(f"✓ Saved {arrivals_df['date'].nunique()} dates to: {by_date_dir}")
        
        # 3. Save by ROUTE -> DATE structure (optimized for route-based queries)
        print("\n🚌 Organizing by route...")
        by_route_dir = self.output_dir / 'by_route'
        by_route_dir.mkdir(exist_ok=True)
        
        for route_num, route_df in tqdm(arrivals_df.groupby('route_num'), desc="  Routes", unit="route"):
            route_dir = by_route_dir / f'route_{str(route_num)}'
            route_dir.mkdir(exist_ok=True)
            
            # Save complete route data
            route_df.to_csv(route_dir / 'all_arrivals.csv', index=False)
            
            # Save metadata for the route
            route_metadata = {
                'route_num': route_num,
                'total_arrivals': len(route_df),
                'dates': sorted(route_df['date'].unique().tolist()),
                'vehicles': route_df['vehicle_id'].nunique(),
                'trips': route_df['trip_id'].nunique(),
                'stops': sorted(route_df['stop_id'].unique().tolist()),
                'avg_confidence': float(route_df['route_confidence'].mean()),
                'generated_at': datetime.now().isoformat()
            }
            
            with open(route_dir / 'metadata.json', 'w') as f:
                json.dump(route_metadata, f, indent=2)
            
            # Save each date within the route
            for date, date_df in route_df.groupby('date'):
                date_df.to_csv(route_dir / f'{date}.csv', index=False)
        
        print(f"✓ Saved {arrivals_df['route_num'].nunique()} routes to: {by_route_dir}")
        
        # Generate summary report
        self._generate_summary_report(arrivals_df, timestamp)
        
        # Generate statistics by route
        self._generate_route_statistics(arrivals_df, timestamp)
        
        return main_file
    
    def _generate_summary_report(self, arrivals_df: pd.DataFrame, timestamp: str):
        """Generate comprehensive summary report"""
        summary_file = self.output_dir / f'summary_report_{timestamp}.txt'
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("BUS ROUTE MAPPING & ARRIVAL TIME ANALYSIS\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Overall statistics
            f.write("OVERALL STATISTICS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total arrival records: {len(arrivals_df):,}\n")
            f.write(f"Date range: {arrivals_df['date'].min()} to {arrivals_df['date'].max()}\n")
            f.write(f"Unique routes detected: {arrivals_df['route_num'].nunique()}\n")
            f.write(f"Unique stops visited: {arrivals_df['stop_id'].nunique()}\n")
            f.write(f"Unique vehicles tracked: {arrivals_df['vehicle_id'].nunique()}\n")
            f.write(f"Total trips: {arrivals_df['trip_id'].nunique()}\n")
            f.write(f"Average route confidence: {arrivals_df['route_confidence'].mean():.2%}\n\n")
            
            # By route
            f.write("STATISTICS BY ROUTE\n")
            f.write("-" * 80 + "\n")
            route_stats = arrivals_df.groupby('route_num').agg({
                'trip_id': 'nunique',
                'stop_id': 'nunique',
                'arrival_time': 'count',
                'route_confidence': 'mean',
                'stop_duration_seconds': 'mean'
            }).rename(columns={
                'trip_id': 'Trips',
                'stop_id': 'Stops',
                'arrival_time': 'Arrivals',
                'route_confidence': 'Avg_Confidence',
                'stop_duration_seconds': 'Avg_Stop_Duration_Sec'
            })
            f.write(route_stats.to_string() + "\n\n")
            
            # By time of day
            f.write("ARRIVALS BY HOUR OF DAY\n")
            f.write("-" * 80 + "\n")
            hourly = arrivals_df.groupby('hour').size()
            for hour, count in hourly.items():
                f.write(f"{hour:02d}:00 - {count:,} arrivals\n")
            f.write("\n")
            
            # By day of week
            f.write("ARRIVALS BY DAY OF WEEK\n")
            f.write("-" * 80 + "\n")
            daily = arrivals_df.groupby('day_of_week').size()
            for day, count in daily.items():
                f.write(f"{day}: {count:,} arrivals\n")
            f.write("\n")
            
            # Top stops
            f.write("TOP 20 BUSIEST STOPS\n")
            f.write("-" * 80 + "\n")
            top_stops = arrivals_df.groupby(['stop_id', 'stop_name']).size().sort_values(ascending=False).head(20)
            for (stop_id, stop_name), count in top_stops.items():
                f.write(f"Stop {stop_id} - {stop_name}: {count:,} arrivals\n")
            f.write("\n")
        
        print(f"📊 Saved summary report to: {summary_file}")
    
    def _generate_route_statistics(self, arrivals_df: pd.DataFrame, timestamp: str):
        """Generate detailed statistics for each route"""
        stats_dir = self.output_dir / 'statistics'
        stats_dir.mkdir(exist_ok=True)
        
        stats_file = stats_dir / f'route_statistics_{timestamp}.csv'
        
        route_stats = []
        
        for route_num, route_df in arrivals_df.groupby('route_num'):
            stats = {
                'route_num': route_num,
                'total_arrivals': len(route_df),
                'unique_trips': route_df['trip_id'].nunique(),
                'unique_stops': route_df['stop_id'].nunique(),
                'unique_vehicles': route_df['vehicle_id'].nunique(),
                'avg_confidence': route_df['route_confidence'].mean(),
                'min_confidence': route_df['route_confidence'].min(),
                'max_confidence': route_df['route_confidence'].max(),
                'avg_stop_duration_sec': route_df['stop_duration_seconds'].mean(),
                'median_stop_duration_sec': route_df['stop_duration_seconds'].median(),
                'avg_distance_to_stop_m': route_df['distance_to_stop_meters'].mean(),
                'door_events_pct': (route_df['had_door_event'].sum() / len(route_df)) * 100,
                'earliest_arrival': route_df['arrival_time'].min(),
                'latest_arrival': route_df['arrival_time'].max(),
                'peak_hour': route_df['hour'].mode()[0] if len(route_df['hour'].mode()) > 0 else None
            }
            
            route_stats.append(stats)
        
        stats_df = pd.DataFrame(route_stats)
        stats_df.to_csv(stats_file, index=False)
        
        print(f"📊 Saved route statistics to: {stats_file}")


def main():
    """Main execution function"""
    print("\n" + "=" * 80)
    print("🚌 BUS ROUTE MAPPER & ARRIVAL TIME GENERATOR")
    print("=" * 80 + "\n")
    
    # Initialize mapper
    mapper = BusRouteMapper()
    
    # Process all files
    # You can optionally filter by date range:
    # arrivals_df = mapper.process_all_files(start_date='2025-04-01', end_date='2025-04-07')
    
    arrivals_df = mapper.process_all_files()
    
    # Save results
    if len(arrivals_df) > 0:
        mapper.save_arrivals(arrivals_df)
        
        # Display sample
        print("\n" + "=" * 80)
        print("SAMPLE RESULTS (First 10 arrivals)")
        print("=" * 80)
        print(arrivals_df.head(10)[['date', 'route_num', 'stop_name', 'time_of_day', 'route_confidence']].to_string(index=False))
        
        print("\n✅ Processing complete!")
    else:
        print("\n❌ No data was processed!")


if __name__ == '__main__':
    main()
