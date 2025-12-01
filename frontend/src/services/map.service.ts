/**
 * Map Service for BusHappy - Leaflet.js Integration
 */

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { BusStop, Location, PlannedRoute } from '@types/index';
import { CONFIG } from '@utils/constants';

// Fix Leaflet default marker icon issue with Webpack
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
});

export interface MarkerData {
    id: string;
    marker: L.Marker;
    data?: any;
}

export class MapService {
    private map: L.Map;
    private markers: Map<string, MarkerData> = new Map();
    private polylines: L.Polyline[] = [];
    private onMarkerClick?: (data: any) => void;

    constructor(containerId: string, center: [number, number] = CONFIG.MAP.DEFAULT_CENTER, zoom: number = CONFIG.MAP.DEFAULT_ZOOM) {
        this.map = L.map(containerId).setView(center, zoom);

        L.tileLayer(CONFIG.MAP.TILE_URL, {
            attribution: CONFIG.MAP.ATTRIBUTION,
            maxZoom: CONFIG.MAP.MAX_ZOOM
        }).addTo(this.map);
    }

    setView(lat: number, lon: number, zoom?: number): void {
        this.map.setView([lat, lon], zoom);
    }

    fitBounds(bounds: L.LatLngBoundsExpression, options?: L.FitBoundsOptions): void {
        this.map.fitBounds(bounds, options);
    }

    onClick(callback: (lat: number, lon: number) => void): void {
        this.map.on('click', (e: L.LeafletMouseEvent) => {
            callback(e.latlng.lat, e.latlng.lng);
        });
    }

    setMarkerClickHandler(handler: (data: any) => void): void {
        this.onMarkerClick = handler;
    }

    addMarker(
        id: string,
        lat: number,
        lon: number,
        options: {
            icon?: string;
            color?: string;
            popup?: string;
            data?: any;
        } = {}
    ): L.Marker {
        // Remove existing marker with same ID
        this.removeMarker(id);

        let marker: L.Marker;

        if (options.icon) {
            // Custom HTML icon
            const iconHtml = `<div style="font-size: 28px; filter: drop-shadow(2px 2px 2px rgba(0,0,0,0.3));">${options.icon}</div>`;
            const customIcon = L.divIcon({
                html: iconHtml,
                className: 'custom-marker',
                iconSize: [30, 30],
                iconAnchor: [15, 30]
            });
            marker = L.marker([lat, lon], { icon: customIcon });
        } else {
            // Default marker
            marker = L.marker([lat, lon]);
        }

        marker.addTo(this.map);

        if (options.popup) {
            marker.bindPopup(options.popup);
        }

        if (options.data && this.onMarkerClick) {
            marker.on('click', () => {
                this.onMarkerClick?.(options.data);
            });
        }

        this.markers.set(id, { id, marker, data: options.data });

        return marker;
    }

    addStopMarker(stop: BusStop, onClick?: (stop: BusStop) => void): void {
        const icon = stop.wheelchair_accessible ? '♿' : '🚏';

        const popup = `
      <div style="min-width: 200px;">
        <div style="font-weight: 600; color: #333; font-size: 15px; margin-bottom: 8px;">
          ${stop.stop_name}
        </div>
        <div style="color: #999; font-size: 12px; margin-bottom: 10px;">
          Code: ${stop.stop_code}
        </div>
        ${stop.distance_km ? `
          <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
            📏 ${stop.distance_km} km away
          </div>
        ` : ''}
        ${stop.wheelchair_accessible ? '<div style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; display: inline-block; margin-bottom: 8px;">♿ Accessible</div>' : ''}
      </div>
    `;

        const marker = this.addMarker(`stop-${stop.stop_id}`, stop.lat, stop.lon, {
            icon,
            popup,
            data: stop
        });

        if (onClick) {
            marker.on('click', () => onClick(stop));
        }
    }

    removeMarker(id: string): void {
        const markerData = this.markers.get(id);
        if (markerData) {
            this.map.removeLayer(markerData.marker);
            this.markers.delete(id);
        }
    }

    clearMarkers(): void {
        this.markers.forEach(({ marker }) => this.map.removeLayer(marker));
        this.markers.clear();
    }

    addPolyline(
        coordinates: [number, number][],
        options: {
            color?: string;
            weight?: number;
            opacity?: number;
            dashArray?: string;
        } = {}
    ): L.Polyline {
        const polyline = L.polyline(coordinates, {
            color: options.color || '#667eea',
            weight: options.weight || 4,
            opacity: options.opacity || 0.7,
            dashArray: options.dashArray
        }).addTo(this.map);

        this.polylines.push(polyline);

        return polyline;
    }

    clearPolylines(): void {
        this.polylines.forEach(polyline => this.map.removeLayer(polyline));
        this.polylines = [];
    }

    clearAll(): void {
        this.clearMarkers();
        this.clearPolylines();
    }

    showRoute(route: PlannedRoute, startLoc: Location, endLoc: Location): void {
        // Add start marker
        this.addMarker('route-start', startLoc.lat, startLoc.lon, {
            icon: '🟢',
            popup: 'Start Point'
        });

        // Add start stop marker
        this.addMarker(
            'route-start-stop',
            route.start_stop.id,
            route.start_stop.id,
            {
                icon: '🚏',
                popup: `Walk ${route.start_stop.walk_distance_km} km to ${route.start_stop.name}`
            }
        );

        // Add end stop marker
        this.addMarker(
            'route-end-stop',
            route.end_stop.id,
            route.end_stop.id,
            {
                icon: '🚏',
                popup: `${route.end_stop.name} - Walk ${route.end_stop.walk_distance_km} km to destination`
            }
        );

        // Add end marker
        this.addMarker('route-end', endLoc.lat, endLoc.lon, {
            icon: '🔴',
            popup: 'Destination'
        });
    }

    getMap(): L.Map {
        return this.map;
    }

    invalidateSize(): void {
        this.map.invalidateSize();
    }
}
