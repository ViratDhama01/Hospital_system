const API_URLS = ['http://127.0.0.1:8000', 'http://localhost:8000'];
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

  try {
    const response = await fetch(`${API_URLS[currentApiUrlIndex]}${endpoint}`, config);

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/';
      return;
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (currentApiUrlIndex === 0) {
      currentApiUrlIndex = 1;
      try {
        const response = await fetch(`${API_URLS[currentApiUrlIndex]}${endpoint}`, config);
        if (response.ok) {
          return await response.json();
        }
      } catch (fallbackError) {
        console.error(`Both API URLs failed:`, fallbackError);
      }
    }
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
};

export const api = {
  get: (endpoint) => apiRequest(endpoint, { method: 'GET' }),
  post: (endpoint, data) => apiRequest(endpoint, { method: 'POST', body: JSON.stringify(data) }),
  put: (endpoint, data) => apiRequest(endpoint, { method: 'PUT', body: JSON.stringify(data) }),
  patch: (endpoint, data) => apiRequest(endpoint, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (endpoint) => apiRequest(endpoint, { method: 'DELETE' }),
};
