import { INITIAL_CAMERAS, INITIAL_EVENTS, INITIAL_ZONES, INITIAL_KPIS, INITIAL_SHIFT_REPORT } from '../constants/mockData';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USE_MOCK = true; // Setează pe false când backend-ul FastAPI este activ

export const safeTarmacApi = {
  // 1. Camere
  async getCameras() {
    if (USE_MOCK) return Promise.resolve([...INITIAL_CAMERAS]);
    const res = await fetch(`${API_BASE_URL}/cameras`);
    return res.json();
  },

  async setEngineState(cameraId, on) {
    if (USE_MOCK) {
      return Promise.resolve({ camera_id: cameraId, engine_on: on });
    }
    const res = await fetch(`${API_BASE_URL}/cameras/${cameraId}/engine`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ on })
    });
    return res.json();
  },

  // 2. Zone & Editor Poligoane
  async getZones(cameraId) {
    if (USE_MOCK) {
      const filtered = cameraId
        ? INITIAL_ZONES.filter((z) => z.camera_id === cameraId)
        : INITIAL_ZONES;
      return Promise.resolve(filtered);
    }
    const res = await fetch(`${API_BASE_URL}/zones?camera_id=${cameraId || ''}`);
    return res.json();
  },

  async saveZone(zoneId, zoneData) {
    if (USE_MOCK) {
      return Promise.resolve({ zone_id: zoneId, ...zoneData, saved: true });
    }
    const res = await fetch(`${API_BASE_URL}/zones/${zoneId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zoneData)
    });
    return res.json();
  },

  async captureReferenceFrame(cameraId) {
    if (USE_MOCK) {
      return Promise.resolve({
        camera_id: cameraId,
        captured_at: new Date().toISOString(),
        reference_frame_url: `/reference_frames/${cameraId}_clean.jpg`
      });
    }
    const res = await fetch(`${API_BASE_URL}/zones/reference-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera_id: cameraId })
    });
    return res.json();
  },

  // 3. Evenimente & Incidente
  async getEvents({ status = '', severity = '', camera_id = '' } = {}) {
    if (USE_MOCK) {
      let filtered = [...INITIAL_EVENTS];
      if (status && status !== 'all') {
        filtered = filtered.filter((e) => e.status === status);
      }
      if (severity && severity !== 'all') {
        filtered = filtered.filter((e) => e.severity === severity);
      }
      if (camera_id && camera_id !== 'all') {
        filtered = filtered.filter((e) => e.camera_id === camera_id);
      }
      return Promise.resolve(filtered);
    }
    const query = new URLSearchParams({ status, severity, camera_id }).toString();
    const res = await fetch(`${API_BASE_URL}/events?${query}`);
    return res.json();
  },

  async getEventById(eventId) {
    if (USE_MOCK) {
      const evt = INITIAL_EVENTS.find((e) => e.event_id === eventId);
      return Promise.resolve(evt || null);
    }
    const res = await fetch(`${API_BASE_URL}/events/${eventId}`);
    return res.json();
  },

  async acknowledgeEvent(eventId, operator = 'Ariana') {
    if (USE_MOCK) {
      return Promise.resolve({
        event_id: eventId,
        status: 'acknowledged',
        acked_at: new Date().toISOString(),
        acked_by: operator
      });
    }
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/ack`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operator })
    });
    return res.json();
  },

  async markFalsePositive(eventId, operator = 'Ariana', note = '') {
    if (USE_MOCK) {
      return Promise.resolve({
        event_id: eventId,
        status: 'false_positive',
        operator,
        note
      });
    }
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/false-positive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operator, note })
    });
    return res.json();
  },

  async reopenEvent(eventId, operator = 'Ariana') {
    if (USE_MOCK) {
      return Promise.resolve({
        event_id: eventId,
        status: 'open',
        reopened_by: operator,
        reopened_at: new Date().toISOString()
      });
    }
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/reopen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operator })
    });
    return res.json();
  },

  async regenerateReport(eventId) {
    if (USE_MOCK) {
      return Promise.resolve({
        event_id: eventId,
        regenerated: true,
        report: {
          what: "Raport actualizat: Risc confirmat la sol.",
          where: "Stand 12.",
          when: new Date().toLocaleTimeString('ro-RO'),
          severity_reason: "Motor în funcțiune; procedură de siguranță activată.",
          recommended_action: "Menține distanța de siguranță de 15m.",
          source: "llm"
        }
      });
    }
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/regenerate-report`, {
      method: 'POST'
    });
    return res.json();
  },

  // 4. KPI & Rapoarte
  async getKPIs(date = '', shift = '') {
    if (USE_MOCK) return Promise.resolve({ ...INITIAL_KPIS });
    const res = await fetch(`${API_BASE_URL}/kpi?date=${date}&shift=${shift}`);
    return res.json();
  },

  async getShiftReport(shift = '', date = '') {
    if (USE_MOCK) return Promise.resolve({ ...INITIAL_SHIFT_REPORT });
    const res = await fetch(`${API_BASE_URL}/reports?shift=${shift}&date=${date}`);
    return res.json();
  },

  // 5. WebSocket & Polling Fallback
  connectEventsSocket(onMessage, onError) {
    if (USE_MOCK) {
      // Simulare WebSocket heartbeat
      const interval = setInterval(() => {
        onMessage({
          action: 'TELEMETRY_TICK',
          kpi: {
            ...INITIAL_KPIS,
            detection_to_alert_latency_s: +(1.6 + Math.random() * 0.4).toFixed(1)
          }
        });
      }, 4000);
      return () => clearInterval(interval);
    }

    const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/events`;
    let ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error('WS Parse Error', err);
      }
    };

    ws.onerror = (err) => {
      if (onError) onError(err);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) ws.close();
    };
  }
};
