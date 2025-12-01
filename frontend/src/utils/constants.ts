/**
 * Configuration constants for BusHappy application
 */

const getEnv = (key: string, fallback: string): string => {
    return import.meta.env?.[key] || fallback;
};

const getEnvNumber = (key: string, fallback: number): number => {
    const value = import.meta.env?.[key];
    return value ? parseFloat(value) : fallback;
};

export const CONFIG = {
    API_BASE_URL: `${getEnv('VITE_API_URL', 'http://localhost:5000')}/api`,

    MAP: {
        DEFAULT_CENTER: [
            getEnvNumber('VITE_MAP_DEFAULT_LAT', 10.762622),
            getEnvNumber('VITE_MAP_DEFAULT_LNG', 106.660172)
        ] as [number, number],
        DEFAULT_ZOOM: getEnvNumber('VITE_MAP_DEFAULT_ZOOM', 13),
        DETAIL_ZOOM: 16,
        MAX_ZOOM: 19,
        TILE_URL: getEnv('VITE_MAP_TILE_URL', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
        ATTRIBUTION: getEnv('VITE_MAP_ATTRIBUTION', '© OpenStreetMap contributors')
    },

    SEARCH: {
        MIN_LENGTH: 2,
        DEBOUNCE_MS: 500,
        MAX_RESULTS: 50
    },

    ROUTING: {
        NEARBY_RADIUS_KM: 0.5,
        DEFAULT_RADIUS_KM: 1,
        MAX_ROUTE_OPTIONS: 5
    },

    UI: {
        NOTIFICATION_DURATION_MS: 3000,
        LOADING_DELAY_MS: 500
    },

    FEATURES: {
        ENABLE_ANALYTICS: getEnv('VITE_ENABLE_ANALYTICS', 'false') === 'true',
        ENABLE_DEBUG: getEnv('VITE_ENABLE_DEBUG', 'true') === 'true'
    }
} as const;

export const ICONS = {
    USER_LOCATION: '📍',
    BUS_STOP: '🚏',
    ACCESSIBLE_STOP: '♿',
    ROUTE_START: '🟢',
    ROUTE_END: '🔴',
    BUS: '🚌',
    WALKING: '🚶'
} as const;

export const MESSAGES = {
    LOADING: {
        LOCATION: 'Getting your location...',
        NEARBY: 'Finding nearby stops...',
        DETAILS: 'Loading stop details...',
        SEARCHING: 'Searching...',
        PLANNING: 'Planning your route...'
    },
    ERROR: {
        API_CONNECT: 'Cannot connect to API server. Make sure the backend is running.',
        GEOLOCATION: 'Unable to get your location. Using default location.',
        GEOLOCATION_UNSUPPORTED: 'Geolocation is not supported by your browser.',
        STOPS_FAILED: 'Failed to load nearby stops',
        DETAILS_FAILED: 'Failed to load stop details',
        SEARCH_FAILED: 'Search failed',
        ROUTING_FAILED: 'Route planning failed'
    },
    SUCCESS: {
        START_SELECTED: 'Start point selected. Click on map to select destination.',
        PLANNING_STARTED: 'Click on the map to select your start point'
    },
    EMPTY: {
        NO_STOPS: 'No stops found nearby',
        NO_ACCESSIBLE_STOPS: 'No accessible stops found nearby',
        NO_RESULTS: 'No results found',
        NO_BUSES: 'No upcoming buses at this time',
        NO_ROUTES: 'No routes found. Try selecting different points or increase search radius.',
        WELCOME: 'Search for stops or find nearby stops to get started'
    }
} as const;
