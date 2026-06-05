# Bus HSL Fullstack Application

This folder contains a new backend FastAPI service and a Next.js frontend for the Bus HSL analytics application.

## Backend

The backend service is in `backend/`.

### Run locally

1. Create a `.env` file from `.env.example`.
2. Install dependencies:
   ```bash
   cd bus_fullstack/backend
   python -m pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### API endpoints

- `GET /api/buses/live`
- `GET /api/routes/impact?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=10&offset=10`
- `GET /api/traffic/ratio?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /api/traffic/heatmap?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=500&offset=500`
- `GET /api/traffic/stats?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` aliases the time-based ratio response.
- `GET /api/traffic/jam?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` aliases the spatial-binned heatmap response.

## Frontend

The frontend service is in `frontend/`.

### Run locally

1. Install dependencies:
   ```bash
   cd bus_fullstack/frontend
   npm install
   ```
2. Start the Next.js dev server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:3000`

### Configuration

The frontend reads the API base URL from `NEXT_PUBLIC_API_BASE_URL` in `.env` or from the browser environment.

## Notes

- Existing `web_service/` logic was preserved and not modified.
- This new app uses Redis for live bus positions and BigQuery for historical traffic analytics.
- Historical congestion grids are aggregated in BigQuery and overlaid on the live Leaflet map.
