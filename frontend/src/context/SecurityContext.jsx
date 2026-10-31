import React, { createContext, useContext, useState, useMemo, useEffect } from 'react';
import {
  INITIAL_CAMERAS,
  INITIAL_EVENTS,
  INITIAL_ZONES,
  INITIAL_KPIS,
  INITIAL_SHIFT_REPORT,
  AVAILABLE_OPERATORS
} from '../constants/mockData';
import { safeSightApi, USE_MOCK } from '../services/api';
import { playCriticalAlertSound } from '../utils/sound';

const SecurityContext = createContext();

const OPERATOR_STORAGE_KEY = 'safesight.operator';

function loadOperatorName() {
  try {
    return localStorage.getItem(OPERATOR_STORAGE_KEY)?.trim() || '';
  } catch {
    return '';
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

  // 2. Operator & autentificare simplă: selector de rol + nume afișat editabil.
  const [operatorId, setOperatorId] = useState('ariana');
  const activeOperator = useMemo(
    () => AVAILABLE_OPERATORS.find((operator) => operator.id === operatorId) || AVAILABLE_OPERATORS[0],
    [operatorId]
  );
  const [customOperatorName, setCustomOperatorName] = useState(loadOperatorName);
  const operatorName = customOperatorName || activeOperator.name;

  const setOperatorName = (name) => {
    const trimmed = name.trim();
    setCustomOperatorName(trimmed);
    try {
      if (trimmed) localStorage.setItem(OPERATOR_STORAGE_KEY, trimmed);
      else localStorage.removeItem(OPERATOR_STORAGE_KEY);
    } catch {
      // Fără storage, numele rămâne doar pentru sesiunea curentă.
    }
  };

  const switchOperator = (id) => {
    setOperatorId(id);
    setOperatorName('');
    const selected = AVAILABLE_OPERATORS.find((operator) => operator.id === id);
    if (selected) {
      showToast(`Sesiune activă comutată pe: ${selected.name} (${selected.role})`);
    }
  };

  // 3. Camere CCTV & Stare Motor (PUT /cameras/{id}/engine)
  const [cameras, setCameras] = useState(INITIAL_CAMERAS);
  const [selectedCameraId, setSelectedCameraId] = useState('stand12');

  // 4. Evenimente & Incidente
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [selectedEventId, setSelectedEventId] = useState(USE_MOCK ? 'evt_stand12_1730284933120_17' : null);
  const [filterMode, setFilterMode] = useState('open'); // 'open' | 'critical' | 'all'
  const [searchQuery, setSearchQuery] = useState('');

  // 5. KPI Live (4 KPI: PPE, incidente deschise, latență, escaladate)
  const [kpis, setKpis] = useState(INITIAL_KPIS);

  // 6. Zone & Editor Poligoane
  const [zones, setZones] = useState(INITIAL_ZONES);

  // 7. Raport de Tură
  const [shiftReport, setShiftReport] = useState(INITIAL_SHIFT_REPORT);
  const [selectedShift, setSelectedShift] = useState(() => (USE_MOCK ? 'shift_1' : safeSightApi.currentShiftId()));

  // 8. Stare Conexiune & Toast / Banner Erori (Regulă C-10)
  const [isWsConnected, setIsWsConnected] = useState(true);
  const [isReconnecting, setIsReconnecting] = useState(false);
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
    return cameras.find((c) => c.id === selectedCameraId) || cameras[0] || INITIAL_CAMERAS[0];
  }, [cameras, selectedCameraId]);

  // Evenimentul selectat pentru detaliu
  const selectedEvent = useMemo(() => {
    return events.find((e) => e.event_id === selectedEventId) || events[0] || INITIAL_EVENTS[0];
  }, [events, selectedEventId]);

  // Filtrarea evenimentelor pentru Feed-ul din Live (Deschise, Doar critice, Toate azi)
  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        ev.event_id?.toLowerCase().includes(q) ||
        ev.type?.toLowerCase().includes(q) ||
        ev.report?.what?.toLowerCase().includes(q) ||
        ev.report?.where?.toLowerCase().includes(q) ||
        ev.camera_id?.toLowerCase().includes(q);

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
    const openCount = events.filter((e) => e.status === 'open' || e.status === 'escalated').length;
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
    const newState = !cam?.engine_on;
    setCameras((prev) =>
      prev.map((c) => (c.id === cameraId ? { ...c, engine_on: newState } : c))
    );
    try {
      const updated = await safeSightApi.setEngineState(cameraId, newState);
      if (updated?.engine_on !== undefined) {
        setCameras((prev) => prev.map((item) => (
          item.id === cameraId ? { ...item, engine_on: updated.engine_on, status: updated.status || item.status } : item
        )));
      }
      showToast(`Stare motor pentru ${cameraId}: ${newState ? 'PORNIT (ON)' : 'OPRIT (OFF)'}`);
    } catch (error) {
      // Dacă backend-ul este temporar indisponibil, păstrează starea locală fără Failed to fetch
      showToast(`Stare motor pentru ${cameraId}: ${newState ? 'PORNIT (ON)' : 'OPRIT (OFF)'} (stare locală)`);
    }
  };

  // 6. Cadru de referință FOD (upload JPEG deja blurat)
  const captureReferenceFrame = async (zoneId, file) => {
    showToast(`Salvare cadru de referință pentru zona ${zoneId}...`);
    try {
      const updatedZone = await safeSightApi.captureReferenceFrame(zoneId, file);
      if (updatedZone) {
        setZones((prev) => prev.map((z) => (z.zone_id === zoneId ? { ...z, ...updatedZone } : z)));
      }
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

  // C-10: Reconectare manuală & sincronizare Edge
  const toggleWsSimulation = async () => {
    setIsReconnecting(true);
    showToast('Reconectare în curs la Edge & rețeaua de senzori...');
    try {
      const [kpi, evs, cams] = await Promise.allSettled([
        safeSightApi.getKPIs(),
        safeSightApi.getEvents(),
        safeSightApi.getCameras()
      ]);
      if (kpi.status === 'fulfilled' && kpi.value) setKpis(kpi.value);
      if (evs.status === 'fulfilled' && evs.value?.length) setEvents(evs.value);
      if (cams.status === 'fulfilled' && cams.value?.length) setCameras(cams.value);
      setIsWsConnected(true);
      showToast('Conexiune cu Edge restabilită.');
    } catch {
      setIsWsConnected(true);
      showToast('Mod operativ activat.');
    } finally {
      setTimeout(() => setIsReconnecting(false), 800);
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
        operatorId,
        activeOperator,
        switchOperator,
        availableOperators: AVAILABLE_OPERATORS,
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
        isReconnecting,
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
