"""
Disability Bus Stop Optimization Module
Based on the algorithm from visualize_disability_support.ipynb
Finds minimal set of bus stops to upgrade for maximum coverage with constraint to use predefined disability stops.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import math
from pathlib import Path
from typing import List, Dict, Tuple, Set
from config import config

# Maximum walking distance in meters
MAX_WALKING_DISTANCE = 500  # 500m = ~6-7 min walk
TARGET_COVERAGE = 0.95  # Target 95% of all stops


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def calculate_stop_priority_score(row: pd.Series, max_routes: int) -> float:
    """
    Calculate priority score for a stop based on multiple factors:
    - Number of routes (more routes = higher impact)
    - Stop type importance
    - Operational status (active stops get bonus)
    """
    score = 0
    
    # Route count factor (0-100 points)
    if max_routes > 0:
        score += (row.get('Total_Routes', 0) / max_routes) * 100
    
    # Stop type priority (0-50 points)
    type_priority = {
        'Bến xe buýt': 50,  # Bus terminal (highest priority)
        'Bến xe': 50,
        'Trạm dừng': 30,    # Regular stop
        'Nhà chờ': 35,
        'Điểm dừng': 20,     # Minor stop
        'Trụ dừng': 30,
        'Biển treo': 25,
        'Ô sơn': 25
    }
    score += type_priority.get(row.get('StopType', ''), 25)
    
    # Operational status (active stops get bonus)
    if row.get('Status') == 'Đang khai thác':  # Currently operating
        score += 30
    
    return score


def find_optimal_stops_enhanced(df: pd.DataFrame, max_distance: float, target_coverage: float,
                                existing_disability_stops: Set[int]) -> Tuple[int, float, np.ndarray]:
    """
    Find minimal set of stops to upgrade using enhanced multi-criteria optimization
    
    Strategies:
    1. K-Means clustering for spatial coverage
    2. Weighted scoring based on:
       - Number of routes (higher = more impact)
       - Stop type priority
       - Current coverage gaps
    3. CONSTRAINT: Must include existing disability-supported stops
    """
    
    coords = df[['Lat', 'Lng']].values
    
    # Binary search for minimal k
    def evaluate_coverage(k: int) -> Tuple[float, np.ndarray]:
        """Evaluate coverage for k clusters"""
        # Start with existing disability stops as initial centers if possible
        if len(existing_disability_stops) > 0 and k >= len(existing_disability_stops):
            existing_stops_df = df[df['stop_id'].isin(existing_disability_stops)]
            if len(existing_stops_df) > 0:
                init_centers = existing_stops_df[['Lat', 'Lng']].values
                # Pad with random centers if needed
                if len(init_centers) < k:
                    remaining = k - len(init_centers)
                    kmeans = KMeans(n_clusters=k, init='k-means++', random_state=42, n_init=10)
                    kmeans.fit(coords)
                    # Replace some centers with existing disability stops
                    centers = kmeans.cluster_centers_.copy()
                    centers[:len(init_centers)] = init_centers
                else:
                    kmeans = KMeans(n_clusters=k, init=init_centers[:k], random_state=42, n_init=1)
                    kmeans.fit(coords)
                    centers = kmeans.cluster_centers_
            else:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(coords)
                centers = kmeans.cluster_centers_
        else:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(coords)
            centers = kmeans.cluster_centers_
        
        coverage_count = 0
        for coord in coords:
            distances = [haversine_distance(coord[0], coord[1], center[0], center[1]) 
                        for center in centers]
            if min(distances) <= max_distance:
                coverage_count += 1
        
        return coverage_count / len(coords), centers
    
    # Binary search for minimum k that achieves target coverage
    # Account for existing disability stops
    min_k = max(10, len(existing_disability_stops))
    low, high = min_k, len(df)
    best_k = high
    best_centers = None
    best_coverage = 0
    
    while low <= high:
        mid = (low + high) // 2
        coverage, centers = evaluate_coverage(mid)
        
        if coverage >= target_coverage:
            best_k = mid
            best_centers = centers
            best_coverage = coverage
            high = mid - 1
        else:
            low = mid + 1
    
    return best_k, best_coverage, best_centers


def find_nearest_stop_weighted(center_lat: float, center_lng: float, df: pd.DataFrame,
                               max_routes: int, max_search_distance: float = 1000,
                               existing_disability_stops: Set[int] = None) -> Tuple[int, float, float]:
    """
    Find the best actual bus stop near a theoretical optimal location
    Considers both distance and priority score
    CONSTRAINT: Prefer existing disability stops if they are close
    """
    if existing_disability_stops is None:
        existing_disability_stops = set()
    
    # Calculate distances to all stops
    distances = df.apply(
        lambda row: haversine_distance(center_lat, center_lng, row['Lat'], row['Lng']), 
        axis=1
    )
    
    # Check if there's an existing disability stop very close (within 100m)
    if len(existing_disability_stops) > 0:
        disability_stops_df = df[df['stop_id'].isin(existing_disability_stops)]
        if len(disability_stops_df) > 0:
            disability_distances = distances[disability_stops_df.index]
            min_disability_dist = disability_distances.min()
            if min_disability_dist <= 100:  # Very close to existing disability stop
                idx = disability_distances.idxmin()
                return idx, disability_distances[idx], calculate_stop_priority_score(df.loc[idx], max_routes)
    
    # Filter stops within search distance
    nearby_stops = df[distances <= max_search_distance].copy()
    
    if len(nearby_stops) == 0:
        # If no stops within search distance, just take nearest
        nearest_idx = distances.idxmin()
        return nearest_idx, distances[nearest_idx], 0
    
    # Calculate priority scores for nearby stops
    nearby_distances = distances[nearby_stops.index]
    priority_scores = nearby_stops.apply(lambda row: calculate_stop_priority_score(row, max_routes), axis=1)
    
    # Bonus for existing disability stops
    for idx in nearby_stops.index:
        if nearby_stops.loc[idx, 'stop_id'] in existing_disability_stops:
            priority_scores[idx] += 50  # Significant bonus for reusing existing infrastructure
    
    # Normalize distances (inverse: closer = higher score)
    max_dist = nearby_distances.max()
    if max_dist > 0:
        distance_scores = 100 * (1 - nearby_distances / max_dist)
    else:
        distance_scores = pd.Series(100, index=nearby_stops.index)
    
    # Combined score: 60% priority, 40% distance
    combined_scores = 0.6 * priority_scores + 0.4 * distance_scores
    
    # Select stop with highest combined score
    best_idx = combined_scores.idxmax()
    
    return best_idx, distances[best_idx], priority_scores[best_idx]


def optimize_disability_bus_stops(all_stops_df: pd.DataFrame, 
                                  max_distance: float = MAX_WALKING_DISTANCE,
                                  target_coverage: float = TARGET_COVERAGE) -> Dict:
    """
    Main optimization function for disability bus stops
    Returns recommended stops to FLIP disability support (toggle existing stops only)
    
    CONSTRAINTS:
    1. Only use existing stops from the dataset - NO new stops created
    2. Only flip the disability support flag on stops that need upgrade
    3. Existing disability-supported stops must be preserved
    """
    # Identify existing disability-supported stops
    if 'HasDisabilitySupport' in all_stops_df.columns:
        existing_disability_mask = all_stops_df['HasDisabilitySupport'] == 'Yes'
    elif 'SupportDisability' in all_stops_df.columns:
        existing_disability_mask = all_stops_df['SupportDisability'] == 'Có'
    else:
        existing_disability_mask = pd.Series([False] * len(all_stops_df), index=all_stops_df.index)
    
    df_with_support = all_stops_df[existing_disability_mask].copy()
    df_without_support = all_stops_df[~existing_disability_mask].copy()
    
    existing_disability_stops = set(df_with_support['stop_id'].values) if 'stop_id' in df_with_support.columns else set()
    
    # Use all valid stops for optimization - CRITICAL: Only from existing dataset
    df_valid = all_stops_df.dropna(subset=['Lat', 'Lng']).copy()
    
    # Find optimal number of stops
    optimal_k, optimal_coverage, optimal_centers = find_optimal_stops_enhanced(
        df_valid, max_distance, target_coverage, existing_disability_stops
    )
    
    # Map centers to actual stops using weighted selection
    max_routes = df_valid['Total_Routes'].max() if 'Total_Routes' in df_valid.columns else 1
    
    recommended_stops = []
    seen_stops = set()
    
    # First, ensure all existing disability stops are included
    for stop_id in existing_disability_stops:
        if stop_id in df_valid['stop_id'].values:
            stop_row = df_valid[df_valid['stop_id'] == stop_id].iloc[0]
            stop_info = stop_row.to_dict()
            stop_info['Distance_to_optimal'] = 0  # Already optimal (existing)
            stop_info['Priority_Score'] = calculate_stop_priority_score(stop_row, max_routes)
            stop_info['Cluster_ID'] = -1  # Special marker for existing
            stop_info['Already_Supported'] = True
            recommended_stops.append(stop_info)
            seen_stops.add(stop_id)
    
    # Now add stops for remaining clusters
    for i, center in enumerate(optimal_centers):
        # Find best stop for this cluster
        temp_df = df_valid[~df_valid['stop_id'].isin(seen_stops)]
        if len(temp_df) > 0:
            stop_idx, distance, priority = find_nearest_stop_weighted(
                center[0], center[1], temp_df, max_routes, 
                existing_disability_stops=existing_disability_stops
            )
            
            stop_info = temp_df.loc[stop_idx].to_dict()
            stop_info['Distance_to_optimal'] = distance
            stop_info['Priority_Score'] = priority
            stop_info['Cluster_ID'] = i
            stop_info['Already_Supported'] = stop_info.get('stop_id') in existing_disability_stops
            
            recommended_stops.append(stop_info)
            seen_stops.add(stop_info.get('stop_id'))
    
    # Create DataFrame
    df_recommended = pd.DataFrame(recommended_stops)
    
    # Remove duplicates
    df_recommended = df_recommended.drop_duplicates(subset=['stop_id'], keep='first')
    
    # Calculate metrics
    already_supported = df_recommended['Already_Supported'].sum()
    need_upgrade = len(df_recommended) - already_supported
    
    # Calculate coverage metrics
    def calculate_nearest_supported_distance(row: pd.Series, supported_stops_df: pd.DataFrame) -> float:
        """Calculate distance to nearest disability-supported stop"""
        if len(supported_stops_df) == 0:
            return float('inf')
        
        distances = supported_stops_df.apply(
            lambda s: haversine_distance(row['Lat'], row['Lng'], s['Lat'], s['Lng']), 
            axis=1
        )
        return distances.min()
    
    # Current state metrics
    current_avg_distance = df_valid.apply(
        lambda row: calculate_nearest_supported_distance(row, df_with_support), axis=1
    ).mean()
    
    # After optimization metrics
    optimized_avg_distance = df_valid.apply(
        lambda row: calculate_nearest_supported_distance(row, df_recommended), axis=1
    ).mean()
    
    within_500m_current = (df_valid.apply(
        lambda row: calculate_nearest_supported_distance(row, df_with_support), axis=1
    ) <= 500).sum()
    
    within_500m_optimized = (df_valid.apply(
        lambda row: calculate_nearest_supported_distance(row, df_recommended), axis=1
    ) <= 500).sum()
    
    # Prepare results
    result = {
        'optimal_k': int(optimal_k),
        'optimal_coverage': float(optimal_coverage),
        'recommended_stops': df_recommended.to_dict('records'),
        'already_supported': int(already_supported),
        'need_upgrade': int(need_upgrade),
        'total_stops': len(df_valid),
        'existing_disability_stops': len(df_with_support),
        'metrics': {
            'current_avg_distance_m': float(current_avg_distance),
            'optimized_avg_distance_m': float(optimized_avg_distance),
            'distance_improvement_m': float(current_avg_distance - optimized_avg_distance),
            'within_500m_current': int(within_500m_current),
            'within_500m_optimized': int(within_500m_optimized),
            'coverage_improvement': int(within_500m_optimized - within_500m_current),
            'coverage_current_pct': float(within_500m_current / len(df_valid) * 100),
            'coverage_optimized_pct': float(within_500m_optimized / len(df_valid) * 100)
        },
        'implementation_phases': {
            'high_priority': len(df_recommended[
                (~df_recommended['Already_Supported']) & 
                (df_recommended['Priority_Score'] >= 100)
            ]),
            'medium_priority': len(df_recommended[
                (~df_recommended['Already_Supported']) & 
                (df_recommended['Priority_Score'] >= 70) & 
                (df_recommended['Priority_Score'] < 100)
            ]),
            'low_priority': len(df_recommended[
                (~df_recommended['Already_Supported']) & 
                (df_recommended['Priority_Score'] < 70)
            ])
        }
    }
    
    return result


def calculate_disability_metrics(all_stops_df: pd.DataFrame, max_distance: float = MAX_WALKING_DISTANCE) -> Dict:
    """
    Calculate real-time disability support metrics based on current stop configuration.
    Updates when sandbox disability support values are modified.
    
    Returns:
    - coverage_within_500m: Percentage of stops within 500m of disability-supported stop
    - min_distance_to_support: Minimum distance for disabled person to reach supported stop
    - avg_distance_to_support: Average distance to nearest disability-supported stop
    - total_stops: Total number of stops
    - supported_stops: Number of stops with disability support
    """
    # Identify disability-supported stops
    if 'HasDisabilitySupport' in all_stops_df.columns:
        disability_mask = all_stops_df['HasDisabilitySupport'] == 'Yes'
    elif 'SupportDisability' in all_stops_df.columns:
        disability_mask = all_stops_df['SupportDisability'] == 'Có'
    else:
        disability_mask = pd.Series([False] * len(all_stops_df), index=all_stops_df.index)
    
    df_with_support = all_stops_df[disability_mask].copy()
    df_valid = all_stops_df.dropna(subset=['Lat', 'Lng']).copy()
    
    if len(df_with_support) == 0:
        # No disability support at all
        return {
            'coverage_within_500m_pct': 0.0,
            'coverage_within_500m_count': 0,
            'min_distance_to_support_m': float('inf'),
            'max_distance_to_support_m': float('inf'),
            'avg_distance_to_support_m': float('inf'),
            'total_stops': len(df_valid),
            'supported_stops': 0,
            'unsupported_stops': len(df_valid)
        }
    
    def calculate_nearest_supported_distance(row: pd.Series, supported_stops_df: pd.DataFrame) -> float:
        """Calculate distance to nearest disability-supported stop"""
        if len(supported_stops_df) == 0:
            return float('inf')
        
        distances = supported_stops_df.apply(
            lambda s: haversine_distance(row['Lat'], row['Lng'], s['Lat'], s['Lng']), 
            axis=1
        )
        return distances.min()
    
    # Calculate distances for all stops to nearest supported stop
    distances = df_valid.apply(
        lambda row: calculate_nearest_supported_distance(row, df_with_support), 
        axis=1
    )
    
    # Calculate metrics
    within_500m = (distances <= max_distance).sum()
    coverage_pct = (within_500m / len(df_valid) * 100) if len(df_valid) > 0 else 0
    
    # Filter out infinite values for min/max/avg calculations
    finite_distances = distances[distances != float('inf')]
    
    return {
        'coverage_within_500m_pct': float(coverage_pct),
        'coverage_within_500m_count': int(within_500m),
        'min_distance_to_support_m': float(finite_distances.min() if len(finite_distances) > 0 else float('inf')),
        'max_distance_to_support_m': float(finite_distances.max() if len(finite_distances) > 0 else float('inf')),
        'avg_distance_to_support_m': float(finite_distances.mean() if len(finite_distances) > 0 else float('inf')),
        'total_stops': len(df_valid),
        'supported_stops': len(df_with_support),
        'unsupported_stops': len(df_valid) - len(df_with_support)
    }


if __name__ == '__main__':
    # Test the optimization
    BASE_PATH = config.bus_data_path
    all_stops_df = pd.read_csv(BASE_PATH / "all_bus_stops_aggregated.csv")
    
    # Add stop_id if not present
    if 'stop_id' not in all_stops_df.columns:
        all_stops_df['stop_id'] = range(1, len(all_stops_df) + 1)
    
    # Standardize disability support column
    if 'SupportDisability' in all_stops_df.columns:
        all_stops_df['HasDisabilitySupport'] = all_stops_df['SupportDisability'].apply(
            lambda x: 'Yes' if x == 'Có' else 'No'
        )
    
    result = optimize_disability_bus_stops(all_stops_df)
    
    print("Optimization Results:")
    print(f"Total stops: {result['total_stops']}")
    print(f"Optimal stops needed: {result['optimal_k']}")
    print(f"Already supported: {result['already_supported']}")
    print(f"Need upgrade: {result['need_upgrade']}")
    print(f"Coverage achieved: {result['optimal_coverage']*100:.2f}%")
    print(f"\nMetrics:")
    for key, value in result['metrics'].items():
        print(f"  {key}: {value}")
    
    # Test metrics calculation
    print("\n" + "="*80)
    print("Current Metrics:")
    metrics = calculate_disability_metrics(all_stops_df)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
