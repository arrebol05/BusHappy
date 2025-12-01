/**
 * BusHappy Main Application Entry Point
 * Professional TypeScript Implementation
 */

import { BusHappyApp } from '@components/App';
import '@styles/main.css';

// Initialize the application when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
    new BusHappyApp();
});
