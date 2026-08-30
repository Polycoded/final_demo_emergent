import { useEffect, useState } from 'react';

const API_URL = import.meta.env.VITE_CAHMA_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8080' : '');
const API_KEY = import.meta.env.VITE_CAHMA_API_KEY || (import.meta.env.DEV ? 'hackathon-demo-key' : '');

export function useLiveRuntime() {
  const [connection, setConnection] = useState({ mode: API_URL ? 'connecting' : 'demo', connected: false, error: null, snapshot: null, decision: null, windowDecision: null, v2Snapshot: null, v2Decision: null, v2Inference: null });

  useEffect(() => {
    if (!API_URL) return undefined;
    const absoluteApi = API_URL.startsWith('/') ? `${window.location.origin}${API_URL}` : API_URL;
    const wsUrl = absoluteApi.replace(/^http/, 'ws').replace(/\/$/, '') + '/v1/events';
    const socket = new WebSocket(wsUrl);
    socket.onopen = () => setConnection((current) => ({ ...current, mode: 'live', connected: true, error: null }));
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'snapshot') setConnection((current) => ({ ...current, snapshot: message.data }));
      if (message.type === 'decision') setConnection((current) => ({ ...current, decision: message.data }));
      if (message.type === 'window_decision') setConnection((current) => ({ ...current, windowDecision: message.data }));
      if (message.type === 'v2_snapshot') setConnection((current) => ({ ...current, v2Snapshot: message.data }));
      if (message.type === 'v2_decision' && message.data?.decision_id && !message.data?.event) setConnection((current) => ({ ...current, v2Decision: message.data }));
      if (message.type === 'v2_decision' && message.data?.event === 'resident_inference') setConnection((current) => ({ ...current, v2Inference: message.data }));
    };
    socket.onerror = () => setConnection((current) => ({ ...current, mode: 'fallback', connected: false, error: 'Edge runtime unavailable' }));
    socket.onclose = () => setConnection((current) => current.connected ? { ...current, mode: 'fallback', connected: false, error: 'Edge runtime disconnected' } : current);
    return () => socket.close();
  }, []);

  const override = async (cameraId, active) => {
    if (!API_URL) return false;
    const response = await fetch(`${API_URL}/v2/cameras/${cameraId}/override`, {
      method: active ? 'POST' : 'DELETE',
      headers: { ...(active ? { 'Content-Type': 'application/json' } : {}), ...(API_KEY ? { 'X-CAHMA-Key': API_KEY } : {}) },
      body: active ? JSON.stringify({ duration_seconds: 300, reason: 'Dashboard operator override' }) : undefined,
    });
    if (!response.ok) throw new Error(`Override request failed: ${response.status}`);
    const runtime = await fetch(`${API_URL}/v2/runtime`, { headers: API_KEY ? { 'X-CAHMA-Key': API_KEY } : {} }).then((item) => item.json());
    setConnection((current) => ({ ...current, v2Snapshot: runtime }));
    return true;
  };

  return { ...connection, override };
}
