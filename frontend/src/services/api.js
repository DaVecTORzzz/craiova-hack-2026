import {
  INITIAL_CAMERAS,
  INITIAL_EVENTS,
  INITIAL_ZONES,
  INITIAL_KPIS,
  INITIAL_SHIFT_REPORT,
} from '../constants/mockData';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK ?? 'false').toLowerCase() === 'true';

const PALETTES = [
  'from-blue-950 via-slate-900 to-indigo-950',
  'from-zinc-900 to-neutral-800',
  'from-slate-900 to-indigo-950',
  'from-slate-900 to-purple-950',
];

const SHIFT_TO_API = {
  shift_1: 'morning',
  shift_2: 'afternoon',
  shift_3: 'night',
};

const SHIFT_LABELS = {
  morning: 'Tura 1 (Dimineață: 06:00 - 14:00)',
  afternoon: 'Tura 2 (Prânz: 14:00 - 22:00)',
  night: 'Tura 3 (Noapte: 22:00 - 06:00)',
};

const TYPE_LABELS = {
  RESTRICTED_ZONE: 'Zonă restricționată',
  NO_PPE: 'Echipament lipsă',
  FOD: 'FOD',
  SMOKING: 'Fumat',
  CAMERA_OFFLINE: 'Cameră offline',
};

function apiPath(path) {
  return `${API_BASE_URL}${path}`;
}

function queryString(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value);
    }
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : '';
}

function resolveAsset(url) {
  if (!url) return '';
  if (/^https?:\/\//i.test(url) || url.startsWith('data:')) return url;
  return `${API_BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`;
}

async function http(path, options = {}) {
  const headers = { ...(options.body ? (options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }) : {}), ...(options.headers || {}) };
  const response = await fetch(apiPath(path), { ...options, headers });
  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch {
      detail = await response.text();
    }
    throw new Error(`${response.status} ${detail || response.statusText}`);
  }
  return response.json();
}

function mapCamera(camera, index = 0) {
  return {
    ...camera,
    status: camera.online ? 'online' : 'offline',
    engine_on: Boolean(camera.engine_on),
    zone: '',
    fps: camera.online ? 30 : 0,
    resolution: camera.online ? 'LIVE MJPEG' : 'SEMNAL PIERDUT',
    previewBg: PALETTES[index % PALETTES.length],
    boxes: [],
    stream_url: `${API_BASE_URL}/stream/${encodeURIComponent(camera.id)}.mjpg`,
  };
}

function mapEvent(event) {
  return { ...event, snapshot_url: resolveAsset(event.snapshot_url) };
}

function mapZone(zone) {
  return {
    ...zone,
    zone_id: zone.id,
    polygon: (zone.polygon || []).map(([x, y]) => ({ x, y })),
  };
}

function toZonePayload(zoneId, zoneData) {
  return {
    id: zoneId,
    camera_id: zoneData.camera_id,
    name: zoneData.name || zoneData.zone_id || zoneId,
    rule_type: zoneData.rule_type,
    active_when: zoneData.active_when,
    required_ppe: zoneData.required_ppe || [],
    severity: zoneData.severity,
    debounce_s: Number(zoneData.debounce_s),
    escalate_after_s: zoneData.escalate_after_s == null ? null : Number(zoneData.escalate_after_s),
    notify_channel: 'slack',
    polygon: (zoneData.polygon || []).map((point) => [Number(point.x), Number(point.y)]),
    reference_frame: zoneData.reference_frame || null,
  };
}

function mapKpi(kpi) {
  return {
    ppe_compliance_pct: kpi.ppe_compliance == null ? '—' : Math.round(kpi.ppe_compliance * 1000) / 10,
    open_incidents_count: kpi.open_incidents,
    detection_to_alert_latency_s: kpi.avg_detection_to_alert_s == null ? '—' : kpi.avg_detection_to_alert_s,
    escalated_incidents_count: kpi.escalated,
  };
}

function mapShiftReport(report) {
  const byType = (report.by_type || []).map((row) => ({
    type: row.type,
    label: TYPE_LABELS[row.type] || row.type,
    count: (row.critical || 0) + (row.warning || 0),
  }));
  const total = byType.reduce((sum, row) => sum + row.count, 0);
  const critical = (report.by_type || []).reduce((sum, row) => sum + (row.critical || 0), 0);
  const warning = (report.by_type || []).reduce((sum, row) => sum + (row.warning || 0), 0);
  const ackValues = (report.by_zone || []).map((zone) => zone.avg_ack_s).filter((value) => value != null);
  const avgAck = ackValues.length
    ? Math.round(ackValues.reduce((sum, value) => sum + value, 0) / ackValues.length)
    : null;

  return {
    shift: SHIFT_LABELS[report.shift] || report.shift,
    date: report.date,
    kpi: {
      total_events: total,
      critical_events: critical,
      warning_events: warning,
      avg_ack_time_s: avgAck == null ? '—' : avgAck,
      ppe_compliance_pct: report.kpi?.ppe_compliance == null
        ? '—'
        : Math.round(report.kpi.ppe_compliance * 1000) / 10,
    },
    summary: report.summary,
    by_type: byType,
    by_zone: (report.by_zone || []).map((zone) => ({
      zone: zone.zone_id,
      critical: zone.critical,
      warning: zone.warning,
      avg_ack_s: zone.avg_ack_s == null ? '—' : zone.avg_ack_s,
    })),
    by_hour: (report.by_hour || []).map((row) => ({
      hour: `${row.hour}:00`,
      events: row.count,
    })),
  };
}

export const safeSightApi = {
  async getCameras() {
    if (USE_MOCK) return INITIAL_CAMERAS;
    const cameras = await http('/cameras');
    return cameras.map(mapCamera);
  },

  async setEngineState(cameraId, on) {
    if (USE_MOCK) return { camera_id: cameraId, engine_on: on };
    const camera = await http(`/cameras/${encodeURIComponent(cameraId)}/engine`, {
      method: 'PUT',
      body: JSON.stringify({ on }),
    });
    return mapCamera(camera);
  },

  async getZones(cameraId) {
    if (USE_MOCK) {
      return cameraId
        ? INITIAL_ZONES.filter((zone) => zone.camera_id === cameraId)
        : INITIAL_ZONES;
    }
    const zones = await http(`/zones${queryString({ camera_id: cameraId })}`);
    return zones.map(mapZone);
  },

  async saveZone(zoneId, zoneData) {
    if (USE_MOCK) return { ...zoneData, zone_id: zoneId, saved: true };
    const zone = await http(`/zones/${encodeURIComponent(zoneId)}`, {
      method: 'PUT',
      body: JSON.stringify(toZonePayload(zoneId, zoneData)),
    });
    return mapZone(zone);
  },

  async captureReferenceFrame(zoneId, file) {
    if (USE_MOCK) return { zone_id: zoneId, captured_at: new Date().toISOString() };
    const form = new FormData();
    form.append('zone_id', zoneId);
    form.append('file', file);
    const zone = await http('/zones/reference-frame', { method: 'POST', body: form });
    return mapZone(zone);
  },

  async getEvents({ status = '', severity = '', camera_id = '' } = {}) {
    if (USE_MOCK) {
      let filtered = [...INITIAL_EVENTS];
      if (status && status !== 'all') filtered = filtered.filter((event) => event.status === status);
      if (severity && severity !== 'all') filtered = filtered.filter((event) => event.severity === severity);
      if (camera_id && camera_id !== 'all') filtered = filtered.filter((event) => event.camera_id === camera_id);
      return filtered;
    }
    const events = await http(`/events${queryString({ status, severity, camera_id, limit: 200 })}`);
    return events.map(mapEvent);
  },

  async getEventById(eventId) {
    if (USE_MOCK) return INITIAL_EVENTS.find((event) => event.event_id === eventId) || null;
    return mapEvent(await http(`/events/${encodeURIComponent(eventId)}`));
  },

  async acknowledgeEvent(eventId, operator = 'Ariana') {
    if (USE_MOCK) return { event_id: eventId, status: 'acknowledged', acked_by: operator };
    return mapEvent(await http(`/events/${encodeURIComponent(eventId)}/ack`, {
      method: 'POST',
      body: JSON.stringify({ operator }),
    }));
  },

  async markFalsePositive(eventId, operator = 'Ariana', note = '') {
    if (USE_MOCK) return { event_id: eventId, status: 'false_positive', note };
    return mapEvent(await http(`/events/${encodeURIComponent(eventId)}/false-positive`, {
      method: 'POST',
      body: JSON.stringify({ operator, note }),
    }));
  },

  async reopenEvent(eventId, operator = 'Ariana') {
    if (USE_MOCK) return { event_id: eventId, status: 'open' };
    return mapEvent(await http(`/events/${encodeURIComponent(eventId)}/reopen`, {
      method: 'POST',
      body: JSON.stringify({ operator }),
    }));
  },

  async regenerateReport(eventId) {
    if (USE_MOCK) return { report: { source: 'llm' } };
    return mapEvent(await http(`/events/${encodeURIComponent(eventId)}/regenerate-report`, { method: 'POST' }));
  },

  async getKPIs(date = '', shift = '') {
    if (USE_MOCK) return { ...INITIAL_KPIS };
    return mapKpi(await http(`/kpi${queryString({ date, shift })}`));
  },

  async getShiftReport(shift = 'morning', date = new Date().toISOString().slice(0, 10)) {
    if (USE_MOCK) return { ...INITIAL_SHIFT_REPORT };
    return mapShiftReport(await http(`/reports${queryString({ shift, date })}`));
  },

  connectEventsSocket(onMessage, onError, onOpen) {
    if (USE_MOCK) {
      const interval = setInterval(() => {
        onMessage({ type: 'kpi.updated', data: { ...INITIAL_KPIS } });
      }, 4000);
      return () => clearInterval(interval);
    }

    const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/ws/events`;
    let socket;
    let stopped = false;
    let retryTimer;

    const connect = () => {
      socket = new WebSocket(wsUrl);
      socket.onopen = () => onOpen?.();
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message?.data && (message.type === 'event.created' || message.type === 'event.updated')) {
            message.data = mapEvent(message.data);
          }
          onMessage(message);
        } catch (error) {
          console.error('WS parse error', error);
        }
      };
      socket.onerror = () => onError?.();
      socket.onclose = () => {
        onError?.();
        if (!stopped) retryTimer = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  },

  shiftToApi(shiftId) {
    return SHIFT_TO_API[shiftId] || 'morning';
  },
};
