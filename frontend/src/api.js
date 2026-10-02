const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');

function endpoint(path) {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;
}

async function request(path, payload) {
  const response = await fetch(endpoint(path), {
    method: payload ? 'POST' : 'GET',
    headers: payload ? { 'Content-Type': 'application/json' } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }

  return response.json();
}

export const checkBackend = () => request('/api/health');

export const generateHooks = ({ community, topic }) =>
  request('/api/hooks', { community, topic });

export const generateScript = ({ community, topic, selected_hook }) =>
  request('/api/script', { community, topic, selected_hook });

export const renderVideo = ({ community, topic, hook }) =>
  request('/api/generate', { community, topic, hook });

export const getRenderStatus = (jobId) =>
  request(`/api/status/${encodeURIComponent(jobId)}`);

export function resolveVideoUrl(rawUrl) {
  if (!rawUrl) return '';

  try {
    const resolved = new URL(rawUrl, new URL(endpoint('/'), window.location.origin));
    const isLoopback = ['localhost', '127.0.0.1', '0.0.0.0'].includes(resolved.hostname);

    if (isLoopback) {
      const apiRoot = API_BASE
        ? new URL(API_BASE, window.location.origin)
        : new URL(window.location.origin);
      const prefix = apiRoot.pathname.replace(/\/+$/, '');
      return `${apiRoot.origin}${prefix}${resolved.pathname}${resolved.search}${resolved.hash}`;
    }

    return resolved.toString();
  } catch {
    return endpoint(rawUrl.startsWith('/') ? rawUrl : `/${rawUrl}`);
  }
}
