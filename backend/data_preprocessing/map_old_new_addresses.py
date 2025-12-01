"""
Map old addresses to new addresses for all bus stops.
Creates a mapping file that shows address changes for each stop.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime


class AddressMapper:
    def __init__(self, base_path: str):
        """
        Initialize address mapper.
        
        Args:
            base_path: Path to Bus_route_data folder
        """
        self.base_path = Path(base_path)
        
        # Load both old and new address files
        self.old_stops = pd.read_csv(self.base_path / "all_bus_stops_ag_old_adr.csv")
        self.new_stops = pd.read_csv(self.base_path / "all_bus_stops_ag_new_adr.csv")
        
        print(f"Loaded {len(self.old_stops)} stops from old address file")
        print(f"Loaded {len(self.new_stops)} stops from new address file")
    
    def generate_mapping(self):
        """Generate address mapping by comparing old and new files."""
        mappings = []
        changes_detected = 0
        
        merged = pd.merge(
            self.old_stops,
            self.new_stops,
            on='StopId',
            suffixes=('_old', '_new'),
            how='outer'
        )
        
        for _, row in merged.iterrows():
            stop_id = row['StopId']
            
            old_address = self._build_address(row, '_old')
            new_address = self._build_address(row, '_new')
            
            address_changed = old_address != new_address
            if address_changed:
                changes_detected += 1
            
            mapping_entry = {
                'stop_id': int(stop_id) if pd.notna(stop_id) else None,
                'code': row.get('Code_old') or row.get('Code_new', ''),
                'name': row.get('Name_old') or row.get('Name_new', ''),
                'old_address': old_address,
                'new_address': new_address,
                'address_changed': address_changed,
                'old_ward': row.get('Ward_old', ''),
                'new_ward': row.get('Ward_new', ''),
                'old_address_no': row.get('AddressNo_old', ''),
                'new_address_no': row.get('AddressNo_new', ''),
                'old_street': row.get('Street_old', ''),
                'new_street': row.get('Street_new', ''),
                'coordinates': {
                    'lat': float(row.get('Lat_old') or row.get('Lat_new', 0)),
                    'lng': float(row.get('Lng_old') or row.get('Lng_new', 0))
                }
            }
            
            mappings.append(mapping_entry)
        
        print(f"\nAddress changes detected: {changes_detected}/{len(mappings)} stops")
        
        return mappings
    
    def _build_address(self, row, suffix):
        """Build full address string from components."""
        parts = []
        
        address_no = row.get(f'AddressNo{suffix}', '')
        street = row.get(f'Street{suffix}', '')
        ward = row.get(f'Ward{suffix}', '')
        
        if pd.notna(address_no) and str(address_no).strip():
            parts.append(str(address_no))
        if pd.notna(street) and str(street).strip():
            parts.append(str(street))
        if pd.notna(ward) and str(ward).strip():
            parts.append(str(ward))
        
        return ', '.join(parts) if parts else 'N/A'
    
    def save_mapping_csv(self, output_path: str):
        """Save mapping to CSV file."""
        mappings = self.generate_mapping()
        
        csv_data = []
        for m in mappings:
            csv_data.append({
                'StopId': m['stop_id'],
                'Code': m['code'],
                'Name': m['name'],
                'Old_Address': m['old_address'],
                'New_Address': m['new_address'],
                'Address_Changed': m['address_changed'],
                'Old_Ward': m['old_ward'],
                'New_Ward': m['new_ward'],
                'Old_AddressNo': m['old_address_no'],
                'New_AddressNo': m['new_address_no'],
                'Old_Street': m['old_street'],
                'New_Street': m['new_street'],
                'Lat': m['coordinates']['lat'],
                'Lng': m['coordinates']['lng']
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ Saved CSV mapping to: {output_path}")
        
        changed = df['Address_Changed'].sum()
        print(f"\nSummary:")
        print(f"  Total stops: {len(df)}")
        print(f"  Addresses changed: {changed}")
        print(f"  Addresses unchanged: {len(df) - changed}")
        print(f"  Change rate: {changed/len(df)*100:.1f}%")
        
        return df
    
    def save_mapping_json(self, output_path: str):
        """Save mapping to JSON file."""
        mappings = self.generate_mapping()
        
        output = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_stops': len(mappings),
                'addresses_changed': sum(1 for m in mappings if m['address_changed']),
                'source_files': {
                    'old_addresses': 'all_bus_stops_ag_old_adr.csv',
                    'new_addresses': 'all_bus_stops_ag_new_adr.csv'
                }
            },
            'mappings': mappings
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Saved JSON mapping to: {output_path}")
    
    def get_changes_only(self):
        """Get only stops where address changed."""
        mappings = self.generate_mapping()
        changed_only = [m for m in mappings if m['address_changed']]
        
        print(f"\n📍 Stops with address changes: {len(changed_only)}")
        print("\nSample changes:")
        for i, m in enumerate(changed_only[:5], 1):
            print(f"\n{i}. Stop {m['stop_id']} - {m['name']}")
            print(f"   Old: {m['old_address']}")
            print(f"   New: {m['new_address']}")
        
        if len(changed_only) > 5:
            print(f"\n... and {len(changed_only) - 5} more changes")
        
        return changed_only


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent.parent
    
    base_path = script_dir / "Bus_route_data"
    output_csv = base_path / "address_mapping.csv"
    output_json = base_path / "address_mapping.json"
    
    # Check if base path exists
    if not base_path.exists():
        print(f"❌ Error: Bus_route_data directory not found at {base_path}")
        return
    
    print("🗺️  Generating address mapping...\n")
    
    # Create mapper
    mapper = AddressMapper(str(base_path))
    
    # Save both CSV and JSON
    mapper.save_mapping_csv(str(output_csv))
    mapper.save_mapping_json(str(output_json))
    
    # Show changes
    mapper.get_changes_only()
    
    print("\n✅ Address mapping complete!")


if __name__ == "__main__":
    main()
