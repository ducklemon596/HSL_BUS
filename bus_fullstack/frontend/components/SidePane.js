const statusMap = {
  GRIDLOCK: { label: "Gridlock", className: "bg-rose-500" },
  HEAVY: { label: "Heavy", className: "bg-orange-500" },
  LIGHT: { label: "Light", className: "bg-amber-400" },
  UNKNOWN: { label: "Unknown", className: "bg-slate-400" },
};

const formatCount = (count) => count?.toLocaleString() || "0";

export default function SidePane({
  dateRange,
  onDateRangeChange,
  onApply,
  stats,
  showOverlay,
  onToggleOverlay,
  loading,
  message,
}) {
  return (
    <div className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-md">
      <div className="space-y-4">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Historical Analytics</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">Date range report</h2>
          <p className="mt-1 text-slate-600">Query BigQuery history and overlay gridlock trajectories on the live map.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            Start date
            <input
              type="date"
              value={dateRange.start}
              onChange={(event) => onDateRangeChange({ ...dateRange, start: event.target.value })}
              className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            End date
            <input
              type="date"
              value={dateRange.end}
              onChange={(event) => onDateRangeChange({ ...dateRange, end: event.target.value })}
              className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={onApply}
          disabled={loading}
          className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {loading ? "Loading history..." : "Apply date range"}
        </button>

        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Overlay</p>
              <p className="text-sm font-semibold text-slate-900">Historical gridlock lines</p>
            </div>
            <button
              type="button"
              onClick={onToggleOverlay}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${showOverlay ? "bg-rose-500 text-white" : "bg-slate-200 text-slate-700"}`}
            >
              {showOverlay ? "Visible" : "Hidden"}
            </button>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Traffic status counts</h3>
          <div className="mt-4 space-y-3">
            {stats.length === 0 ? (
              <p className="text-sm text-slate-600">No historical status counts available.</p>
            ) : (
              stats.map((item) => {
                const status = item.traffic_status || "UNKNOWN";
                const entry = statusMap[status] || statusMap.UNKNOWN;
                return (
                  <div key={status} className="flex items-center justify-between gap-3 rounded-3xl bg-white p-4 shadow-sm">
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex h-3 w-3 rounded-full ${entry.className}`}></span>
                      <span className="font-medium text-slate-800">{entry.label}</span>
                    </div>
                    <span className="text-lg font-semibold text-slate-900">{formatCount(item.count)}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          <p>{message}</p>
        </div>
      </div>
    </div>
  );
}
