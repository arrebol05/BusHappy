/**
 * BusHappy Main Application Component
 */

import { BusHappyAPI, GeocodingService } from '@services/api.service';
import { MapService } from '@services/map.service';
import type { BusStop, PlannedRoute, Location, AppState, SelectedPoint } from '@types/index';
import { CONFIG, MESSAGES, ICONS } from '@utils/constants';
import '@styles/main.css';

export class BusHappyApp {
    private api: BusHappyAPI;
    private geocoding: GeocodingService;
    private map: MapService;
    private state: AppState;
    private searchTimeout: number | null = null;

    constructor() {
        this.api = new BusHappyAPI();
        this.geocoding = new GeocodingService();

        // Initialize map centered on Ho Chi Minh City
        this.map = new MapService('map');

        // Initialize state
        this.state = {
            wheelchairMode: false,
            useOldAddresses: true,
            currentLocation: null,
            pinnedLocation: null,
            selectedStop: null,
            planningMode: false,
            planningStep: null,
            selectedDestination: null,
            selectedOrigin: null,
            searchMode: 'stops'
        };

        this.init();
    }

    private init(): void {
        this.setupEventListeners();
        this.checkAPIHealth();

        setTimeout(() => this.getUserLocation(), CONFIG.UI.LOADING_DELAY_MS);
    }

    private setupEventListeners(): void {
        // Settings button
        document.getElementById('settings-btn')?.addEventListener('click', () => {
            this.toggleSettingsPanel();
        });

        // Search tabs
        const stopsTab = document.getElementById('tab-stops');
        const locationsTab = document.getElementById('tab-locations');

        stopsTab?.addEventListener('click', () => {
            this.state.searchMode = 'stops';
            this.updateSearchTabs();
            this.clearSearchInput();
        });

        locationsTab?.addEventListener('click', () => {
            this.state.searchMode = 'locations';
            this.updateSearchTabs();
            this.clearSearchInput();
        });

        // Search input
        const searchInput = document.getElementById('search-input') as HTMLInputElement;
        searchInput?.addEventListener('input', (e) => {
            const query = (e.target as HTMLInputElement).value.trim();
            this.onSearchInput(query);
        });

        // Action buttons
        document.getElementById('nearby-btn')?.addEventListener('click', () => {
            this.getUserLocation();
        });

        document.getElementById('plan-route-btn')?.addEventListener('click', () => {
            this.startRoutePlanning();
        });

        // Map click handler
        this.map.onClick((lat, lon) => this.onMapClick(lat, lon));

        // Stop marker click handler
        this.map.setMarkerClickHandler((stop: BusStop) => {
            if (this.state.planningMode) {
                this.selectBusStopForPlanning(stop);
            } else {
                this.loadStopDetails(stop.stop_id);
            }
        });
    }

    private updateSearchTabs(): void {
        const stopsTab = document.getElementById('tab-stops');
        const locationsTab = document.getElementById('tab-locations');

        if (this.state.searchMode === 'stops') {
            stopsTab?.classList.add('active');
            locationsTab?.classList.remove('active');
            (document.getElementById('search-input') as HTMLInputElement).placeholder = 'Search for bus stops...';
        } else {
            stopsTab?.classList.remove('active');
            locationsTab?.classList.add('active');
            (document.getElementById('search-input') as HTMLInputElement).placeholder = 'Search for locations...';
        }
    }

    private clearSearchInput(): void {
        const searchInput = document.getElementById('search-input') as HTMLInputElement;
        if (searchInput) searchInput.value = '';
    }

    private async checkAPIHealth(): Promise<void> {
        try {
            const health = await this.api.healthCheck();
            console.log('✅ API Connected:', health);
        } catch (error) {
            this.showError(MESSAGES.ERROR.API_CONNECT);
            console.error('❌ API Health Check Failed:', error);
        }
    }

    private getUserLocation(): void {
        if (navigator.geolocation) {
            this.showLoading(MESSAGES.LOADING.LOCATION);

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.state.currentLocation = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude
                    };

                    // Zoom animation: start zoomed out, then zoom in
                    this.map.setView(this.state.currentLocation.lat, this.state.currentLocation.lon, CONFIG.MAP.DEFAULT_ZOOM);
                    setTimeout(() => {
                        if (this.state.currentLocation) {
                            this.map.setView(this.state.currentLocation.lat, this.state.currentLocation.lon, CONFIG.MAP.DETAIL_ZOOM);
                        }
                    }, 300);

                    this.map.addMarker('user-location', this.state.currentLocation.lat, this.state.currentLocation.lon, {
                        icon: ICONS.USER_LOCATION,
                        popup: 'Your Location'
                    });

                    this.loadNearbyStops(this.state.currentLocation.lat, this.state.currentLocation.lon);
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    this.showNotification(MESSAGES.ERROR.GEOLOCATION, 'error');

                    // Set map view to default center with zoom animation
                    this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DEFAULT_ZOOM);
                    setTimeout(() => {
                        this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DETAIL_ZOOM);
                    }, 300);

                    this.loadNearbyStops(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1]);
                }
            );
        } else {
            this.showError(MESSAGES.ERROR.GEOLOCATION_UNSUPPORTED);

            // Set map view to default center with zoom animation
            this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DEFAULT_ZOOM);
            setTimeout(() => {
                this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DETAIL_ZOOM);
            }, 300);

            this.loadNearbyStops(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1]);
        }
    }

    private async loadNearbyStops(lat: number, lon: number, radius: number = CONFIG.ROUTING.DEFAULT_RADIUS_KM): Promise<void> {
        try {
            this.showLoading(MESSAGES.LOADING.NEARBY);
            this.map.clearAll();

            const data = await this.api.getNearbyStops(lat, lon, radius, this.state.wheelchairMode);

            // Add appropriate marker based on location type
            if (this.state.pinnedLocation) {
                // Show pinned location marker if custom location is set
                this.map.addMarker('pinned-location', lat, lon, {
                    icon: '📍',
                    popup: 'Pinned Location'
                });
            } else if (this.state.currentLocation) {
                // Show user location marker if geolocation is available
                this.map.addMarker('user-location', this.state.currentLocation.lat, this.state.currentLocation.lon, {
                    icon: ICONS.USER_LOCATION,
                    popup: 'Your Location'
                });
            } else {
                // Show default center marker when neither user location nor pinned location exists
                this.map.addMarker('default-location', lat, lon, {
                    icon: '📍',
                    popup: 'Default Location (HCMC Center)'
                });
            }

            // Add stop markers
            data.stops.forEach(stop => {
                this.map.addStopMarker(stop, (s) => this.loadStopDetails(s.stop_id));
            });

            this.displayNearbyStops(data.stops, lat, lon);
        } catch (error) {
            this.showError(MESSAGES.ERROR.STOPS_FAILED + ': ' + (error as Error).message);
        }
    }

    private displayNearbyStops(stops: BusStop[], _centerLat?: number, _centerLon?: number): void {
        const contentArea = document.getElementById('content-area')!;

        let html = '';

        // Show pinned location info with reset button if pinned location is set
        if (this.state.pinnedLocation) {
            html += `
                <div style="padding: 15px; background: #fff4e6; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="font-size: 12px; color: #ea580c; margin-bottom: 4px;">📍 CUSTOM LOCATION</div>
                        <div style="font-size: 13px; color: #9a3412;">Showing nearby stops from pinned location</div>
                    </div>
                    <button class="btn btn-secondary" id="reset-pinpoint" style="padding: 8px 16px; font-size: 13px;">Reset</button>
                </div>
            `;
        }

        if (stops.length === 0) {
            html += `
        <div class="empty-state">
          <div class="empty-state-icon">😕</div>
          <p>No ${this.state.wheelchairMode ? 'accessible ' : ''}stops found nearby</p>
        </div>
      `;
            contentArea.innerHTML = html;

            // Add reset pinpoint handler even when no stops
            document.getElementById('reset-pinpoint')?.addEventListener('click', () => {
                this.resetPinpoint();
            });
            return;
        }

        html += `<div class="section-title">📍 Nearby Stops (${stops.length})</div>`;

        stops.forEach(stop => {
            html += this.createStopCardHTML(stop);
        });

        contentArea.innerHTML = html;

        // Add reset pinpoint handler
        document.getElementById('reset-pinpoint')?.addEventListener('click', () => {
            this.resetPinpoint();
        });

        // Add click handlers
        stops.forEach(stop => {
            document.getElementById(`stop-${stop.stop_id}`)?.addEventListener('click', () => {
                this.loadStopDetails(stop.stop_id);
            });
        });
    }

    private async loadStopDetails(stopId: number): Promise<void> {
        try {
            this.showLoading(MESSAGES.LOADING.DETAILS);

            const data = await this.api.getStopDetails(stopId);
            this.state.selectedStop = data.stop;

            this.map.setView(data.stop.lat, data.stop.lon, CONFIG.MAP.DETAIL_ZOOM);

            this.displayStopDetails(data);
        } catch (error) {
            this.showError(MESSAGES.ERROR.DETAILS_FAILED + ': ' + (error as Error).message);
        }
    }

    private displayStopDetails(data: { stop: BusStop; upcoming_buses: any[] }): void {
        const contentArea = document.getElementById('content-area')!;
        const { stop, upcoming_buses } = data;
        const address = this.getStopAddress(stop);

        let html = `
      <div class="section-title">
        <span class="back-button" id="back-btn">← Back</span>
      </div>
      <div style="padding: 20px; background: white; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h2 style="font-size: 20px; margin-bottom: 10px; color: var(--text-primary);">${stop.stop_name}</h2>
        <div style="color: var(--text-light); font-size: 13px; margin-bottom: 8px;">Code: ${stop.stop_code}</div>
        ${address ? `<div style="color: var(--text-secondary); font-size: 13px; margin-bottom: 8px; line-height: 1.5;">📍 ${address}</div>` : ''}
        ${stop.routes ? `<div style="color: var(--text-secondary); font-size: 13px; margin-bottom: 8px; line-height: 1.5;">🚌 ${stop.routes.replace(/ \| /g, '<br>🚌 ')}</div>` : ''}
        ${stop.wheelchair_accessible ? '<div class="wheelchair-badge" style="margin-top: 8px;">♿ Wheelchair Accessible</div>' : ''}
      </div>
      <div class="section-title">🚌 Upcoming Buses</div>
    `;

        if (upcoming_buses.length === 0) {
            html += `
        <div class="empty-state">
          <div class="empty-state-icon">⏰</div>
          <p>No upcoming buses at this time</p>
        </div>
      `;
        } else {
            upcoming_buses.forEach(bus => {
                html += `
          <div class="bus-card">
            <div class="bus-route">🚌 Route ${bus.route_number}</div>
            <div class="bus-headsign">${bus.headsign || bus.route_name}</div>
            <div class="bus-time">⏰ Arrives at ${bus.arrival_time}</div>
            <div class="bus-details">
              <span>${bus.direction}</span>
              ${bus.wheelchair_accessible ? '<span>• ♿ Accessible</span>' : ''}
            </div>
          </div>
        `;
            });
        }

        contentArea.innerHTML = html;

        document.getElementById('back-btn')?.addEventListener('click', () => {
            if (this.state.currentLocation) {
                this.loadNearbyStops(this.state.currentLocation.lat, this.state.currentLocation.lon);
            } else {
                this.getUserLocation();
            }
        });
    }

    private onSearchInput(query: string): void {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < CONFIG.SEARCH.MIN_LENGTH) {
            this.hideSearchResults();
            return;
        }

        this.searchTimeout = window.setTimeout(() => {
            if (this.state.searchMode === 'stops') {
                this.searchStops(query);
            } else {
                this.searchLocations(query);
            }
        }, 500);
    }

    private async searchStops(query: string): Promise<void> {
        try {
            this.showLoading('Searching...');
            if (!this.state.planningMode) {
                this.map.clearAll();
            }

            const data = await this.api.searchStops(query, this.state.wheelchairMode);

            // Add markers
            data.results.forEach(stop => {
                const clickHandler = this.state.planningMode
                    ? (s: BusStop) => this.selectBusStopForPlanning(s)
                    : (s: BusStop) => this.loadStopDetails(s.stop_id);
                this.map.addStopMarker(stop as BusStop, clickHandler);
            });

            // Fit bounds if results exist
            if (data.results.length > 0) {
                const bounds = data.results.map(s => [s.lat, s.lon] as [number, number]);
                this.map.fitBounds(bounds, { padding: [50, 50] });
            }

            this.displaySearchResults(data.results, 'stops');
        } catch (error) {
            this.showError('Search failed: ' + (error as Error).message);
        }
    }

    private async searchLocations(query: string): Promise<void> {
        try {
            const results = await this.geocoding.searchLocation(query);
            this.displaySearchResults(results, 'locations');
        } catch (error) {
            console.error('Location search failed:', error);
        }
    }

    private displaySearchResults(results: any[], type: 'stops' | 'locations'): void {
        const contentArea = document.getElementById('content-area')!;

        if (results.length === 0) {
            contentArea.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <p>No results found</p>
        </div>
      `;
            return;
        }

        let html = '';

        // Show planning header if in planning mode
        if (this.state.planningMode) {
            const step = this.state.planningStep === 'destination' ? 'Destination' : 'Origin';
            html += `
                <div class="section-title">
                    <span class="back-button" id="back-btn">← Cancel</span>
                </div>
                <div style="padding: 20px; background: white; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="font-size: 18px; margin-bottom: 10px; color: var(--text-primary);">Select ${step}</h2>
                    <p style="color: var(--text-secondary); font-size: 14px;">Pick a location on the map or search for a bus stop</p>
                </div>
            `;
        }

        html += `<div class="section-title">🔍 Search Results (${results.length})</div>`;

        if (type === 'stops') {
            results.forEach((stop: any) => {
                html += this.createStopCardHTML(stop);
            });

            contentArea.innerHTML = html;

            if (this.state.planningMode) {
                document.getElementById('back-btn')?.addEventListener('click', () => {
                    this.cancelRoutePlanning();
                });
            }

            results.forEach((stop: any) => {
                document.getElementById(`stop-${stop.stop_id}`)?.addEventListener('click', () => {
                    if (this.state.planningMode) {
                        this.selectBusStopForPlanning(stop as BusStop);
                    } else {
                        this.loadStopDetails(stop.stop_id);
                    }
                });
            });
        } else {
            results.forEach((location: any, index: number) => {
                // Split display_name into name and address
                const parts = location.display_name.split(',');
                const name = parts[0]?.trim() || location.display_name;
                const address = parts.length > 1 ? parts.slice(1).join(',').trim() : '';

                html += `
          <div class="stop-card" id="location-${index}">
            <div class="stop-name">${name}</div>
            ${address ? `<div class="stop-address" title="${address}">${address}</div>` : ''}
            <div class="stop-code">${location.type}</div>
          </div>
        `;
            });

            contentArea.innerHTML = html;

            if (this.state.planningMode) {
                document.getElementById('back-btn')?.addEventListener('click', () => {
                    this.cancelRoutePlanning();
                });
            }

            results.forEach((location: any, index: number) => {
                document.getElementById(`location-${index}`)?.addEventListener('click', () => {
                    if (this.state.planningMode) {
                        this.selectLocationForPlanning(location.lat, location.lon, location.display_name);
                    } else {
                        this.selectLocation(location.lat, location.lon, location.display_name);
                    }
                });
            });
        }
    }

    private selectLocation(lat: number, lon: number, _name: string): void {
        this.state.pinnedLocation = { lat, lon };
        this.map.setView(lat, lon, 16);
        this.loadNearbyStops(lat, lon, 0.5);
    }

    private resetPinpoint(): void {
        this.state.pinnedLocation = null;

        if (this.state.currentLocation) {
            // Zoom animation: zoom out first, then zoom in
            const currentLoc = this.state.currentLocation;
            this.map.setView(currentLoc.lat, currentLoc.lon, CONFIG.MAP.DEFAULT_ZOOM);
            setTimeout(() => {
                this.map.setView(currentLoc.lat, currentLoc.lon, CONFIG.MAP.DETAIL_ZOOM);
            }, 300);
            this.loadNearbyStops(currentLoc.lat, currentLoc.lon);
        } else {
            // Zoom animation for default center
            this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DEFAULT_ZOOM);
            setTimeout(() => {
                this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DETAIL_ZOOM);
            }, 300);
            this.loadNearbyStops(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1]);
        }

        this.showNotification('Pinpoint reset to default location', 'success');
    }

    private hideSearchResults(): void {
        // Implementation if needed for dropdown
    }

    private toggleSettingsPanel(): void {
        const existingPanel = document.getElementById('settings-panel');
        if (existingPanel) {
            existingPanel.remove();
            return;
        }

        this.showSettingsPanel();
    }

    private showSettingsPanel(): void {
        const panel = document.createElement('div');
        panel.id = 'settings-panel';
        panel.className = 'settings-panel';
        panel.innerHTML = `
            <div class="settings-overlay" id="settings-overlay"></div>
            <div class="settings-content">
                <div class="settings-header">
                    <h2>⚙️ Settings</h2>
                    <button class="settings-close" id="settings-close">✕</button>
                </div>
                <div class="settings-body">
                    <div class="settings-item">
                        <div class="settings-item-header">
                            <label class="settings-label">♿ Wheelchair Accessible Only</label>
                            <input type="checkbox" id="settings-wheelchair" ${this.state.wheelchairMode ? 'checked' : ''} />
                        </div>
                        <p class="settings-description">Show only wheelchair accessible bus stops and routes</p>
                    </div>
                    
                    <div class="settings-item">
                        <div class="settings-item-header">
                            <label class="settings-label">📍 Address Format</label>
                            <input type="checkbox" id="settings-old-address" ${!this.state.useOldAddresses ? 'checked' : ''} />
                        </div>
                        <p class="settings-description">OFF = Old address format (default) | ON = New address format</p>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // Event listeners
        document.getElementById('settings-close')?.addEventListener('click', () => {
            panel.remove();
        });

        document.getElementById('settings-overlay')?.addEventListener('click', () => {
            panel.remove();
        });

        document.getElementById('settings-wheelchair')?.addEventListener('change', (e) => {
            this.state.wheelchairMode = (e.target as HTMLInputElement).checked;
            this.onWheelchairModeChange();
        });

        document.getElementById('settings-old-address')?.addEventListener('change', (e) => {
            this.state.useOldAddresses = !(e.target as HTMLInputElement).checked;
            const format = this.state.useOldAddresses ? 'Old (Traditional)' : 'New (Modern)';
            this.showNotification(`Address format: ${format}`, 'success');

            // Reload current view to update addresses
            if (this.state.selectedStop) {
                this.loadStopDetails(this.state.selectedStop.stop_id);
            } else if (this.state.pinnedLocation) {
                this.loadNearbyStops(this.state.pinnedLocation.lat, this.state.pinnedLocation.lon);
            } else if (this.state.currentLocation) {
                this.loadNearbyStops(this.state.currentLocation.lat, this.state.currentLocation.lon);
            }
        });
    }

    private startRoutePlanning(): void {
        this.state.planningMode = true;
        this.state.planningStep = 'destination';
        this.state.selectedDestination = null;
        this.state.selectedOrigin = null;
        this.map.clearAll();

        this.showRoutePlanningUI();
        this.showNotification('Select your destination - click on map or search', 'success');
    }

    private showRoutePlanningUI(): void {
        const contentArea = document.getElementById('content-area')!;
        const step = this.state.planningStep === 'destination' ? 'Destination' : 'Origin';
        const icon = this.state.planningStep === 'destination' ? '🎯' : '🚌';

        let selectedInfo = '';
        if (this.state.planningStep === 'origin' && this.state.selectedDestination) {
            selectedInfo = `
                <div style="padding: 15px; background: #f0f9ff; border-radius: 8px; margin-bottom: 16px;">
                    <div style="font-size: 12px; color: #0284c7; margin-bottom: 4px;">DESTINATION</div>
                    <div style="font-weight: 600; color: #0c4a6e;">${this.state.selectedDestination.name}</div>
                </div>
            `;
        }

        contentArea.innerHTML = `
            <div class="section-title">
                <span class="back-button" id="back-btn">← Cancel</span>
            </div>
            <div style="padding: 20px; background: white; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
                    <div style="font-size: 32px;">${icon}</div>
                    <h2 style="font-size: 18px; color: var(--text-primary);">Select ${step}</h2>
                </div>
                ${selectedInfo}
                <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.6;">
                    • Click anywhere on the map to select a location<br>
                    • Or search for a bus stop using the search bar above
                </p>
            </div>
        `;

        document.getElementById('back-btn')?.addEventListener('click', () => {
            this.cancelRoutePlanning();
        });
    }

    private async onMapClick(lat: number, lon: number): Promise<void> {
        // Get address for this location
        this.showLoading('Getting location details...');
        let locationName = `Location (${lat.toFixed(5)}, ${lon.toFixed(5)})`;

        try {
            locationName = await this.geocoding.reverseGeocode(lat, lon);
        } catch (error) {
            console.error('Reverse geocoding failed:', error);
        }

        // Update search input with the location name
        const searchInput = document.getElementById('search-input') as HTMLInputElement;
        if (searchInput) {
            searchInput.value = locationName;
        }

        if (this.state.planningMode) {
            this.selectLocationForPlanning(lat, lon, locationName);
        } else {
            // In nearby stops mode, update pinpoint
            this.selectLocation(lat, lon, locationName);
        }
    }

    private selectLocationForPlanning(lat: number, lon: number, name: string): void {
        const selectedPoint: SelectedPoint = {
            location: { lat, lon },
            type: 'location',
            name
        };

        if (this.state.planningStep === 'destination') {
            this.state.selectedDestination = selectedPoint;
            this.map.addMarker('route-destination', lat, lon, {
                icon: '🎯',
                popup: `Destination: ${name}`
            });
            this.displaySelectedPoint(selectedPoint, 'destination');
        } else if (this.state.planningStep === 'origin') {
            this.state.selectedOrigin = selectedPoint;
            this.map.addMarker('route-origin', lat, lon, {
                icon: '🚌',
                popup: `Origin: ${name}`
            });
            this.executeRoutePlanning();
        }
    }

    private selectBusStopForPlanning(stop: BusStop): void {
        const selectedPoint: SelectedPoint = {
            location: { lat: stop.lat, lon: stop.lon },
            type: 'bus_stop',
            name: stop.stop_name,
            busStop: stop
        };

        if (this.state.planningStep === 'destination') {
            this.state.selectedDestination = selectedPoint;
            this.map.setView(stop.lat, stop.lon, CONFIG.MAP.DETAIL_ZOOM);
            this.map.addMarker('route-destination', stop.lat, stop.lon, {
                icon: '🎯',
                popup: `Destination: ${stop.stop_name}`
            });
            this.displaySelectedPoint(selectedPoint, 'destination');
        } else if (this.state.planningStep === 'origin') {
            this.state.selectedOrigin = selectedPoint;
            this.map.setView(stop.lat, stop.lon, CONFIG.MAP.DETAIL_ZOOM);
            this.map.addMarker('route-origin', stop.lat, stop.lon, {
                icon: '🚌',
                popup: `Origin: ${stop.stop_name}`
            });
            this.executeRoutePlanning();
        }
    }

    private displaySelectedPoint(point: SelectedPoint, step: 'destination' | 'origin'): void {
        const contentArea = document.getElementById('content-area')!;
        const stepLabel = step === 'destination' ? 'Destination' : 'Origin';
        const icon = step === 'destination' ? '🎯' : '🚌';

        let detailsHtml = '';
        if (point.type === 'bus_stop' && point.busStop) {
            const address = this.getStopAddress(point.busStop);
            detailsHtml = `
                <div style="padding: 20px; background: white; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 8px;">🚏 BUS STOP</div>
                    <h3 style="font-size: 18px; margin-bottom: 8px; color: var(--text-primary);">${point.busStop.stop_name}</h3>
                    <div style="color: var(--text-light); font-size: 13px; margin-bottom: 8px;">Code: ${point.busStop.stop_code}</div>
                    ${address ? `<div style="color: var(--text-secondary); font-size: 13px; margin-bottom: 8px; line-height: 1.5;">📍 ${address}</div>` : ''}
                    ${point.busStop.routes ? `<div style="color: var(--text-secondary); font-size: 13px; margin-bottom: 8px; line-height: 1.5;">🚌 ${point.busStop.routes.replace(/ \| /g, '<br>🚌 ')}</div>` : ''}
                    ${point.busStop.wheelchair_accessible ? '<div class="wheelchair-badge">♿ Wheelchair Accessible</div>' : ''}
                </div>
            `;
        } else {
            detailsHtml = `
                <div style="padding: 20px; background: white; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 8px;">📍 LOCATION</div>
                    <h3 style="font-size: 16px; color: var(--text-primary); line-height: 1.4;">${point.name}</h3>
                </div>
            `;
        }

        if (step === 'destination') {
            // After selecting destination, move to origin selection
            contentArea.innerHTML = `
                <div class="section-title">
                    <span class="back-button" id="back-btn">← Back</span>
                </div>
                <div style="padding: 20px; background: #f0f9ff; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; color: #0284c7; margin-bottom: 8px;">${stepLabel.toUpperCase()} SELECTED</div>
                    <div style="font-weight: 600; color: #0c4a6e; font-size: 16px;">${icon} ${point.name}</div>
                </div>
                ${detailsHtml}
                <button class="btn btn-primary" id="continue-btn" style="width: 100%; padding: 16px; font-size: 16px;">Continue to Select Origin</button>
            `;

            document.getElementById('back-btn')?.addEventListener('click', () => {
                this.state.selectedDestination = null;
                this.map.removeMarker('route-destination');
                this.showRoutePlanningUI();
            });

            document.getElementById('continue-btn')?.addEventListener('click', () => {
                this.state.planningStep = 'origin';

                // Reset map view to user location or default center with zoom animation
                if (this.state.currentLocation) {
                    const currentLoc = this.state.currentLocation;
                    this.map.setView(currentLoc.lat, currentLoc.lon, CONFIG.MAP.DEFAULT_ZOOM);
                    setTimeout(() => {
                        this.map.setView(currentLoc.lat, currentLoc.lon, CONFIG.MAP.DETAIL_ZOOM);
                    }, 300);
                } else {
                    this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DEFAULT_ZOOM);
                    setTimeout(() => {
                        this.map.setView(CONFIG.MAP.DEFAULT_CENTER[0], CONFIG.MAP.DEFAULT_CENTER[1], CONFIG.MAP.DETAIL_ZOOM);
                    }, 300);
                }

                this.showRoutePlanningUI();
                this.showNotification('Now select your origin point', 'success');
            });
        }
    }

    private async executeRoutePlanning(): Promise<void> {
        if (!this.state.selectedDestination || !this.state.selectedOrigin) return;

        this.state.planningMode = false;
        await this.planRoute(this.state.selectedOrigin.location, this.state.selectedDestination.location);
    }

    private async planRoute(from: Location, to: Location): Promise<void> {
        try {
            this.showLoading('Planning your route...');

            const data = await this.api.planRoute(
                from.lat,
                from.lon,
                to.lat,
                to.lon,
                this.state.wheelchairMode
            );

            this.displayRoutePlan(data.routes);
        } catch (error) {
            this.showError('Route planning failed: ' + (error as Error).message);
            this.cancelRoutePlanning();
        }
    }

    private displayRoutePlan(routes: PlannedRoute[]): void {
        const contentArea = document.getElementById('content-area')!;

        if (routes.length === 0) {
            contentArea.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">😕</div>
          <p style="margin-bottom: 20px;">No routes found. Try selecting different points or increase search radius.</p>
          <button class="btn btn-primary" id="try-again">Try Again</button>
        </div>
      `;

            document.getElementById('try-again')?.addEventListener('click', () => {
                this.startRoutePlanning();
            });
            return;
        }

        let html = `
      <div class="section-title">
        <span class="back-button" id="back-btn">← Back</span>
      </div>
      <div class="section-title">🗺️ Recommended Routes (${routes.length})</div>
    `;

        routes.forEach((route, index) => {
            html += `
        <div class="route-plan-card">
          <div class="route-plan-header">
            <span>Option ${index + 1}</span>
            <span style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">
              📏 ${route.total_walk_distance_km} km total walk
            </span>
          </div>
          
          <div class="route-step">
            <div class="route-step-icon">🚶</div>
            <div class="route-step-content">
              <div class="route-step-title">Walk to ${route.start_stop.name}</div>
              <div class="route-step-desc">${route.start_stop.walk_distance_km} km</div>
            </div>
          </div>
          
          <div class="route-step">
            <div class="route-step-icon">🚌</div>
            <div class="route-step-content">
              <div class="route-step-title">Take Bus ${route.route.number}</div>
              <div class="route-step-desc">${route.route.name}</div>
            </div>
          </div>
          
          <div class="route-step">
            <div class="route-step-icon">🚶</div>
            <div class="route-step-content">
              <div class="route-step-title">Walk to destination</div>
              <div class="route-step-desc">${route.end_stop.walk_distance_km} km from ${route.end_stop.name}</div>
            </div>
          </div>
        </div>
      `;
        });

        contentArea.innerHTML = html;

        document.getElementById('back-btn')?.addEventListener('click', () => {
            this.cancelRoutePlanning();
        });
    }

    private cancelRoutePlanning(): void {
        this.state.planningMode = false;
        this.state.planningStep = null;
        this.state.selectedDestination = null;
        this.state.selectedOrigin = null;
        this.map.clearAll();

        // Clear search input
        const searchInput = document.getElementById('search-input') as HTMLInputElement;
        if (searchInput) {
            searchInput.value = '';
        }

        if (this.state.currentLocation) {
            this.loadNearbyStops(this.state.currentLocation.lat, this.state.currentLocation.lon);
        } else {
            const contentArea = document.getElementById('content-area')!;
            contentArea.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🚏</div>
          <p>Search for stops or find nearby stops to get started</p>
        </div>
      `;
        }
    }

    private onWheelchairModeChange(): void {
        if (this.state.pinnedLocation) {
            this.loadNearbyStops(this.state.pinnedLocation.lat, this.state.pinnedLocation.lon);
        } else if (this.state.currentLocation) {
            this.loadNearbyStops(this.state.currentLocation.lat, this.state.currentLocation.lon);
        }
    }

    private createStopCardHTML(stop: BusStop): string {
        const address = this.getStopAddress(stop);
        return `
      <div class="stop-card" id="stop-${stop.stop_id}">
        <div class="stop-card-header">
          <div class="stop-name">${stop.stop_name}</div>
          ${stop.distance_km ? `<div class="stop-distance">${stop.distance_km} km</div>` : ''}
        </div>
        <div class="stop-code">Code: ${stop.stop_code}</div>
        ${address ? `<div class="stop-address" title="${address}">${address}</div>` : ''}
        ${stop.routes ? `<div class="stop-routes">${stop.routes.replace(/ \| /g, '<br>')}</div>` : ''}
        ${stop.wheelchair_accessible ? '<div class="wheelchair-badge">♿ Accessible</div>' : ''}
      </div>
    `;
    }

    private getStopAddress(stop: BusStop): string {
        if (this.state.useOldAddresses && stop.old_address) {
            return stop.old_address;
        } else if (!this.state.useOldAddresses && stop.new_address) {
            return stop.new_address;
        } else if (stop.description) {
            return stop.description;
        }
        return '';
    }

    private showLoading(message: string = 'Loading...'): void {
        const contentArea = document.getElementById('content-area')!;
        contentArea.innerHTML = `
      <div class="spinner"></div>
      <div class="loading-text">${message}</div>
    `;
    }

    private showError(message: string): void {
        const contentArea = document.getElementById('content-area')!;
        contentArea.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <p>${message}</p>
      </div>
    `;
    }

    private showNotification(message: string, type: 'success' | 'error' = 'success'): void {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
      <div style="font-size: 20px;">${type === 'success' ? '✅' : '❌'}</div>
      <div>${message}</div>
    `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, CONFIG.UI.NOTIFICATION_DURATION_MS);
    }
}


