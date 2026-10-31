import React, { createContext, useContext, useState, useMemo, useEffect } from 'react';
import {
  INITIAL_CAMERAS,
  INITIAL_EVENTS,
  INITIAL_ZONES,
  INITIAL_KPIS,
  INITIAL_SHIFT_REPORT
} from '../constants/mockData';
import { safeSightApi, USE_MOCK } from '../services/api';
import { playCriticalAlertSound } from '../utils/sound';

const SecurityContext = createContext();

const OPERATOR_STORAGE_KEY = 'safesight.operator';

function loadOperatorName() {
  try {
    return localStorage.getItem(OPERATOR_STORAGE_KEY) || 'Operator';
  } catch {
    return 'Operator';
  }
}

const EMPTY_KPIS = {
  ppe_compliance_pct: '—',
  open_incidents_count: 0,
  detection_to_alert_latency_s: '—',
  escalated_incidents_count: 0,
};

const EMPTY_SHIFT_REPORT = {
  shift: '—',
  date: '—',
  kpi: {
    total_events: 0,
    critical_events: 0,
    warning_events: 0,
    avg_ack_time_s: '—',
    ppe_compliance_pct: '—',
  },
  summary: 'Se încarcă raportul de tură...',
  by_type: [],
  by_zone: [],
  by_hour: [],
};

export function SecurityProvider({ children }) {
  // 1. Navigare Ecrane (Conform 03_C_frontend.pdf):
  // 'live' | 'incident_detail' | 'zones' | 'reports' | 'mobile' | 'settings'
  const [currentView, setCurrentView] = useState('live');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // 2. Operator & Autentificare Simplă (Decizie N08: câmp operator în demo)
  const [operatorName, setOperatorNameState] = useState(loadOperatorName);
  const setOperatorName = (name) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setOperatorNameState(trimmed);
    try {
      localStorage.setItem(OPERATOR_STORAGE_KEY, trimmed);
    } catch {
      // Fără storage, numele rămâne doar pentru sesiunea curentă.
    }
  };

  // 3. Camere CCTV & Stare Motor (PUT /cameras/{id}/engine)
  const [cameras, setCameras] = useState(USE_MOCK ? INITIAL_CAMERAS : []);
  const [selectedCameraId, setSelectedCameraId] = useState('stand12');

  // 4. Evenimente & Incidente
  const [events, setEvents] = useState(USE_MOCK ? INITIAL_EVENTS : []);
  const [selectedEventId, setSelectedEventId] = useState(USE_MOCK ? 'evt_stand12_1730284933120_17' : null);
  const [filterMode, setFilterMode] = useState('open'); // 'open' | 'critical' | 'all'
  const [searchQuery, setSearchQuery] = useState('');

  // 5. KPI Live (4 KPI: PPE, incidente deschise, latență, escaladate)
  const [kpis, setKpis] = useState(USE_MOCK ? INITIAL_KPIS : EMPTY_KPIS);

  // 6. Zone & Editor Poligoane
  const [zones, setZones] = useState(USE_MOCK ? INITIAL_ZONES : []);

  // 7. Raport de Tură
  const [shiftReport, setShiftReport] = useState(USE_MOCK ? INITIAL_SHIFT_REPORT : EMPTY_SHIFT_REPORT);
  const [selectedShift, setSelectedShift] = useState(() => safeSightApi.currentShiftId());

  // 8. Stare Conexiune & Toast / Banner Erori (Regulă C-10)
  const [isWsConnected, setIsWsConnected] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3800);
  };

  // Încarcă datele reale din backend. Un endpoint picat nu le blochează pe celelalte.
  useEffect(() => {
    if (USE_MOCK) return;
    let cancelled = false;

    const load = async () => {
      const [cams, evs, zs, kpi] = await Promise.allSettled([
        safeSightApi.getCameras(),
        safeSightApi.getEvents(),
        safeSightApi.getZones(),
        safeSightApi.getKPIs()
      ]);
      if (cancelled) return;

      const failures = [];
      if (cams.status === 'fulfilled') {
        setCameras(cams.value);
        setSelectedCameraId((current) =>
          cams.value.some((c) => c.id === current) ? current : cams.value[0]?.id
        );
      } else {
        failures.push('camere');
      }
      if (evs.status === 'fulfilled') {
        setEvents(evs.value);
        setSelectedEventId((current) =>
          evs.value.some((e) => e.event_id === current) ? current : evs.value[0]?.event_id
        );
      } else {
        failures.push('evenimente');
      }
      if (zs.status === 'fulfilled') {
        setZones(zs.value);
      } else {
        failures.push('zone');
      }
      if (kpi.status === 'fulfilled') {
        setKpis(kpi.value);
      } else {
        failures.push('KPI');
      }

      if (failures.length) {
        showToast(`Backend incomplet: ${failures.join(', ')} indisponibil. Restul datelor sunt reale.`);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  // Raportul de tură se reîncarcă la schimbarea turei.
  useEffect(() => {
    if (USE_MOCK) return;
    let cancelled = false;
    safeSightApi
      .getShiftReport(safeSightApi.shiftToApi(selectedShift), safeSightApi.shiftDate(selectedShift))
      .then((report) => { if (!cancelled) setShiftReport(report); })
      .catch(() => { if (!cancelled) showToast('Raportul de tură nu a putut fi încărcat.'); });
    return () => { cancelled = true; };
  }, [selectedShift]);

  // Camera activă curentă
  const activeCamera = useMemo(() => {
    return cameras.find((c) => c.id === selectedCameraId) || cameras[0];
  }, [cameras, selectedCameraId]);

  // Evenimentul selectat pentru detaliu
  const selectedEvent = useMemo(() => {
    return events.find((e) => e.event_id === selectedEventId) || events[0];
  }, [events, selectedEventId]);

  // Filtrarea evenimentelor pentru Feed-ul din Live (Deschise, Doar critice, Toate azi)
  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        ev.event_id.toLowerCase().includes(q) ||
        ev.type.toLowerCase().includes(q) ||
        ev.report?.what?.toLowerCase().includes(q) ||
        ev.report?.where?.toLowerCase().includes(q) ||
        ev.camera_id.toLowerCase().includes(q);

      let matchesFilter = true;
      if (filterMode === 'open') {
        matchesFilter = ev.status === 'open' || ev.status === 'escalated';
      } else if (filterMode === 'critical') {
        matchesFilter = ev.severity === 'CRITICAL';
      } else if (filterMode === 'all') {
        matchesFilter = true;
      }

      return matchesSearch && matchesFilter;
    });
  }, [events, filterMode, searchQuery]);

  // Recalculare KPI doar în mock; în producție cifrele vin din `/kpi`.
  useEffect(() => {
    if (!USE_MOCK) return;
    const openCount = events.filter((e) => e.status === 'open').length;
    const escalatedCount = events.filter((e) => e.status === 'escalated').length;
    setKpis((prev) => ({
      ...prev,
      open_incidents_count: openCount,
      escalated_incidents_count: escalatedCount
    }));
  }, [events]);

  // Escaladare simulată doar în mock; în producție backend-ul ține timerul.
  useEffect(() => {
    if (!USE_MOCK) return;
    const escalationInterval = setInterval(() => {
      const now = Date.now();
      setEvents((prevEvents) =>
        prevEvents.map((ev) => {
          if (ev.status === 'open' && ev.escalate_after_s) {
            const detectedTime = new Date(ev.detected_at).getTime();
            if (now - detectedTime >= ev.escalate_after_s * 1000) {
              // Escaladare declanșată!
              return {
                ...ev,
                status: 'escalated',
                escalated_at: new Date().toISOString()
              };
            }
          }
          return ev;
        })
      );
    }, 1000);

    return () => clearInterval(escalationInterval);
  }, []);

  // WebSocket real; dacă pică, polling la 2 s (C-10).
  useEffect(() => {
    const disconnect = safeSightApi.connectEventsSocket(
      (msg) => {
        setIsWsConnected(true);
        if (msg.type === 'kpi.updated' && msg.data) {
          setKpis((prev) => ({ ...prev, ...msg.data }));
          return;
        }
        if (msg.type === 'event.created' || msg.type === 'event.updated') {
          const incoming = msg.data;
          setEvents((prev) => {
            const index = prev.findIndex((event) => event.event_id === incoming.event_id);
            if (index >= 0) {
              const next = [...prev];
              next[index] = incoming;
              return next;
            }
            return [incoming, ...prev].slice(0, 200);
          });
          if (msg.type === 'event.created' && incoming.severity === 'CRITICAL') {
            playCriticalAlertSound();
          }
          safeSightApi.getKPIs().then(setKpis).catch(() => {});
        }
      },
      () => setIsWsConnected(false),
      () => setIsWsConnected(true)
    );
    return () => disconnect();
  }, []);

  useEffect(() => {
    if (USE_MOCK || isWsConnected) return;
    const poll = async () => {
      try {
        const [evs, kpi] = await Promise.all([safeSightApi.getEvents(), safeSightApi.getKPIs()]);
        setEvents(evs);
        setKpis(kpi);
      } catch {
        // Banner-ul de conexiune rămâne vizibil; reîncercăm la următorul tick.
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [isWsConnected]);

  // ACȚIUNI PRINCIPALE:

  // 1. Acknowledge (Buton principal, un singur clic - C-02)
  const acknowledgeEvent = async (eventId, e) => {
    if (e) e.stopPropagation();
    const previous = events.find((ev) => ev.event_id === eventId);
    setEvents((prev) =>
      prev.map((ev) =>
        ev.event_id === eventId
          ? {
              ...ev,
              status: 'acknowledged',
              acked_at: new Date().toISOString(),
              acked_by: operatorName
            }
          : ev
      )
    );
    try {
      const updated = await safeSightApi.acknowledgeEvent(eventId, operatorName);
      setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? { ...ev, ...updated } : ev)));
      showToast(`Evenimentul ${eventId.slice(-6)} confirmat de ${operatorName}. Escaladare anulată.`);
    } catch (error) {
      if (previous) setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? previous : ev)));
      showToast(`Ack eșuat: ${error.message}`);
    }
  };

  // 2. Fals Pozitiv (C-03: Iese din Deschise, rămâne în Toate)
  const markFalsePositive = async (eventId, note = '') => {
    const previous = events.find((ev) => ev.event_id === eventId);
    setEvents((prev) =>
      prev.map((ev) =>
        ev.event_id === eventId
          ? {
              ...ev,
              status: 'false_positive',
              false_positive_note: note,
              false_positive_by: operatorName
            }
          : ev
      )
    );
    try {
      const updated = await safeSightApi.markFalsePositive(eventId, operatorName, note);
      setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? { ...ev, ...updated } : ev)));
      showToast('Marcat ca Fals Pozitiv. Feedback înregistrat pentru modelul AI.');
    } catch (error) {
      if (previous) setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? previous : ev)));
      showToast(`Fals pozitiv eșuat: ${error.message}`);
    }
  };

  // 3. Reopen (C-04: Revine în Deschise; timerul repornește)
  const reopenEvent = async (eventId) => {
    const previous = events.find((ev) => ev.event_id === eventId);
    setEvents((prev) =>
      prev.map((ev) =>
        ev.event_id === eventId
          ? {
              ...ev,
              status: 'open',
              detected_at: new Date().toISOString(),
              escalated_at: null,
              acked_at: null,
              acked_by: null
            }
          : ev
      )
    );
    try {
      const updated = await safeSightApi.reopenEvent(eventId, operatorName);
      setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? { ...ev, ...updated } : ev)));
      showToast('Eveniment redeschis. Timerul de escaladare a repornit.');
    } catch (error) {
      if (previous) setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? previous : ev)));
      showToast(`Reopen eșuat: ${error.message}`);
    }
  };

  // 4. Regenerare Raport (LLM)
  const regenerateReport = async (eventId) => {
    showToast('Regenerare raport LLM în curs...');
    try {
      const updated = await safeSightApi.regenerateReport(eventId);
      setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? { ...ev, ...updated } : ev)));
      showToast('Raportul de incident a fost actualizat.');
    } catch (error) {
      showToast(`Regenerarea raportului a eșuat: ${error.message}`);
    }
  };

  // 5. Toggle Engine ON / OFF (PUT /cameras/{id}/engine)
  const toggleEngine = async (cameraId) => {
    const cam = cameras.find((c) => c.id === cameraId);
    const previous = cam?.engine_on;
    const newState = !cam?.engine_on;
    setCameras((prev) =>
      prev.map((c) => (c.id === cameraId ? { ...c, engine_on: newState } : c))
    );
    try {
      const updated = await safeSightApi.setEngineState(cameraId, newState);
      setCameras((prev) => prev.map((item) => (
        item.id === cameraId ? { ...item, engine_on: updated.engine_on, status: updated.status } : item
      )));
      showToast(`Stare motor pentru ${cameraId}: ${newState ? 'PORNIT (ON)' : 'OPRIT (OFF)'}`);
    } catch (error) {
      setCameras((prev) => prev.map((item) => (
        item.id === cameraId ? { ...item, engine_on: previous } : item
      )));
      showToast(`Comutarea motorului a eșuat: ${error.message}`);
    }
  };

  // 6. Cadru de referință FOD (upload JPEG deja blurat)
  const captureReferenceFrame = async (zoneId, file) => {
    showToast(`Salvare cadru de referință pentru zona ${zoneId}...`);
    try {
      await safeSightApi.captureReferenceFrame(zoneId, file);
      showToast('Cadru de referință curat salvat cu succes.');
    } catch (error) {
      showToast(`Cadrul de referință a eșuat: ${error.message}`);
    }
  };

  // 7. Salvare Zonă Poligon
  const saveZone = async (zoneId, zoneData) => {
    setZones((prev) => {
      const idx = prev.findIndex((z) => z.zone_id === zoneId);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = { ...updated[idx], ...zoneData };
        return updated;
      }
      return [...prev, zoneData];
    });
    showToast(`Zona ${zoneId} salvată. Rețeaua AI o aplică fără restart.`);
    try {
      const updated = await safeSightApi.saveZone(zoneId, zoneData);
      setZones((prev) => {
        const index = prev.findIndex((zone) => zone.zone_id === zoneId);
        if (index >= 0) {
          const next = [...prev];
          next[index] = { ...next[index], ...updated, zone_id: zoneId };
          return next;
        }
        return [...prev, { ...updated, zone_id: zoneId }];
      });
    } catch (error) {
      showToast(`Salvarea zonei a eșuat: ${error.message}`);
    }
  };

  // 8. SIMULATOR DEMO PITCH (Pentru Ariana & Dalina în fața juriului):
  // C-01: Simulare sosire eveniment nou prin WebSocket
  const simulateIncomingWsEvent = (type = 'RESTRICTED_ZONE', severity = 'CRITICAL') => {
    const newId = `evt_stand12_${Date.now()}_${Math.floor(Math.random() * 80 + 10)}`;
    const newEvent = {
      event_id: newId,
      type: type,
      severity: severity,
      camera_id: 'stand12',
      zone_id: 'engine-left',
      track_id: Math.floor(Math.random() * 50 + 10),
      confidence: { detector: 0.94, temporal: { seen: 14, window: 15 } },
      duration_s: 1.2,
      context: { engine_on: true },
      snapshot_url: 'https://images.unsplash.com/photo-1542296332-2e4473faf563?w=800&auto=format&fit=crop&q=60',
      model: 'person-ppe-v1',
      detected_at: new Date().toISOString(),
      status: 'open',
      received_at: new Date().toISOString(),
      notified_at: new Date().toISOString(),
      escalated_at: null,
      escalate_after_s: 30, // 30s până la escaladare
      acked_at: null,
      acked_by: null,
      report: {
        what: 'Alertă Live: Operator GSE a intrat în raza jet-blast a turbinei stângi.',
        where: 'Stand 12, zona engine-left.',
        when: new Date().toLocaleTimeString('ro-RO'),
        severity_reason: 'Turbină activă cu flux de admisie critic; risc major de accident.',
        recommended_action: 'Avertizare imediată prin radio și oprire procedură pushback.',
        source: 'llm'
      }
    };

    setEvents((prev) => [newEvent, ...prev]);
    setSelectedEventId(newId);

    // Sunet scurt pentru alerte CRITICAL (Conform §4.3)
    if (severity === 'CRITICAL') {
      playCriticalAlertSound();
    }
    showToast(`Eveniment nou detectat prin WebSocket: ${newEvent.report.what}`);
  };

  // C-10: simulare doar în mock; în real WS-ul se reconectează singur.
  const toggleWsSimulation = () => {
    if (!USE_MOCK) {
      showToast('WebSocket-ul se reconectează automat; polling-ul rămâne activ până revine.');
      return;
    }
    if (isWsConnected) {
      setIsWsConnected(false);
      showToast('Simulare WS Căzut: Polling activat la 2s conform C-10.');
    } else {
      setIsWsConnected(true);
      showToast('Simulare WS Reconectat: Date sincronizate.');
    }
  };

  return (
    <SecurityContext.Provider
      value={{
        currentView,
        setCurrentView,
        isSidebarCollapsed,
        setIsSidebarCollapsed,
        operatorName,
        setOperatorName,
        cameras,
        selectedCameraId,
        setSelectedCameraId,
        activeCamera,
        events,
        filteredEvents,
        selectedEventId,
        setSelectedEventId,
        selectedEvent,
        filterMode,
        setFilterMode,
        searchQuery,
        setSearchQuery,
        kpis,
        zones,
        shiftReport,
        selectedShift,
        setSelectedShift,
        isWsConnected,
        setIsWsConnected,
        toastMessage,
        showToast,
        acknowledgeEvent,
        markFalsePositive,
        reopenEvent,
        regenerateReport,
        toggleEngine,
        captureReferenceFrame,
        saveZone,
        simulateIncomingWsEvent,
        toggleWsSimulation
      }}
    >
      {children}
    </SecurityContext.Provider>
  );
}

export function useSecurity() {
  const context = useContext(SecurityContext);
  if (!context) {
    throw new Error('useSecurity must be used within a SecurityProvider');
  }
  return context;
}
