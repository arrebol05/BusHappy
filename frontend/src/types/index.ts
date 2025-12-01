/**
 * Core type definitions for BusHappy application
 */

export interface Location {
    lat: number;
    lon: number;
}

export interface BusStop {
    stop_id: number;
    stop_name: string;
    stop_code: string;
    lat: number;
    lon: number;
    wheelchair_accessible: boolean;
    routes?: string;
    description?: string;
    distance_km?: number;
    old_address?: string;
    new_address?: string;
    address_changed?: boolean;
}

export interface UpcomingBus {
    route_number: string;
    route_name: string;
    headsign: string;
    arrival_time: string;
    direction: string;
    wheelchair_accessible: boolean;
}

export interface StopDetails {
    stop: BusStop;
    upcoming_buses: UpcomingBus[];
}

export interface BusRoute {
    route_id: number;
    route_number: string;
    route_name: string;
    description: string;
    color: string;
}

export interface RouteStop {
    stop_id: number;
    stop_name: string;
    sequence: number;
    lat: number;
    lon: number;
}

export interface RouteDetails {
    route_id: number;
    route_info: BusRoute;
    outbound_stops?: RouteStop[];
    inbound_stops?: RouteStop[];
}

export interface PlannedRoute {
    type: 'direct' | 'transfer';
    start_stop: {
        id: number;
        name: string;
        walk_distance_km: number;
    };
    end_stop: {
        id: number;
        name: string;
        walk_distance_km: number;
    };
    route: {
        id: string;
        number: string;
        name: string;
    };
    total_walk_distance_km: number;
    transfer_stop?: {
        id: number;
        name: string;
    };
    second_route?: {
        id: string;
        number: string;
        name: string;
    };
}

export interface RoutePlanResult {
    from: Location;
    to: Location;
    wheelchair_accessible: boolean;
    routes: PlannedRoute[];
    count: number;
}

export interface GeocodingResult {
    lat: number;
    lon: number;
    display_name: string;
    type: string;
    importance: number;
}

export interface SelectedPoint {
    location: Location;
    type: 'location' | 'bus_stop';
    name: string;
    busStop?: BusStop;
}

export interface AppState {
    wheelchairMode: boolean;
    useOldAddresses: boolean;
    currentLocation: Location | null;
    pinnedLocation: Location | null;
    selectedStop: BusStop | null;
    planningMode: boolean;
    planningStep: 'destination' | 'origin' | null;
    selectedDestination: SelectedPoint | null;
    selectedOrigin: SelectedPoint | null;
    searchMode: 'stops' | 'locations';
}

export type NotificationType = 'success' | 'error' | 'info';
