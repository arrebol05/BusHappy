"""
Timetable Loader Module
Loads and manages bus route timetable data from HCMC_bus_routes directories.
Provides functions to query upcoming buses and calculate trip times.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import math


class TimetableManager:
    """Manages loading and querying bus timetables"""
    
    def __init__(self, base_path: Path):
        """
        Initialize timetable manager
        
        Args:
            base_path: Path to Bus_route_data directory
        """
        self.base_path = Path(base_path)
        self.routes_path = self.base_path / "HCMC_bus_routes"
        
        # Fallback to production path if routes don't exist in sandbox
        # Routes are read-only data, so safe to use production data
        if not self.routes_path.exists():
            production_path = Path(__file__).parent / "Bus_route_data" / "HCMC_bus_routes"
            if production_path.exists():
                print(f"Note: Using production route data from {production_path}")
                self.routes_path = production_path
        
        # Cache for loaded timetables
        self.timetables = {}  # route_num -> timetable data
        self.route_metadata = {}  # route_num -> metadata (running time, headway, etc)
        self.route_stops = {}  # route_num -> {direction: [stops]}
        
        # Load all available routes
        self._load_all_routes()
    
    def _load_all_routes(self):
        """Load timetable data for all available routes"""
        if not self.routes_path.exists():
            print(f"Warning: Routes path does not exist: {self.routes_path}")
            return
        
        route_dirs = [d for d in self.routes_path.iterdir() if d.is_dir()]
        
        for route_dir in route_dirs:
            route_num = route_dir.name
            try:
                self._load_route(route_num, route_dir)
            except Exception as e:
                print(f"Warning: Failed to load route {route_num}: {e}")
    
    def _load_route(self, route_num: str, route_dir: Path):
        """
        Load timetable data for a specific route
        
        Args:
            route_num: Route number
            route_dir: Path to route directory
        """
        # Load metadata from timetable_raw.json
        metadata_file = route_dir / "timetable_raw.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                self.route_metadata[route_num] = metadata
        
        # Load timetables
        timetables = {}
        
        # Load outbound timetable
        outbound_file = route_dir / "timetable_outbound.csv"
        if outbound_file.exists():
            df_outbound = pd.read_csv(outbound_file)
            timetables['outbound'] = df_outbound
        
        # Load inbound timetable
        inbound_file = route_dir / "timetable_inbound.csv"
        if inbound_file.exists():
            df_inbound = pd.read_csv(inbound_file)
            timetables['inbound'] = df_inbound
        
        if timetables:
            self.timetables[route_num] = timetables
        
        # Load stops information
        stops_by_direction = {'outbound': [], 'inbound': []}
        
        # Load outbound stops
        outbound_file = route_dir / "stops_by_var.csv"
        if outbound_file.exists():
            df_outbound = pd.read_csv(outbound_file)
            for _, row in df_outbound.iterrows():
                stops_by_direction['outbound'].append({
                    'stop_id': int(row['StopId']),
                    'code': row['Code'],
                    'name': row['Name'],
                    'lat': float(row['Lat']),
                    'lng': float(row['Lng']),
                    'sequence': len(stops_by_direction['outbound'])
                })
        
        # Load inbound stops
        inbound_file = route_dir / "rev_stops_by_var.csv"
        if inbound_file.exists():
            df_inbound = pd.read_csv(inbound_file)
            for _, row in df_inbound.iterrows():
                stops_by_direction['inbound'].append({
                    'stop_id': int(row['StopId']),
                    'code': row['Code'],
                    'name': row['Name'],
                    'lat': float(row['Lat']),
                    'lng': float(row['Lng']),
                    'sequence': len(stops_by_direction['inbound'])
                })
        
        if stops_by_direction['outbound'] or stops_by_direction['inbound']:
            self.route_stops[route_num] = stops_by_direction
    
    def get_route_metadata(self, route_num: str) -> Optional[List[Dict]]:
        """
        Get metadata for a route (running time, headway, operation hours, etc)
        
        Args:
            route_num: Route number
            
        Returns:
            List of metadata dicts for each direction, or None if not found
        """
        return self.route_metadata.get(route_num)
    
    def get_upcoming_departures(self, route_num: str, direction: str = 'outbound', 
                               current_time: Optional[datetime] = None, 
                               limit: int = 10) -> List[Dict]:
        """
        Get upcoming departure times for a route
        
        Args:
            route_num: Route number
            direction: 'outbound' or 'inbound'
            current_time: Current time (uses now() if None)
            limit: Maximum number of departures to return
            
        Returns:
            List of departure info dicts
        """
        if route_num not in self.timetables:
            return []
        
        if direction not in self.timetables[route_num]:
            return []
        
        if current_time is None:
            current_time = datetime.now()
        
        timetable_df = self.timetables[route_num][direction]
        
        # Parse departure times
        departures = []
        for _, row in timetable_df.iterrows():
            start_time_str = row.get('StartTime', '')
            end_time_str = row.get('EndTime', '')
            
            if pd.isna(start_time_str) or start_time_str == '':
                continue
            
            try:
                # Parse start time
                start_time = datetime.strptime(start_time_str, '%H:%M').replace(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day
                )
                
                # Parse end time if available
                end_time = None
                if not pd.isna(end_time_str) and end_time_str != '':
                    end_time = datetime.strptime(end_time_str, '%H:%M').replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day
                    )
                
                # Only include future departures
                if start_time >= current_time:
                    departures.append({
                        'departure_time': start_time,
                        'arrival_time': end_time,
                        'route_num': route_num,
                        'direction': direction,
                        'route_var_id': row.get('RouteVarId'),
                        'timetable_id': row.get('TimeTableId'),
                        'trip_no': row.get('TripNo', '')
                    })
            
            except (ValueError, TypeError) as e:
                # Skip invalid time formats
                continue
        
        # Sort by departure time and limit
        departures.sort(key=lambda x: x['departure_time'])
        return departures[:limit]
    
    def get_upcoming_arrivals_at_stop(self, route_num: str, stop_id: int, 
                                      current_time: Optional[datetime] = None,
                                      limit: int = 10) -> List[Dict]:
        """
        Get upcoming bus arrivals at a specific stop for a given route
        
        Args:
            route_num: Route number
            stop_id: Stop ID
            current_time: Current time (uses now() if None)
            limit: Maximum number of arrivals to return
            
        Returns:
            List of arrival info dicts with estimated times
        """
        if current_time is None:
            current_time = datetime.now()
        
        results = []
        
        # Get metadata for running time
        metadata = self.get_route_metadata(route_num)
        if not metadata:
            return []
        
        # Check both directions
        for direction in ['outbound', 'inbound']:
            # Get stops for this direction
            if route_num not in self.route_stops:
                continue
            
            stops = self.route_stops[route_num].get(direction, [])
            
            # Find the stop in the route
            stop_sequence = None
            total_stops = len(stops)
            
            for seq, stop in enumerate(stops):
                if stop.get('stop_id') == stop_id:
                    stop_sequence = seq
                    break
            
            if stop_sequence is None:
                continue
            
            # Get upcoming departures from origin
            departures = self.get_upcoming_departures(route_num, direction, current_time, limit * 2)
            
            # Calculate arrival time at this stop
            # Find matching metadata for this direction
            dir_metadata = None
            for meta in metadata:
                meta_direction = 'outbound' if meta.get('RouteVarId') == 1 else 'inbound'
                if meta_direction == direction:
                    dir_metadata = meta
                    break
            
            if not dir_metadata:
                continue
            
            # Extract running time (total trip time in minutes)
            running_time_str = dir_metadata.get('RunningTime', '35')
            try:
                total_running_time = int(running_time_str)
            except (ValueError, TypeError):
                total_running_time = 35  # Default
            
            # Estimate time to reach this stop (proportional to stop sequence)
            if total_stops > 0:
                time_to_stop = (stop_sequence / total_stops) * total_running_time
            else:
                time_to_stop = 0
            
            # Calculate arrivals at this stop
            for dep in departures:
                arrival_at_stop = dep['departure_time'] + timedelta(minutes=time_to_stop)
                
                # Only include future arrivals
                if arrival_at_stop >= current_time:
                    results.append({
                        'route_num': route_num,
                        'direction': direction,
                        'departure_from_origin': dep['departure_time'],
                        'arrival_at_stop': arrival_at_stop,
                        'minutes_until_arrival': int((arrival_at_stop - current_time).total_seconds() / 60),
                        'stop_sequence': stop_sequence,
                        'total_stops': total_stops,
                        'headsign': dir_metadata.get('EndStop', ''),
                        'running_time_minutes': total_running_time
                    })
        
        # Sort by arrival time and limit
        results.sort(key=lambda x: x['arrival_at_stop'])
        return results[:limit]
    
    def get_all_upcoming_arrivals_at_stop(self, stop_id: int, 
                                          current_time: Optional[datetime] = None,
                                          limit: int = 10) -> List[Dict]:
        """
        Get upcoming arrivals from ALL routes at a specific stop
        
        Args:
            stop_id: Stop ID
            current_time: Current time (uses now() if None)
            limit: Maximum number of arrivals to return
            
        Returns:
            List of arrival info dicts from all routes
        """
        all_arrivals = []
        
        # Query all loaded routes
        for route_num in self.timetables.keys():
            arrivals = self.get_upcoming_arrivals_at_stop(route_num, stop_id, current_time, limit)
            all_arrivals.extend(arrivals)
        
        # Sort by arrival time and limit
        all_arrivals.sort(key=lambda x: x['arrival_at_stop'])
        return all_arrivals[:limit]
    
    def calculate_trip_time(self, route_num: str, from_stop_id: int, to_stop_id: int,
                           current_time: Optional[datetime] = None) -> Optional[Dict]:
        """
        Calculate approximate trip time from one stop to another on the same route
        
        Args:
            route_num: Route number
            from_stop_id: Origin stop ID
            to_stop_id: Destination stop ID
            current_time: Current time (uses now() if None)
            
        Returns:
            Dict with trip details or None if not possible
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Get metadata
        metadata = self.get_route_metadata(route_num)
        if not metadata:
            return None
        
        # Check both directions
        for direction in ['outbound', 'inbound']:
            if route_num not in self.route_stops:
                continue
            
            stops = self.route_stops[route_num].get(direction, [])
            
            # Find both stops in the route
            from_sequence = None
            to_sequence = None
            
            for seq, stop in enumerate(stops):
                if stop.get('stop_id') == from_stop_id:
                    from_sequence = seq
                if stop.get('stop_id') == to_stop_id:
                    to_sequence = seq
            
            # Check if both stops found and in correct order
            if from_sequence is not None and to_sequence is not None and from_sequence < to_sequence:
                # Get upcoming arrivals at origin
                arrivals = self.get_upcoming_arrivals_at_stop(route_num, from_stop_id, current_time, 1)
                
                if not arrivals:
                    continue
                
                next_bus = arrivals[0]
                
                # Find metadata for this direction
                dir_metadata = None
                for meta in metadata:
                    meta_direction = 'outbound' if meta.get('RouteVarId') == 1 else 'inbound'
                    if meta_direction == direction:
                        dir_metadata = meta
                        break
                
                if not dir_metadata:
                    continue
                
                # Extract running time
                running_time_str = dir_metadata.get('RunningTime', '35')
                try:
                    total_running_time = int(running_time_str)
                except (ValueError, TypeError):
                    total_running_time = 35
                
                total_stops = len(stops)
                
                # Calculate times
                wait_time = next_bus['minutes_until_arrival']
                
                # Travel time is proportional to stops traveled
                stops_traveled = to_sequence - from_sequence
                if total_stops > 0:
                    travel_time = (stops_traveled / total_stops) * total_running_time
                else:
                    travel_time = 0
                
                total_time = wait_time + travel_time
                
                # Estimated arrival at destination
                arrival_at_destination = next_bus['arrival_at_stop'] + timedelta(minutes=travel_time)
                
                return {
                    'route_num': route_num,
                    'direction': direction,
                    'from_stop_id': from_stop_id,
                    'to_stop_id': to_stop_id,
                    'next_bus_arrival_at_origin': next_bus['arrival_at_stop'],
                    'wait_time_minutes': wait_time,
                    'travel_time_minutes': int(travel_time),
                    'total_time_minutes': int(total_time),
                    'estimated_arrival': arrival_at_destination,
                    'stops_traveled': stops_traveled,
                    'headsign': dir_metadata.get('EndStop', '')
                }
        
        return None
    
    def calculate_multi_segment_trip_time(self, segments: List[Dict],
                                         current_time: Optional[datetime] = None) -> Dict:
        """
        Calculate total trip time for a journey with multiple segments (transfers)
        
        Args:
            segments: List of segment dicts with:
                - route_num: Route number
                - from_stop_id: Origin stop ID
                - to_stop_id: Destination stop ID
                - transfer_walk_time: Walking time to next segment (minutes)
            current_time: Current time (uses now() if None)
            
        Returns:
            Dict with total trip details
        """
        if current_time is None:
            current_time = datetime.now()
        
        total_wait_time = 0
        total_travel_time = 0
        total_walk_time = 0
        segment_details = []
        
        arrival_time = current_time
        
        for i, segment in enumerate(segments):
            # Calculate trip time for this segment
            trip = self.calculate_trip_time(
                segment['route_num'],
                segment['from_stop_id'],
                segment['to_stop_id'],
                arrival_time
            )
            
            if not trip:
                return {
                    'success': False,
                    'error': f'Cannot calculate segment {i+1}',
                    'segments': segment_details
                }
            
            total_wait_time += trip['wait_time_minutes']
            total_travel_time += trip['travel_time_minutes']
            
            # Add walking time to next segment
            walk_time = segment.get('transfer_walk_time', 0)
            total_walk_time += walk_time
            
            # Update arrival time for next segment
            arrival_time = trip['estimated_arrival'] + timedelta(minutes=walk_time)
            
            segment_details.append({
                'segment_number': i + 1,
                'route_num': trip['route_num'],
                'direction': trip['direction'],
                'from_stop_id': trip['from_stop_id'],
                'to_stop_id': trip['to_stop_id'],
                'wait_time_minutes': trip['wait_time_minutes'],
                'travel_time_minutes': trip['travel_time_minutes'],
                'transfer_walk_time_minutes': walk_time,
                'departure_time': trip['next_bus_arrival_at_origin'],
                'arrival_time': trip['estimated_arrival'],
                'headsign': trip['headsign']
            })
        
        total_time = total_wait_time + total_travel_time + total_walk_time
        
        return {
            'success': True,
            'current_time': current_time,
            'estimated_arrival': arrival_time,
            'total_time_minutes': int(total_time),
            'total_wait_time_minutes': int(total_wait_time),
            'total_travel_time_minutes': int(total_travel_time),
            'total_walk_time_minutes': int(total_walk_time),
            'number_of_segments': len(segments),
            'segments': segment_details
        }
    
    def get_available_routes(self) -> List[str]:
        """Get list of all available route numbers"""
        return list(self.timetables.keys())


# Global instance
_timetable_manager = None


def get_timetable_manager(base_path: Path = None) -> TimetableManager:
    """
    Get or create global TimetableManager instance
    
    Args:
        base_path: Path to Bus_route_data directory
        
    Returns:
        TimetableManager instance
    """
    global _timetable_manager
    
    if _timetable_manager is None:
        if base_path is None:
            from config import config
            base_path = config.bus_data_path
        
        _timetable_manager = TimetableManager(base_path)
    
    return _timetable_manager


if __name__ == '__main__':
    # Test the timetable loader
    from config import config
    
    tm = TimetableManager(config.bus_data_path)
    
    print(f"Loaded {len(tm.get_available_routes())} routes")
    print(f"Available routes: {', '.join(sorted(tm.get_available_routes(), key=lambda x: int(x) if x.isdigit() else 999))}")
    
    # Test route 1
    if '1' in tm.get_available_routes():
        print("\n" + "="*80)
        print("Testing Route 1:")
        
        metadata = tm.get_route_metadata('1')
        if metadata:
            for meta in metadata:
                print(f"\nDirection: {meta.get('RouteVarShortName')}")
                print(f"  Running Time: {meta.get('RunningTime')} minutes")
                print(f"  Headway: {meta.get('Headway')} minutes")
                print(f"  Operation Time: {meta.get('OperationTime')}")
        
        # Get upcoming departures
        print("\nUpcoming Departures (Outbound):")
        departures = tm.get_upcoming_departures('1', 'outbound', limit=5)
        for dep in departures:
            print(f"  {dep['departure_time'].strftime('%H:%M')} -> {dep['arrival_time'].strftime('%H:%M') if dep['arrival_time'] else 'N/A'}")
        
        # Test arrivals at a specific stop (stop 33 - Công Trường Mê Linh)
        print("\nUpcoming Arrivals at Stop 33 (Route 1):")
        arrivals = tm.get_upcoming_arrivals_at_stop('1', 33, limit=5)
        for arr in arrivals:
            print(f"  {arr['arrival_at_stop'].strftime('%H:%M')} - {arr['direction']} to {arr['headsign']} (in {arr['minutes_until_arrival']} min)")
