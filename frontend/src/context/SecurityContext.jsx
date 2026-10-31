import React, { createContext, useContext, useState, useMemo, useEffect } from 'react';
import {
  INITIAL_CAMERAS,
  INITIAL_EVENTS,
  INITIAL_ZONES,
  INITIAL_KPIS,
  INITIAL_SHIFT_REPORT
} from '../constants/mockData';
import { safeTarmacApi } from '../services/api';
import { playCriticalAlertSound } from '../utils/sound';

const SecurityContext = createContext();

export function SecurityProvider({ children }) {
  // 1. Navigare Ecrane (Conform 03_C_frontend.pdf):
  // 'live' | 'incident_detail' | 'zones' | 'reports' | 'mobile' | 'settings'
  const [currentView, setCurrentView] = useState('live');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // 2. Operator & Autentificare Simplă (Decizie N08: câmp operator în demo)
  const [operatorName, setOperatorName] = useState('Ariana');

  // 3. Camere CCTV & Stare Motor (PUT /cameras/{id}/engine)
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

  // Recalculare automată KPI din lista curentă de evenimente
  useEffect(() => {
    const openCount = events.filter((e) => e.status === 'open').length;
    const escalatedCount = events.filter((e) => e.status === 'escalated').length;
    setKpis((prev) => ({
      ...prev,
      open_incidents_count: openCount,
      escalated_incidents_count: escalatedCount
    }));
  }, [events]);

  // Escaladare automată bazată pe timp (Decizie N22: escalate_after_s per zonă/eveniment)
  useEffect(() => {
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

  // Conectare WebSocket / Heartbeat (sau Polling dacă WS cade - C-10)
  useEffect(() => {
    const disconnect = safeTarmacApi.connectEventsSocket(
      (msg) => {
        setIsWsConnected(true);
        if (msg.kpi) {
          setKpis((prev) => ({ ...prev, ...msg.kpi }));
        }
      },
      () => {
        setIsWsConnected(false);
      }
    );
    return () => disconnect();
  }, []);

  // ACȚIUNI PRINCIPALE:

  // 1. Acknowledge (Buton principal, un singur clic - C-02)
  const acknowledgeEvent = async (eventId, e) => {
    if (e) e.stopPropagation();
    // Optimistic update
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
    showToast(`Evenimentul ${eventId.slice(-6)} confirmat de ${operatorName}. Escaladare anulată.`);
    await safeTarmacApi.acknowledgeEvent(eventId, operatorName);
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
    showToast(`Marcat ca Fals Pozitiv. Feedback înregistrat pentru modelul AI.`);
    await safeTarmacApi.markFalsePositive(eventId, operatorName, note);
  };

  // 3. Reopen (C-04: Revine în Deschise; timerul repornește)
  const reopenEvent = async (eventId) => {
    setEvents((prev) =>
      prev.map((ev) =>
        ev.event_id === eventId
          ? {
              ...ev,
              status: 'open',
              detected_at: new Date().toISOString(), // Repornește timerul de escaladare
              escalated_at: null,
              acked_at: null,
              acked_by: null
            }
          : ev
      )
    );
    showToast(`Eveniment redeschis. Timerul de escaladare a repornit.`);
    await safeTarmacApi.reopenEvent(eventId, operatorName);
  };

  // 4. Regenerare Raport (LLM)
  const regenerateReport = async (eventId) => {
    showToast('Regenerare raport LLM în curs...');
    const result = await safeTarmacApi.regenerateReport(eventId);
    if (result?.report) {
      setEvents((prev) =>
        prev.map((ev) =>
          ev.event_id === eventId ? { ...ev, report: result.report } : ev
        )
      );
      showToast('Raportul de incident a fost actualizat prin LLM.');
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
    await safeTarmacApi.setEngineState(cameraId, newState);
  };

  // 6. Cadru de referință FOD (Capture empty frame)
  const captureReferenceFrame = async (cameraId) => {
    showToast(`Salvare cadru de referință FOD pentru ${cameraId}...`);
    await safeTarmacApi.captureReferenceFrame(cameraId);
    showToast(`Cadru de referință curat salvat cu succes.`);
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
    await safeTarmacApi.saveZone(zoneId, zoneData);
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

  // C-10: Simulare cădere / reconectare WebSocket
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
