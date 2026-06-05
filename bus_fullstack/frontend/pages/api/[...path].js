const DEFAULT_BACKEND_API_URL = "http://localhost:8000";

const getBackendApiUrl = () => {
  const rawUrl = process.env.BACKEND_API_URL || DEFAULT_BACKEND_API_URL;
  return rawUrl.replace(/\/+$/, "");
};

export default async function handler(req, res) {
  const path = Array.isArray(req.query.path) ? req.query.path.join("/") : "";
  const query = { ...req.query };
  delete query.path;

  const searchParams = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => searchParams.append(key, item));
      return;
    }
    if (value !== undefined) {
      searchParams.append(key, value);
    }
  });

  const queryString = searchParams.toString();
  const targetUrl = `${getBackendApiUrl()}/api/${path}${queryString ? `?${queryString}` : ""}`;

  try {
    const upstreamResponse = await fetch(targetUrl, {
      method: req.method,
      headers: {
        accept: req.headers.accept || "application/json",
        "content-type": req.headers["content-type"] || "application/json",
      },
    });

    const contentType = upstreamResponse.headers.get("content-type") || "application/json";
    const body = await upstreamResponse.text();

    res.status(upstreamResponse.status);
    res.setHeader("content-type", contentType);
    res.send(body);
  } catch (error) {
    res.status(502).json({
      detail: "Frontend proxy failed to reach backend API.",
      backend_api_url: getBackendApiUrl(),
      error: error.message,
    });
  }
}
