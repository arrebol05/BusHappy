/**
 * Dashboard Type Definitions
 */

export interface DashboardRoute {
    route_id: number;
    route_number: string;
    route_name: string;
    color: string;
    outbound_stops: RouteStop[];
    inbound_stops: RouteStop[];
}

export interface RouteStop {
    stop_id: number;
    stop_name: string;
    sequence: number;
    lat: number;
    lon: number;
}

export interface RouteStats {
    route_id: number;
    total_stops: number;
    outbound_stops: number;
    inbound_stops: number;
    route_length_km: number;
    avg_stop_distance_km: number;
    coverage_area_km2: number;
}

export interface SystemStats {
    total_routes: number;
    total_stops: number;
    unique_stops: number;
    avg_route_length_km: number;
    total_coverage_area_km2: number;
}

export interface RouteChange {
    type: 'add' | 'remove' | 'reorder';
    direction: 'outbound' | 'inbound';
    stop?: RouteStop;
    fromSequence?: number;
    toSequence?: number;
    description: string;
}

export interface RouteComparison {
    route_id: number;
    original_stats: RouteStats;
    new_stats: RouteStats;
    improvements: string[];
    decreases: string[];
    changes: RouteChange[];
}

export interface OptimizationResult {
    route_id?: number;
    optimized_routes: DashboardRoute[];
    removed_stops: RouteStop[];
    added_stops: RouteStop[];
    efficiency_gain: number;
    warning: string;
}

export type DashboardMode = 'schedule' | 'design' | 'disability';

export interface DashboardState {
    mode: DashboardMode;
    routes: DashboardRoute[];
    selectedRoute: DashboardRoute | null;
    systemStats: SystemStats | null;
    routeStats: Map<number, RouteStats>;
    hasChanges: boolean;
    currentComparison: RouteComparison | null;
    editingDirection: 'outbound' | 'inbound' | null;
}

export interface DisabilityStop {
    stop_id: number;
    code: string;
    name: string;
    lat: number;
    lon: number;
    zone: string;
    stop_type: string;
    status: string;
    total_routes: number;
    has_disability_support: boolean;
}

export interface DisabilityOptimizationResult {
    optimal_k: number;
    optimal_coverage: number;
    recommended_stops: any[];
    already_supported: number;
    need_upgrade: number;
    total_stops: number;
    existing_disability_stops: number;
    metrics: {
        current_avg_distance_m: number;
        optimized_avg_distance_m: number;
        distance_improvement_m: number;
        within_500m_current: number;
        within_500m_optimized: number;
        coverage_improvement: number;
        coverage_current_pct: number;
        coverage_optimized_pct: number;
    };
    implementation_phases: {
        high_priority: number;
        medium_priority: number;
        low_priority: number;
    };
}
