"""
Configuration management for BusHappy API Server
Supports production and sandbox environments to protect real data during testing/editing
"""

import os
from pathlib import Path
from typing import Literal

# Environment mode
ENV_MODE = os.getenv('BUSHAPPY_ENV', 'sandbox').lower()  # Default to sandbox for safety
VALID_MODES = ['production', 'sandbox']

if ENV_MODE not in VALID_MODES:
    raise ValueError(f"Invalid environment mode: {ENV_MODE}. Must be one of {VALID_MODES}")


class Config:
    """Configuration class for environment-specific settings"""
    
    BASE_DIR = Path(__file__).parent
    
    # Production paths
    PRODUCTION_GTFS_PATH = BASE_DIR / "gtfs"
    PRODUCTION_BUS_DATA_PATH = BASE_DIR / "Bus_route_data"
    
    # Sandbox paths
    SANDBOX_GTFS_PATH = BASE_DIR / "gtfs_sandbox"
    SANDBOX_BUS_DATA_PATH = BASE_DIR / "Bus_route_data_sandbox"
    
    def __init__(self, mode: Literal['production', 'sandbox'] = None):
        """
        Initialize configuration with specified mode
        
        Args:
            mode: Environment mode ('production' or 'sandbox')
                  If None, uses ENV_MODE from environment variable
        """
        self.mode = mode or ENV_MODE
        
        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid mode: {self.mode}. Must be one of {VALID_MODES}")
    
    @property
    def is_sandbox(self) -> bool:
        """Check if running in sandbox mode"""
        return self.mode == 'sandbox'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.mode == 'production'
    
    @property
    def gtfs_path(self) -> Path:
        """Get GTFS path for current environment"""
        return self.SANDBOX_GTFS_PATH if self.is_sandbox else self.PRODUCTION_GTFS_PATH
    
    @property
    def bus_data_path(self) -> Path:
        """Get bus route data path for current environment"""
        return self.SANDBOX_BUS_DATA_PATH if self.is_sandbox else self.PRODUCTION_BUS_DATA_PATH
    
    @property
    def arrival_times_path(self) -> Path:
        """Get arrival times data path for current environment"""
        return self.bus_data_path / "arrival_times"
    
    def ensure_sandbox_exists(self):
        """
        Ensure sandbox directories exist and are initialized with production data copy
        This creates a safe copy of production data for testing/editing
        """
        if not self.is_sandbox:
            raise RuntimeError("Cannot initialize sandbox in production mode")
        
        # Create sandbox directories
        self.SANDBOX_GTFS_PATH.mkdir(parents=True, exist_ok=True)
        self.SANDBOX_BUS_DATA_PATH.mkdir(parents=True, exist_ok=True)
        
        # Check if sandbox is already populated
        sandbox_initialized = (
            (self.SANDBOX_GTFS_PATH / "stops.txt").exists() and
            (self.SANDBOX_GTFS_PATH / "routes.txt").exists()
        )
        
        if not sandbox_initialized:
            print("🔧 Initializing sandbox environment with production data copy...")
            self._copy_production_to_sandbox()
            print("✅ Sandbox initialized successfully!")
        
        return True
    
    def _copy_production_to_sandbox(self):
        """Copy production GTFS data to sandbox"""
        import shutil
        
        # Copy GTFS files
        if self.PRODUCTION_GTFS_PATH.exists():
            for gtfs_file in self.PRODUCTION_GTFS_PATH.glob("*.txt"):
                dest_file = self.SANDBOX_GTFS_PATH / gtfs_file.name
                shutil.copy2(gtfs_file, dest_file)
            print(f"  ✓ Copied GTFS files to {self.SANDBOX_GTFS_PATH}")
        
        # Copy essential bus route data (without copying large datasets)
        if self.PRODUCTION_BUS_DATA_PATH.exists():
            # Copy aggregated stop files
            essential_files = [
                "all_bus_stops_aggregated.csv",
                "all_bus_stops_ag_old_adr.csv",
                "all_bus_stops_ag_new_adr.csv",
                "address_mapping.csv",
                "address_mapping.json"
            ]
            
            for filename in essential_files:
                src = self.PRODUCTION_BUS_DATA_PATH / filename
                if src.exists():
                    dest = self.SANDBOX_BUS_DATA_PATH / filename
                    shutil.copy2(src, dest)
            
            print(f"  ✓ Copied essential data files to {self.SANDBOX_BUS_DATA_PATH}")
    
    def reset_sandbox(self):
        """
        Reset sandbox to production state
        WARNING: This deletes all sandbox modifications!
        """
        if not self.is_sandbox:
            raise RuntimeError("Cannot reset sandbox in production mode")
        
        import shutil
        
        # Remove sandbox directories
        if self.SANDBOX_GTFS_PATH.exists():
            shutil.rmtree(self.SANDBOX_GTFS_PATH)
        
        if self.SANDBOX_BUS_DATA_PATH.exists():
            shutil.rmtree(self.SANDBOX_BUS_DATA_PATH)
        
        # Reinitialize
        self.ensure_sandbox_exists()
        
        print("🔄 Sandbox has been reset to production state")
    
    def get_info(self) -> dict:
        """Get current configuration information"""
        return {
            'mode': self.mode,
            'is_sandbox': self.is_sandbox,
            'gtfs_path': str(self.gtfs_path),
            'bus_data_path': str(self.bus_data_path),
            'gtfs_exists': self.gtfs_path.exists(),
            'bus_data_exists': self.bus_data_path.exists()
        }


# Global configuration instance
config = Config()

# Initialize sandbox if needed
if config.is_sandbox:
    config.ensure_sandbox_exists()
