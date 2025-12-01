/**
 * Dashboard Main Application
 */

import { DashboardMapService } from '@dashboard/map.service';
import { DashboardAPI } from '@dashboard/api.service';
import type {
    DashboardRoute,
    DashboardState,
    RouteStats,
    RouteStop,
    RouteComparison
} from '@dashboard/types';

export class DashboardApp {
    private state: DashboardState;
    private mapService: DashboardMapService;
    private api: DashboardAPI;
    private originalRoutes: Map<number, DashboardRoute> = new Map();
    private disabilityOptimizationResults: any = null;

    constructor() {
        this.state = {
            mode: 'design',
            routes: [],
            selectedRoute: null,
            systemStats: null,
            routeStats: new Map(),
            hasChanges: false,
            currentComparison: null,
            editingDirection: null
        };

        this.mapService = new DashboardMapService();
        this.api = new DashboardAPI();

        this.initialize();
    }

    private async initialize(): Promise<void> {
        // Initialize map
        this.mapService.initialize('dashboard-map');

        // Setup event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();
    }

    private setupEventListeners(): void {
        // Mode switcher
        document.getElementById('mode-schedule-btn')?.addEventListener('click', () => {
            this.switchMode('schedule');
        });

        document.getElementById('mode-design-btn')?.addEventListener('click', () => {
            this.switchMode('design');
        });

        document.getElementById('mode-disability-btn')?.addEventListener('click', () => {
            this.switchMode('disability');
        });

        // Map controls
        document.getElementById('reset-view-btn')?.addEventListener('click', () => {
            this.mapService.resetView();
        });

        document.getElementById('toggle-labels-btn')?.addEventListener('click', () => {
            this.mapService.toggleLabels();
        });

        // Route operations
        document.getElementById('deselect-route-btn')?.addEventListener('click', () => {
            this.deselectRoute();
        });

        document.getElementById('edit-stops-btn')?.addEventListener('click', () => {
            this.openEditStopsModal();
        });

        document.getElementById('add-stop-btn')?.addEventListener('click', () => {
            this.openAddStopModal();
        });

        document.getElementById('remove-stop-btn')?.addEventListener('click', () => {
            this.openRemoveStopModal();
        });

        document.getElementById('optimize-route-btn')?.addEventListener('click', () => {
            this.optimizeRoute();
        });

        document.getElementById('optimize-system-btn')?.addEventListener('click', () => {
            this.optimizeSystem();
        });

        document.getElementById('save-plan-btn')?.addEventListener('click', () => {
            this.savePlan();
        });

        // Modal controls
        document.getElementById('close-modal-btn')?.addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('cancel-modal-btn')?.addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('apply-modal-btn')?.addEventListener('click', () => {
            this.applyModalChanges();
        });

        // Disability mode controls
        document.getElementById('run-disability-optimization-btn')?.addEventListener('click', () => {
            this.runDisabilityOptimization();
        });

        document.getElementById('apply-disability-optimization-btn')?.addEventListener('click', () => {
            this.applyDisabilityOptimization();
        });

        document.getElementById('export-disability-results-btn')?.addEventListener('click', () => {
            this.exportDisabilityResults();
        });

        document.getElementById('reset-disability-sandbox-btn')?.addEventListener('click', () => {
            this.resetSandbox('disability');
        });

        document.getElementById('reset-schedule-sandbox-btn')?.addEventListener('click', () => {
            this.resetSandbox('schedule');
        });

        document.getElementById('reset-design-sandbox-btn')?.addEventListener('click', () => {
            this.resetSandbox('design');
        });
    }

    private async loadData(): Promise<void> {
        try {
            // Load all routes with details
            const routes = await this.api.getAllRoutesDetailed();
            this.state.routes = routes;

            // Store original routes for comparison
            routes.forEach(route => {
                this.originalRoutes.set(route.route_id, JSON.parse(JSON.stringify(route)));
            });

            // Load system stats
            const systemStats = await this.api.getSystemStats();
            this.state.systemStats = systemStats;

            // Set up route click callback for isolation feature
            this.mapService.setRouteClickCallback((routeId: number) => {
                this.selectRoute(routeId);
            });

            // Render routes on map
            this.mapService.renderRoutes(routes);

            // Update UI
            this.updateSystemStatsUI();
            this.renderRouteLegend();
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showNotification('Failed to load data', 'error');
        }
    }

    private switchMode(mode: 'schedule' | 'design' | 'disability'): void {
        this.state.mode = mode;

        // Update UI
        const scheduleModeContent = document.getElementById('schedule-mode-content');
        const designModeContent = document.getElementById('design-mode-content');
        const disabilityModeContent = document.getElementById('disability-mode-content');
        const scheduleBtn = document.getElementById('mode-schedule-btn');
        const designBtn = document.getElementById('mode-design-btn');
        const disabilityBtn = document.getElementById('mode-disability-btn');

        // Hide all mode contents
        scheduleModeContent?.style.setProperty('display', 'none');
        designModeContent?.style.setProperty('display', 'none');
        disabilityModeContent?.style.setProperty('display', 'none');

        // Remove active class from all buttons
        scheduleBtn?.classList.remove('active');
        designBtn?.classList.remove('active');
        disabilityBtn?.classList.remove('active');

        // Show selected mode and activate button
        if (mode === 'schedule') {
            scheduleModeContent?.style.setProperty('display', 'block');
            scheduleBtn?.classList.add('active');
            // Clear map for schedule mode
            this.mapService.clearAllRoutes();
        } else if (mode === 'design') {
            designModeContent?.style.setProperty('display', 'block');
            designBtn?.classList.add('active');
            // Show all routes with different colors for design mode
            this.mapService.clearAllRoutes();
            this.mapService.renderRoutes(this.state.routes);
        } else if (mode === 'disability') {
            disabilityModeContent?.style.setProperty('display', 'block');
            disabilityBtn?.classList.add('active');
            this.loadDisabilityData();
        }
    }

    private updateSystemStatsUI(): void {
        if (!this.state.systemStats) return;

        const stats = this.state.systemStats;
        document.getElementById('stat-total-routes')!.textContent = stats.total_routes.toString();
        document.getElementById('stat-total-stops')!.textContent = stats.unique_stops.toString();
        document.getElementById('stat-avg-length')!.textContent = `${stats.avg_route_length_km.toFixed(1)} km`;
        document.getElementById('stat-coverage')!.textContent = `${stats.total_coverage_area_km2.toFixed(1)} km²`;
    }

    private renderRouteLegend(): void {
        const legendContainer = document.getElementById('route-legend');
        if (!legendContainer) return;

        legendContainer.innerHTML = '';

        this.state.routes.forEach(route => {
            const color = this.mapService.getRouteColor(route.route_id);

            const item = document.createElement('div');
            item.className = 'route-legend-item';
            item.dataset.routeId = route.route_id.toString();

            item.innerHTML = `
                <div class="route-color-box" style="background-color: ${color};"></div>
                <div class="route-legend-info">
                    <div class="route-legend-name">${route.route_name}</div>
                    <div class="route-legend-number">Route ${route.route_number}</div>
                </div>
            `;

            item.addEventListener('click', () => {
                this.selectRoute(route.route_id);
            });

            legendContainer.appendChild(item);
        });
    }

    private async selectRoute(routeId: number): Promise<void> {
        const route = this.state.routes.find(r => r.route_id === routeId);
        if (!route) return;

        this.state.selectedRoute = route;

        // Different behavior based on mode
        if (this.state.mode === 'design') {
            // In design mode, only isolate the route visually
            this.mapService.selectRoute(routeId);
            this.mapService.fitBoundsToRoute(route);

            // Don't show route info panel in design mode - just isolate the route
            const routeInfoSection = document.getElementById('route-info-section');
            if (routeInfoSection) {
                routeInfoSection.style.display = 'none';
            }
        } else {
            // In other modes, show full route details
            this.mapService.selectRoute(routeId);

            // Update legend selection
            document.querySelectorAll('.route-legend-item').forEach(item => {
                if (item.getAttribute('data-route-id') === routeId.toString()) {
                    item.classList.add('selected');
                } else {
                    item.classList.remove('selected');
                }
            });

            // Show route info section
            const routeInfoSection = document.getElementById('route-info-section');
            if (routeInfoSection) {
                routeInfoSection.style.display = 'block';
            }

            // Load and display route stats
            try {
                const stats = await this.api.getRouteStats(routeId);
                this.state.routeStats.set(routeId, stats);
                this.updateRouteStatsUI(route, stats);
            } catch (error) {
                console.error('Failed to load route stats:', error);
            }

            // Fit map to route
            this.mapService.fitBoundsToRoute(route);
        }
    }

    private deselectRoute(): void {
        this.state.selectedRoute = null;
        this.state.currentComparison = null;
        this.state.editingDirection = null;

        this.mapService.deselectRoute();

        // Update legend
        document.querySelectorAll('.route-legend-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Hide route info section
        const routeInfoSection = document.getElementById('route-info-section');
        if (routeInfoSection) {
            routeInfoSection.style.display = 'none';
        }

        // Hide change summary
        const changeSummary = document.getElementById('change-summary');
        if (changeSummary) {
            changeSummary.style.display = 'none';
        }
    }

    private updateRouteStatsUI(route: DashboardRoute, stats: RouteStats): void {
        document.getElementById('selected-route-name')!.textContent = route.route_name;
        document.getElementById('route-number')!.textContent = route.route_number;
        document.getElementById('route-outbound-stops')!.textContent = stats.outbound_stops.toString();
        document.getElementById('route-inbound-stops')!.textContent = stats.inbound_stops.toString();
        document.getElementById('route-length')!.textContent = `${stats.route_length_km.toFixed(1)} km`;
    }

    private openEditStopsModal(): void {
        if (!this.state.selectedRoute) return;

        const modal = document.getElementById('edit-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');

        if (!modal || !modalTitle || !modalBody) return;

        modalTitle.textContent = 'Edit Route Stops';

        modalBody.innerHTML = `
            <div style="margin-bottom: 1rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Direction:</label>
                <select id="edit-direction-select" style="width: 100%; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 0.375rem;">
                    <option value="outbound">Outbound</option>
                    <option value="inbound">Inbound</option>
                </select>
            </div>
            <div id="stops-list-container">
                ${this.renderStopsList('outbound')}
            </div>
        `;

        // Add event listener for direction change
        const directionSelect = document.getElementById('edit-direction-select') as HTMLSelectElement;
        directionSelect?.addEventListener('change', (e) => {
            const direction = (e.target as HTMLSelectElement).value as 'outbound' | 'inbound';
            const container = document.getElementById('stops-list-container');
            if (container) {
                container.innerHTML = this.renderStopsList(direction);
                this.setupDragAndDrop();
            }
        });

        modal.style.display = 'flex';
        this.setupDragAndDrop();
    }

    private renderStopsList(direction: 'outbound' | 'inbound'): string {
        if (!this.state.selectedRoute) return '';

        const stops = direction === 'outbound'
            ? this.state.selectedRoute.outbound_stops
            : this.state.selectedRoute.inbound_stops;

        return `
            <ul class="stop-list" data-direction="${direction}">
                ${stops.map((stop) => `
                    <li class="stop-list-item" draggable="true" data-stop-id="${stop.stop_id}" data-sequence="${stop.sequence}">
                        <span class="stop-drag-handle">☰</span>
                        <div class="stop-info">
                            <div class="stop-name">${stop.stop_name}</div>
                            <div class="stop-sequence">Stop #${stop.sequence}</div>
                        </div>
                        <div class="stop-actions">
                            <button class="btn-icon" onclick="dashboardApp.removeStopFromList(${stop.stop_id}, '${direction}')" title="Remove">🗑️</button>
                        </div>
                    </li>
                `).join('')}
            </ul>
        `;
    }

    private setupDragAndDrop(): void {
        const stopItems = document.querySelectorAll('.stop-list-item');

        stopItems.forEach(item => {
            item.addEventListener('dragstart', this.handleDragStart.bind(this));
            item.addEventListener('dragover', this.handleDragOver.bind(this));
            item.addEventListener('drop', this.handleDrop.bind(this));
            item.addEventListener('dragend', this.handleDragEnd.bind(this));
        });
    }

    private handleDragStart(e: Event): void {
        const target = e.target as HTMLElement;
        target.classList.add('dragging');
        if (e instanceof DragEvent && e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', target.innerHTML);
        }
    }

    private handleDragOver(e: Event): boolean {
        if (e.preventDefault) {
            e.preventDefault();
        }
        if (e instanceof DragEvent && e.dataTransfer) {
            e.dataTransfer.dropEffect = 'move';
        }
        return false;
    }

    private handleDrop(e: Event): boolean {
        if (e.stopPropagation) {
            e.stopPropagation();
        }

        const target = e.target as HTMLElement;
        const dragging = document.querySelector('.dragging') as HTMLElement;

        if (dragging !== target) {
            const list = target.closest('.stop-list');
            const items = Array.from(list?.querySelectorAll('.stop-list-item') || []);
            const dragIndex = items.indexOf(dragging);
            const targetIndex = items.indexOf(target.closest('.stop-list-item')!);

            if (dragIndex < targetIndex) {
                target.closest('.stop-list-item')?.after(dragging);
            } else {
                target.closest('.stop-list-item')?.before(dragging);
            }
        }

        return false;
    } private handleDragEnd(e: Event): void {
        const target = e.target as HTMLElement;
        target.classList.remove('dragging');
    }

    private openAddStopModal(): void {
        if (!this.state.selectedRoute) return;

        this.showNotification('Add stop feature: Click on the map to select a location for a new stop', 'info');
        // Placeholder for future implementation
    }

    private openRemoveStopModal(): void {
        if (!this.state.selectedRoute) return;

        this.showNotification('Remove stop feature: Select stops from the edit panel', 'info');
        // Can reuse edit stops modal
        this.openEditStopsModal();
    }

    removeStopFromList(stopId: number, direction: string): void {
        // This would update the route's stops array
        this.showNotification(`Removing stop ${stopId} from ${direction}`, 'info');
    }

    private async optimizeRoute(): Promise<void> {
        if (!this.state.selectedRoute) return;

        if (!confirm('Auto optimization may remove existing stops to improve efficiency. Continue?')) {
            return;
        }

        try {
            const result = await this.api.optimizeRoute(this.state.selectedRoute.route_id);
            this.showNotification(`Optimization completed. Efficiency gain: ${result.efficiency_gain.toFixed(1)}%`, 'success');

            if (result.removed_stops.length > 0) {
                this.showNotification(`Warning: ${result.removed_stops.length} stops will be removed`, 'warning');
            }
        } catch (error) {
            console.error('Optimization failed:', error);
            this.showNotification('Optimization failed', 'error');
        }
    }

    private async optimizeSystem(): Promise<void> {
        if (!confirm('System-wide optimization will analyze all routes and may remove stops. This cannot be undone. Continue?')) {
            return;
        }

        try {
            const result = await this.api.optimizeSystem();
            this.showNotification(`System optimization completed. Overall efficiency gain: ${result.efficiency_gain.toFixed(1)}%`, 'success');
        } catch (error) {
            console.error('System optimization failed:', error);
            this.showNotification('System optimization failed', 'error');
        }
    }

    private async applyModalChanges(): Promise<void> {
        // Get reordered stops from the modal
        const stopsList = document.querySelector('.stop-list');
        if (!stopsList || !this.state.selectedRoute) return;

        const direction = stopsList.getAttribute('data-direction') as 'outbound' | 'inbound';
        const stopItems = stopsList.querySelectorAll('.stop-list-item');

        const reorderedStops: RouteStop[] = Array.from(stopItems).map((item, index) => {
            const stopId = parseInt(item.getAttribute('data-stop-id') || '0');
            const originalStops = direction === 'outbound'
                ? this.state.selectedRoute!.outbound_stops
                : this.state.selectedRoute!.inbound_stops;
            const stop = originalStops.find(s => s.stop_id === stopId)!;

            return {
                ...stop,
                sequence: index + 1
            };
        });

        // Update the route
        if (direction === 'outbound') {
            this.state.selectedRoute.outbound_stops = reorderedStops;
        } else {
            this.state.selectedRoute.inbound_stops = reorderedStops;
        }

        // Calculate new stats and comparison
        await this.calculateRouteComparison(this.state.selectedRoute);

        // Update map
        this.mapService.updateRoute(this.state.selectedRoute);

        // Mark as having changes
        this.state.hasChanges = true;
        this.enableSaveButton();

        this.closeModal();
        this.showNotification('Route updated successfully', 'success');
    }

    private async calculateRouteComparison(route: DashboardRoute): Promise<void> {
        const original = this.originalRoutes.get(route.route_id);
        if (!original) return;

        try {
            const comparison = await this.api.compareRoutes(
                route.route_id,
                original.outbound_stops,
                original.inbound_stops,
                route.outbound_stops,
                route.inbound_stops
            );

            this.state.currentComparison = comparison;
            this.displayComparison(comparison);
        } catch (error) {
            console.error('Failed to calculate comparison:', error);
        }
    }

    private displayComparison(comparison: RouteComparison): void {
        const changeSummary = document.getElementById('change-summary');
        const changesList = document.getElementById('changes-list');
        const improvementsValue = document.getElementById('improvements-value');
        const decreasesValue = document.getElementById('decreases-value');

        if (!changeSummary || !changesList || !improvementsValue || !decreasesValue) return;

        changeSummary.style.display = 'block';

        // Display changes
        changesList.innerHTML = comparison.changes.map(change => `
            <div class="change-item">
                ${change.description}
            </div>
        `).join('');

        // Display improvements and decreases
        improvementsValue.textContent = comparison.improvements.join(', ') || 'None';
        decreasesValue.textContent = comparison.decreases.join(', ') || 'None';
    }

    private enableSaveButton(): void {
        const saveBtn = document.getElementById('save-plan-btn') as HTMLButtonElement;
        if (saveBtn) {
            saveBtn.disabled = false;
        }
    }

    private async savePlan(): Promise<void> {
        if (!this.state.hasChanges) return;

        if (!confirm('Save all route changes? This will update the system configuration.')) {
            return;
        }

        try {
            // Save all modified routes
            for (const route of this.state.routes) {
                const original = this.originalRoutes.get(route.route_id);
                if (!original) continue;

                // Check if route has been modified
                if (JSON.stringify(route) !== JSON.stringify(original)) {
                    await this.api.saveRouteChanges(
                        route.route_id,
                        route.outbound_stops,
                        route.inbound_stops
                    );
                }
            }

            this.showNotification('All changes saved successfully', 'success');
            this.state.hasChanges = false;

            // Update original routes
            this.state.routes.forEach(route => {
                this.originalRoutes.set(route.route_id, JSON.parse(JSON.stringify(route)));
            });

            // Disable save button
            const saveBtn = document.getElementById('save-plan-btn') as HTMLButtonElement;
            if (saveBtn) {
                saveBtn.disabled = true;
            }

            // Reload system stats
            const systemStats = await this.api.getSystemStats();
            this.state.systemStats = systemStats;
            this.updateSystemStatsUI();
        } catch (error) {
            console.error('Failed to save changes:', error);
            this.showNotification('Failed to save changes', 'error');
        }
    }

    private closeModal(): void {
        const modal = document.getElementById('edit-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    private showNotification(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
        // Simple console notification for now
        console.log(`[${type.toUpperCase()}] ${message}`);
        // In production, this would show a toast notification
        alert(`${type.toUpperCase()}: ${message}`);
    }

    // ============================================================================
    // DISABILITY SUPPORT OPTIMIZATION METHODS
    // ============================================================================

    private async loadDisabilityData(): Promise<void> {
        try {
            // Load stops data
            const response = await fetch('http://localhost:5000/api/disability/stops');
            const data = await response.json();

            if (data.success) {
                // Update stats
                document.getElementById('stat-disability-supported')!.textContent = data.with_support.toString();
                document.getElementById('stat-disability-needed')!.textContent = data.without_support.toString();

                // Render disability stops on map
                this.mapService.renderDisabilityStops(data.stops);
            }

            // Load real-time metrics
            await this.loadDisabilityMetrics();
        } catch (error) {
            console.error('Failed to load disability data:', error);
            this.showNotification('Failed to load disability support data', 'error');
        }
    }

    private async loadDisabilityMetrics(): Promise<void> {
        try {
            const response = await fetch('http://localhost:5000/api/disability/metrics');
            const data = await response.json();

            if (data.success) {
                const metrics = data.metrics;

                // Update real-time metrics display
                document.getElementById('metric-coverage-pct')!.textContent =
                    `${metrics.coverage_within_500m_pct.toFixed(1)}%`;

                document.getElementById('metric-avg-distance')!.textContent =
                    `${metrics.avg_distance_to_support_m === Infinity ? '∞' : metrics.avg_distance_to_support_m.toFixed(0)}m`;

                document.getElementById('metric-min-distance')!.textContent =
                    `${metrics.min_distance_to_support_m === Infinity ? '∞' : metrics.min_distance_to_support_m.toFixed(0)}m`;

                document.getElementById('metric-max-distance')!.textContent =
                    `${metrics.max_distance_to_support_m === Infinity ? '∞' : metrics.max_distance_to_support_m.toFixed(0)}m`;

                document.getElementById('metric-supported-stops')!.textContent =
                    metrics.supported_stops.toString();

                document.getElementById('metric-unsupported-stops')!.textContent =
                    metrics.unsupported_stops.toString();

                document.getElementById('metric-total-stops')!.textContent =
                    metrics.total_stops.toString();

                // Update overview stats as well
                document.getElementById('stat-disability-coverage')!.textContent =
                    `${metrics.coverage_within_500m_pct.toFixed(1)}%`;

                document.getElementById('stat-disability-distance')!.textContent =
                    `${metrics.avg_distance_to_support_m === Infinity ? '∞' : metrics.avg_distance_to_support_m.toFixed(0)}m`;
            }
        } catch (error) {
            console.error('Failed to load disability metrics:', error);
        }
    } private async runDisabilityOptimization(): Promise<void> {
        const maxDistance = parseInt((document.getElementById('disability-max-distance') as HTMLInputElement)?.value || '500');
        const targetCoverage = parseFloat((document.getElementById('disability-target-coverage') as HTMLInputElement)?.value || '95') / 100;

        this.showNotification('Running disability support optimization...', 'info');

        try {
            const response = await fetch('http://localhost:5000/api/disability/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    max_distance: maxDistance,
                    target_coverage: targetCoverage
                })
            });

            const data = await response.json();

            if (data.success) {
                this.disabilityOptimizationResults = data.optimization_results;
                this.displayDisabilityResults(data.optimization_results);
                this.showNotification('Optimization completed successfully', 'success');
            } else {
                throw new Error(data.error || 'Optimization failed');
            }
        } catch (error) {
            console.error('Optimization failed:', error);
            this.showNotification('Optimization failed: ' + error, 'error');
        }
    }

    private displayDisabilityResults(results: any): void {
        const resultsSection = document.getElementById('disability-results-section');
        const resultsContent = document.getElementById('disability-results-content');

        if (!resultsSection || !resultsContent) return;

        resultsSection.style.display = 'block';

        const html = `
            <div style="background: #f7fafc; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: #2d3748;">Optimization Summary</h4>
                <div style="font-size: 0.875rem; color: #4a5568;">
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Optimal stops needed:</strong> ${results.optimal_k}
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Already supported:</strong> ${results.already_supported}
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Need to flip support:</strong> ${results.need_upgrade}
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Coverage achieved:</strong> ${(results.optimal_coverage * 100).toFixed(1)}%
                    </div>
                </div>
                <div style="margin-top: 0.5rem; padding: 0.5rem; background: #fff3cd; border-radius: 0.25rem; font-size: 0.75rem; color: #856404;">
                    ℹ️ Only existing stops will have their disability support flag flipped. No new stops will be created.
                </div>
            </div>

            <div style="background: #edf2f7; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: #2d3748;">Improvement Metrics</h4>
                <div style="font-size: 0.875rem; color: #4a5568;">
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Avg distance improvement:</strong> ${results.metrics.distance_improvement_m.toFixed(0)}m
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Coverage improvement:</strong> +${results.metrics.coverage_improvement} stops
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Current coverage:</strong> ${results.metrics.coverage_current_pct.toFixed(1)}%
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Optimized coverage:</strong> ${results.metrics.coverage_optimized_pct.toFixed(1)}%
                    </div>
                </div>
            </div>

            <div style="background: #e6fffa; padding: 1rem; border-radius: 0.5rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: #2d3748;">Implementation Phases</h4>
                <div style="font-size: 0.875rem; color: #4a5568;">
                    <div style="margin-bottom: 0.25rem;">
                        <strong>High Priority:</strong> ${results.implementation_phases.high_priority} stops
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Medium Priority:</strong> ${results.implementation_phases.medium_priority} stops
                    </div>
                    <div style="margin-bottom: 0.25rem;">
                        <strong>Low Priority:</strong> ${results.implementation_phases.low_priority} stops
                    </div>
                </div>
            </div>
        `;

        resultsContent.innerHTML = html;

        // Update map stats
        document.getElementById('stat-disability-coverage')!.textContent =
            `${results.metrics.coverage_optimized_pct.toFixed(1)}%`;
        document.getElementById('stat-disability-distance')!.textContent =
            `${results.metrics.optimized_avg_distance_m.toFixed(0)}m`;

        // Render recommended stops on map
        this.mapService.renderDisabilityOptimizationResults(results.recommended_stops);
    }

    private applyDisabilityOptimization(): void {
        if (!this.disabilityOptimizationResults) {
            this.showNotification('No optimization results to apply', 'warning');
            return;
        }

        if (!confirm('Apply disability support optimization? This will FLIP the disability support flag on recommended stops (existing stops only - no new stops created).')) {
            return;
        }

        // Get stop IDs that need upgrade (flip from No to Yes)
        const stopsToUpgrade = this.disabilityOptimizationResults.recommended_stops
            .filter((s: any) => !s.Already_Supported)
            .map((s: any) => s.stop_id);

        if (stopsToUpgrade.length === 0) {
            this.showNotification('No stops need upgrade', 'info');
            return;
        }

        // Call API to flip disability support for these stops
        this.updateDisabilitySupport(stopsToUpgrade, true);
    }

    private async updateDisabilitySupport(stopIds: number[], enableSupport: boolean): Promise<void> {
        try {
            const response = await fetch('http://localhost:5000/api/disability/update-support', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    stop_ids: stopIds,
                    enable_support: enableSupport
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(`Updated ${data.modified_count} stops successfully`, 'success');

                // Reload metrics to show updated values
                await this.loadDisabilityMetrics();

                // Reload map to show changes
                await this.loadDisabilityData();
            } else {
                throw new Error(data.error || 'Failed to update disability support');
            }
        } catch (error) {
            console.error('Failed to update disability support:', error);
            this.showNotification('Failed to update disability support: ' + error, 'error');
        }
    }

    private async resetSandbox(mode?: 'schedule' | 'design' | 'disability'): Promise<void> {
        if (!confirm('Reset sandbox to production data? This will discard all sandbox changes.')) {
            return;
        }

        try {
            const response = await fetch('http://localhost:5000/api/environment/reset-sandbox', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Sandbox reset successfully', 'success');

                // Reload data based on mode
                const currentMode = mode || this.state.mode;
                if (currentMode === 'disability') {
                    await this.loadDisabilityData();
                    await this.loadDisabilityMetrics();
                } else if (currentMode === 'design') {
                    await this.loadData();
                } else if (currentMode === 'schedule') {
                    // Schedule mode reload (to be implemented)
                    await this.loadData();
                }
            } else {
                throw new Error(data.error || 'Failed to reset sandbox');
            }
        } catch (error) {
            console.error('Failed to reset sandbox:', error);
            this.showNotification('Failed to reset sandbox: ' + error, 'error');
        }
    }

    private exportDisabilityResults(): void {
        if (!this.disabilityOptimizationResults) {
            this.showNotification('No results to export', 'warning');
            return;
        }

        // Create CSV content
        const stops = this.disabilityOptimizationResults.recommended_stops.filter(
            (s: any) => !s.Already_Supported
        );

        const csvHeader = 'Code,Name,Zone,StopType,Lat,Lng,TotalRoutes,PriorityScore\n';
        const csvRows = stops.map((s: any) =>
            `${s.Code || ''},${s.Name || ''},${s.Zone || ''},${s.StopType || ''},${s.Lat},${s.Lng},${s.Total_Routes || 0},${s.Priority_Score || 0}`
        ).join('\n');

        const csvContent = csvHeader + csvRows;

        // Download CSV
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `disability_stops_recommendations_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        this.showNotification('Results exported successfully', 'success');
    }
}

// Make app globally accessible for inline event handlers
declare global {
    interface Window {
        dashboardApp: DashboardApp;
    }
}
