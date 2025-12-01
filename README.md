# 🚌 BusHappy - Ho Chi Minh City Bus Navigator

A comprehensive web application for navigating the Ho Chi Minh City bus network with real-time information, route planning, and accessibility features.

## 🌟 Features Overview

- 🗺️ **Interactive Map** - Leaflet.js powered map with OpenStreetMap tiles
- 📍 **Location Services** - GPS-based nearby stop finder and address search
- 🚏 **Stop Information** - Comprehensive stop details and upcoming buses
- 🗺️ **Route Planning** - Multi-option journey planning with walking distances
- ♿ **Accessibility Mode** - Wheelchair-accessible filtering for stops and routes
- 🔍 **Smart Search** - Real-time search by stop name, code, or route
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile devices

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ and npm
- Modern web browser (Chrome, Firefox, Edge, Safari)

### Installation & Setup

```powershell
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Configure environment variables
cp .env.example .env
# Edit .env and update VITE_API_URL if needed

# Navigate to backend
cd ../backend

# Install Python dependencies
pip install -r requirements.txt

# Configure backend environment (optional - defaults to sandbox)
cp .env.example .env

# Generate GTFS data (first time only)
cd data_preprocessing
python generate_gtfs.py
cd ..
```

**Run the application:**
```powershell
# Terminal 1 - Start Flask API Server (in sandbox mode by default)
cd backend
python api_server.py

# Terminal 2 - Start Vite Development Server (from project root)
cd frontend
npm run dev
```

> **🔒 Data Safety:** The backend runs in **sandbox mode** by default, creating isolated copies of GTFS data for safe testing and editing. See [backend/ENVIRONMENT_GUIDE.md](backend/ENVIRONMENT_GUIDE.md) for details.

Then open http://localhost:3000 in your browser.

**Build for production:**
```powershell
cd frontend
npm run build:production
# Output will be in frontend/dist/ folder
```

See [frontend/DEPLOYMENT.md](frontend/DEPLOYMENT.md) for detailed deployment instructions.

## 📖 User Guide

### Finding Nearby Bus Stops

1. Click **"📍 Nearby Stops"** button
2. Allow location access when prompted by your browser
3. View nearby stops on the map and in the sidebar
4. Click any stop to see upcoming buses

### Searching for Stops

**By Name or Code:**
1. Type in the search box (minimum 2 characters)
2. Results appear automatically as you type
3. Click any result to view details

**By Location (TypeScript version):**
1. Click the **"📍 Locations"** tab
2. Search for addresses, landmarks, or districts
3. Click a result to see nearby stops

### Planning a Route

**From Current Location:**
1. Click **"📍 Nearby Stops"** to set your location
2. Click **"🗺️ Plan Route"**
3. Click on the map to select your destination
4. View multiple route options with walking distances

**Custom Start and End:**
1. Click **"🗺️ Plan Route"**
2. Click the map for your start point (green marker 🟢)
3. Click the map for your destination (red marker 🔴)
4. Compare route options

### Using Accessibility Mode

1. Toggle **"♿ Wheelchair Accessible Only"** in the header
2. Only wheelchair-accessible stops and routes will be shown
3. Route planning considers accessibility
4. Look for ♿ badges on stops and buses

## 📁 Project Structure

```
BusHappy/
├── backend/                           # Backend API Server
│   ├── api_server.py                  # Flask REST API server
│   ├── requirements.txt               # Python dependencies
│   ├── visualize_bus_speed.ipynb     # Data analysis notebook
│   ├── data_processing/               # Data setup scripts
│   │   ├── generate_gtfs.py          # GTFS data generator
│   │   ├── aggregate_all_bus_stops.py # Stop aggregation
│   │   ├── clean_raw_gps.py          # GPS data cleaner
│   │   └── clean_support_disability.py # Accessibility data cleaner
│   ├── Bus_route_data/                # Source route data
│   │   ├── all_bus_stops_aggregated.csv
│   │   ├── HCMC_bus_routes/          # Individual route data
│   │   ├── raw_GPS/                   # GPS tracking data
│   │   └── Timetable/
│   └── gtfs/                          # Generated GTFS files
│       ├── stops.txt
│       ├── routes.txt
│       ├── trips.txt
│       ├── stop_times.txt
│       ├── calendar.txt
│       ├── agency.txt
│       └── feed_info.txt
├── frontend/                          # TypeScript Frontend Application
│   ├── main.ts                        # Application entry point
│   ├── vite.config.ts                 # Vite build configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── .env                           # Environment variables (git-ignored)
│   ├── .env.example                   # Example environment config
│   ├── DEPLOYMENT.md                  # Deployment guide
│   ├── components/                    # UI components
│   │   └── App.ts                     # Main app component
│   ├── services/                      # Business logic services
│   │   ├── api.service.ts             # API client service
│   │   └── map.service.ts             # Map management service
│   ├── types/                         # TypeScript type definitions
│   │   └── index.ts                   # Core types
│   ├── utils/                         # Utility functions
│   │   ├── constants.ts               # App-wide constants (uses env vars)
│   │   └── helpers.ts                 # Helper functions
│   ├── vite-env.d.ts                  # Vite environment types
│   ├── assets.d.ts                    # Asset type declarations
│   ├── index.html                     # HTML template
│   └── styles.css                     # Global styles
├── dist/                              # Built/compiled files (generated)
├── package.json                       # Node dependencies
├── webpack.config.js                  # Webpack config (legacy)
└── README.md                          # This file
```

## 🔧 API Reference

### Base URL
```
http://localhost:5000/api
```

### Environment Management

BusHappy supports **sandbox** and **production** modes to protect real data:

```powershell
# Check environment status
python manage_env.py status

# Run in sandbox mode (default - safe for editing)
python api_server.py

# Run in production mode (read-only)
$env:BUSHAPPY_ENV = "production"
python api_server.py

# Reset sandbox to production state
python manage_env.py reset
```

📖 **Full documentation:** [backend/ENVIRONMENT_GUIDE.md](backend/ENVIRONMENT_GUIDE.md)

### Endpoints

**Health Check**
```
GET /api/health
Response: { 
  status, 
  timestamp, 
  environment,        # "sandbox" or "production"
  is_sandbox,         # true/false
  total_stops, 
  total_routes 
}
```

**Find Nearby Stops**
```
GET /api/stops/nearby?lat={lat}&lon={lon}&radius_km={radius}&wheelchair_only={bool}
Parameters:
  - lat: Latitude (required)
  - lon: Longitude (required)
  - radius_km: Search radius in km (default: 1)
  - wheelchair_only: Filter accessible stops (default: false)
```

**Get Stop Details**
```
GET /api/stops/{stop_id}
Response: Stop info + upcoming buses
```

**Search Stops**
```
GET /api/search?q={query}&wheelchair_only={bool}
Parameters:
  - q: Search query (minimum 2 characters)
  - wheelchair_only: Filter accessible stops (default: false)
```

**Get All Routes**
```
GET /api/routes?wheelchair_only={bool}
Response: List of all bus routes
```

**Get Route Stops**
```
GET /api/routes/{route_id}/stops
Response: Outbound and inbound stops for route
```

**Plan Route**
```
POST /api/plan
Body: {
  "from_lat": 10.762622,
  "from_lon": 106.660172,
  "to_lat": 10.823099,
  "to_lon": 106.629664,
  "wheelchair_accessible": false
}
Response: Multiple route options with walking distances
```

**Environment Info** (New)
```
GET /api/environment/info
Response: Current environment configuration
```

**Reset Sandbox** (New)
```
POST /api/environment/reset-sandbox
Response: { success, message }
Note: Only works in sandbox mode
```

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- TypeScript 5.3
- Vite 7.2 - Fast build tool and dev server
- Leaflet.js 1.9 - Interactive maps
- OpenStreetMap tiles
- CSS3 - Modern styling with flexbox/grid
- Environment-based configuration

**Backend:**
- Python 3.8+
- Flask 3.0.0 - REST API framework
- Flask-CORS 4.0.0 - Cross-origin requests
- Pandas 2.1.4 - Data manipulation

**Data:**
- GTFS Format - Standard transit feed
- CSV files - Source data storage
- 2,138 bus stops - Complete HCMC coverage
- 30+ routes - Major bus lines

### Key Algorithms

**Haversine Distance:**
- Calculates great circle distance between GPS coordinates
- Used for finding nearby stops and walking distances
- Earth radius: 6371 km

**Route Planning:**
1. Find stops within 500m of start/end points
2. Build route graph by stop
3. Find common routes between stops
4. Calculate total walking distances
5. Return top 5 options sorted by walking distance

### Data Flow

**Finding Nearby Stops:**
```
User clicks "Nearby" → Browser GPS → API call
→ Calculate distances (Haversine) → Filter by radius
→ Sort by distance → Return JSON → Display on map
```

**Planning Routes:**
```
User selects points → API call → Find nearby stops
→ Build route graph → Find common routes
→ Calculate walking distances → Sort options
→ Return top 5 → Display step-by-step
```

## 📊 Data Processing

The project includes several data processing scripts in `backend/data_processing/`:

**generate_gtfs.py** - Converts HCMC bus route data to GTFS format
```powershell
cd backend/data_processing
python generate_gtfs.py
```

**aggregate_all_bus_stops.py** - Aggregates stops from all routes
```powershell
cd backend/data_processing
python aggregate_all_bus_stops.py
```

**clean_raw_gps.py** - Processes raw GPS tracking data
```powershell
cd backend/data_processing
python clean_raw_gps.py
```

**clean_support_disability.py** - Normalizes accessibility data
```powershell
cd backend/data_processing
python clean_support_disability.py
```

## 🛠️ Development

### Frontend Development
```powershell
cd frontend

# Start dev server with hot reload
npm run dev

# Build for production
npm run build:production

# Preview production build
npm run preview

# Type check
npm run type-check
```

### Environment Configuration

The frontend uses environment variables for configuration. See `frontend/.env.example` for available options:

```bash
# Copy example file
cp frontend/.env.example frontend/.env

# Edit configuration
VITE_API_URL=http://localhost:5000
VITE_MAP_DEFAULT_LAT=10.762622
VITE_MAP_DEFAULT_LNG=106.660172
# ... more options in .env.example
```

All hardcoded values have been replaced with configuration from `utils/constants.ts`, which reads from environment variables.

### Project Structure Highlights

**Backend** (`backend/`)
- `api_server.py` - Main Flask API
- `config.py` - Environment configuration management
- `manage_env.py` - Environment management CLI tool
- `ENVIRONMENT_GUIDE.md` - Full environment documentation
- `data_preprocessing/` - All data setup and processing scripts
- `Bus_route_data/` - Production source data files
- `Bus_route_data_sandbox/` - Sandbox data files (auto-generated)
- `gtfs/` - Production GTFS files
- `gtfs_sandbox/` - Sandbox GTFS files (auto-generated)

**Frontend** (`frontend/`)
- `main.ts` - Application entry point
- `components/` - React-style components (App.ts)
- `services/` - API and Map service layer
- `types/` - TypeScript type definitions
- `utils/` - Constants and helper functions

**Configuration Files**
- `frontend/package.json` - npm dependencies and scripts
- `frontend/tsconfig.json` - TypeScript compiler options
- `frontend/vite.config.ts` - Vite build configuration
- `frontend/.env` - Environment variables (git-ignored)
- `frontend/.env.example` - Example configuration
- `frontend/webpack.config.js` - Webpack config (legacy, optional)
- `.gitignore` - Git ignore patterns

## 🐛 Troubleshooting

### Common Issues

**API Server Won't Start**
- Check if port 5000 is already in use: `netstat -ano | findstr :5000`
- Verify Python dependencies: `pip install -r requirements.txt`
- Ensure GTFS files exist in `backend/gtfs/` folder

**Map Not Loading**
- Check browser console (F12) for errors
- Verify internet connection (map tiles require online access)
- Ensure API server is running at `http://localhost:5000`

**No Nearby Stops Found**
- Verify your location is within HCMC area
- Try increasing the search radius
- Check if wheelchair mode is limiting results
- Disable browser location blocking

**Route Planning Not Working**
- Ensure both points are within ~500m of bus stops
- Try different locations
- Check if wheelchair mode is limiting route options

**TypeScript Build Errors**
```powershell
# Clean reinstall
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

### Getting Help

1. Check browser console (F12) for error messages
2. Verify API server is running: http://localhost:5000/api/health
3. Check that both servers are running (API + Web)
4. Review this README for setup steps

## 🌐 Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Mobile browsers (iOS Safari, Android Chrome)

## 📊 Project Statistics

- **Total Bus Stops**: 2,138+
- **Total Routes**: 30+
- **Code Lines**: ~2,500 (TypeScript) + ~800 (Python)
- **API Endpoints**: 7
- **Coverage**: Complete HCMC metro area

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Real-time GPS bus tracking integration
- Multi-language support (Vietnamese/English)
- Offline mode with service workers
- User accounts and favorite stops
- Mobile app version
- Dark mode theme

## 📝 License

This project uses public transit data provided by HCMC Public Transport Authority.

---

**Built with ❤️ for Ho Chi Minh City commuters**

🚌 Happy traveling with BusHappy! 🎉
