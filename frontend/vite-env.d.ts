/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL: string;
    readonly VITE_MAP_TILE_URL: string;
    readonly VITE_MAP_ATTRIBUTION: string;
    readonly VITE_MAP_DEFAULT_LAT: string;
    readonly VITE_MAP_DEFAULT_LNG: string;
    readonly VITE_MAP_DEFAULT_ZOOM: string;
    readonly VITE_ENABLE_ANALYTICS: string;
    readonly VITE_ENABLE_DEBUG: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
