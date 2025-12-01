/**
 * Dashboard Entry Point
 */

import { DashboardApp } from '@dashboard/Dashboard';
import '@dashboard/dashboard.css';

// Initialize the dashboard when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
    const app = new DashboardApp();
    window.dashboardApp = app;
});
