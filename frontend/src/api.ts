const tokenKey = 'dex_session';
const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');
const apiUrl = (endpoint: string) => `${base}${endpoint}`;

export const auth = {
  get: () => sessionStorage.getItem(tokenKey),
  set: (v: string) => sessionStorage.setItem(tokenKey, v),
  clear: () => sessionStorage.removeItem(tokenKey),
};
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (auth.get()) headers.Authorization = `Bearer ${auth.get()}`;
  let result: Response;
  try {
    result = await fetch(apiUrl(`/api/v1${path}`), { ...options, headers });
  } catch {
    throw new Error('No se pudo conectar con la API');
  }
  if (!result.ok) {
    const payload = await result.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail || payload));
  }
  return result.json();
}
export const post = <T,>(path: string, data: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(data) });
export const patch = <T,>(path: string, data: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(data) });
export const put = <T,>(path: string, data: unknown) => api<T>(path, { method: 'PUT', body: JSON.stringify(data) });

// SSE con fetch autenticado: EventSource nativo no permite Authorization.
export async function watchDispatch(onUpdate: () => void, signal: AbortSignal, onConnected?: () => void): Promise<void> {
  const token = auth.get();
  if (!token) return;
  const response = await fetch(apiUrl('/api/v1/dispatch/stream'), {
    headers: { Authorization: `Bearer ${token}` }, signal, cache: 'no-store',
  });
  if (!response.ok || !response.body) throw new Error('No se pudo abrir el canal de despacho');
  onConnected?.();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
      const segments = buffer.split('\n\n');
      buffer = segments.pop() || '';
      for (const segment of segments) if (segment.includes('event: update')) onUpdate();
    }
  } finally { reader.releaseLock(); }
}
