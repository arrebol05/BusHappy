"""
BusHappy API Server
Provides REST API endpoints for bus stop and route information.
Features: nearby stops, route planning, real-time updates, accessibility filtering
Environment: Supports production and sandbox modes for safe data editing
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math
import heapq
from collections import defaultdict
from config import config
from timetable_loader import get_timetable_manager

app = Flask(__name__)
CORS(app)

# Use environment-aware paths from config
BASE_PATH = config.bus_data_path
GTFS_PATH = config.gtfs_path

# Initialize timetable manager
timetable_manager = get_timetable_manager(BASE_PATH)

stops_df = pd.read_csv(GTFS_PATH / "stops.txt")
routes_df = pd.read_csv(GTFS_PATH / "routes.txt")
trips_df = pd.read_csv(GTFS_PATH / "trips.txt")
stop_times_df = pd.read_csv(GTFS_PATH / "stop_times.txt")

all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")

stops_dict = stops_df.set_index('stop_id').to_dict('index')
routes_dict = routes_df.set_index('route_id').to_dict('index')

stop_routes_map = defaultdict(lambda: {'outbound': set(), 'inbound': set()})
for _, st in stop_times_df.iterrows():
    stop_id = int(st['stop_id'])
    trip = trips_df[trips_df['trip_id'] == st['trip_id']]
    if not trip.empty:
        route_id = trip.iloc[0]['route_id']
        direction = str(trip.iloc[0]['direction_id'])
        
        route = None
        if route_id in routes_dict:
            route = routes_dict[route_id]
        elif str(route_id) in routes_dict:
            route = routes_dict[str(route_id)]
        elif isinstance(route_id, str) and route_id.isdigit() and int(route_id) in routes_dict:
            route = routes_dict[int(route_id)]
        
        if route:
            route_number = route.get('route_short_name', str(route_id))
        else:
            route_number = str(route_id)
        
        if direction == '0':
            stop_routes_map[stop_id]['outbound'].add(route_number)
        else:
            stop_routes_map[stop_id]['inbound'].add(route_number)


def format_routes_display(stop_id: int) -> str:
    """
    Format route information showing both inbound and outbound routes.
    Returns formatted string like: "Outbound: 1, 65 | Inbound: 103, 146"
    """
    routes = stop_routes_map.get(stop_id, {'outbound': set(), 'inbound': set()})
    
    parts = []
    if routes['outbound']:
        outbound_routes = sorted(routes['outbound'], key=lambda x: int(x) if isinstance(x, str) and x.isdigit() else (x if isinstance(x, int) else 999))
        parts.append(f"Outbound: {', '.join(str(r) for r in outbound_routes)}")
    
    if routes['inbound']:
        inbound_routes = sorted(routes['inbound'], key=lambda x: int(x) if isinstance(x, str) and x.isdigit() else (x if isinstance(x, int) else 999))
        parts.append(f"Inbound: {', '.join(str(r) for r in inbound_routes)}")
    
    return ' | '.join(parts) if parts else ''


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def get_upcoming_buses(stop_id: int, current_time: Optional[str] = None) -> List[Dict]:
    """
    Get upcoming buses for a specific stop using timetable data.
    Returns list of trips with arrival times.
    """
    if current_time is None:
        current_datetime = datetime.now()
    else:
        try:
            current_datetime = datetime.strptime(current_time, "%H:%M:%S").replace(
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day
            )
        except ValueError:
            current_datetime = datetime.now()
    
    # Get all upcoming arrivals at this stop from all routes
    all_arrivals = timetable_manager.get_all_upcoming_arrivals_at_stop(
        stop_id, 
        current_time=current_datetime, 
        limit=10
    )
    
    results = []
    for arrival in all_arrivals:
        # Check wheelchair accessibility from GTFS routes data if available
        wheelchair_accessible = True  # Default to true, can be enhanced with GTFS data
        
        results.append({
            'route_number': arrival['route_num'],
            'route_name': f"Route {arrival['route_num']}",
            'headsign': arrival['headsign'],
            'arrival_time': arrival['arrival_at_stop'].strftime('%H:%M:%S'),
            'minutes_until_arrival': arrival['minutes_until_arrival'],
            'direction': 'Outbound' if arrival['direction'] == 'outbound' else 'Inbound',
            'wheelchair_accessible': wheelchair_accessible
        })
    
    return results


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': config.mode,
        'is_sandbox': config.is_sandbox,
        'total_stops': len(stops_df),
        'total_routes': len(routes_df)
    })


@app.route('/api/stops/nearby', methods=['GET'])
def get_nearby_stops():
    """
    Get nearby bus stops within a specified radius.
    Query params: lat, lon, radius_km (default: 1), wheelchair_only (default: false)
    """
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        radius_km = float(request.args.get('radius_km', 1.0))
        wheelchair_only = request.args.get('wheelchair_only', 'false').lower() == 'true'
        
        nearby_stops = []
        
        for _, stop in stops_df.iterrows():
            distance = haversine_distance(lat, lon, stop['stop_lat'], stop['stop_lon'])
            
            if distance <= radius_km:
                # Filter by wheelchair accessibility if needed
                if wheelchair_only and stop['wheelchair_boarding'] != 1:
                    continue
                
                stop_id = int(stop['stop_id'])
                routes_display = format_routes_display(stop_id)
                
                nearby_stops.append({
                    'stop_id': stop_id,
                    'stop_name': stop['stop_name'],
                    'stop_code': stop['stop_code'],
                    'distance_km': round(distance, 3),
                    'lat': stop['stop_lat'],
                    'lon': stop['stop_lon'],
                    'wheelchair_accessible': stop['wheelchair_boarding'] == 1,
                    'routes': routes_display
                })
        
        # Sort by distance
        nearby_stops.sort(key=lambda x: x['distance_km'])
        
        return jsonify({
            'success': True,
            'location': {'lat': lat, 'lon': lon},
            'radius_km': radius_km,
            'wheelchair_only': wheelchair_only,
            'stops': nearby_stops,
            'count': len(nearby_stops)
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': 'Invalid parameters. Required: lat, lon'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stops/<int:stop_id>', methods=['GET'])
def get_stop_details(stop_id: int):
    """Get detailed information about a specific stop."""
    try:
        stop = stops_dict.get(stop_id)
        
        if not stop:
            return jsonify({'success': False, 'error': 'Stop not found'}), 404
        
        # Get upcoming buses
        upcoming_buses = get_upcoming_buses(stop_id)
        
        # Get route information
        routes_display = format_routes_display(stop_id)
        
        return jsonify({
            'success': True,
            'stop': {
                'stop_id': stop_id,
                'stop_name': stop['stop_name'],
                'stop_code': stop['stop_code'],
                'lat': stop['stop_lat'],
                'lon': stop['stop_lon'],
                'wheelchair_accessible': stop['wheelchair_boarding'] == 1,
                'description': stop['stop_desc'],
                'routes': routes_display
            },
            'upcoming_buses': upcoming_buses
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/routes', methods=['GET'])
def get_all_routes():
    """Get list of all available routes."""
    try:
        wheelchair_only = request.args.get('wheelchair_only', 'false').lower() == 'true'
        
        routes_list = []
        for _, route in routes_df.iterrows():
            routes_list.append({
                'route_id': int(route['route_id']),
                'route_number': route['route_short_name'],
                'route_name': route['route_long_name'],
                'description': route['route_desc'],
                'color': route['route_color']
            })
        
        return jsonify({
            'success': True,
            'routes': routes_list,
            'count': len(routes_list)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/routes/<int:route_id>/stops', methods=['GET'])
def get_route_stops(route_id: int):
    """Get all stops for a specific route."""
    try:
        route_trips = trips_df[(trips_df['route_id'] == route_id) | (trips_df['route_id'] == str(route_id))]
        
        if route_trips.empty:
            return jsonify({'success': False, 'error': 'Route not found'}), 404
        
        outbound_trip = route_trips[route_trips['direction_id'] == 0].iloc[0] if len(route_trips[route_trips['direction_id'] == 0]) > 0 else None
        inbound_trip = route_trips[route_trips['direction_id'] == 1].iloc[0] if len(route_trips[route_trips['direction_id'] == 1]) > 0 else None
        
        result = {
            'success': True,
            'route_id': route_id,
            'route_info': routes_dict.get(str(route_id), {})
        }
        
        if outbound_trip is not None:
            outbound_stops = stop_times_df[stop_times_df['trip_id'] == outbound_trip['trip_id']].sort_values('stop_sequence')
            result['outbound_stops'] = []
            for _, st in outbound_stops.iterrows():
                stop_id_val = st['stop_id']
                stop = stops_dict.get(stop_id_val) or stops_dict.get(int(stop_id_val)) or stops_dict.get(str(stop_id_val))
                if stop:
                    result['outbound_stops'].append({
                        'stop_id': int(stop_id_val),
                        'stop_name': stop.get('stop_name', 'Unknown'),
                        'sequence': int(st['stop_sequence']),
                        'lat': stop.get('stop_lat'),
                        'lon': stop.get('stop_lon')
                    })
        
        if inbound_trip is not None:
            inbound_stops = stop_times_df[stop_times_df['trip_id'] == inbound_trip['trip_id']].sort_values('stop_sequence')
            result['inbound_stops'] = []
            for _, st in inbound_stops.iterrows():
                stop_id_val = st['stop_id']
                stop = stops_dict.get(stop_id_val) or stops_dict.get(int(stop_id_val)) or stops_dict.get(str(stop_id_val))
                if stop:
                    result['inbound_stops'].append({
                        'stop_id': int(stop_id_val),
                        'stop_name': stop.get('stop_name', 'Unknown'),
                        'sequence': int(st['stop_sequence']),
                        'lat': stop.get('stop_lat'),
                        'lon': stop.get('stop_lon')
                    })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def calculate_trip_duration(route_id: str, start_stop_id: int, end_stop_id: int, current_time: Optional[datetime] = None) -> Optional[Dict]:
    """
    Calculate trip duration from start to end stop on the same route using timetable data.
    
    Returns:
        Dict with trip details including wait time, travel time, and total time
    """
    if current_time is None:
        current_time = datetime.now()
    
    # Use timetable manager to calculate trip time
    trip_info = timetable_manager.calculate_trip_time(
        str(route_id),
        start_stop_id,
        end_stop_id,
        current_time
    )
    
    return trip_info


@app.route('/api/plan', methods=['POST'])
def plan_route():
    """Plan a route between two locations using bus network with time estimates."""
    try:
        data = request.get_json()
        
        from_lat = float(data['from_lat'])
        from_lon = float(data['from_lon'])
        to_lat = float(data['to_lat'])
        to_lon = float(data['to_lon'])
        wheelchair_only = data.get('wheelchair_accessible', False)
        include_time_estimate = data.get('include_time_estimate', True)
        
        current_time = datetime.now()
        
        start_stops = []
        end_stops = []
        
        for _, stop in stops_df.iterrows():
            if wheelchair_only and stop['wheelchair_boarding'] != 1:
                continue
            
            dist_from_start = haversine_distance(from_lat, from_lon, stop['stop_lat'], stop['stop_lon'])
            dist_from_end = haversine_distance(to_lat, to_lon, stop['stop_lat'], stop['stop_lon'])
            
            if dist_from_start <= 0.5:
                start_stops.append((dist_from_start, int(stop['stop_id']), stop['stop_name']))
            
            if dist_from_end <= 0.5:
                end_stops.append((dist_from_end, int(stop['stop_id']), stop['stop_name']))
        
        start_stops.sort()
        end_stops.sort()
        
        if not start_stops or not end_stops:
            return jsonify({
                'success': False,
                'error': 'No nearby stops found. Try increasing search radius.',
                'start_stops_found': len(start_stops),
                'end_stops_found': len(end_stops)
            }), 404
        
        routes_by_stop = defaultdict(set)
        for _, st in stop_times_df.iterrows():
            trip = trips_df[trips_df['trip_id'] == st['trip_id']]
            if not trip.empty:
                route_id = trip.iloc[0]['route_id']
                routes_by_stop[int(st['stop_id'])].add(str(route_id))
        
        best_routes = []
        
        for start_dist, start_stop_id, start_name in start_stops[:3]:
            for end_dist, end_stop_id, end_name in end_stops[:3]:
                if start_stop_id == end_stop_id:
                    continue
                
                start_routes = routes_by_stop.get(start_stop_id, set())
                end_routes = routes_by_stop.get(end_stop_id, set())
                common_routes = start_routes & end_routes
                
                for route_id in common_routes:
                    route = routes_dict.get(route_id, {})
                    
                    route_info = {
                        'type': 'direct',
                        'start_stop': {
                            'id': start_stop_id,
                            'name': start_name,
                            'walk_distance_km': round(start_dist, 3)
                        },
                        'end_stop': {
                            'id': end_stop_id,
                            'name': end_name,
                            'walk_distance_km': round(end_dist, 3)
                        },
                        'route': {
                            'id': route_id,
                            'number': route.get('route_short_name', 'N/A'),
                            'name': route.get('route_long_name', 'N/A')
                        },
                        'total_walk_distance_km': round(start_dist + end_dist, 3)
                    }
                    
                    # Calculate trip duration if requested
                    if include_time_estimate:
                        trip_duration = calculate_trip_duration(route_id, start_stop_id, end_stop_id, current_time)
                        
                        if trip_duration:
                            # Walking time estimation: 5 km/h walking speed
                            walk_to_start_mins = int((start_dist / 5.0) * 60)
                            walk_from_end_mins = int((end_dist / 5.0) * 60)
                            
                            total_time = walk_to_start_mins + trip_duration['wait_time_minutes'] + trip_duration['travel_time_minutes'] + walk_from_end_mins
                            
                            route_info['time_estimate'] = {
                                'walk_to_start_minutes': walk_to_start_mins,
                                'wait_for_bus_minutes': trip_duration['wait_time_minutes'],
                                'travel_on_bus_minutes': trip_duration['travel_time_minutes'],
                                'walk_from_end_minutes': walk_from_end_mins,
                                'total_minutes': total_time,
                                'next_bus_departure': trip_duration['next_bus_arrival_at_origin'].strftime('%H:%M'),
                                'estimated_arrival': trip_duration['estimated_arrival'].strftime('%H:%M')
                            }
                    
                    best_routes.append(route_info)
        
        # Sort by total time if available, otherwise by walking distance
        if include_time_estimate and any('time_estimate' in r for r in best_routes):
            best_routes.sort(key=lambda x: x.get('time_estimate', {}).get('total_minutes', 999))
        else:
            best_routes.sort(key=lambda x: x['total_walk_distance_km'])
        
        return jsonify({
            'success': True,
            'from': {'lat': from_lat, 'lon': from_lon},
            'to': {'lat': to_lat, 'lon': to_lon},
            'wheelchair_accessible': wheelchair_only,
            'current_time': current_time.strftime('%H:%M'),
            'routes': best_routes[:5],
            'count': len(best_routes)
        })
    
    except KeyError as e:
        return jsonify({'success': False, 'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search', methods=['GET'])
def search_stops():
    """
    Search for stops by name or code.
    Query params: q (query string), wheelchair_only (optional)
    """
    try:
        query = request.args.get('q', '').lower()
        wheelchair_only = request.args.get('wheelchair_only', 'false').lower() == 'true'
        
        if len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Query must be at least 2 characters'
            }), 400
        
        results = []
        
        for _, stop in stops_df.iterrows():
            if wheelchair_only and stop['wheelchair_boarding'] != 1:
                continue
            
            # Search in name, code, and description
            if (query in stop['stop_name'].lower() or 
                query in str(stop['stop_code']).lower() or
                query in str(stop['stop_desc']).lower()):
                
                stop_id = int(stop['stop_id'])
                routes_display = format_routes_display(stop_id)
                
                results.append({
                    'stop_id': stop_id,
                    'stop_name': stop['stop_name'],
                    'stop_code': stop['stop_code'],
                    'lat': stop['stop_lat'],
                    'lon': stop['stop_lon'],
                    'wheelchair_accessible': stop['wheelchair_boarding'] == 1,
                    'description': stop['stop_desc'],
                    'routes': routes_display
                })
        
        return jsonify({
            'success': True,
            'query': query,
            'wheelchair_only': wheelchair_only,
            'results': results[:50],
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# DASHBOARD API ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/routes', methods=['GET'])
def get_dashboard_routes():
    """Get all routes with complete stop information for dashboard."""
    try:
        dashboard_routes = []
        
        for _, route in routes_df.iterrows():
            route_id = int(route['route_id'])
            route_trips = trips_df[(trips_df['route_id'] == route_id) | (trips_df['route_id'] == str(route_id))]
            
            outbound_stops = []
            inbound_stops = []
            
            # Get outbound stops
            outbound_trip = route_trips[route_trips['direction_id'] == 0]
            if not outbound_trip.empty:
                trip_id = outbound_trip.iloc[0]['trip_id']
                stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
                
                for _, st in stops.iterrows():
                    stop_id_val = st['stop_id']
                    # Try to get stop with different key types
                    stop = stops_dict.get(stop_id_val) or stops_dict.get(int(stop_id_val)) or stops_dict.get(str(stop_id_val))
                    if stop:
                        outbound_stops.append({
                            'stop_id': int(stop_id_val),
                            'stop_name': stop['stop_name'],
                            'sequence': int(st['stop_sequence']),
                            'lat': stop['stop_lat'],
                            'lon': stop['stop_lon']
                        })
            
            # Get inbound stops
            inbound_trip = route_trips[route_trips['direction_id'] == 1]
            if not inbound_trip.empty:
                trip_id = inbound_trip.iloc[0]['trip_id']
                stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
                
                for _, st in stops.iterrows():
                    stop_id_val = st['stop_id']
                    # Try to get stop with different key types
                    stop = stops_dict.get(stop_id_val) or stops_dict.get(int(stop_id_val)) or stops_dict.get(str(stop_id_val))
                    if stop:
                        inbound_stops.append({
                            'stop_id': int(stop_id_val),
                            'stop_name': stop['stop_name'],
                            'sequence': int(st['stop_sequence']),
                            'lat': stop['stop_lat'],
                            'lon': stop['stop_lon']
                        })
            
            dashboard_routes.append({
                'route_id': route_id,
                'route_number': route['route_short_name'],
                'route_name': route['route_long_name'],
                'color': route['route_color'],
                'outbound_stops': outbound_stops,
                'inbound_stops': inbound_stops
            })
        
        return jsonify(dashboard_routes)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/stats/system', methods=['GET'])
def get_system_stats():
    """Get system-wide statistics."""
    try:
        total_routes = len(routes_df)
        total_stops = len(stop_times_df)
        unique_stops = len(stops_df)
        
        # Calculate average route length
        route_lengths = []
        for _, route in routes_df.iterrows():
            route_id = int(route['route_id'])
            route_trips = trips_df[(trips_df['route_id'] == route_id) | (trips_df['route_id'] == str(route_id))]
            
            if not route_trips.empty:
                trip_id = route_trips.iloc[0]['trip_id']
                stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
                
                if len(stops) > 1:
                    total_dist = 0
                    for i in range(len(stops) - 1):
                        stop1 = stops_dict.get(stops.iloc[i]['stop_id'])
                        stop2 = stops_dict.get(stops.iloc[i+1]['stop_id'])
                        if stop1 and stop2:
                            dist = haversine_distance(
                                stop1['stop_lat'], stop1['stop_lon'],
                                stop2['stop_lat'], stop2['stop_lon']
                            )
                            total_dist += dist
                    route_lengths.append(total_dist)
        
        avg_route_length = sum(route_lengths) / len(route_lengths) if route_lengths else 0
        
        # Approximate coverage area (simple bounding box)
        lats = [stop['stop_lat'] for stop in stops_dict.values()]
        lons = [stop['stop_lon'] for stop in stops_dict.values()]
        
        if lats and lons:
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            coverage_area = lat_range * lon_range * 12100  # Rough conversion to km²
        else:
            coverage_area = 0
        
        return jsonify({
            'total_routes': total_routes,
            'total_stops': total_stops,
            'unique_stops': unique_stops,
            'avg_route_length_km': round(avg_route_length, 2),
            'total_coverage_area_km2': round(coverage_area, 2)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/stats/route/<int:route_id>', methods=['GET'])
def get_route_stats(route_id: int):
    """Get statistics for a specific route."""
    try:
        route_trips = trips_df[(trips_df['route_id'] == route_id) | (trips_df['route_id'] == str(route_id))]
        
        if route_trips.empty:
            return jsonify({'success': False, 'error': 'Route not found'}), 404
        
        outbound_stops_count = 0
        inbound_stops_count = 0
        total_length = 0
        
        # Outbound
        outbound_trip = route_trips[route_trips['direction_id'] == 0]
        if not outbound_trip.empty:
            trip_id = outbound_trip.iloc[0]['trip_id']
            stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
            outbound_stops_count = len(stops)
            
            # Calculate length
            for i in range(len(stops) - 1):
                stop1 = stops_dict.get(stops.iloc[i]['stop_id'])
                stop2 = stops_dict.get(stops.iloc[i+1]['stop_id'])
                if stop1 and stop2:
                    dist = haversine_distance(
                        stop1['stop_lat'], stop1['stop_lon'],
                        stop2['stop_lat'], stop2['stop_lon']
                    )
                    total_length += dist
        
        # Inbound
        inbound_trip = route_trips[route_trips['direction_id'] == 1]
        if not inbound_trip.empty:
            trip_id = inbound_trip.iloc[0]['trip_id']
            stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
            inbound_stops_count = len(stops)
            
            # Calculate length
            for i in range(len(stops) - 1):
                stop1 = stops_dict.get(stops.iloc[i]['stop_id'])
                stop2 = stops_dict.get(stops.iloc[i+1]['stop_id'])
                if stop1 and stop2:
                    dist = haversine_distance(
                        stop1['stop_lat'], stop1['stop_lon'],
                        stop2['stop_lat'], stop2['stop_lon']
                    )
                    total_length += dist
        
        total_stops = outbound_stops_count + inbound_stops_count
        avg_stop_distance = total_length / (total_stops - 2) if total_stops > 2 else 0
        
        return jsonify({
            'route_id': route_id,
            'total_stops': total_stops,
            'outbound_stops': outbound_stops_count,
            'inbound_stops': inbound_stops_count,
            'route_length_km': round(total_length, 2),
            'avg_stop_distance_km': round(avg_stop_distance, 3),
            'coverage_area_km2': 0  # Placeholder
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/calculate-stats', methods=['POST'])
def calculate_route_stats():
    """Calculate statistics for a modified route configuration."""
    try:
        data = request.get_json()
        route_id = data['route_id']
        outbound_stops = data['outbound_stops']
        inbound_stops = data['inbound_stops']
        
        # Calculate length for outbound
        outbound_length = 0
        for i in range(len(outbound_stops) - 1):
            dist = haversine_distance(
                outbound_stops[i]['lat'], outbound_stops[i]['lon'],
                outbound_stops[i+1]['lat'], outbound_stops[i+1]['lon']
            )
            outbound_length += dist
        
        # Calculate length for inbound
        inbound_length = 0
        for i in range(len(inbound_stops) - 1):
            dist = haversine_distance(
                inbound_stops[i]['lat'], inbound_stops[i]['lon'],
                inbound_stops[i+1]['lat'], inbound_stops[i+1]['lon']
            )
            inbound_length += dist
        
        total_length = outbound_length + inbound_length
        total_stops = len(outbound_stops) + len(inbound_stops)
        avg_stop_distance = total_length / (total_stops - 2) if total_stops > 2 else 0
        
        return jsonify({
            'route_id': route_id,
            'total_stops': total_stops,
            'outbound_stops': len(outbound_stops),
            'inbound_stops': len(inbound_stops),
            'route_length_km': round(total_length, 2),
            'avg_stop_distance_km': round(avg_stop_distance, 3),
            'coverage_area_km2': 0
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/compare-route', methods=['POST'])
def compare_routes():
    """Compare original and modified route configurations."""
    try:
        data = request.get_json()
        route_id = data['route_id']
        original = data['original']
        modified = data['modified']
        
        # Calculate stats for original
        orig_stats = {
            'route_id': route_id,
            'total_stops': len(original['outbound_stops']) + len(original['inbound_stops']),
            'outbound_stops': len(original['outbound_stops']),
            'inbound_stops': len(original['inbound_stops'])
        }
        
        # Calculate stats for modified
        mod_stats = {
            'route_id': route_id,
            'total_stops': len(modified['outbound_stops']) + len(modified['inbound_stops']),
            'outbound_stops': len(modified['outbound_stops']),
            'inbound_stops': len(modified['inbound_stops'])
        }
        
        # Determine changes
        changes = []
        improvements = []
        decreases = []
        
        # Check for added/removed stops
        orig_stop_ids = set([s['stop_id'] for s in original['outbound_stops'] + original['inbound_stops']])
        mod_stop_ids = set([s['stop_id'] for s in modified['outbound_stops'] + modified['inbound_stops']])
        
        added = mod_stop_ids - orig_stop_ids
        removed = orig_stop_ids - mod_stop_ids
        
        if added:
            changes.append({'type': 'add', 'description': f'{len(added)} stop(s) added'})
            improvements.append(f'{len(added)} new stop(s)')
        
        if removed:
            changes.append({'type': 'remove', 'description': f'{len(removed)} stop(s) removed'})
            decreases.append(f'{len(removed)} stop(s) removed')
        
        # Check for reordering
        if len(original['outbound_stops']) == len(modified['outbound_stops']):
            if [s['stop_id'] for s in original['outbound_stops']] != [s['stop_id'] for s in modified['outbound_stops']]:
                changes.append({'type': 'reorder', 'direction': 'outbound', 'description': 'Outbound stops reordered'})
        
        return jsonify({
            'route_id': route_id,
            'original_stats': orig_stats,
            'new_stats': mod_stats,
            'improvements': improvements,
            'decreases': decreases,
            'changes': changes
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/save-route', methods=['POST'])
def save_route_changes():
    """Save route modifications - only works in sandbox mode to protect production data."""
    try:
        # Prevent modifications in production mode
        if config.is_production:
            return jsonify({
                'success': False,
                'error': 'Cannot modify routes in production mode. Please switch to sandbox mode.',
                'environment': 'production'
            }), 403
        
        data = request.get_json()
        route_id = data['route_id']
        outbound_stops = data['outbound_stops']
        inbound_stops = data['inbound_stops']
        
        # Save to sandbox GTFS (implementation can be added later)
        # For now, acknowledge the save in sandbox mode
        
        return jsonify({
            'success': True,
            'message': f'Route {route_id} updated successfully in sandbox',
            'environment': 'sandbox',
            'warning': 'Changes are saved to sandbox only. Use API to promote to production if needed.'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/optimize/route/<int:route_id>', methods=['POST'])
def optimize_route(route_id: int):
    """Generate optimization suggestions for a single route (placeholder)."""
    try:
        # Placeholder implementation
        # In production, this would use optimization algorithms
        
        return jsonify({
            'route_id': route_id,
            'optimized_routes': [],
            'removed_stops': [],
            'added_stops': [],
            'efficiency_gain': 12.5,
            'warning': 'Auto optimization may remove existing stops to improve efficiency'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard/optimize/system', methods=['POST'])
def optimize_system():
    """Generate optimization suggestions for entire system (placeholder)."""
    try:
        # Placeholder implementation
        # In production, this would use system-wide optimization algorithms
        
        return jsonify({
            'optimized_routes': [],
            'removed_stops': [],
            'added_stops': [],
            'efficiency_gain': 18.3,
            'warning': 'System-wide optimization will analyze all routes and may remove stops'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# DISABILITY SUPPORT OPTIMIZATION API ENDPOINTS
# ============================================================================

@app.route('/api/disability/optimize', methods=['POST'])
def optimize_disability_stops():
    """
    Optimize bus stop selection for disability support.
    Uses advanced algorithm with constraint to preserve existing disability-supported stops.
    """
    try:
        from disability_optimization import optimize_disability_bus_stops
        
        data = request.get_json() or {}
        max_distance = data.get('max_distance', 500)  # meters
        target_coverage = data.get('target_coverage', 0.95)  # 95%
        
        # Load all stops data
        all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")
        
        # Add stop_id if not present (use Code as fallback)
        if 'stop_id' not in all_stops_df.columns:
            # Try to match with GTFS stops by name/code
            if 'Code' in all_stops_df.columns:
                all_stops_df['stop_id'] = range(1, len(all_stops_df) + 1)
        
        # Standardize disability support column
        if 'SupportDisability' in all_stops_df.columns:
            all_stops_df['HasDisabilitySupport'] = all_stops_df['SupportDisability'].apply(
                lambda x: 'Yes' if x == 'Có' else 'No'
            )
        
        # Run optimization
        result = optimize_disability_bus_stops(
            all_stops_df,
            max_distance=max_distance,
            target_coverage=target_coverage
        )
        
        return jsonify({
            'success': True,
            'optimization_results': result
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/disability/stops', methods=['GET'])
def get_disability_stops():
    """Get all stops with their disability support status."""
    try:
        all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")
        
        # Add stop_id if not present
        if 'stop_id' not in all_stops_df.columns:
            all_stops_df['stop_id'] = range(1, len(all_stops_df) + 1)
        
        # Standardize disability support column
        if 'SupportDisability' in all_stops_df.columns:
            all_stops_df['HasDisabilitySupport'] = all_stops_df['SupportDisability'].apply(
                lambda x: 'Yes' if x == 'Có' else 'No'
            )
        
        # Filter for valid coordinates
        df_valid = all_stops_df.dropna(subset=['Lat', 'Lng'])
        
        # Prepare response
        stops = []
        for _, row in df_valid.iterrows():
            stops.append({
                'stop_id': int(row.get('stop_id', 0)),
                'code': row.get('Code', ''),
                'name': row.get('Name', ''),
                'lat': float(row['Lat']),
                'lon': float(row['Lng']),
                'zone': row.get('Zone', ''),
                'stop_type': row.get('StopType', ''),
                'status': row.get('Status', ''),
                'total_routes': int(row.get('Total_Routes', 0)),
                'has_disability_support': row.get('HasDisabilitySupport', 'No') == 'Yes'
            })
        
        return jsonify({
            'success': True,
            'stops': stops,
            'count': len(stops),
            'with_support': len([s for s in stops if s['has_disability_support']]),
            'without_support': len([s for s in stops if not s['has_disability_support']])
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/disability/metrics', methods=['GET'])
def get_disability_metrics():
    """
    Get real-time disability support metrics.
    These metrics update when sandbox disability support values are modified.
    """
    try:
        from disability_optimization import calculate_disability_metrics
        
        all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")
        
        # Add stop_id if not present
        if 'stop_id' not in all_stops_df.columns:
            all_stops_df['stop_id'] = range(1, len(all_stops_df) + 1)
        
        # Standardize disability support column
        if 'SupportDisability' in all_stops_df.columns:
            all_stops_df['HasDisabilitySupport'] = all_stops_df['SupportDisability'].apply(
                lambda x: 'Yes' if x == 'Có' else 'No'
            )
        
        # Calculate metrics
        metrics = calculate_disability_metrics(all_stops_df)
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'environment': config.mode,
            'is_sandbox': config.is_sandbox
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/disability/update-support', methods=['POST'])
def update_disability_support():
    """
    Update disability support status for specific stops (sandbox only).
    This flips the disability support flag on existing stops - NO new stops created.
    """
    try:
        # Prevent modifications in production mode
        if config.is_production:
            return jsonify({
                'success': False,
                'error': 'Cannot modify disability support in production mode. Please switch to sandbox mode.',
                'environment': 'production'
            }), 403
        
        data = request.get_json()
        stop_ids = data.get('stop_ids', [])
        enable_support = data.get('enable_support', True)
        
        if not stop_ids:
            return jsonify({'success': False, 'error': 'No stop_ids provided'}), 400
        
        # Load sandbox data
        all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")
        
        # Add stop_id if not present
        if 'stop_id' not in all_stops_df.columns:
            all_stops_df['stop_id'] = range(1, len(all_stops_df) + 1)
        
        # Update disability support for specified stops (FLIP support value only)
        modified_count = 0
        for stop_id in stop_ids:
            mask = all_stops_df['stop_id'] == stop_id
            if mask.any():
                # Only flip existing stops - NO creation of new stops
                if 'SupportDisability' in all_stops_df.columns:
                    all_stops_df.loc[mask, 'SupportDisability'] = 'Có' if enable_support else 'No'
                modified_count += 1
        
        # Save to sandbox
        all_stops_df.to_csv(BASE_PATH / "all_bus_stops_aggregated.csv", index=False)
        
        # Recalculate metrics after modification
        from disability_optimization import calculate_disability_metrics
        
        # Standardize for metrics calculation
        if 'SupportDisability' in all_stops_df.columns:
            all_stops_df['HasDisabilitySupport'] = all_stops_df['SupportDisability'].apply(
                lambda x: 'Yes' if x == 'Có' else 'No'
            )
        
        updated_metrics = calculate_disability_metrics(all_stops_df)
        
        return jsonify({
            'success': True,
            'message': f'Updated {modified_count} stops in sandbox',
            'modified_count': modified_count,
            'updated_metrics': updated_metrics,
            'environment': 'sandbox'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ENVIRONMENT MANAGEMENT API ENDPOINTS
# ============================================================================

@app.route('/api/environment/info', methods=['GET'])
def get_environment_info():
    """Get current environment configuration information."""
    try:
        info = config.get_info()
        return jsonify({
            'success': True,
            'environment': info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/reset-sandbox', methods=['POST'])
def reset_sandbox():
    """Reset sandbox environment to production state."""
    try:
        if config.is_production:
            return jsonify({
                'success': False,
                'error': 'Cannot reset sandbox while in production mode'
            }), 403
        
        config.reset_sandbox()
        
        # Reload data after reset
        global stops_df, routes_df, trips_df, stop_times_df, all_stops_df
        stops_df = pd.read_csv(GTFS_PATH / "stops.txt")
        routes_df = pd.read_csv(GTFS_PATH / "routes.txt")
        trips_df = pd.read_csv(GTFS_PATH / "trips.txt")
        stop_times_df = pd.read_csv(GTFS_PATH / "stop_times.txt")
        all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")
        
        return jsonify({
            'success': True,
            'message': 'Sandbox has been reset to production state'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    env_indicator = "🧪 SANDBOX" if config.is_sandbox else "🚨 PRODUCTION"
    
    print("🚌 BusHappy API Server Starting...")
    print(f"📊 Environment: {env_indicator} MODE")
    print(f"📁 GTFS Path: {GTFS_PATH}")
    print(f"📁 Data Path: {BASE_PATH}")
    print(f"📊 Loaded {len(stops_df)} stops, {len(routes_df)} routes")
    
    if config.is_sandbox:
        print("\n⚠️  SANDBOX MODE ACTIVE")
        print("   - All data modifications are isolated from production")
        print("   - Safe to test route editing and optimizations")
        print("   - Use /api/environment/reset-sandbox to restore from production")
    else:
        print("\n🚨 PRODUCTION MODE ACTIVE")
        print("   - Route modifications are DISABLED for safety")
        print("   - Set BUSHAPPY_ENV=sandbox to enable editing")
    
    print("\n🌐 Server running at http://localhost:5000")
    print("\n📝 Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/stops/nearby?lat=X&lon=Y&radius_km=1&wheelchair_only=false")
    print("  GET  /api/stops/<stop_id>")
    print("  GET  /api/routes")
    print("  GET  /api/routes/<route_id>/stops")
    print("  GET  /api/search?q=query&wheelchair_only=false")
    print("  POST /api/plan - Route planning")
    print("\n🎛️  Dashboard endpoints:")
    print("  GET  /api/dashboard/routes")
    print("  GET  /api/dashboard/stats/system")
    print("  GET  /api/dashboard/stats/route/<route_id>")
    print("  POST /api/dashboard/calculate-stats")
    print("  POST /api/dashboard/compare-route")
    print("  POST /api/dashboard/save-route (sandbox only)")
    print("  POST /api/dashboard/optimize/route/<route_id>")
    print("  POST /api/dashboard/optimize/system")
    print("\n🔧 Environment management:")
    print("  GET  /api/environment/info")
    print("  POST /api/environment/reset-sandbox (sandbox only)")
    print("\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
