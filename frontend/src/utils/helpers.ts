/**
 * Utility helper functions
 */

export class Helpers {
    static formatDistance(km: number): string {
        if (km < 1) {
            return `${Math.round(km * 1000)} m`;
        }
        return `${km.toFixed(2)} km`;
    }

    static formatTime(timeString: string): string {
        try {
            const [hours, minutes] = timeString.split(':');
            return `${hours}:${minutes}`;
        } catch {
            return timeString;
        }
    }

    static debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
        let timeout: ReturnType<typeof setTimeout> | null = null;

        return function executedFunction(...args: Parameters<T>) {
            const later = () => {
                timeout = null;
                func(...args);
            };

            if (timeout) clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static sanitizeHTML(str: string): string {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    static generateId(prefix: string = 'id'): string {
        return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    static getWheelchairText(wheelchairMode: boolean): string {
        return wheelchairMode ? 'accessible ' : '';
    }
}
