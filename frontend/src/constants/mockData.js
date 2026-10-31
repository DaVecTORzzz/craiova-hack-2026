// Contractul canonic SafeSight conform specificațiilor din 03_C_frontend.pdf

export const INITIAL_CAMERAS = [
  {
    id: "stand12",
    code: "CAM-01",
    name: "CAM-01 • Stand 12 Avion B777",
    subtitle: "Alimentare & Întreținere (Zonă Motor Apron)",
    category: "Alimentare & Rampă",
    zone_id: "engine-left",
    rtsp_url: "rtsp://edge.airport.local/live/stand12",
    status: "online",
    engine_on: true,
    fps: 30,
    resolution: "4K (3840x2160)",
    previewBg: "from-blue-950 via-slate-900 to-indigo-950",
    boxes: [
      {
        id: "box-stand12-1",
        label: "Persoană #17 în Zonă Motor",
        type: "critical",
        coords: { top: "34%", left: "54%", width: "18%", height: "42%" },
        trackingId: "track_17",
        details: "Persoană în zona motorului stâng, cu motorul pornit (1.4s)"
      },
      {
        id: "box-stand12-2",
        label: "Zonă Motor GE90 Activă",
        type: "warning",
        coords: { top: "25%", left: "48%", width: "30%", height: "55%" },
        trackingId: "engine-left",
        details: "active_when: engine_on = true"
      }
    ]
  },
  {
    id: "runway08",
    code: "CAM-02",
    name: "CAM-02 • Pista 08R Runway",
    subtitle: "Cale de Rulare & Axa Centrală Decolare",
    category: "Pistă & Căi Rulare",
    zone_id: "runway-center",
    rtsp_url: "rtsp://edge.airport.local/live/runway08",
    status: "online",
    engine_on: false,
    fps: 60,
    resolution: "4K 60FPS HDR",
    previewBg: "from-zinc-900 to-neutral-800",
    boxes: [
      {
        id: "box-runway08-1",
        label: "FOD Detectat pe Cale Rulare",
        type: "critical",
        coords: { top: "58%", left: "38%", width: "20%", height: "18%" },
        trackingId: "fod_441",
        details: "Obiect metalic nespecificat ~14cm pe axul pistei"
      }
    ]
  },
  {
    id: "gate4b",
    code: "CAM-03",
    name: "CAM-03 • Terminal 1 - Poarta 4B",
    subtitle: "Zonă Îmbarcare Pasageri & Finger",
    category: "Terminal & Porți",
    zone_id: "gate-boarding",
    rtsp_url: "rtsp://edge.airport.local/live/gate4b",
    status: "online",
    engine_on: false,
    fps: 30,
    resolution: "1080p 30FPS",
    previewBg: "from-slate-900 to-indigo-950",
    boxes: [
      {
        id: "box-gate4b-1",
        label: "Aglomerație 3.8 p/m²",
        type: "warning",
        coords: { top: "35%", left: "48%", width: "24%", height: "38%" },
        trackingId: "crowd_92",
        details: "Formare de bottleneck la scanare bilete"
      }
    ]
  },
  {
    id: "checkin_t1",
    code: "CAM-04",
    name: "CAM-04 • Terminal Plecări",
    subtitle: "Hol Public & Ghișee Check-In",
    category: "Terminal & Porți",
    zone_id: "public-hall",
    rtsp_url: "rtsp://edge.airport.local/live/checkin",
    status: "online",
    engine_on: false,
    fps: 30,
    resolution: "4K (3840x2160)",
    previewBg: "from-slate-900 to-purple-950",
    boxes: [
      {
        id: "box-checkin-1",
        label: "Bagaj Abandonat #991",
        type: "critical",
        coords: { top: "52%", left: "44%", width: "20%", height: "28%" },
        trackingId: "bagg_991",
        details: "Valiză statică nesupravegheată de peste 10 minute"
      }
    ]
  },
  {
    id: "baggage_south",
    code: "CAM-05",
    name: "CAM-05 • Rampă Sud",
    subtitle: "Triere & Manipulare Bagaje Cală",
    category: "Alimentare & Rampă",
    zone_id: "ramp-south",
    rtsp_url: "rtsp://edge.airport.local/live/baggage_south",
    status: "offline", // CAMERA_OFFLINE generat după 5s fără cadre
    engine_on: false,
    fps: 0,
    resolution: "Semnal Nedisponibil",
    previewBg: "from-neutral-900 to-black",
    boxes: []
  }
];

export const AVAILABLE_OPERATORS = [
  { id: 'ariana', name: 'Ariana V.', role: 'Dispatcher Principal (Lead)', badge: 'AIRSIDE-LEAD' },
  { id: 'mihai', name: 'Mihai D.', role: 'Șef Tură Rampă & Apron', badge: 'RAMP-CHIEF' },
  { id: 'radu', name: 'Radu P.', role: 'Inspector Siguranță Sol', badge: 'SAFETY-INSP' }
];

export const INITIAL_EVENTS = [
  {
    event_id: "evt_stand12_1730284933120_17",
    type: "RESTRICTED_ZONE",
    severity: "CRITICAL",
    camera_id: "stand12",
    zone_id: "engine-left",
    track_id: 17,
    confidence: { detector: 0.91, temporal: { seen: 14, window: 15 } },
    duration_s: 1.4,
    context: { engine_on: true },
    snapshot_url: "https://images.unsplash.com/photo-1542296332-2e4473faf563?w=800&auto=format&fit=crop&q=60",
    model: "person-ppe-v1",
    detected_at: "2026-10-31T07:42:13.120Z",
    status: "open", // open, acknowledged, false_positive, escalated, resolved
    received_at: "2026-10-31T07:42:13.310Z",
    notified_at: "2026-10-31T07:42:14.920Z",
    escalated_at: null,
    escalate_after_s: 30, // Seed 30s demo, 120s producție
    acked_at: null,
    acked_by: null,
    report: {
      what: "Persoană în zona motorului stâng, cu motorul pornit.",
      where: "Stand 12, zona engine-left.",
      when: "10:42:13, timp în zonă 1,4 s.",
      severity_reason: "Motorul e pornit; risc de ingestie sau jet blast.",
      recommended_action: "Oprește activitatea la Stand 12. Contactează persoana prin radio.",
      source: "llm"
    }
  },
  {
    event_id: "evt_runway08_1730284520110_44",
    type: "FOD_DETECTED",
    severity: "CRITICAL",
    camera_id: "runway08",
    zone_id: "runway-center",
    track_id: 44,
    confidence: { detector: 0.96, temporal: { seen: 15, window: 15 } },
    duration_s: 3.2,
    context: { engine_on: false },
    snapshot_url: "https://images.unsplash.com/photo-1508873696983-2df5703bc20d?w=800&auto=format&fit=crop&q=60",
    model: "fod-detector-v2",
    detected_at: "2026-10-31T07:38:15.000Z",
    status: "open",
    received_at: "2026-10-31T07:38:15.200Z",
    notified_at: "2026-10-31T07:38:16.100Z",
    escalated_at: null,
    escalate_after_s: 30,
    acked_at: null,
    acked_by: null,
    report: {
      what: "Fragment metalic reflectorizant de ~14cm pe axul pistei active.",
      where: "Pista 08R, intersecție calea de rulare Bravo.",
      when: "10:38:15, identificat la 420m de prag.",
      severity_reason: "Pericol de absorbție în turbinele avioanelor sau tăiere anvelopă la decolare.",
      recommended_action: "Blochează autorizările de decolare din TWR și trimite vehiculul 'Follow-Me' FOD sweeper.",
      source: "llm"
    }
  },
  {
    event_id: "evt_stand12_1730283921004_12",
    type: "PPE_VIOLATION",
    severity: "WARNING",
    camera_id: "stand12",
    zone_id: "engine-left",
    track_id: 12,
    confidence: { detector: 0.88, temporal: { seen: 13, window: 15 } },
    duration_s: 4.5,
    context: { engine_on: true },
    snapshot_url: "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=800&auto=format&fit=crop&q=60",
    model: "person-ppe-v1",
    detected_at: "2026-10-31T07:31:30.000Z",
    status: "acknowledged",
    received_at: "2026-10-31T07:31:30.220Z",
    notified_at: "2026-10-31T07:31:31.050Z",
    escalated_at: null,
    escalate_after_s: 60,
    acked_at: "2026-10-31T07:32:05.100Z",
    acked_by: "Ariana V.",
    report: {
      what: "Tehnician de mentenanță fără căști antifonice conforme EN 352.",
      where: "Stand 12, proximitate motor B777.",
      when: "10:31:30, la o distanță de 7m de turbină.",
      severity_reason: "Nivel acustic >110dB generat de APU și motor în idle.",
      recommended_action: "Avertizează echipa la sol prin canalul radio TETRA alocat.",
      source: "llm"
    }
  },
  {
    event_id: "evt_checkin_1730283120011_99",
    type: "UNATTENDED_BAGGAGE",
    severity: "CRITICAL",
    camera_id: "checkin_t1",
    zone_id: "public-hall",
    track_id: 991,
    confidence: { detector: 0.98, temporal: { seen: 15, window: 15 } },
    duration_s: 620.0,
    context: { engine_on: false },
    snapshot_url: "https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=800&auto=format&fit=crop&q=60",
    model: "baggage-tracker-v3",
    detected_at: "2026-10-31T07:25:12.000Z",
    status: "escalated", // A depășit timpul fără confirmare
    received_at: "2026-10-31T07:25:12.200Z",
    notified_at: "2026-10-31T07:25:13.500Z",
    escalated_at: "2026-10-31T07:25:43.500Z",
    escalate_after_s: 30,
    acked_at: null,
    acked_by: null,
    report: {
      what: "Rucsac negru abandonat fără pasager pe o rază de 3.5m timp de peste 10 minute.",
      where: "Terminal Plecări, în fața Ghișeului 14.",
      when: "10:25:12.",
      severity_reason: "Risc potențial de securitate; alertă de tip EOD.",
      recommended_action: "Izolează perimetrul pe o rază de 15m și apelează patrula pirotehnică.",
      source: "llm"
    }
  },
  {
    event_id: "evt_baggage_1730282000000_01",
    type: "CAMERA_OFFLINE",
    severity: "WARNING",
    camera_id: "baggage_south",
    zone_id: "ramp-south",
    track_id: 0,
    confidence: { detector: 1.0, temporal: { seen: 15, window: 15 } },
    duration_s: 180.0,
    context: { engine_on: false },
    snapshot_url: "",
    model: "system-health-v1",
    detected_at: "2026-10-31T07:15:00.000Z",
    status: "open",
    received_at: "2026-10-31T07:15:00.100Z",
    notified_at: "2026-10-31T07:15:01.000Z",
    escalated_at: null,
    escalate_after_s: null,
    acked_at: null,
    acked_by: null,
    report: {
      what: "Flux video întrerupt de peste 5 secunde.",
      where: "Rampa Sud, sector triere bagaje.",
      when: "10:15:00.",
      severity_reason: "Pierdere vizibilitate operațională în zona critică de cală.",
      recommended_action: "Verifică switch-ul PoE de rețea sau trimite tehnician IT.",
      source: "template"
    }
  }
];

export const INITIAL_ZONES = [
  {
    zone_id: "engine-left",
    camera_id: "stand12",
    rule_type: "RESTRICTED_ZONE",
    active_when: "engine_on",
    required_ppe: ["ear_protection", "high_vis_vest"],
    severity: "CRITICAL",
    debounce_s: 1.4,
    notify_channel: "slack_safety_ops",
    escalate_after_s: 30,
    polygon: [
      { x: 0.45, y: 0.2 },
      { x: 0.78, y: 0.2 },
      { x: 0.85, y: 0.82 },
      { x: 0.42, y: 0.82 }
    ]
  },
  {
    zone_id: "runway-center",
    camera_id: "runway08",
    rule_type: "FOD_DETECTED",
    active_when: "always",
    required_ppe: [],
    severity: "CRITICAL",
    debounce_s: 3.0,
    notify_channel: "slack_tower_ops",
    escalate_after_s: 30,
    polygon: [
      { x: 0.15, y: 0.4 },
      { x: 0.85, y: 0.4 },
      { x: 0.95, y: 0.85 },
      { x: 0.05, y: 0.85 }
    ]
  }
];

export const INITIAL_KPIS = {
  ppe_compliance_pct: 94.2,
  open_incidents_count: 3,
  detection_to_alert_latency_s: 1.8,
  escalated_incidents_count: 1
};

export const INITIAL_SHIFT_REPORT = {
  shift: "Tura 1 (Dimineață: 06:00 - 14:00)",
  date: "2026-10-31",
  kpi: {
    total_events: 18,
    critical_events: 4,
    warning_events: 14,
    avg_ack_time_s: 38,
    ppe_compliance_pct: 94.2
  },
  summary: "Tura de dimineață a decurs conform normelor ICAO, cu un nivel de conformitate PPE de 94.2%. A fost neutralizat rapid un fragment FOD pe Pista 08R în mai puțin de 4 minute, prevenind întârzieri pe fluxul de decolare.",
  by_type: [
    { type: "PPE_VIOLATION", count: 9, label: "Echipament Lipsă" },
    { type: "RESTRICTED_ZONE", count: 4, label: "Zonă Restricționată" },
    { type: "FOD_DETECTED", count: 2, label: "FOD Runway" },
    { type: "UNATTENDED_BAGGAGE", count: 2, label: "Bagaje Abandonate" },
    { type: "CAMERA_OFFLINE", count: 1, label: "Camere Offline" }
  ],
  by_zone: [
    { zone: "Stand 12 (Apron Est)", critical: 2, warning: 5, avg_ack_s: 28 },
    { zone: "Pista 08R (Runway)", critical: 1, warning: 1, avg_ack_s: 14 },
    { zone: "Terminal 1 (Check-in/Gate)", critical: 1, warning: 4, avg_ack_s: 46 },
    { zone: "Triere Bagaje Sud", critical: 0, warning: 4, avg_ack_s: 62 }
  ],
  by_hour: [
    { hour: "06:00", events: 1 },
    { hour: "07:00", events: 3 },
    { hour: "08:00", events: 5 },
    { hour: "09:00", events: 4 },
    { hour: "10:00", events: 5 }
  ]
};
