"""
Run timetable crawler for all bus routes
"""
import sys
sys.path.append('data_preprocessing')

from crawl_timetable import BusTimetableCrawler

def main():
    print("="*70)
    print("HCMC Bus Route Timetable Crawler")
    print("="*70)
    print("\nThis script will crawl timetable data for all routes from:")
    print("API: http://apicms.ebms.vn/businfo/")
    print("\nData will be saved to: Bus_route_data/HCMC_bus_routes/{route_id}/")
    print("Files created:")
    print("  - timetable_outbound.csv (outbound direction)")
    print("  - timetable_inbound.csv (inbound direction)")
    print("  - timetable_raw.json (raw API response)")
    print("\n" + "="*70)
    
    crawler = BusTimetableCrawler()
    
    # Get all existing routes
    routes = crawler.get_existing_routes()
    
    if not routes:
        print("\nNo routes found in Bus_route_data/HCMC_bus_routes/")
        print("Please ensure the route directories exist.")
        return
    
    print(f"\nReady to crawl {len(routes)} routes: {routes}")
    
    # Uncomment to add confirmation prompt
    # response = input("\nProceed? (y/n): ")
    # if response.lower() != 'y':
    #     print("Cancelled.")
    #     return
    
    print("\nStarting crawl...\n")
    crawler.crawl_all_routes(delay=1)
    
    print("\nDone!")

if __name__ == '__main__':
    main()
