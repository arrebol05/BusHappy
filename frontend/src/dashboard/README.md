# BusHappy Admin Dashboard

## Overview

The BusHappy Admin Dashboard is a comprehensive tool for managing and designing the Ho Chi Minh City bus system. It provides two main operational modes:

### 1. Schedule Adjustment Mode
- **Status**: Placeholder (Coming Soon)
- **Purpose**: Adjust bus schedules and timetables

### 2. Bus System Design Mode
- **Status**: Fully Functional
- **Features**:
  - Visual route mapping with color-coded routes
  - Interactive route selection and editing
  - Stop management (add, remove, reorder)
  - Real-time statistics calculation
  - Route comparison and impact analysis
  - Auto-optimization capabilities

## Features

### Route Visualization
- **Color Legend**: Each bus route is displayed with a unique color
- **Interactive Map**: Click on routes to select and view details
- **Dual Direction Display**: 
  - Solid lines = Outbound routes
  - Dashed lines = Inbound routes

### System Statistics
- Total routes count
- Total unique stops
- Average route length
- Coverage area estimation

### Route Operations

#### Edit Stops
- Drag and drop to reorder stops
- Visual sequence editor
- Direction-specific editing (outbound/inbound)

#### Add Stop
- Click on map to select location
- Add to existing route
- Automatic sequence assignment

#### Remove Stop
- Select stops for removal
- Preview impact before confirming

#### Auto Optimize
- **Single Route**: Optimize one route for efficiency
- **Entire System**: System-wide optimization
- ⚠️ **Warning**: May remove existing stops for better efficiency

### Change Management

#### Comparison View
Shows before/after metrics:
- Stop count changes
- Route length modifications
- Improvements and decreases

#### Save Plan
- Batch save all modifications
- Update system configuration
- Confirmation required

## Access

The dashboard is completely separate from the main BusHappy frontend:

- **URL**: `http://localhost:3000/dashboard/`
- **No Navigation**: Not linked from main app (admin-only access)

## Technical Architecture

### Frontend Components
- `Dashboard.ts`: Main application controller
- `map.service.ts`: Leaflet map integration and visualization
- `api.service.ts`: Backend API communication
- `types.ts`: TypeScript type definitions
- `dashboard.css`: Styling and layout

### Backend Endpoints

All endpoints are prefixed with `/api/dashboard/`:

- `GET /routes` - Get all routes with stops
- `GET /stats/system` - System-wide statistics
- `GET /stats/route/:id` - Route-specific statistics
- `POST /calculate-stats` - Calculate stats for modified route
- `POST /compare-route` - Compare original vs. modified
- `POST /save-route` - Save route changes
- `POST /optimize/route/:id` - Optimize single route
- `POST /optimize/system` - Optimize entire system

## Usage Guide

### 1. Viewing Routes
1. Open dashboard
2. View route legend on left panel
3. Click any route to select it
4. Map automatically zooms to selected route

### 2. Editing a Route
1. Select a route from the legend
2. Click "Edit Stops" button
3. Choose direction (outbound/inbound)
4. Drag stops to reorder
5. Click "Apply Changes"
6. Review comparison metrics
7. Click "Save Plan" to persist

### 3. Optimizing Routes
1. Select a route
2. Click "Auto Optimize"
3. Review proposed changes
4. Confirm or cancel
5. Save if satisfied

### 4. System-Wide Optimization
1. Click "Auto Optimize Entire System"
2. ⚠️ Confirm warning prompt
3. Review all proposed changes
4. Save plan to apply

## Development

### Running Locally

1. **Start Backend**:
   ```bash
   cd backend
   python api_server.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access Dashboard**:
   - Main App: http://localhost:3000
   - Dashboard: http://localhost:3000/dashboard/

### Building for Production

```bash
cd frontend
npm run build
```

The dashboard will be built to `dist/dashboard/`.

## Future Enhancements

### Schedule Adjustment Mode
- Timetable editor
- Frequency adjustment
- Peak/off-peak scheduling
- Holiday schedules

### Design Mode Enhancements
- Coverage heat maps
- Population density overlay
- Demand prediction
- Multi-modal integration
- Accessibility analysis
- Cost estimation

### Optimization Features
- Machine learning-based optimization
- Traffic pattern integration
- Historical ridership data
- Multi-objective optimization
- Constraint satisfaction

## Security Notes

⚠️ **Important**: This dashboard has no authentication system. In production:
- Implement proper authentication
- Add role-based access control
- Use HTTPS
- Add audit logging
- Implement change approval workflow

## Data Persistence

Currently, changes are simulated and not persisted to GTFS files. For production:
- Implement GTFS file updates
- Add database layer
- Version control for changes
- Rollback capabilities
- Change history tracking

## Support

For issues or questions:
- Check browser console for errors
- Verify backend is running on port 5000
- Ensure GTFS data is properly loaded
- Review API endpoint responses
