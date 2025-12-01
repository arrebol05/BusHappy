"""
Query Tool for Bus Arrival Data

Provides simple functions to query bus arrivals using timetable data.

Usage:
    python query_arrivals.py --route 1 --stop 33
    python query_arrivals.py --route 1 --summary
    python query_arrivals.py --list-routes
    python query_arrivals.py --route 1 --stop 33 --predict
"""

import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime, timedelta
from timetable_loader import get_timetable_manager
from config import config


class ArrivalDataQuery:
    """Query interface for bus arrival data using timetables"""
    
    def __init__(self):
        """
        Initialize with timetable data
        """
        print(f"📂 Loading timetable data from {config.bus_data_path / 'HCMC_bus_routes'}...")
        
        self.tm = get_timetable_manager(config.bus_data_path)
        
        available_routes = self.tm.get_available_routes()
        
        print(f"✓ Loaded {len(available_routes)} routes with timetable data")
        print(f"  Routes: {', '.join(sorted(available_routes, key=lambda x: int(x) if x.isdigit() else 999)[:10])}...")
    
    def list_routes(self):
        """List all available routes with timetable info"""
        print("\n" + "=" * 80)
        print("AVAILABLE ROUTES")
        print("=" * 80)
        
        routes = sorted(self.tm.get_available_routes(), key=lambda x: int(x) if x.isdigit() else 999)
        
        for route_num in routes:
            metadata = self.tm.get_route_metadata(route_num)
            if metadata:
                print(f"\nRoute {route_num}:")
                for meta in metadata:
                    direction = meta.get('RouteVarShortName', 'Unknown')
                    running_time = meta.get('RunningTime', 'N/A')
                    headway = meta.get('Headway', 'N/A')
                    operation_time = meta.get('OperationTime', 'N/A')
                    
                    print(f"  {direction}:")
                    print(f"    Running Time: {running_time} min | Headway: {headway} min | Hours: {operation_time}")
        
        print(f"\nTotal: {len(routes)} routes")
    
    def list_stops(self, route_num: str = None):
        """List stops for a route"""
        if not route_num:
            print("⚠️  Please specify a route number with --route")
            return
        
        print("\n" + "=" * 80)
        print(f"STOPS FOR ROUTE {route_num}")
        print("=" * 80)
        
        if route_num not in self.tm.route_stops:
            print(f"❌ Route {route_num} not found")
            return
        
        route_stops = self.tm.route_stops[route_num]
        
        for direction in ['outbound', 'inbound']:
            if direction in route_stops and route_stops[direction]:
                print(f"\n{direction.upper()}:")
                for i, stop in enumerate(route_stops[direction], 1):
                    print(f"  {i}. Stop {stop.get('stop_id', 'N/A')} - {stop.get('name', 'Unknown')} ({stop.get('code', 'N/A')})")
    
    def route_summary(self, route_num: str):
        """Get detailed summary for a specific route"""
        metadata = self.tm.get_route_metadata(route_num)
        
        if not metadata:
            print(f"❌ No data found for route {route_num}")
            return
        
        print("\n" + "=" * 80)
        print(f"ROUTE {route_num} SUMMARY")
        print("=" * 80)
        
        for meta in metadata:
            direction = meta.get('RouteVarShortName', 'Unknown')
            print(f"\n{direction}:")
            print(f"  Start: {meta.get('StartStop', 'N/A')}")
            print(f"  End: {meta.get('EndStop', 'N/A')}")
            print(f"  Running Time: {meta.get('RunningTime', 'N/A')} minutes")
            print(f"  Headway: {meta.get('Headway', 'N/A')} minutes")
            print(f"  Total Trips: {meta.get('TotalTrip', 'N/A')}")
            print(f"  Operation Time: {meta.get('OperationTime', 'N/A')}")
            print(f"  Apply Dates: {meta.get('ApplyDates', 'N/A')}")
        
        # Show stops count
        if route_num in self.tm.route_stops:
            route_stops = self.tm.route_stops[route_num]
            outbound_count = len(route_stops.get('outbound', []))
            inbound_count = len(route_stops.get('inbound', []))
            print(f"\nStops:")
            print(f"  Outbound: {outbound_count} stops")
            print(f"  Inbound: {inbound_count} stops")
    
    def stop_schedule(self, route_num: str, stop_id: int):
        """Get schedule for a route at a specific stop"""
        arrivals = self.tm.get_upcoming_arrivals_at_stop(route_num, stop_id, limit=20)
        
        if not arrivals:
            print(f"❌ No arrivals found for Route {route_num} at Stop {stop_id}")
            return
        
        # Get stop name from route stops
        stop_name = "Unknown"
        if route_num in self.tm.route_stops:
            for direction in ['outbound', 'inbound']:
                for stop in self.tm.route_stops[route_num].get(direction, []):
                    if stop.get('stop_id') == stop_id:
                        stop_name = stop.get('name', 'Unknown')
                        break
        
        print("\n" + "=" * 80)
        print(f"SCHEDULE: Route {route_num} at Stop {stop_id} ({stop_name})")
        print("=" * 80)
        
        print(f"\nUpcoming Arrivals:")
        for arr in arrivals:
            time_str = arr['arrival_at_stop'].strftime('%H:%M')
            mins = arr['minutes_until_arrival']
            direction = arr['direction']
            headsign = arr['headsign']
            
            print(f"  {time_str} ({mins:3d} min) - {direction:8s} to {headsign}")
    
    def predict_next_arrival(self, route_num: str, stop_id: int):
        """Predict next bus arrival based on timetable"""
        now = datetime.now()
        
        arrivals = self.tm.get_upcoming_arrivals_at_stop(route_num, stop_id, current_time=now, limit=5)
        
        if not arrivals:
            print(f"❌ No upcoming arrivals for Route {route_num} at Stop {stop_id}")
            return
        
        # Get stop name
        stop_name = "Unknown"
        if route_num in self.tm.route_stops:
            for direction in ['outbound', 'inbound']:
                for stop in self.tm.route_stops[route_num].get(direction, []):
                    if stop.get('stop_id') == stop_id:
                        stop_name = stop.get('name', 'Unknown')
                        break
        
        print("\n" + "=" * 80)
        print(f"NEXT BUS PREDICTION")
        print("==" * 80)
        print(f"Route: {route_num}")
        print(f"Stop: {stop_id} ({stop_name})")
        print(f"Current Time: {now.strftime('%H:%M:%S')}")
        
        next_arrival = arrivals[0]
        
        print(f"\n✓ Next bus: {next_arrival['arrival_at_stop'].strftime('%H:%M')}")
        print(f"  Direction: {next_arrival['direction']} to {next_arrival['headsign']}")
        print(f"  Approximately {next_arrival['minutes_until_arrival']} minutes away")
        
        if len(arrivals) > 1:
            print(f"\nFollowing buses:")
            for arr in arrivals[1:]:
                print(f"  {arr['arrival_at_stop'].strftime('%H:%M')} - {arr['direction']} to {arr['headsign']} (in {arr['minutes_until_arrival']} min)")


def main():
    parser = argparse.ArgumentParser(description='Query bus arrival data using timetables')
    
    parser.add_argument('--list-routes', action='store_true', help='List all routes')
    parser.add_argument('--list-stops', action='store_true', help='List stops for a route')
    parser.add_argument('--route', type=str, help='Route number')
    parser.add_argument('--stop', type=int, help='Stop ID')
    parser.add_argument('--summary', action='store_true', help='Show route summary')
    parser.add_argument('--schedule', action='store_true', help='Show stop schedule')
    parser.add_argument('--predict', action='store_true', help='Predict next arrival')
    
    args = parser.parse_args()
    
    try:
        query = ArrivalDataQuery()
    except Exception as e:
        print(f"\n❌ {e}")
        return 1
    
    if args.list_routes:
        query.list_routes()
    
    elif args.list_stops:
        query.list_stops(route_num=args.route)
    
    elif args.route and args.summary:
        query.route_summary(args.route)
    
    elif args.route and args.stop and args.schedule:
        query.stop_schedule(args.route, args.stop)
    
    elif args.route and args.stop and args.predict:
        query.predict_next_arrival(args.route, args.stop)
    
    else:
        print("\n⚠️  No action specified. Use --help to see options.")
        print("\nQuick examples:")
        print("  python query_arrivals.py --list-routes")
        print("  python query_arrivals.py --route 1 --summary")
        print("  python query_arrivals.py --route 1 --list-stops")
        print("  python query_arrivals.py --route 1 --stop 33 --schedule")
        print("  python query_arrivals.py --route 1 --stop 33 --predict")
    
    return 0


if __name__ == '__main__':
    exit(main())
