/**
 * Dashboard API Service
 */

import type {
    DashboardRoute,
    RouteStats,
    SystemStats,
    RouteComparison,
    OptimizationResult,
    RouteStop
} from '@dashboard/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export class DashboardAPI {
    private baseURL: string;

    constructor(baseURL: string = API_BASE_URL) {
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

    /**
     * Get all routes with detailed stop information
     */
    async getAllRoutesDetailed(): Promise<DashboardRoute[]> {
        return this.fetchJSON<DashboardRoute[]>('/api/dashboard/routes');
    }

    /**
     * Get system-wide statistics
     */
    async getSystemStats(): Promise<SystemStats> {
        return this.fetchJSON<SystemStats>('/api/dashboard/stats/system');
    }

    /**
     * Get statistics for a specific route
     */
    async getRouteStats(routeId: number): Promise<RouteStats> {
        return this.fetchJSON<RouteStats>(`/api/dashboard/stats/route/${routeId}`);
    }

    /**
     * Calculate stats for a modified route
     */
    async calculateRouteStats(
        routeId: number,
        outboundStops: RouteStop[],
        inboundStops: RouteStop[]
    ): Promise<RouteStats> {
        return this.fetchJSON<RouteStats>('/api/dashboard/calculate-stats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                route_id: routeId,
                outbound_stops: outboundStops,
                inbound_stops: inboundStops
            })
        });
    }

    /**
     * Compare original and modified route
     */
    async compareRoutes(
        routeId: number,
        originalOutbound: RouteStop[],
        originalInbound: RouteStop[],
        newOutbound: RouteStop[],
        newInbound: RouteStop[]
    ): Promise<RouteComparison> {
        return this.fetchJSON<RouteComparison>('/api/dashboard/compare-route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                route_id: routeId,
                original: {
                    outbound_stops: originalOutbound,
                    inbound_stops: originalInbound
                },
                modified: {
                    outbound_stops: newOutbound,
                    inbound_stops: newInbound
                }
            })
        });
    }

    /**
     * Save route modifications
     */
    async saveRouteChanges(
        routeId: number,
        outboundStops: RouteStop[],
        inboundStops: RouteStop[]
    ): Promise<{ success: boolean; message: string }> {
        return this.fetchJSON('/api/dashboard/save-route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                route_id: routeId,
                outbound_stops: outboundStops,
                inbound_stops: inboundStops
            })
        });
    }

    /**
     * Get optimization suggestions for a single route
     */
    async optimizeRoute(routeId: number): Promise<OptimizationResult> {
        return this.fetchJSON<OptimizationResult>(`/api/dashboard/optimize/route/${routeId}`, {
            method: 'POST'
        });
    }

    /**
     * Get optimization suggestions for entire system
     */
    async optimizeSystem(): Promise<OptimizationResult> {
        return this.fetchJSON<OptimizationResult>('/api/dashboard/optimize/system', {
            method: 'POST'
        });
    }
}
