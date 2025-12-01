"""
Helper script to run bus route matching with various options

Usage:
    python run_route_matching.py --all                    # Process all dates
    python run_route_matching.py --date 2025-04-01        # Process single date
    python run_route_matching.py --start 2025-04-01 --end 2025-04-07  # Date range
    python run_route_matching.py --sample                 # Process first 5 files as sample
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data_preprocessing.match_buses_to_routes import BusRouteMapper


def main():
    parser = argparse.ArgumentParser(
        description='Match buses to routes and calculate arrival times'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all available GPS data files'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Process a single date (format: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        help='Start date for date range (format: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date for date range (format: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Process first 5 files as a sample test'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Custom output filename (optional)'
    )
    
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.6,
        help='Minimum confidence threshold for route matching (default: 0.6)'
    )
    
    parser.add_argument(
        '--no-gpu',
        action='store_true',
        help='Disable GPU acceleration (use CPU only)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='Batch size for GPU processing (default: 10000)'
    )
    
    args = parser.parse_args()
    
    # Initialize mapper
    print("Initializing Bus Route Mapper...")
    mapper = BusRouteMapper(use_gpu=not args.no_gpu, batch_size=args.batch_size)
    
    # Update confidence threshold if specified
    if args.min_confidence:
        mapper.CONFIDENCE_THRESHOLD = args.min_confidence
        print(f"Set confidence threshold to: {args.min_confidence:.2f}")
    
    # Determine processing mode
    if args.sample:
        print("\n📊 SAMPLE MODE: Processing first 5 files")
        print("=" * 80)
        start_date = '2025-04-01'
        end_date = '2025-04-05'
        arrivals_df = mapper.process_all_files(start_date=start_date, end_date=end_date)
        
    elif args.date:
        print(f"\n📅 SINGLE DATE MODE: Processing {args.date}")
        print("=" * 80)
        arrivals_df = mapper.process_all_files(start_date=args.date, end_date=args.date)
        
    elif args.start and args.end:
        print(f"\n📅 DATE RANGE MODE: Processing {args.start} to {args.end}")
        print("=" * 80)
        arrivals_df = mapper.process_all_files(start_date=args.start, end_date=args.end)
        
    elif args.all:
        print("\n📊 FULL PROCESSING MODE: Processing all available files")
        print("=" * 80)
        arrivals_df = mapper.process_all_files()
        
    else:
        print("\n⚠️  No processing mode specified!")
        print("Use --help to see available options")
        print("\nRunning SAMPLE MODE by default (first 5 files)...")
        print("=" * 80)
        start_date = '2025-04-01'
        end_date = '2025-04-05'
        arrivals_df = mapper.process_all_files(start_date=start_date, end_date=end_date)
    
    # Save results
    if len(arrivals_df) > 0:
        mapper.save_arrivals(arrivals_df, filename=args.output)
        
        print("\n" + "=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print(f"\n📊 Processing Summary:")
        print(f"  Total arrivals:      {len(arrivals_df):,}")
        print(f"  Routes detected:     {arrivals_df['route_num'].nunique()}")
        print(f"  Stops visited:       {arrivals_df['stop_id'].nunique()}")
        print(f"  Vehicles tracked:    {arrivals_df['vehicle_id'].nunique()}")
        print(f"  Trips recorded:      {arrivals_df['trip_id'].nunique()}")
        print(f"  Average confidence:  {arrivals_df['route_confidence'].mean():.2%}")
        print(f"  Date range:          {arrivals_df['date'].min()} to {arrivals_df['date'].max()}")
        
        # Show route breakdown
        print("\n📈 Top 10 Routes by Arrivals:")
        route_counts = arrivals_df.groupby('route_num').size().sort_values(ascending=False)
        for i, (route, count) in enumerate(route_counts.head(10).items(), 1):
            print(f"  {i:2d}. Route {route:>3s}: {count:>6,} arrivals")
        
        if len(route_counts) > 10:
            print(f"  ... and {len(route_counts) - 10} more routes")
        
        print("\n" + "=" * 80)
        print("📂 Data saved in hierarchical structure:")
        print(f"  • Complete dataset: Bus_route_data/arrival_times/{args.output or 'latest'}")
        print(f"  • By date: Bus_route_data/arrival_times/by_date/YYYY-MM-DD/route_XX/")
        print(f"  • By route: Bus_route_data/arrival_times/by_route/route_XX/YYYY-MM-DD.csv")
        print("=" * 80)
    else:
        print("\n❌ No data was processed!")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
