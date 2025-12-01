"""
Script to crawl bus timetable data from official HCMC bus API
API discovered from: http://buyttphcm.com.vn/en-us/RouteDetail?rId=1&sP=Route
API endpoint: http://apicms.ebms.vn/businfo/gettimetablebyroute/{route_id}
"""

import requests
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
import json


class BusTimetableCrawler:
    def __init__(self, base_dir='Bus_route_data/HCMC_bus_routes'):
        self.api_base_url = 'http://apicms.ebms.vn'
        self.base_dir = Path(base_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
        })
    
    def get_timetable_data(self, route_id):
        """Fetch timetable data from API"""
        url = f"{self.api_base_url}/businfo/gettimetablebyroute/{route_id}"
        
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data if data else []
        except requests.RequestException as e:
            print(f"Error fetching route {route_id}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON for route {route_id}: {e}")
            return []
    
    def get_trips_data(self, route_id, timetable_id):
        """Fetch detailed trip times from API"""
        url = f"{self.api_base_url}/businfo/gettripsbytimetable/{route_id}/{timetable_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data if data else []
        except requests.RequestException as e:
            print(f"Error fetching trips for timetable {timetable_id}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON for trips {timetable_id}: {e}")
            return []
    
    def process_timetable(self, route_id):
        """Process timetable data and organize by direction"""
        timetable_data = self.get_timetable_data(route_id)
        
        if not timetable_data:
            print(f"No timetable data found for route {route_id}")
            return {'outbound': [], 'inbound': []}
        
        # Group by direction
        # The API returns timetable objects with properties like:
        # RouteId, RouteVarId, RouteVarName, TimeTableId, DayOfWeek, etc.
        
        outbound_data = []
        inbound_data = []
        
        for timetable in timetable_data:
            # Get detailed trip information
            timetable_id = timetable.get('TimeTableId')
            route_var_name = timetable.get('RouteVarName', '')
            
            print(f"  Processing: {route_var_name} (TimeTableId: {timetable_id})")
            
            # Get trips for this timetable
            trips = self.get_trips_data(route_id, timetable_id)
            
            # Add timetable metadata to each trip
            for trip in trips:
                trip_data = {
                    'RouteVarId': timetable.get('RouteVarId'),
                    'RouteVarName': route_var_name,
                    'TimeTableId': timetable_id,
                    'DayOfWeek': timetable.get('DayOfWeek'),
                    'EffectiveDate': timetable.get('EffectiveDate'),
                    'StartTime': trip.get('StartTime'),
                    'EndTime': trip.get('EndTime'),
                    'TripNo': trip.get('TripNo'),
                    'Note': trip.get('Note', ''),
                }
                
                # Determine direction based on RouteVarId
                # Typically, RouteVarId ending in 0 or 1 is outbound, 2 or 3 is inbound
                # Or we can use the first/second appearance pattern
                route_var_id = timetable.get('RouteVarId', 0)
                
                # Simple heuristic: lower RouteVarId is usually outbound
                if not outbound_data or (outbound_data and outbound_data[0]['RouteVarId'] == route_var_id):
                    outbound_data.append(trip_data)
                else:
                    inbound_data.append(trip_data)
            
            # Small delay between requests
            time.sleep(0.3)
        
        # If we only got one direction, try to split based on RouteVarId
        if outbound_data and not inbound_data:
            unique_var_ids = list(set([d['RouteVarId'] for d in outbound_data]))
            if len(unique_var_ids) > 1:
                # Split into two directions
                first_var_id = min(unique_var_ids)
                inbound_data = [d for d in outbound_data if d['RouteVarId'] != first_var_id]
                outbound_data = [d for d in outbound_data if d['RouteVarId'] == first_var_id]
        
        return {'outbound': outbound_data, 'inbound': inbound_data}
    
    def save_timetable(self, route_id, direction, data):
        """Save timetable data to CSV"""
        if not data or len(data) == 0:
            print(f"No data to save for route {route_id} {direction}")
            return False
        
        route_dir = self.base_dir / str(route_id)
        route_dir.mkdir(parents=True, exist_ok=True)
        
        filename = route_dir / f'timetable_{direction}.csv'
        
        try:
            df = pd.DataFrame(data)
            
            # Sort by StartTime for better readability
            if 'StartTime' in df.columns:
                df = df.sort_values('StartTime')
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✓ Saved {filename} ({len(data)} trips)")
            return True
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return False
    
    def save_raw_json(self, route_id, data):
        """Save raw API response as JSON for reference"""
        route_dir = self.base_dir / str(route_id)
        route_dir.mkdir(parents=True, exist_ok=True)
        
        filename = route_dir / 'timetable_raw.json'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved raw data to {filename}")
            return True
        except Exception as e:
            print(f"Error saving raw JSON: {e}")
            return False
    
    def crawl_route(self, route_id):
        """Crawl timetable for a single route"""
        print(f"\n{'='*60}")
        print(f"Crawling route {route_id}...")
        print(f"{'='*60}")
        
        # Get raw timetable data
        raw_data = self.get_timetable_data(route_id)
        if raw_data:
            self.save_raw_json(route_id, raw_data)
        
        # Process and organize timetable
        timetables = self.process_timetable(route_id)
        
        success = False
        for direction, data in timetables.items():
            if data:
                if self.save_timetable(route_id, direction, data):
                    success = True
            else:
                print(f"No {direction} timetable found for route {route_id}")
        
        return success
    
    def get_existing_routes(self):
        """Get list of route IDs from existing directory structure"""
        routes = []
        if self.base_dir.exists():
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    try:
                        route_id = int(item.name)
                        routes.append(route_id)
                    except ValueError:
                        pass
        return sorted(routes)
    
    def crawl_all_routes(self, route_ids=None, delay=1):
        """Crawl timetables for all routes"""
        if route_ids is None:
            route_ids = self.get_existing_routes()
        
        if not route_ids:
            print("No routes found. Please provide route IDs.")
            return
        
        print(f"Found {len(route_ids)} routes to crawl: {route_ids}")
        
        success_count = 0
        failed_routes = []
        
        for idx, route_id in enumerate(route_ids, 1):
            try:
                print(f"\n[{idx}/{len(route_ids)}] ", end='')
                if self.crawl_route(route_id):
                    success_count += 1
                else:
                    failed_routes.append(route_id)
                
                # Be polite to the server
                if idx < len(route_ids):
                    time.sleep(delay)
            except Exception as e:
                print(f"Unexpected error crawling route {route_id}: {e}")
                import traceback
                traceback.print_exc()
                failed_routes.append(route_id)
        
        print(f"\n{'='*60}")
        print(f"Crawling complete!")
        print(f"Success: {success_count}/{len(route_ids)}")
        if failed_routes:
            print(f"Failed routes: {failed_routes}")
        print(f"{'='*60}")


def main():
    crawler = BusTimetableCrawler()
    
    # Option 1: Crawl all existing routes
    crawler.crawl_all_routes()
    
    # Option 2: Crawl specific routes
    # crawler.crawl_all_routes(route_ids=[1, 4, 6, 9, 20])
    
    # Option 3: Crawl a single route for testing
    # crawler.crawl_route(1)


if __name__ == '__main__':
    main()
