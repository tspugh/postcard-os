// Thin JSON client. Server errors carry actionable `detail` strings (the service
// layer's guard messages) — surface them verbatim in toasts.

async function handle(res) {
  if (res.ok) return res.json();
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail || JSON.stringify(body);
  } catch { /* non-JSON error body */ }
  throw new Error(detail);
}

const opts = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  get: (path) => fetch('/api' + path).then(handle),
  post: (path, body) => fetch('/api' + path, opts('POST', body)).then(handle),
  patch: (path, body) => fetch('/api' + path, opts('PATCH', body)).then(handle),
  del: (path) => fetch('/api' + path, opts('DELETE')).then(handle),
};
