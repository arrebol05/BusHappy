# BusHappy Frontend

Professional TypeScript application for bus navigation and system design.

## Quick Start

```bash
npm install             # Install dependencies
npm run dev             # Start dev server (http://localhost:3000)
npm run build           # Production build
```

## Applications

### 🚌 Main App - Bus Navigator
**URL:** `http://localhost:3000/`  
**Entry:** `src/main.ts`

Public-facing bus finder with:
- Search stops by name/location
- Find nearby stops with accessibility info
- Plan routes between locations
- Real-time bus arrivals
- Interactive Leaflet map

### 🎛️ Admin Dashboard - System Designer
**URL:** `http://localhost:3000/dashboard.html`  
**Entry:** `src/dashboard/main.ts`

Admin tool for bus system design:
- **Route Visualization** - Color-coded route mapping
- **System Statistics** - Routes, stops, coverage metrics
- **Route Editor** - Drag-and-drop stop reordering
- **Stop Management** - Add, remove, modify stops
- **Impact Analysis** - Before/after comparison
- **Auto-Optimization** - Single route or system-wide

## Project Structure

```
frontend/
├── index.html              # Main app
├── dashboard.html          # Admin dashboard
├── package.json
├── tsconfig.json           # Path aliases configured
├── vite.config.ts          # Multi-page build
│
└── src/
    ├── main.ts             # Main app entry
    │
    ├── components/         # UI components
    │   ├── App.ts
    │   └── index.ts        # Barrel export
    │
    ├── services/           # Business logic
    │   ├── api.service.ts
    │   ├── map.service.ts
    │   └── index.ts
    │
    ├── utils/              # Helpers
    │   ├── constants.ts
    │   ├── helpers.ts
    │   └── index.ts
    │
    ├── types/              # TypeScript types
    │   └── index.ts
    │
    ├── styles/             # Global CSS
    │   └── main.css
    │
    └── dashboard/          # Admin dashboard
        ├── Dashboard.ts
        ├── api.service.ts
        ├── map.service.ts
        ├── types.ts
        ├── dashboard.css
        ├── main.ts
        └── index.ts
```

## Path Aliases

Clean imports without relative paths:

```typescript
// ✅ Use path aliases
import { BusHappyApp } from '@components';
import { BusHappyAPI, MapService } from '@services';
import { CONFIG } from '@utils';
import type { BusStop } from '@types/index';

// ❌ Avoid relative paths
import { BusHappyApp } from '../../../components/App';
```

| Alias | Resolves to |
|-------|-------------|
| `@components` | `src/components` |
| `@services` | `src/services` |
| `@utils` | `src/utils` |
| `@types` | `src/types` |
| `@styles` | `src/styles` |
| `@dashboard` | `src/dashboard` |

## Dashboard Usage

### Access
Navigate to `http://localhost:3000/dashboard.html`

### Workflow
1. **View Routes** - All routes displayed in different colors
2. **Select Route** - Click legend to focus on one route
3. **Edit Stops** - Click "Edit Stops", choose direction
4. **Reorder** - Drag stops to reorder
5. **Compare** - Review before/after metrics
6. **Save** - Click "Save Plan" to persist

### Features
- **Auto-Optimize** - Single route or system-wide
- **Impact Analysis** - Compare original vs. modified
- **API Endpoints** - All prefixed `/api/dashboard/`

## Scripts

```bash
npm run dev              # Dev server
npm run build            # Production build
npm run preview          # Preview build
npm run type-check       # TypeScript validation
npm run clean            # Remove dist/
```

## Environment Variables

Create `.env`:
```env
VITE_API_URL=http://localhost:5000/api
```

Access in code:
```typescript
const apiUrl = import.meta.env.VITE_API_URL;
```

## Development Guidelines

1. Use path aliases (`@components`, `@services`, etc.)
2. Export through `index.ts` barrel files
3. Keep components single-purpose
4. Add types for new features
5. Follow existing naming conventions

---

**See also:** `STRUCTURE.md` for complete architecture | `MIGRATION.md` for migration details
