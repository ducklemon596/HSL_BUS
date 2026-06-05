import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from "react-leaflet";
import L from "leaflet";

const DEFAULT_CENTER = [60.1699, 24.9384];

const buildBusIcon = (route, isStuck) => {
  const badge = `
    <div style="position:absolute;top:0;left:50%;transform:translateX(-50%);padding:4px 8px;background:#007bff;color:white;font-size:11px;font-weight:700;border-radius:999px;white-space:nowrap;box-shadow:0 3px 6px rgba(0,0,0,0.22);">
      ${route}
    </div>
  `;

  const alertTriangle = isStuck
    ? `<div style="position:absolute;top:24px;left:50%;transform:translateX(-50%);width:0;height:0;border-left:10px solid transparent;border-right:10px solid transparent;border-bottom:16px solid #ffc107;"></div>`
    : "";

  const html = `
    <div style="position:relative;width:42px;height:54px;text-align:center;">
      ${badge}
      ${alertTriangle}
      <div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);font-size:28px;line-height:1;text-shadow:0 2px 6px rgba(0,0,0,0.3);">🚌</div>
    </div>
  `;

  return new L.DivIcon({ html, className: "", iconSize: [42, 54], iconAnchor: [21, 54], popupAnchor: [0, -50] });
};

const safeNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export default function MapPane({ heatmapPoints, showOverlay }) {
  const [buses, setBuses] = useState([]);
  const [error, setError] = useState(null);
  const maxIntensity = Math.max(
    1,
    ...(Array.isArray(heatmapPoints) ? heatmapPoints.map((point) => Number(point.intensity) || 0) : [])
  );

  useEffect(() => {
    let intervalId;
    const fetchLive = async () => {
      try {
        const response = await fetch('/api/buses/live');
        if (!response.ok) {
          throw new Error("Live bus request failed.");
        }
        const json = await response.json();
        setBuses(Array.isArray(json.buses) ? json.buses : []);
        setError(null);
      } catch (err) {
        setError(err.message);
      }
    };

    fetchLive();
    intervalId = setInterval(fetchLive, 3000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="relative h-full w-full">
      <div className="absolute right-4 top-4 z-20 rounded-3xl border border-white bg-white/90 px-4 py-3 text-slate-700 shadow-xl backdrop-blur">
        <p className="text-sm font-semibold">Live / Historical Map</p>
        <p className="text-xs text-slate-500">Live feed refreshes every 3 seconds.</p>
        {error ? <p className="mt-2 text-xs text-rose-600">{error}</p> : null}
      </div>

      <MapContainer center={DEFAULT_CENTER} zoom={14} scrollWheelZoom={true} className="h-full w-full">
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          attribution='&copy; CARTO'
        />

        {buses.map((bus) => {
          const data = bus.data || {};
          const lat = safeNumber(data.lat);
          const lon = safeNumber(data.long || data.lng || data.lon);
          if (lat === null || lon === null) return null;

          const route = data.desi || data.route || data.line || "?";
          const isStuck =
            data.is_stuck === true ||
            data.is_stuck === "true" ||
            data.is_stuck === "True" ||
            String(data.traffic_status || "").toUpperCase() === "GRIDLOCK";
          const avgSpeed = data.avg_speed ? Number(data.avg_speed).toFixed(1) : "--";
          const currentSpeed = data.spd !== undefined ? Number(data.spd).toFixed(1) : "--";

          return (
            <Marker key={bus.id} position={[lat, lon]} icon={buildBusIcon(route, isStuck)}>
              <Popup>
                <div className="max-w-xs text-sm">
                  <div className="mb-2 rounded-2xl bg-slate-100 px-3 py-2 font-semibold text-slate-900">Bus {bus.id}</div>
                  <div className="space-y-2 text-slate-800">
                    <div className="flex justify-between"><span>Route</span><span className="font-semibold">{route}</span></div>
                    <div className="flex justify-between"><span>Status</span><span className="font-semibold">{isStuck ? "GRIDLOCK" : "NORMAL"}</span></div>
                    <div className="flex justify-between"><span>Avg speed</span><span className="font-semibold">{avgSpeed} km/h</span></div>
                    <div className="flex justify-between"><span>Current speed</span><span className="font-semibold">{currentSpeed} km/h</span></div>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {showOverlay &&
          heatmapPoints.map((point, index) => {
            const lat = safeNumber(point.grid_lat);
            const lon = safeNumber(point.grid_lon);
            const intensity = Number(point.intensity) || 0;
            if (lat === null || lon === null || intensity <= 0) return null;

            const weight = intensity / maxIntensity;
            const radius = 8 + weight * 22;

            return (
              <CircleMarker
                key={`heat-${index}-${lat}-${lon}`}
                center={[lat, lon]}
                radius={radius}
                pathOptions={{
                  color: "#991b1b",
                  fillColor: "#ef4444",
                  fillOpacity: 0.22 + weight * 0.38,
                  opacity: 0.25 + weight * 0.45,
                  weight: 1,
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold text-slate-900">Congestion grid</div>
                    <div className="mt-1 text-slate-700">Intensity: {intensity.toLocaleString()}</div>
                    <div className="text-slate-500">{lat.toFixed(3)}, {lon.toFixed(3)}</div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
      </MapContainer>
    </div>
  );
}
