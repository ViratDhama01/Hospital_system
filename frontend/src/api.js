const configuredApiUrl = process.env.REACT_APP_API_URL;
const API_URLS = configuredApiUrl
  ? [configuredApiUrl]
  : ['http://127.0.0.1:8000', 'http://localhost:8000'];
let currentApiUrlIndex = 0;

export const apiRequest = async (endpoint, options = {}) => {
  const token = localStorage.getItem('access_token');

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  let response;
  try {
    response = await fetch(`${API_URLS[currentApiUrlIndex]}${endpoint}`, config);
  } catch (error) {
    if (config.method !== 'GET' || currentApiUrlIndex + 1 >= API_URLS.length) throw error;
    currentApiUrlIndex += 1;
    response = await fetch(`${API_URLS[currentApiUrlIndex]}${endpoint}`, config);
  }

  if (response.status === 401) {
    // Ignore a stale response from a request sent before a new login or token rotation.
    if (token && localStorage.getItem('access_token') === token) {
      localStorage.removeItem('access_token');
      window.location.replace('/');
    }
  }

  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}));
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join('. ') : detail;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
};

export const api = {
  get: (endpoint) => apiRequest(endpoint, { method: 'GET' }),
  post: (endpoint, data) => apiRequest(endpoint, { method: 'POST', body: JSON.stringify(data) }),
  put: (endpoint, data) => apiRequest(endpoint, { method: 'PUT', body: JSON.stringify(data) }),
  patch: (endpoint, data) => apiRequest(endpoint, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (endpoint) => apiRequest(endpoint, { method: 'DELETE' }),
};
