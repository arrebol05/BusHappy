/**
 * Dashboard Map Service
 * Handles map visualization for route design
 */

import L from 'leaflet';
import type { DashboardRoute, RouteStop } from '@dashboard/types';

const HCMC_CENTER: [number, number] = [10.8231, 106.6297];
const ROUTE_COLORS = [
    '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6',
    '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16',
    '#6366f1', '#f43f5e', '#0ea5e9', '#a855f7', '#22c55e'
];

export class DashboardMapService {
    private map: L.Map | null = null;
    private routeLayers: Map<number, L.LayerGroup> = new Map();
    private stopMarkers: Map<number, L.Marker> = new Map();
    private selectedRouteId: number | null = null;
    private showLabels: boolean = true;
    private disabilityStopsLayer: L.LayerGroup | null = null;
    private onRouteClickCallback: ((routeId: number) => void) | null = null;

    /**
     * Initialize the map
     */
    initialize(containerId: string): void {
        this.map = L.map(containerId, {
            center: HCMC_CENTER,
            zoom: 12,
            zoomControl: true
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);
    }

    /**
     * Get color for a route (cycling through predefined colors)
     */
    getRouteColor(routeId: number): string {
        return ROUTE_COLORS[routeId % ROUTE_COLORS.length];
    }

    /**
     * Render all routes on the map
     */
    renderRoutes(routes: DashboardRoute[]): void {
        if (!this.map) return;

        // Clear existing layers
        this.clearAllRoutes();

        routes.forEach(route => {
            this.renderRoute(route);
        });

        // Fit bounds to show all routes
        this.fitBoundsToRoutes(routes);
    }

    /**
     * Render a single route
     */
    private renderRoute(route: DashboardRoute): void {
        if (!this.map) return;

        const layerGroup = L.layerGroup();
        const color = this.getRouteColor(route.route_id);

        // Render outbound route
        if (route.outbound_stops && route.outbound_stops.length > 1) {
            this.renderRouteDirection(
                route.outbound_stops,
                color,
                'outbound',
                layerGroup,
                route.route_number,
                route.route_id
            );
        }

        // Render inbound route
        if (route.inbound_stops && route.inbound_stops.length > 1) {
            this.renderRouteDirection(
                route.inbound_stops,
                color,
                'inbound',
                layerGroup,
                route.route_number,
                route.route_id
            );
        }

        layerGroup.addTo(this.map);
        this.routeLayers.set(route.route_id, layerGroup);
    }

    /**
     * Render one direction of a route
     */
    private renderRouteDirection(
        stops: RouteStop[],
        color: string,
        direction: 'outbound' | 'inbound',
        layerGroup: L.LayerGroup,
        routeNumber: string,
        routeId: number
    ): void {
        // Create polyline connecting stops
        const latLngs: [number, number][] = stops.map(stop => [stop.lat, stop.lon]);
        const polyline = L.polyline(latLngs, {
            color: color,
            weight: 4,
            opacity: 0.7,
            dashArray: direction === 'inbound' ? '10, 5' : undefined
        });

        polyline.bindPopup(`Route ${routeNumber} - ${direction}<br><small>Click to isolate this route</small>`);

        // Add click event to isolate route
        polyline.on('click', (e) => {
            L.DomEvent.stopPropagation(e);
            if (this.onRouteClickCallback) {
                this.onRouteClickCallback(routeId);
            }
        });

        polyline.addTo(layerGroup);

        // Add stop markers
        stops.forEach((stop, index) => {
            const marker = L.circleMarker([stop.lat, stop.lon], {
                radius: 6,
                fillColor: color,
                color: 'white',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });

            const popupContent = `
                <div style="min-width: 200px;">
                    <strong>${stop.stop_name}</strong><br>
                    <small>Stop ${stop.sequence} (${direction})</small><br>
                    <small>Route ${routeNumber}</small>
                </div>
            `;
            marker.bindPopup(popupContent);

            // Add click event to marker as well
            marker.on('click', (e) => {
                L.DomEvent.stopPropagation(e);
                if (this.onRouteClickCallback) {
                    this.onRouteClickCallback(routeId);
                }
            });

            // Add label if enabled
            if (this.showLabels && index % 3 === 0) {
                marker.bindTooltip(stop.stop_name, {
                    permanent: false,
                    direction: 'top',
                    className: 'route-stop-label'
                });
            }

            marker.addTo(layerGroup);
        });
    }

    /**
     * Select a specific route (hide others)
     */
    selectRoute(routeId: number): void {
        this.selectedRouteId = routeId;

        this.routeLayers.forEach((layer, id) => {
            if (id === routeId) {
                layer.eachLayer((l: any) => {
                    if (l.setStyle) {
                        l.setStyle({ opacity: 1 });
                    }
                });
            } else {
                layer.remove();
            }
        });
    }

    /**
     * Deselect route (show all routes)
     */
    deselectRoute(): void {
        this.selectedRouteId = null;

        this.routeLayers.forEach((layer) => {
            if (!this.map?.hasLayer(layer)) {
                layer.addTo(this.map!);
            }
        });
    }

    /**
     * Update a route's visualization
     */
    updateRoute(route: DashboardRoute): void {
        if (!this.map) return;

        // Remove old layer
        const oldLayer = this.routeLayers.get(route.route_id);
        if (oldLayer) {
            oldLayer.remove();
            this.routeLayers.delete(route.route_id);
        }

        // Render new route
        this.renderRoute(route);

        // If this route was selected, select it again
        if (this.selectedRouteId === route.route_id) {
            this.selectRoute(route.route_id);
        }
    }

    /**
     * Clear all route layers
     */
    clearAllRoutes(): void {
        this.routeLayers.forEach(layer => layer.remove());
        this.routeLayers.clear();
        this.stopMarkers.clear();
    }

    /**
     * Fit map bounds to show all routes
     */
    private fitBoundsToRoutes(routes: DashboardRoute[]): void {
        if (!this.map || routes.length === 0) return;

        const allStops: RouteStop[] = [];
        routes.forEach(route => {
            if (route.outbound_stops) allStops.push(...route.outbound_stops);
            if (route.inbound_stops) allStops.push(...route.inbound_stops);
        });

        if (allStops.length === 0) return;

        const bounds = L.latLngBounds(
            allStops.map(stop => [stop.lat, stop.lon] as [number, number])
        );

        this.map.fitBounds(bounds, { padding: [50, 50] });
    }

    /**
     * Fit bounds to selected route
     */
    fitBoundsToRoute(route: DashboardRoute): void {
        if (!this.map) return;

        const allStops: RouteStop[] = [
            ...(route.outbound_stops || []),
            ...(route.inbound_stops || [])
        ];

        if (allStops.length === 0) return;

        const bounds = L.latLngBounds(
            allStops.map(stop => [stop.lat, stop.lon] as [number, number])
        );

        this.map.fitBounds(bounds, { padding: [50, 50] });
    }

    /**
     * Reset map view to HCMC center
     */
    resetView(): void {
        if (!this.map) return;
        this.map.setView(HCMC_CENTER, 12);
    }

    /**
     * Toggle stop labels
     */
    toggleLabels(): void {
        this.showLabels = !this.showLabels;
        // Note: To fully implement this, routes would need to be re-rendered
        // This is a simplified implementation that toggles the flag
    }

    /**
     * Highlight a specific stop
     */
    highlightStop(stopId: number): void {
        const marker = this.stopMarkers.get(stopId);
        if (marker) {
            marker.openPopup();
            this.map?.panTo(marker.getLatLng());
        }
    }

    /**
     * Get map instance
     */
    getMap(): L.Map | null {
        return this.map;
    }

    /**
     * Set callback for route click events
     */
    setRouteClickCallback(callback: (routeId: number) => void): void {
        this.onRouteClickCallback = callback;
    }

    /**
     * Render disability support stops on the map
     */
    renderDisabilityStops(stops: any[]): void {
        if (!this.map) return;

        // Clear existing disability layer
        if (this.disabilityStopsLayer) {
            this.disabilityStopsLayer.remove();
        }

        this.disabilityStopsLayer = L.layerGroup();

        stops.forEach(stop => {
            const color = stop.has_disability_support ? '#2ecc71' : '#e74c3c';
            const icon = stop.has_disability_support ? '♿' : '🚏';

            const marker = L.circleMarker([stop.lat, stop.lon], {
                radius: 5,
                fillColor: color,
                color: 'white',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.7
            });

            const popupContent = `
                <div style="min-width: 200px;">
                    <strong>${icon} ${stop.name}</strong><br>
                    <small>${stop.code}</small><br>
                    <small>Zone: ${stop.zone}</small><br>
                    <small>Type: ${stop.stop_type}</small><br>
                    <small>Routes: ${stop.total_routes}</small><br>
                    <strong style="color: ${color};">
                        ${stop.has_disability_support ? '✓ Has Disability Support' : '✗ No Disability Support'}
                    </strong>
                </div>
            `;
            marker.bindPopup(popupContent);

            marker.addTo(this.disabilityStopsLayer!);
        });

        this.disabilityStopsLayer.addTo(this.map);
    }

    /**
     * Render disability optimization results on the map
     */
    renderDisabilityOptimizationResults(recommendedStops: any[]): void {
        if (!this.map) return;

        // Clear existing disability layer
        if (this.disabilityStopsLayer) {
            this.disabilityStopsLayer.remove();
        }

        this.disabilityStopsLayer = L.layerGroup();

        recommendedStops.forEach(stop => {
            let color: string;
            let icon: string;
            let description: string;

            if (stop.Already_Supported) {
                color = '#2ecc71'; // Green for already supported
                icon = '♿';
                description = 'Already has disability support';
            } else {
                // Color by priority
                if (stop.Priority_Score >= 100) {
                    color = '#3498db'; // Blue for high priority
                } else if (stop.Priority_Score >= 70) {
                    color = '#f39c12'; // Orange for medium priority
                } else {
                    color = '#95a5a6'; // Gray for low priority
                }
                icon = '⭐';
                description = `Recommended for upgrade (Priority: ${stop.Priority_Score.toFixed(1)})`;
            }

            const marker = L.circleMarker([stop.Lat, stop.Lng], {
                radius: 7,
                fillColor: color,
                color: 'white',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });

            const popupContent = `
                <div style="min-width: 220px;">
                    <strong>${icon} ${stop.Name}</strong><br>
                    <small>${stop.Code}</small><br>
                    <small>Zone: ${stop.Zone}</small><br>
                    <small>Type: ${stop.StopType}</small><br>
                    <small>Routes: ${stop.Total_Routes || 0}</small><br>
                    <strong style="color: ${color};">${description}</strong>
                    ${!stop.Already_Supported ? `<br><small>Priority Score: ${stop.Priority_Score.toFixed(1)}</small>` : ''}
                </div>
            `;
            marker.bindPopup(popupContent);

            marker.addTo(this.disabilityStopsLayer!);
        });

        this.disabilityStopsLayer.addTo(this.map);

        // Fit bounds to show all recommended stops
        if (recommendedStops.length > 0) {
            const bounds = L.latLngBounds(
                recommendedStops.map(stop => [stop.Lat, stop.Lng] as [number, number])
            );
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }
}
