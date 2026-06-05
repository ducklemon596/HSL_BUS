/**
 * API Utility Module for Bus HSL Frontend
 * Manages API calls to the FastAPI backend service
 */

// API calls are routed through frontend relative paths and rewritten to the backend via Next.js rewrites.
const API_BASE_URL = '';

/**
 * Helper function to make API requests with error handling
 * @param {string} endpoint - The API endpoint path (e.g., '/api/buses/live')
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<object>} - The JSON response from the API
 */
async function apiCall(endpoint, options = {}) {
  const url = endpoint;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Failed to fetch from ${url}:`, error);
    throw error;
  }
}

/**
 * Fetch live bus locations and current status
 * @returns {Promise<Array>} - Array of live bus objects
 */
export async function fetchLiveBuses() {
  try {
    const data = await apiCall('/api/buses/live');
    return data;
  } catch (error) {
    console.error('Error fetching live buses:', error);
    throw error;
  }
}

/**
 * Fetch historical statistics for bus operations
 * @param {string} startDate - Start date for historical data (ISO 8601 format: YYYY-MM-DD)
 * @param {string} endDate - End date for historical data (ISO 8601 format: YYYY-MM-DD)
 * @returns {Promise<object>} - Statistics object containing aggregated bus data
 */
export async function fetchHistoricalStats(startDate, endDate) {
  try {
    const queryParams = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    const data = await apiCall(`/api/traffic/ratio?${queryParams.toString()}`);
    return data;
  } catch (error) {
    console.error('Error fetching historical statistics:', error);
    throw error;
  }
}

/**
 * Fetch route impact ranking from BigQuery
 * @param {string} startDate - Start date for historical data (YYYY-MM-DD)
 * @param {string} endDate - End date for historical data (YYYY-MM-DD)
 * @param {number} pageSize - Bus HSL page-size control
 * @returns {Promise<object>} - Route impact response
 */
export async function fetchRouteImpact(startDate, endDate, pageSize = 10) {
  try {
    const queryParams = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      limit: String(pageSize),
      offset: String(pageSize),
    });
    const data = await apiCall(`/api/routes/impact?${queryParams.toString()}`);
    return data;
  } catch (error) {
    console.error('Error fetching route impact:', error);
    throw error;
  }
}

/**
 * Fetch spatial-binned congestion heatmap points
 * @param {string} startDate - Start date for historical data (YYYY-MM-DD)
 * @param {string} endDate - End date for historical data (YYYY-MM-DD)
 * @param {number} pageSize - Bus HSL page-size control
 * @returns {Promise<object>} - Heatmap point response
 */
export async function fetchTrafficHeatmap(startDate, endDate, pageSize = 500) {
  try {
    const queryParams = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      limit: String(pageSize),
      offset: String(pageSize),
      min_intensity: '1',
    });
    const data = await apiCall(`/api/traffic/heatmap?${queryParams.toString()}`);
    return data;
  } catch (error) {
    console.error('Error fetching traffic heatmap:', error);
    throw error;
  }
}

/**
 * Get API base URL (useful for debugging or dynamic URL construction)
 * @returns {string} - The current API base URL
 */
export function getApiBaseUrl() {
  return API_BASE_URL;
}

export default {
  fetchLiveBuses,
  fetchHistoricalStats,
  fetchRouteImpact,
  fetchTrafficHeatmap,
  getApiBaseUrl,
};
