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

export function SecurityProvider({ children }) {
  // 1. Navigare Ecrane:
  // 'live' | 'incident_detail' | 'zones' | 'reports' | 'mobile' | 'settings'
  const [currentView, setCurrentView] = useState('live');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // 2. Operator & Autentificare Simplă (Multi-User Switcher)
  const [operatorId, setOperatorId] = useState('ariana');
  const activeOperator = useMemo(() => {
    return AVAILABLE_OPERATORS.find((o) => o.id === operatorId) || AVAILABLE_OPERATORS[0];
  }, [operatorId]);

  const operatorName = activeOperator.name;

  const switchOperator = (id) => {
    setOperatorId(id);
    const op = AVAILABLE_OPERATORS.find((o) => o.id === id);
    if (op) {
      showToast(`Sesiune activă comutată pe: ${op.name} (${op.role})`);
    }
  };

  // 3. Camere CCTV & Stare Motor (PUT /cameras/{id}/engine)
  // Începe întotdeauna cu datele mock ca fallback garantat, apoi se sincronizează dacă backend-ul răspunde
  const [cameras, setCameras] = useState(INITIAL_CAMERAS);
  const [selectedCameraId, setSelectedCameraId] = useState('stand12');

  // 4. Evenimente & Incidente
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [selectedEventId, setSelectedEventId] = useState('evt_stand12_1730284933120_17');
  const [filterMode, setFilterMode] = useState('open'); // 'open' | 'critical' | 'all'
  const [searchQuery, setSearchQuery] = useState('');

  // 5. KPI Live (4 KPI: PPE, incidente deschise, latență, escaladate)
  const [kpis, setKpis] = useState(INITIAL_KPIS);

  // 6. Zone & Editor Poligoane
  const [zones, setZones] = useState(INITIAL_ZONES);

  // 7. Raport de Tură
  const [shiftReport, setShiftReport] = useState(INITIAL_SHIFT_REPORT);
  const [selectedShift, setSelectedShift] = useState('shift_1');

  // 8. Stare Conexiune & Toast / Banner Erori (Regulă C-10)
  const [isWsConnected, setIsWsConnected] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3800);
  };

  // Sincronizare cu backend-ul real când este disponibil (fără a bloca UI-ul dacă este oprit)
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

      if (cams.status === 'fulfilled' && cams.value?.length > 0) {
        setCameras(cams.value);
        setSelectedCameraId((current) =>
          cams.value.some((c) => c.id === current) ? current : cams.value[0]?.id
        );
      }
      if (evs.status === 'fulfilled' && evs.value?.length > 0) {
        setEvents(evs.value);
        setSelectedEventId((current) =>
          evs.value.some((e) => e.event_id === current) ? current : evs.value[0]?.event_id
        );
      }
      if (zs.status === 'fulfilled' && zs.value?.length > 0) {
        setZones(zs.value);
      }
      if (kpi.status === 'fulfilled' && kpi.value) {
        setKpis(kpi.value);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  // Raportul de tură se reîncarcă la schimbarea turei
  useEffect(() => {
    if (USE_MOCK) return;
    let cancelled = false;
    safeSightApi
      .getShiftReport(safeSightApi.shiftToApi(selectedShift))
      .then((report) => { if (!cancelled && report) setShiftReport(report); })
      .catch(() => {});
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
    return (events || []).filter((ev) => {
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

  // Actualizare automată a KPI-urilor când se schimbă evenimentele
  useEffect(() => {
    const openCount = (events || []).filter((e) => e.status === 'open' || e.status === 'escalated').length;
    const escalatedCount = (events || []).filter((e) => e.status === 'escalated').length;
    setKpis((prev) => ({
      ...prev,
      open_incidents_count: openCount,
      escalated_incidents_count: escalatedCount
    }));
  }, [events]);

  // Escaladare automată (timer în frontend dacă backend-ul nu este activ)
  useEffect(() => {
    const escalationInterval = setInterval(() => {
      const now = Date.now();
      setEvents((prevEvents) =>
        prevEvents.map((ev) => {
          if (ev.status === 'open' && ev.escalate_after_s) {
            const detectedTime = new Date(ev.detected_at).getTime();
            if (now - detectedTime >= ev.escalate_after_s * 1000) {
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

  // WebSocket real cu reconnect la 2s conform C-10
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

  // Polling fallback la 2s dacă WebSocket-ul pică
  useEffect(() => {
    if (USE_MOCK || isWsConnected) return;
    const poll = async () => {
      try {
        const [evs, kpi] = await Promise.all([safeSightApi.getEvents(), safeSightApi.getKPIs()]);
        if (evs?.length) setEvents(evs);
        if (kpi) setKpis(kpi);
      } catch {
        // Bannerul C-10 rămâne activ
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
      if (updated) {
        setEvents((prev) => prev.map((ev) => (ev.event_id === eventId ? { ...ev, ...updated } : ev)));
      }
      showToast(`Evenimentul ${eventId.slice(-6)} confirmat de ${operatorName}. Escaladare oprită.`);
    } catch {
      // Păstrează starea optimistă în caz de deconectare
      showToast(`Eveniment confirmat local de ${operatorName}.`);
    }
  };

  // 2. Fals Pozitiv (C-03: Iese din Deschise, rămâne în Toate)
  const markFalsePositive = async (eventId, note = '') => {
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
      await safeSightApi.markFalsePositive(eventId, operatorName, note);
      showToast('Marcat ca Fals Pozitiv. Feedback înregistrat.');
    } catch {
      showToast('Marcat ca Fals Pozitiv local.');
    }
  };

  // 3. Reopen (C-04: Revine în Deschise; timerul repornește)
  const reopenEvent = async (eventId) => {
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
      await safeSightApi.reopenEvent(eventId, operatorName);
      showToast('Eveniment redeschis. Timerul de escaladare a repornit.');
    } catch {
      showToast('Eveniment redeschis local.');
    }
  };

  // 4. Regenerare Raport (LLM)
  const regenerateReport = async (eventId) => {
    showToast('Regenerare raport LLM în curs...');
    try {
      const result = await safeSightApi.regenerateReport(eventId);
      if (result?.report) {
        setEvents((prev) =>
          prev.map((ev) =>
            ev.event_id === eventId ? { ...ev, report: result.report } : ev
          )
        );
        showToast('Raportul a fost recalculat prin LLM.');
      }
    } catch {
      showToast('Raport recalculat pe șablon local.');
    }
  };

  // 5. Toggle Engine ON / OFF (PUT /cameras/{id}/engine)
  const toggleEngine = async (cameraId) => {
    const cam = cameras.find((c) => c.id === cameraId);
    const newState = !cam?.engine_on;
    setCameras((prev) =>
      prev.map((c) => (c.id === cameraId ? { ...c, engine_on: newState } : c))
    );
    showToast(`Stare motor pentru ${cameraId}: ${newState ? 'PORNIT (ON)' : 'OPRIT (OFF)'}`);
    try {
      await safeSightApi.setEngineState(cameraId, newState);
    } catch {
      // Păstrează modificarea UI
    }
  };

  // 6. Cadru de referință FOD
  const captureReferenceFrame = async (cameraId) => {
    showToast(`Salvare cadru de referință FOD pentru ${cameraId}...`);
    try {
      await safeSightApi.captureReferenceFrame(cameraId);
      showToast(`Cadru de referință salvat cu succes.`);
    } catch {
      showToast(`Cadru de referință simulat salvat.`);
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
    try {
      await safeSightApi.saveZone(zoneId, zoneData);
      showToast(`Zona ${zoneId} salvată. Aplicată fără restart.`);
    } catch {
      showToast(`Zona ${zoneId} salvată local.`);
    }
  };

  // 8. SIMULATOR DEMO PITCH:
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
      escalate_after_s: 30,
      acked_at: null,
      acked_by: null,
      report: {
        what: 'Alertă Live: Operator GSE a intrat în raza de admisie a motorului.',
        where: 'Stand 12, zona engine-left.',
        when: new Date().toLocaleTimeString('ro-RO'),
        severity_reason: 'Turbină activă cu flux de admisie critic; risc major de accident.',
        recommended_action: 'Avertizare imediată prin radio și oprire procedură pushback.',
        source: 'llm'
      }
    };

    setEvents((prev) => [newEvent, ...prev]);
    setSelectedEventId(newId);

    if (severity === 'CRITICAL') {
      playCriticalAlertSound();
    }
    showToast(`Eveniment nou: ${newEvent.report.what}`);
  };

  const toggleWsSimulation = () => {
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
        setOperatorName: (name) => {
          const found = AVAILABLE_OPERATORS.find((o) => o.name === name);
          if (found) setOperatorId(found.id);
        },
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
