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
    const data = await apiCall(`/api/traffic/stats?${queryParams.toString()}`);
    return data;
  } catch (error) {
    console.error('Error fetching historical statistics:', error);
    throw error;
  }
}

/**
 * Fetch bus route information
 * @param {string} routeId - The route ID to fetch
 * @returns {Promise<object>} - Route information object
 */
export async function fetchRouteInfo(routeId) {
  try {
    const data = await apiCall(`/routes/${routeId}`);
    return data;
  } catch (error) {
    console.error(`Error fetching route info for ${routeId}:`, error);
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
  fetchRouteInfo,
  getApiBaseUrl,
};
