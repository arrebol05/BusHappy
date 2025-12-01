import os
import csv
from pathlib import Path

def clean_support_disability_column(base_dir):
    """
    Clean the SupportDisability column in all CSV files within HCMC_bus_routes directory.
    Replace empty/missing values with 'Không'.
    """
    base_path = Path(base_dir)
    files_processed = 0
    rows_updated = 0
    
    # Find all CSV files in subdirectories
    for route_folder in base_path.iterdir():
        if route_folder.is_dir():
            for csv_file in route_folder.glob('*.csv'):
                # Process each CSV file
                rows = []
                file_updated = False
                
                try:
                    # Read the CSV file
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        fieldnames = reader.fieldnames
                        
                        # Check if SupportDisability column exists
                        if not fieldnames or 'SupportDisability' not in fieldnames:
                            continue
                        
                        for row in reader:
                            # Replace empty/missing values with 'Không'
                            if not row['SupportDisability'] or row['SupportDisability'].strip() == '':
                                row['SupportDisability'] = 'Không'
                                rows_updated += 1
                                file_updated = True
                            rows.append(row)
                    
                    # Write back to the file if there were updates
                    if file_updated:
                        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(rows)
                        files_processed += 1
                        print(f"✓ Processed: {csv_file.relative_to(base_path)}")
                
                except Exception as e:
                    print(f"✗ Error processing {csv_file}: {e}")
    
    return files_processed, rows_updated

if __name__ == "__main__":
    # Set the base directory
    base_dir = Path(__file__).parent.parent / "Bus_route_data" / "HCMC_bus_routes"
    
    print(f"Cleaning SupportDisability column in: {base_dir}")
    print("-" * 60)
    
    files_processed, rows_updated = clean_support_disability_column(base_dir)
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"Files processed: {files_processed}")
    print(f"Rows updated: {rows_updated}")
    print("\nDone!")
