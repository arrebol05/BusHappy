"""
Environment Management Utility for BusHappy
Manage sandbox and production environments easily from command line
"""

import argparse
import sys
from pathlib import Path
from config import config


def show_status():
    """Display current environment status"""
    info = config.get_info()
    
    print("\n" + "=" * 60)
    print("BusHappy Environment Status")
    print("=" * 60)
    print(f"Current Mode: {info['mode'].upper()}")
    print(f"Sandbox Active: {info['is_sandbox']}")
    print(f"GTFS Path: {info['gtfs_path']}")
    print(f"GTFS Exists: {info['gtfs_exists']}")
    print(f"Bus Data Path: {info['bus_data_path']}")
    print(f"Bus Data Exists: {info['bus_data_exists']}")
    
    if info['is_sandbox']:
        print("\n⚠️  SANDBOX MODE")
        print("   All modifications are isolated from production data")
        print("   Use 'python manage_env.py reset' to restore from production")
    else:
        print("\n🚨 PRODUCTION MODE")
        print("   Route modifications are disabled for safety")
        print("   Use BUSHAPPY_ENV=sandbox to enable editing mode")
    
    print("=" * 60 + "\n")


def reset_sandbox():
    """Reset sandbox to production state"""
    if config.is_production:
        print("❌ Error: Cannot reset sandbox while in production mode")
        print("   Set BUSHAPPY_ENV=sandbox first")
        return 1
    
    print("⚠️  WARNING: This will delete all sandbox modifications!")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("❌ Reset cancelled")
        return 0
    
    print("\n🔄 Resetting sandbox...")
    config.reset_sandbox()
    print("✅ Sandbox has been reset to production state\n")
    return 0


def init_sandbox():
    """Initialize sandbox environment"""
    if config.is_production:
        print("❌ Error: Cannot initialize sandbox while in production mode")
        print("   Set BUSHAPPY_ENV=sandbox first")
        return 1
    
    print("🔧 Initializing sandbox environment...")
    config.ensure_sandbox_exists()
    print("✅ Sandbox initialized successfully\n")
    return 0


def compare_environments():
    """Compare sandbox and production data"""
    print("\n" + "=" * 60)
    print("Environment Comparison")
    print("=" * 60)
    
    prod_gtfs = config.PRODUCTION_GTFS_PATH
    sandbox_gtfs = config.SANDBOX_GTFS_PATH
    
    if not prod_gtfs.exists():
        print("❌ Production GTFS not found")
        return 1
    
    if not sandbox_gtfs.exists():
        print("❌ Sandbox GTFS not found")
        return 1
    
    import pandas as pd
    
    # Compare key files
    files_to_compare = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt']
    
    for filename in files_to_compare:
        prod_file = prod_gtfs / filename
        sandbox_file = sandbox_gtfs / filename
        
        if prod_file.exists() and sandbox_file.exists():
            prod_df = pd.read_csv(prod_file)
            sandbox_df = pd.read_csv(sandbox_file)
            
            print(f"\n{filename}:")
            print(f"  Production rows: {len(prod_df)}")
            print(f"  Sandbox rows: {len(sandbox_df)}")
            
            if len(prod_df) != len(sandbox_df):
                diff = len(sandbox_df) - len(prod_df)
                print(f"  Difference: {diff:+d} rows")
            else:
                print(f"  Status: ✓ Same size")
    
    print("\n" + "=" * 60 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Manage BusHappy environments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_env.py status          # Show current environment status
  python manage_env.py init            # Initialize sandbox environment
  python manage_env.py reset           # Reset sandbox to production state
  python manage_env.py compare         # Compare sandbox vs production

Environment Variables:
  BUSHAPPY_ENV=sandbox    # Run in sandbox mode (default)
  BUSHAPPY_ENV=production # Run in production mode
        """
    )
    
    parser.add_argument(
        'command',
        choices=['status', 'reset', 'init', 'compare'],
        help='Command to execute'
    )
    
    args = parser.parse_args()
    
    if args.command == 'status':
        return show_status() or 0
    elif args.command == 'reset':
        return reset_sandbox()
    elif args.command == 'init':
        return init_sandbox()
    elif args.command == 'compare':
        return compare_environments()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
