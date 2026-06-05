import dynamic from "next/dynamic";
import { useState } from "react";
import SidePane from "../components/SidePane";

const MapPane = dynamic(() => import("../components/MapPane"), { ssr: false });

const apiBase = "/api proxy";

export default function Home() {
  const [dateRange, setDateRange] = useState({ start: "", end: "" });
  const [stats, setStats] = useState([]);
  const [routeImpact, setRouteImpact] = useState([]);
  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [showOverlay, setShowOverlay] = useState(true);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Select a range and press Apply to load historical traffic analytics.");

  const fetchHistorical = async (start, end) => {
    if (!start || !end) {
      setMessage("Please select both a start date and an end date.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const commonParams = `start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;
      const [statsRes, routeRes, heatmapRes] = await Promise.all([
        fetch(`/api/traffic/ratio?${commonParams}`),
        fetch(`/api/routes/impact?${commonParams}&limit=10&offset=10`),
        fetch(`/api/traffic/heatmap?${commonParams}&limit=500&offset=500&min_intensity=1`),
      ]);

      if (!statsRes.ok || !routeRes.ok || !heatmapRes.ok) {
        throw new Error("Unable to fetch historical analytics from the API.");
      }

      const statsJson = await statsRes.json();
      const routeJson = await routeRes.json();
      const heatmapJson = await heatmapRes.json();

      setStats(statsJson.stats || []);
      setRouteImpact(routeJson.routes || []);
      setHeatmapPoints(heatmapJson.points || []);

      if ((heatmapJson.points || []).length === 0 && (routeJson.routes || []).length === 0) {
        setMessage("No historical congestion aggregates found for the selected range.");
      }
    } catch (error) {
      setMessage(error.message || "Failed to load historical data.");
      setStats([]);
      setRouteImpact([]);
      setHeatmapPoints([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Bus HSL</p>
            <h1 className="text-3xl font-semibold text-slate-900">Real-time Monitoring & Historical Analytics</h1>
            <p className="mt-1 text-slate-600">Live positions from Redis, traffic history from BigQuery external tables.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700">
            API base: <span className="font-semibold">{apiBase || "same origin"}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-6 lg:grid-cols-[1.8fr_0.9fr]">
        <section className="min-h-[76vh] rounded-[32px] border border-slate-200 bg-white shadow-md">
          <MapPane heatmapPoints={heatmapPoints} showOverlay={showOverlay} />
        </section>

        <section className="space-y-6">
          <SidePane
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
            onApply={() => fetchHistorical(dateRange.start, dateRange.end)}
            stats={stats}
            routeImpact={routeImpact}
            heatmapPoints={heatmapPoints}
            showOverlay={showOverlay}
            onToggleOverlay={() => setShowOverlay(!showOverlay)}
            loading={loading}
            message={message}
          />
        </section>
      </main>
    </div>
  );
}
