import { useCallback, useEffect, useRef, useState } from 'react';

const API_URL = import.meta.env.VITE_CAHMA_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8080' : '');
const API_KEY = import.meta.env.VITE_CAHMA_API_KEY || (import.meta.env.DEV ? 'hackathon-demo-key' : '');
const MAX_DECISIONS = 24;

const headers = (json = false) => ({ ...(json ? { 'Content-Type': 'application/json' } : {}), ...(API_KEY ? { 'X-CAHMA-Key': API_KEY } : {}) });

export function useLiveRuntime() {
  const [connection, setConnection] = useState({ phase: API_URL ? 'connecting' : 'demo', connected: false, error: null, lastEventAt: null, v2Snapshot: null, v2Decision: null, v2Inference: null, inferenceByCamera: {}, decisionHistory: [], telemetry: null });
  const retryRef = useRef(null);

  useEffect(() => {
    if (!API_URL) return undefined;
    let socket;
    let disposed = false;
    const connect = () => {
      if (disposed) return;
      const absoluteApi = API_URL.startsWith('/') ? `${window.location.origin}${API_URL}` : API_URL;
      const wsUrl = absoluteApi.replace(/^http/, 'ws').replace(/\/$/, '') + '/v1/events';
      setConnection((current) => ({ ...current, phase: 'connecting', error: null }));
      socket = new WebSocket(wsUrl);
      socket.onopen = () => setConnection((current) => ({ ...current, phase: 'live', connected: true, error: null, lastEventAt: Date.now() }));
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        const now = Date.now();
        setConnection((current) => {
          const next = { ...current, lastEventAt: now };
          if (message.type === 'v2_snapshot') next.v2Snapshot = message.data;
          if (message.type === 'v2_decision' && message.data?.decision_id && !message.data?.event) {
            next.v2Decision = message.data;
            next.decisionHistory = [message.data, ...current.decisionHistory.filter((item) => item.decision_id !== message.data.decision_id)].slice(0, MAX_DECISIONS);
          }
          if (message.type === 'v2_decision' && message.data?.event === 'resident_inference') {
            next.v2Inference = message.data;
            next.inferenceByCamera = { ...current.inferenceByCamera, [message.data.camera_id]: message.data };
          }
          if (message.type === 'v2_decision' && message.data?.event === 'override_activated' && current.v2Snapshot) next.v2Snapshot = { ...current.v2Snapshot, overrides: [...(current.v2Snapshot.overrides || []).filter((item) => item.camera_id !== message.data.camera_id), message.data] };
          if (message.type === 'v2_decision' && message.data?.event === 'override_released' && current.v2Snapshot) next.v2Snapshot = { ...current.v2Snapshot, overrides: (current.v2Snapshot.overrides || []).filter((item) => item.camera_id !== message.data.camera_id) };
          return next;
        });
      };
      socket.onerror = () => setConnection((current) => ({ ...current, phase: 'degraded', connected: false, error: 'Edge runtime unavailable' }));
      socket.onclose = () => {
        if (disposed) return;
        setConnection((current) => ({ ...current, phase: 'disconnected', connected: false, error: 'Runtime disconnected; retrying' }));
        retryRef.current = window.setTimeout(connect, 3000);
      };
    };
    connect();
    return () => { disposed = true; window.clearTimeout(retryRef.current); socket?.close(); };
  }, []);

  useEffect(() => {
    if (!API_URL) return undefined;
    let disposed = false;
    const readTelemetry = async () => {
      try {
        const response = await fetch(`${API_URL}/v1/telemetry`, { headers: headers() });
        if (!response.ok) return;
        const telemetry = await response.json();
        if (!disposed) setConnection((current) => ({ ...current, telemetry }));
      } catch { /* Optional telemetry does not own connection state. */ }
    };
    readTelemetry();
    const timer = window.setInterval(readTelemetry, 5000);
    return () => { disposed = true; window.clearInterval(timer); };
  }, []);

  const refreshRuntime = useCallback(async () => {
    if (!API_URL) return null;
    const response = await fetch(`${API_URL}/v2/runtime`, { headers: headers() });
    if (!response.ok) throw new Error(`Runtime refresh failed (${response.status})`);
    const runtime = await response.json();
    setConnection((current) => ({ ...current, v2Snapshot: runtime }));
    return runtime;
  }, []);

  const override = useCallback(async (cameraId, active) => {
    if (!API_URL) throw new Error('Operator controls require the live edge runtime');
    const response = await fetch(`${API_URL}/v2/cameras/${cameraId}/override`, { method: active ? 'POST' : 'DELETE', headers: headers(active), body: active ? JSON.stringify({ duration_seconds: 300, reason: 'Dashboard operator override' }) : undefined });
    if (!response.ok) throw new Error(`Override request failed (${response.status})`);
    await refreshRuntime();
    return true;
  }, [refreshRuntime]);

  return { ...connection, override, refreshRuntime };
}
