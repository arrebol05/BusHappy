/**
 * API Service for BusHappy Backend
 */

import type {
    Location,
    BusStop,
    BusRoute,
    RouteDetails,
    RoutePlanResult,
    GeocodingResult
} from '@types/index';
import { CONFIG } from '@utils/constants';

interface NearbyStopsResponse {
    success: boolean;
    location: Location;
    radius_km: number;
    wheelchair_only: boolean;
    stops: BusStop[];
    count: number;
}

interface StopDetailsResponse {
    success: boolean;
    stop: BusStop;
    upcoming_buses: any[];
}

interface SearchResult {
    stop_id: number;
    stop_name: string;
    stop_code: string;
    lat: number;
    lon: number;
    wheelchair_accessible: boolean;
    description: string;
}

export class BusHappyAPI {
    private baseURL: string;

    constructor(baseURL: string = CONFIG.API_BASE_URL) {
        this.baseURL = baseURL;
    }

    private async fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const response = await fetch(`${this.baseURL}${endpoint}`, options);

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if ('success' in data && !data.success) {
            throw new Error(data.error || 'API request failed');
        }

        return data as T;
    }

    private parseStopDescription(description: string): {
        old_address?: string;
        new_address?: string;
        routes?: string;
    } {
        const result: { old_address?: string; new_address?: string; routes?: string } = {};

        if (!description) return result;

        const parts = description.split(' | ');
        const routeParts: string[] = [];

        for (const part of parts) {
            if (part.startsWith('Old: ')) {
                result.old_address = part.substring(5).trim();
            } else if (part.startsWith('New: ')) {
                result.new_address = part.substring(5).trim();
            } else if (part.startsWith('Outbound: ') || part.startsWith('Inbound: ')) {
                routeParts.push(part);
            }
        }

        if (routeParts.length > 0) {
            result.routes = routeParts.join(' | ');
        }

        return result;
    }

    private transformStop(stop: any): BusStop {
        const parsed = this.parseStopDescription(stop.description || stop.routes || '');

        return {
            stop_id: stop.stop_id,
            stop_name: stop.stop_name,
            stop_code: stop.stop_code,
            lat: stop.lat,
            lon: stop.lon,
            wheelchair_accessible: stop.wheelchair_accessible,
            routes: parsed.routes,
            description: stop.description,
            distance_km: stop.distance_km,
            old_address: parsed.old_address,
            new_address: parsed.new_address,
            address_changed: !!(parsed.old_address && parsed.new_address && parsed.old_address !== parsed.new_address)
        };
    }

    async getNearbyStops(
        lat: number,
        lon: number,
        radiusKm: number = CONFIG.ROUTING.DEFAULT_RADIUS_KM,
        wheelchairOnly: boolean = false
    ): Promise<NearbyStopsResponse> {
        const response = await this.fetchJSON<NearbyStopsResponse>(
            `/stops/nearby?lat=${lat}&lon=${lon}&radius_km=${radiusKm}&wheelchair_only=${wheelchairOnly}`
        );

        // Transform stops to include parsed address and route information
        response.stops = response.stops.map(stop => this.transformStop(stop));

        return response;
    }

    async getStopDetails(stopId: number): Promise<StopDetailsResponse> {
        const response = await this.fetchJSON<StopDetailsResponse>(`/stops/${stopId}`);

        // Transform stop to include parsed address and route information
        response.stop = this.transformStop(response.stop);

        return response;
    }

    async getAllRoutes(wheelchairOnly: boolean = false): Promise<{
        success: boolean;
        routes: BusRoute[];
        count: number;
    }> {
        return this.fetchJSON(`/routes?wheelchair_only=${wheelchairOnly}`);
    }

    async getRouteStops(routeId: number): Promise<{ success: boolean } & RouteDetails> {
        return this.fetchJSON(`/routes/${routeId}/stops`);
    }

    async searchStops(
        query: string,
        wheelchairOnly: boolean = false
    ): Promise<{
        success: boolean;
        query: string;
        wheelchair_only: boolean;
        results: SearchResult[];
        count: number;
    }> {
        const response = await this.fetchJSON<{
            success: boolean;
            query: string;
            wheelchair_only: boolean;
            results: SearchResult[];
            count: number;
        }>(
            `/search?q=${encodeURIComponent(query)}&wheelchair_only=${wheelchairOnly}`
        );

        // Transform search results to include parsed address and route information
        response.results = response.results.map(stop => this.transformStop(stop) as any);

        return response;
    }

    async planRoute(
        fromLat: number,
        fromLon: number,
        toLat: number,
        toLon: number,
        wheelchairAccessible: boolean = false
    ): Promise<{ success: boolean } & RoutePlanResult> {
        return this.fetchJSON('/plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                from_lat: fromLat,
                from_lon: fromLon,
                to_lat: toLat,
                to_lon: toLon,
                wheelchair_accessible: wheelchairAccessible
            })
        });
    }

    async healthCheck(): Promise<{
        status: string;
        timestamp: string;
        total_stops: number;
        total_routes: number;
    }> {
        return this.fetchJSON('/health');
    }
}

export class GeocodingService {
    private baseURL: string = 'https://nominatim.openstreetmap.org';

    async searchLocation(query: string): Promise<GeocodingResult[]> {
        // Add HCMC bounds to prioritize results in Ho Chi Minh City
        const bounds = '106.4,10.5,107.0,11.2'; // HCMC approximate bounds

        const response = await fetch(
            `${this.baseURL}/search?` +
            `q=${encodeURIComponent(query)},Ho Chi Minh City,Vietnam&` +
            `format=json&` +
            `limit=5&` +
            `viewbox=${bounds}&` +
            `bounded=1`,
            {
                headers: {
                    Accept: 'application/json',
                    'User-Agent': 'BusHappy/1.0'
                }
            }
        );

        if (!response.ok) {
            throw new Error('Geocoding request failed');
        }

        const data = await response.json();

        return data.map((item: any) => ({
            lat: parseFloat(item.lat),
            lon: parseFloat(item.lon),
            display_name: item.display_name,
            type: item.type,
            importance: item.importance || 0
        }));
    }

    async reverseGeocode(lat: number, lon: number): Promise<string> {
        const response = await fetch(
            `${this.baseURL}/reverse?lat=${lat}&lon=${lon}&format=json`,
            {
                headers: {
                    Accept: 'application/json',
                    'User-Agent': 'BusHappy/1.0'
                }
            }
        );

        if (!response.ok) {
            throw new Error('Reverse geocoding failed');
        }

        const data = await response.json();
        return data.display_name;
    }
}
