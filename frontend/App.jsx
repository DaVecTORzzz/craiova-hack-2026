import React, { useState, useMemo, useEffect } from "react";
import {
  Shield,
  ShieldAlert,
  Video,
  Camera,
  Search,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Volume2,
  VolumeX,
  Eye,
  Activity,
  Wifi,
  WifiOff,
  UserCheck,
  Clock,
  Sliders,
  X,
  Check,
  Radio,
  FileText,
  Settings,
  BarChart3,
  Layers,
  Sparkles,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Info,
  CornerDownRight,
  Download,
  RefreshCw,
  Play,
  Pause,
  Flame,
  Luggage,
  Users,
  Plane,
  Headphones,
  HardHat,
  Filter,
  Trash2,
  ExternalLink,
  SplitSquareVertical,
  LayoutDashboard,
  ShieldCheck,
  Cpu
} from "lucide-react";

// ==========================================
// MOCK DATA: CAMERE CCTV AEROPORT
// ==========================================
const INITIAL_CAMERAS = [
  {
    id: "CAM-01",
    name: "Terminal 1 - Poarta 4B",
    zone: "Zonă Îmbarcare Pasageri",
    status: "online",
    fps: 30,
    resolution: "4K (3840x2160)",
    feedType: "interior",
    incidentsCount: 1,
    previewBg: "from-slate-900 to-indigo-950",
    boxes: [
      {
        id: "box-1",
        label: "Aglomerație Flux 74%",
        type: "warning", // yellow
        coords: { top: "35%", left: "48%", width: "24%", height: "38%" },
        trackingId: "TRK-0192",
        details: "Densitate 3.8 pers/m² lângă ghișeul de îmbarcare."
      },
      {
        id: "box-2",
        label: "Cale Evacuare Sigură",
        type: "resolved", // green
        coords: { top: "20%", left: "12%", width: "18%", height: "45%" },
        trackingId: "TRK-0193",
        details: "Ușă evacuare liberă, flux optim."
      }
    ]
  },
  {
    id: "CAM-02",
    name: "Pista 08R - Runway & Cale Rulare",
    zone: "Zonă Critică Decolare / Aterizare",
    status: "online",
    fps: 60,
    resolution: "4K 60FPS HDR",
    feedType: "runway",
    incidentsCount: 1,
    previewBg: "from-zinc-900 to-neutral-800",
    boxes: [
      {
        id: "box-3",
        label: "FOD Detectat pe Cale Rulare 96%",
        type: "critical", // red
        coords: { top: "58%", left: "38%", width: "22%", height: "20%" },
        trackingId: "FOD-8841",
        details: "Obiect metalic nespecificat ~14cm pe axul pistei."
      }
    ]
  },
  {
    id: "CAM-03",
    name: "Zonă Alimentare B777 (Apron Est)",
    zone: "Tarmac / Alimentare Cherosen Jet-A1",
    status: "online",
    fps: 30,
    resolution: "1080p 60FPS",
    feedType: "apron",
    incidentsCount: 2,
    previewBg: "from-blue-950 to-slate-900",
    boxes: [
      {
        id: "box-4",
        label: "FUMAT INTERZIS ÎN PERIMETRU 99%",
        type: "critical", // red
        coords: { top: "28%", left: "62%", width: "22%", height: "42%" },
        trackingId: "HAZ-003",
        details: "Sursă activă de fum detectată lângă cisterna de combustibil."
      },
      {
        id: "box-5",
        label: "FĂRĂ CĂȘTI ANTIFONICE 88%",
        type: "warning", // yellow
        coords: { top: "42%", left: "22%", width: "19%", height: "40%" },
        trackingId: "PPE-109",
        details: "Operator la sol sub 10m de motor fără EIP auditiv."
      }
    ]
  },
  {
    id: "CAM-04",
    name: "Terminal Plecări - Check-In",
    zone: "Hol Public Principal",
    status: "online",
    fps: 30,
    resolution: "4K (3840x2160)",
    feedType: "interior",
    incidentsCount: 1,
    previewBg: "from-slate-900 to-purple-950",
    boxes: [
      {
        id: "box-6",
        label: "BAGAJ ABANDONAT 98%",
        type: "critical", // red
        coords: { top: "52%", left: "44%", width: "20%", height: "28%" },
        trackingId: "BAGG-991",
        details: "Rucsac negru nesupravegheat de peste 10 minute."
      }
    ]
  },
  {
    id: "CAM-05",
    name: "Triere Bagaje & Rampă Sud",
    zone: "Zonă Tehnică Cală & Benzi Transfer",
    status: "offline",
    fps: 0,
    resolution: "Semnal Nedisponibil",
    feedType: "technical",
    incidentsCount: 0,
    previewBg: "from-neutral-900 to-black",
    boxes: []
  },
  {
    id: "CAM-06",
    name: "Control Securitate - Porți X-Ray",
    zone: "Filtru Control Pasageri & Bagaje Cabină",
    status: "online",
    fps: 30,
    resolution: "1080p 30FPS",
    feedType: "security",
    incidentsCount: 1,
    previewBg: "from-slate-900 to-slate-800",
    boxes: [
      {
        id: "box-7",
        label: "Distanță Siguranță Respectată 95%",
        type: "resolved", // green
        coords: { top: "30%", left: "32%", width: "36%", height: "50%" },
        trackingId: "SAF-202",
        details: "Conformitate maximă protocol inspecție corporală."
      }
    ]
  },
  {
    id: "CAM-07",
    name: "Perimetru Gard Nord (Linie Graniță)",
    zone: "Senzori Optici & PIDS Exterioare",
    status: "offline",
    fps: 0,
    resolution: "Semnal Nedisponibil",
    feedType: "perimeter",
    incidentsCount: 0,
    previewBg: "from-black to-zinc-950",
    boxes: []
  },
  {
    id: "CAM-08",
    name: "Stand 12 - Descărcare Cărucioare Bagaje",
    zone: "Tarmac Descărcare Aeronave",
    status: "online",
    fps: 30,
    resolution: "1080p 30FPS",
    feedType: "apron",
    incidentsCount: 1,
    previewBg: "from-slate-950 to-blue-950",
    boxes: [
      {
        id: "box-8",
        label: "Manipulare Brutală Bagaje 82%",
        type: "warning", // yellow
        coords: { top: "40%", left: "40%", width: "25%", height: "35%" },
        trackingId: "BAGG-412",
        details: "Aruncare repetată a bagajelor de cală peste 1.4m înălțime."
      }
    ]
  }
];

// ==========================================
// MOCK DATA: ALERTE INCIDENTE AI (XAI)
// ==========================================
const INITIAL_INCIDENTS = [
  {
    id: "INC-8901",
    cameraId: "CAM-04",
    cameraName: "Terminal Plecări - Check-In",
    title: "Bagaj Nesupravegheat (Posibil Dispozitiv)",
    category: "Securitate Publică",
    severity: "critical", // red: pericol iminent
    confidence: 98,
    detectedAt: "19:57:12 (Acum 2 min)",
    boxLabel: "BAGAJ ABANDONAT [PERICOL IMINENT]",
    reasoning:
      "Obiect volumetric static identificat de peste 10 minute fără pasager asociat pe o rază de 3.5m. Risc ridicat de explozibil sau substanțe periculoase.",
    targetType: "Valiză / Rucsac Negru",
    zone: "Hol Plecări, Ghișeu 14",
    snapshotId: "SNAP-8901-T1.jpg",
    actionSuggested: "Izolare zonă și alertare echipă pirotehnică (EOD)."
  },
  {
    id: "INC-8902",
    cameraId: "CAM-03",
    cameraName: "Zonă Alimentare B777 (Apron Est)",
    title: "Fumat Activ în Proximitatea Cisternei Jet-A1",
    category: "Risc Incendiu / Explozie",
    severity: "critical", // red: pericol iminent
    confidence: 99,
    detectedAt: "19:55:04 (Acum 4 min)",
    boxLabel: "FUMAT LÂNGĂ CISTERNE [PERICOL IMINENT]",
    reasoning:
      "Detecție optică spectrală de flacără deschisă și emisie de fum de la o țigară activă la 4 metri de furtunul de transfer combustibil.",
    targetType: "Operator Sol Neneidentificat",
    zone: "Stand Apron 03",
    snapshotId: "SNAP-8902-FUEL.jpg",
    actionSuggested: "Oprire imediată alimentare și evacuare/reținere operator."
  },
  {
    id: "INC-8903",
    cameraId: "CAM-03",
    cameraName: "Zonă Alimentare B777 (Apron Est)",
    title: "Personal Fără Căști Antifonice (EIP Lipsă)",
    category: "Protecția Muncii & EIP",
    severity: "warning", // yellow: avertisment
    confidence: 88,
    detectedAt: "19:51:30 (Acum 8 min)",
    boxLabel: "PROTECȚIE AUDITIVĂ LIPSĂ [AVERTISMENT]",
    reasoning:
      "Tehnician mentenanță aflat în perimetrul de 9 metri de turbina GE90 în regim de relanti (idle) fără căști fonoizolante conforme EN 352.",
    targetType: "Muncitor Sol GSE",
    zone: "Perimetru Motor Stâng B777",
    snapshotId: "SNAP-8903-EIP.jpg",
    actionSuggested: "Transmitere avertisment acustic pe stația de sol a echipei."
  },
  {
    id: "INC-8904",
    cameraId: "CAM-02",
    cameraName: "Pista 08R - Runway & Cale Rulare",
    title: "FOD (Foreign Object Debris) pe Pista Activă",
    category: "Siguranță Aeronautică",
    severity: "critical", // red: pericol iminent
    confidence: 96,
    detectedAt: "19:48:15 (Acum 11 min)",
    boxLabel: "OBIECT METALIC STRĂIN [PERICOL IMINENT]",
    reasoning:
      "Fragment metalic reflectorizant de ~14cm identificat pe axul pistei la 420m de prag. Pericol extrem de ingestie în motoare sau explozie anvelopă.",
    targetType: "Piesă Metalică Pierdută",
    zone: "Pista 08R - Segment Intersecție Bravo",
    snapshotId: "SNAP-8904-FOD.jpg",
    actionSuggested: "Blocare decolări din TWR și trimitere vehicul 'Follow-Me' FOD sweeper."
  },
  {
    id: "INC-8905",
    cameraId: "CAM-08",
    cameraName: "Stand 12 - Descărcare Cărucioare Bagaje",
    title: "Manipulare Brutală / Aruncare Bagaje",
    category: "Integritate Bagaje & Conduită",
    severity: "warning", // yellow: avertisment
    confidence: 82,
    detectedAt: "19:44:20 (Acum 15 min)",
    boxLabel: "ARUNCARE REPETATĂ BAGAJ [AVERTISMENT]",
    reasoning:
      "Analiza cinematică indică aruncarea bagajelor fragile de la o înălțime de 1.5m cu forță de impact ce depășește standardele IATA de manipulare.",
    targetType: "Echipă Manipulanți Bagaje",
    zone: "Platforma Cărucioare C12",
    snapshotId: "SNAP-8905-BAG.jpg",
    actionSuggested: "Înregistrare abatere în registrul de calitate handling."
  },
  {
    id: "INC-8906",
    cameraId: "CAM-01",
    cameraName: "Terminal 1 - Poarta 4B",
    title: "Supra-Aglomerație Critică la Poarta de Îmbarcare",
    category: "Control Mulțimi",
    severity: "warning", // yellow: avertisment
    confidence: 74,
    detectedAt: "19:41:00 (Acum 18 min)",
    boxLabel: "DENSITATE DEPASITĂ 3.8 P/M² [AVERTISMENT]",
    reasoning:
      "Formare de 'bottleneck' în fața porții 4B cauzată de întârzierea scanării biletelor; căile de evacuare de urgență sunt parțial obstrucționate.",
    targetType: "Grup Pasageri Îmbarcare",
    zone: "Coridor Poarta 4B",
    snapshotId: "SNAP-8906-CROWD.jpg",
    actionSuggested: "Deschidere bandă secundară de acces și ghidare flux."
  },
  {
    id: "INC-8907",
    cameraId: "CAM-06",
    cameraName: "Control Securitate - Porți X-Ray",
    title: "Distanță Siguranță Echipament X-Ray Restabilită",
    category: "Protocol Securitate",
    severity: "resolved", // green: remediat
    confidence: 95,
    detectedAt: "19:37:44 (Acum 22 min)",
    boxLabel: "PROTOCOL CONFORM [REMEDIAT]",
    reasoning:
      "Operatorul a recalibrat poziția de protecție la scanarea scanerului computer tomograf. Niciun risc activ.",
    targetType: "Filtru Securitate Linia 2",
    zone: "Punct Control Pasageri",
    snapshotId: "SNAP-8907-SAFE.jpg",
    actionSuggested: "Nicio acțiune necesară. Incident remediat."
  }
];

export default function App() {
  // 1. TEMA: Dark / Light Mode (STRICT conform specificațiilor din enunț)
  // Dark Mode: bg: #292929, panels: #352F6B, accent: #4034AD, text: alb/gri
  // Light Mode: bg: #F5F5F5, panels: #B3F1B2, accent: #70ED6E, text: negru/gri
  const [isDarkMode, setIsDarkMode] = useState(true);

  // 2. NAVIGARE & VIZUALIZĂRI
  // currentView: 'dashboard' | 'feed-fullscreen' | 'feed-split' | 'analytics' | 'settings'
  const [currentView, setCurrentView] = useState("dashboard");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // 3. STATURI CAMERE & SELECTIE
  const [cameras, setCameras] = useState(INITIAL_CAMERAS);
  const [selectedCameraId, setSelectedCameraId] = useState("CAM-04");

  // 4. STATURI INCIDENTE & FILTRARE
  const [incidents, setIncidents] = useState(INITIAL_INCIDENTS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [severityFilter, setSeverityFilter] = useState("all"); // 'all' | 'critical' | 'warning' | 'resolved'

  // 5. CAPTURI AUTOMATE (AUTO-SCREENSHOT ON DETECTION)
  const [capturedScreenshots, setCapturedScreenshots] = useState([
    {
      id: "SNAP-8901",
      camera: "CAM-04 (Terminal Plecări)",
      title: "Bagaj Nesupravegheat 98%",
      time: "19:57:12",
      type: "critical",
      hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    {
      id: "SNAP-8902",
      camera: "CAM-03 (Zonă Alimentare)",
      title: "Fumat Lângă Cisterne 99%",
      time: "19:55:04",
      type: "critical",
      hash: "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
    },
    {
      id: "SNAP-8904",
      camera: "CAM-02 (Pista 08R)",
      title: "FOD Detectat Pista 08R 96%",
      time: "19:48:15",
      type: "critical",
      hash: "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
    }
  ]);
  const [showSnapshotModal, setShowSnapshotModal] = useState(false);
  const [activeSnapshot, setActiveSnapshot] = useState(null);

  // 6. TOAST DE FEEDBACK
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  // Camera activă curentă
  const activeCamera = useMemo(() => {
    return cameras.find((c) => c.id === selectedCameraId) || cameras[0];
  }, [cameras, selectedCameraId]);

  // Filtrarea incidentelor în timp real din Search Bar + filtru severitate
  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        inc.title.toLowerCase().includes(q) ||
        inc.cameraName.toLowerCase().includes(q) ||
        inc.reasoning.toLowerCase().includes(q) ||
        inc.boxLabel.toLowerCase().includes(q) ||
        inc.targetType.toLowerCase().includes(q);

      const matchesSeverity =
        severityFilter === "all" || inc.severity === severityFilter;

      return matchesSearch && matchesSeverity;
    });
  }, [incidents, searchQuery, severityFilter]);

  // Acknowledge incident: eliminare din listă + notificare
  const handleAcknowledge = (id, e) => {
    if (e) e.stopPropagation();
    const incToRemove = incidents.find((i) => i.id === id);
    setIncidents((prev) => prev.filter((i) => i.id !== id));
    showToast(
      `Incidentul "${incToRemove?.title || id}" a fost arhivat și marcat ca REZOLVAT.`
    );
  };

  // Declanșare captură ecran manuală / simulare auto-captură
  const handleManualCapture = () => {
    const newSnap = {
      id: `SNAP-${Date.now().toString().slice(-4)}`,
      camera: `${activeCamera.id} (${activeCamera.name})`,
      title: activeCamera.boxes[0]?.label || "Captură Supraveghere Live",
      time: new Date().toLocaleTimeString("ro-RO"),
      type: activeCamera.boxes[0]?.type || "resolved",
      hash: Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
    };
    setCapturedScreenshots((prev) => [newSnap, ...prev]);
    showToast(`Captură automată AI salvată cu hash: ${newSnap.hash.slice(0, 12)}...`);
  };

  // Reset date demo
  const handleResetData = () => {
    setIncidents(INITIAL_INCIDENTS);
    setCameras(INITIAL_CAMERAS);
    showToast("Datele demonstrative au fost reîncărcate complet.");
  };

  // Configurare culori conform specificațiilor stricte
  // Dark:  Main bg: #292929, Panels: #352F6B, Accent: #4034AD, Text: Alb/Gri
  // Light: Main bg: #F5F5F5, Panels: #B3F1B2, Accent: #70ED6E, Text: Negru/Gri închis
  const themeStyles = {
    appBg: isDarkMode ? "#292929" : "#F5F5F5",
    panelBg: isDarkMode ? "#352F6B" : "#B3F1B2",
    panelBorder: isDarkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
    accentColor: isDarkMode ? "#4034AD" : "#70ED6E",
    accentHover: isDarkMode ? "#4e41cb" : "#5cdc5a",
    textColor: isDarkMode ? "#FFFFFF" : "#0F172A",
    textMuted: isDarkMode ? "#CBD5E1" : "#334155",
    headerBg: isDarkMode ? "#352F6B" : "#B3F1B2",
    cardBg: isDarkMode ? "rgba(41, 41, 41, 0.45)" : "rgba(255, 255, 255, 0.55)",
    badgeBg: isDarkMode ? "rgba(64, 52, 173, 0.35)" : "rgba(112, 237, 110, 0.45)",
    inputBg: isDarkMode ? "#292929" : "#FFFFFF"
  };

  // Render bounding boxes color-coded
  // Pericole iminente: chenar rosu
  // Warning-uri: chenar galben
  // Remediate: chenar verde
  const renderBoundingBox = (box) => {
    const isCritical = box.type === "critical";
    const isWarning = box.type === "warning";
    const isResolved = box.type === "resolved";

    let borderColor = "border-emerald-400";
    let bgColor = "bg-emerald-500/10";
    let tagBg = "bg-emerald-600 text-white";
    let pulseRing = "ring-emerald-400/40";

    if (isCritical) {
      borderColor = "border-red-500";
      bgColor = "bg-red-500/15";
      tagBg = "bg-red-600 text-white animate-pulse";
      pulseRing = "ring-red-500/50";
    } else if (isWarning) {
      borderColor = "border-amber-400";
      bgColor = "bg-amber-400/15";
      tagBg = "bg-amber-500 text-slate-900";
      pulseRing = "ring-amber-400/40";
    }

    return (
      <div
        key={box.id}
        style={{
          top: box.coords.top,
          left: box.coords.left,
          width: box.coords.width,
          height: box.coords.height
        }}
        className={`absolute border-2 ${borderColor} ${bgColor} rounded-sm transition-all duration-300 ring-2 ${pulseRing} pointer-events-auto cursor-pointer group shadow-lg`}
        onClick={() => {
          showToast(`Obiect AI: ${box.label} [ID: ${box.trackingId}]`);
        }}
      >
        {/* Etichetă superioară AI Tracking */}
        <div
          className={`absolute -top-7 left-0 px-2 py-0.5 rounded text-[11px] font-bold tracking-wider flex items-center gap-1.5 shadow-md whitespace-nowrap ${tagBg}`}
        >
          {isCritical && <AlertOctagon size={13} className="animate-spin" />}
          {isWarning && <AlertTriangle size={13} />}
          {isResolved && <CheckCircle2 size={13} />}
          <span>{box.label}</span>
          <span className="opacity-80 text-[9px] font-mono">[{box.trackingId}]</span>
        </div>

        {/* Colțuri stil HUD Sci-Fi */}
        <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-white opacity-80" />
        <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-white opacity-80" />
        <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-white opacity-80" />
        <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-white opacity-80" />

        {/* Tooltip la hover cu detalii detecție */}
        <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-full mb-8 left-1/2 -translate-x-1/2 w-48 p-2 rounded bg-slate-950/95 text-white text-[11px] pointer-events-none z-30 shadow-xl border border-slate-700">
          <p className="font-semibold text-slate-200">{box.label}</p>
          <p className="text-[10px] text-slate-400 mt-1">{box.details}</p>
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        backgroundColor: themeStyles.appBg,
        color: themeStyles.textColor,
        fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
      }}
      className="min-h-screen w-full flex flex-col antialiased selection:bg-indigo-500 selection:text-white"
    >
      {/* ========================================================
          1. HEADER (BARA DE SUS)
          ======================================================== */}
      <header
        style={{
          backgroundColor: themeStyles.headerBg,
          borderColor: themeStyles.panelBorder
        }}
        className="h-16 px-4 md:px-6 flex items-center justify-between border-b shadow-sm z-20 sticky top-0"
      >
        {/* Titlu & Logo */}
        <div className="flex items-center gap-3">
          <div
            style={{ backgroundColor: themeStyles.accentColor }}
            className={`w-10 h-10 rounded-lg flex items-center justify-center shadow-md ${
              isDarkMode ? "text-white" : "text-slate-950"
            }`}
          >
            <Shield size={22} className="animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-black text-lg md:text-xl tracking-tight leading-none uppercase">
                Airport AI Command Center
              </h1>
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-600/20 text-red-400 border border-red-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                LIVE OPS
              </span>
            </div>
            <p
              style={{ color: themeStyles.textMuted }}
              className="text-xs font-mono font-medium hidden md:block"
            >
              Surveillance Vision Neural Engine v4.2 • Runway, Ramp & Terminal Protection
            </p>
          </div>
        </div>

        {/* Bara de căutare funcțională (Filtrare Incidente în timp real) */}
        <div className="flex-1 max-w-md mx-4 hidden sm:block">
          <div className="relative">
            <Search
              size={17}
              style={{ color: themeStyles.textMuted }}
              className="absolute left-3 top-1/2 -translate-y-1/2"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Caută incidente, camere, fumat, căști, bagaj, FOD..."
              style={{
                backgroundColor: themeStyles.inputBg,
                color: themeStyles.textColor,
                borderColor: themeStyles.panelBorder
              }}
              className="w-full pl-9 pr-9 py-2 text-xs md:text-sm rounded-lg border focus:outline-none focus:ring-2 focus:ring-indigo-400 shadow-inner transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 opacity-60 hover:opacity-100"
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>

        {/* Controale Dreapta: Toggle Teme, Capturi, Profil */}
        <div className="flex items-center gap-2 md:gap-3">
          {/* Buton Galerie Capturi Automate */}
          <button
            onClick={() => setShowSnapshotModal(true)}
            style={{
              backgroundColor: themeStyles.cardBg,
              borderColor: themeStyles.panelBorder
            }}
            className="px-2.5 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 shadow-sm"
            title="Vezi capturile automate generate la detecție de erori"
          >
            <Camera size={16} />
            <span className="hidden lg:inline">Capturi AI</span>
            <span
              style={{ backgroundColor: themeStyles.accentColor }}
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                isDarkMode ? "text-white" : "text-slate-950"
              }`}
            >
              {capturedScreenshots.length}
            </span>
          </button>

          {/* Toggle DARK / LIGHT MODE */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            style={{
              backgroundColor: themeStyles.cardBg,
              borderColor: themeStyles.panelBorder
            }}
            className="p-2 rounded-lg border hover:scale-105 transition-transform shadow-sm flex items-center gap-1.5 text-xs font-bold"
            title={isDarkMode ? "Comută la Light Mode" : "Comută la Dark Mode"}
          >
            {isDarkMode ? (
              <>
                <Sun size={17} className="text-amber-300" />
                <span className="hidden md:inline text-xs">Light</span>
              </>
            ) : (
              <>
                <Moon size={17} className="text-indigo-800" />
                <span className="hidden md:inline text-xs">Dark</span>
              </>
            )}
          </button>

          {/* Profil Utilizator */}
          <div
            style={{
              backgroundColor: themeStyles.cardBg,
              borderColor: themeStyles.panelBorder
            }}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border shadow-sm"
          >
            <div className="relative">
              <div
                style={{ backgroundColor: themeStyles.accentColor }}
                className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                  isDarkMode ? "text-white" : "text-slate-950"
                }`}
              >
                RO
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-slate-900" />
            </div>
            <div className="hidden xl:block text-left text-xs leading-tight">
              <p className="font-bold">Ofițer Securitate</p>
              <p style={{ color: themeStyles.textMuted }} className="text-[10px]">
                Turn Control & Sol
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* ========================================================
          ZONA CENTRALĂ (LAYOUT PRINCIPAL)
          ======================================================== */}
      <div className="flex-1 flex overflow-hidden">
        {/* ========================================================
            A. SIDEBAR STÂNGA (NAVIGARE & VIZUALIZĂRI DEDICATE)
            ======================================================== */}
        <aside
          style={{
            backgroundColor: themeStyles.panelBg,
            borderColor: themeStyles.panelBorder,
            width: isSidebarCollapsed ? "4.5rem" : "15rem"
          }}
          className="flex flex-col justify-between border-r transition-all duration-300 z-10 select-none shadow-md shrink-0"
        >
          {/* Elementele Meniului */}
          <div className="py-4 px-2 space-y-1.5">
            <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider opacity-60">
              {!isSidebarCollapsed ? "Sistem Supraveghere" : "Meniu"}
            </div>

            {/* Dashboard General (4 Zone) */}
            <button
              onClick={() => setCurrentView("dashboard")}
              style={{
                backgroundColor:
                  currentView === "dashboard" ? themeStyles.accentColor : "transparent",
                color:
                  currentView === "dashboard" && !isDarkMode
                    ? "#0F172A"
                    : themeStyles.textColor
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all hover:bg-white/10 group"
              title="Dashboard Principal"
            >
              <LayoutDashboard size={19} className="shrink-0" />
              {!isSidebarCollapsed && (
                <div className="text-left flex-1">
                  <span>Dashboard</span>
                  <p className="text-[10px] opacity-75 font-normal">Command Deck 4 Zone</p>
                </div>
              )}
            </button>

            {/* Pagina Dedicată 1: Feed Full-Screen */}
            <button
              onClick={() => setCurrentView("feed-fullscreen")}
              style={{
                backgroundColor:
                  currentView === "feed-fullscreen" ? themeStyles.accentColor : "transparent",
                color:
                  currentView === "feed-fullscreen" && !isDarkMode
                    ? "#0F172A"
                    : themeStyles.textColor
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all hover:bg-white/10 group"
              title="Feed Dedicat Full-Screen"
            >
              <Maximize2 size={19} className="shrink-0" />
              {!isSidebarCollapsed && (
                <div className="text-left flex-1">
                  <span>Feed Full-Screen</span>
                  <p className="text-[10px] opacity-75 font-normal">Perete Video Imersiv</p>
                </div>
              )}
            </button>

            {/* Pagina Dedicată 2: Split View (Feed Sus, Probleme Jos) */}
            <button
              onClick={() => setCurrentView("feed-split")}
              style={{
                backgroundColor:
                  currentView === "feed-split" ? themeStyles.accentColor : "transparent",
                color:
                  currentView === "feed-split" && !isDarkMode
                    ? "#0F172A"
                    : themeStyles.textColor
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all hover:bg-white/10 group"
              title="Feed Parțial & Probleme"
            >
              <SplitSquareVertical size={19} className="shrink-0" />
              {!isSidebarCollapsed && (
                <div className="text-left flex-1">
                  <span>Split View</span>
                  <p className="text-[10px] opacity-75 font-normal">Feed sus, Probleme jos</p>
                </div>
              )}
            </button>

            {/* Analytics & Metrici Siguranță */}
            <button
              onClick={() => setCurrentView("analytics")}
              style={{
                backgroundColor:
                  currentView === "analytics" ? themeStyles.accentColor : "transparent",
                color:
                  currentView === "analytics" && !isDarkMode
                    ? "#0F172A"
                    : themeStyles.textColor
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all hover:bg-white/10 group"
              title="Statistici & Risc"
            >
              <BarChart3 size={19} className="shrink-0" />
              {!isSidebarCollapsed && (
                <div className="text-left flex-1">
                  <span>Analytics AI</span>
                  <p className="text-[10px] opacity-75 font-normal">Metrici ICAO & EASA</p>
                </div>
              )}
            </button>

            {/* Setări Sistem & Detecție */}
            <button
              onClick={() => setCurrentView("settings")}
              style={{
                backgroundColor:
                  currentView === "settings" ? themeStyles.accentColor : "transparent",
                color:
                  currentView === "settings" && !isDarkMode
                    ? "#0F172A"
                    : themeStyles.textColor
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all hover:bg-white/10 group"
              title="Setări Algoritmi AI"
            >
              <Settings size={19} className="shrink-0" />
              {!isSidebarCollapsed && (
                <div className="text-left flex-1">
                  <span>Setări AI</span>
                  <p className="text-[10px] opacity-75 font-normal">Praguri & Sensibilitate</p>
                </div>
              )}
            </button>
          </div>

          {/* Partea de Jos a Sidebar-ului: Sumar Sănătate & Buton Colapsare */}
          <div
            style={{ borderColor: themeStyles.panelBorder }}
            className="p-3 border-t space-y-3"
          >
            {/* Status Sănătate Sistem */}
            {!isSidebarCollapsed && (
              <div
                style={{ backgroundColor: themeStyles.cardBg }}
                className="p-2.5 rounded-lg text-[11px] space-y-1.5"
              >
                <div className="flex items-center justify-between font-bold">
                  <span className="flex items-center gap-1.5">
                    <Cpu size={14} className="text-indigo-400" />
                    GPU Vision Node
                  </span>
                  <span className="text-emerald-400 font-mono">98.4%</span>
                </div>
                <div className="w-full bg-black/20 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full w-[98%]" />
                </div>
                <p style={{ color: themeStyles.textMuted }} className="text-[10px]">
                  6/8 Camere Online • Latency 42ms
                </p>
              </div>
            )}

            {/* BUTONUL COLLAPSIBLE (Restrânge / Extinde cu tranziție fluidă) */}
            <button
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              style={{
                backgroundColor: themeStyles.cardBg,
                borderColor: themeStyles.panelBorder
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border hover:opacity-80 transition-all font-semibold text-xs shadow-sm"
              title={isSidebarCollapsed ? "Extinde Bara Laterală" : "Restrânge Bara Laterală"}
            >
              {isSidebarCollapsed ? (
                <ChevronRight size={18} />
              ) : (
                <>
                  <ChevronLeft size={18} />
                  <span>Restrânge Meniul</span>
                </>
              )}
            </button>
          </div>
        </aside>

        {/* ========================================================
            ZONĂ CONȚINUT DINAMIC (DASHBOARD vs. PAGINI DEDICATE)
            ======================================================== */}
        {currentView === "feed-fullscreen" ? (
          // ==================== VIZUALIZARE DEDICATĂ: FULL-SCREEN FEED ====================
          <div className="flex-1 flex flex-col p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded bg-red-600 text-white font-bold text-xs uppercase flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                  PERETE VIDEO IMERSIV (FULL-SCREEN STREAM)
                </span>
                <span className="font-mono text-sm font-bold">
                  {activeCamera.id} • {activeCamera.name}
                </span>
              </div>
              <button
                onClick={() => setCurrentView("dashboard")}
                style={{ backgroundColor: themeStyles.accentColor }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 ${
                  isDarkMode ? "text-white" : "text-slate-950"
                }`}
              >
                <Minimize2 size={15} />
                Ieșire din Full-Screen
              </button>
            </div>

            {/* Ecran Video Mare Full Height */}
            <div className="flex-1 relative rounded-xl overflow-hidden shadow-2xl bg-black border border-slate-700 min-h-[500px]">
              {activeCamera.status === "offline" ? (
                <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-zinc-950 text-white">
                  <WifiOff size={64} className="text-red-500 animate-bounce mb-4" />
                  <h2 className="text-3xl font-black text-red-500 tracking-widest font-mono">
                    SEMNAL PIERDUT
                  </h2>
                  <p className="text-sm text-slate-400 mt-2 font-mono">
                    RTSP STREAM OFFLINE • CAMERA: {activeCamera.id}
                  </p>
                </div>
              ) : (
                <>
                  <div
                    className={`w-full h-full bg-gradient-to-br ${activeCamera.previewBg} flex items-center justify-center relative overflow-hidden`}
                  >
                    {/* Grilă tactică video de fundal */}
                    <div
                      className="absolute inset-0 opacity-15"
                      style={{
                        backgroundImage:
                          "linear-gradient(rgba(255,255,255,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.15) 1px, transparent 1px)",
                        backgroundSize: "40px 40px"
                      }}
                    />

                    {/* Simulare scenă video SVG în funcție de tip */}
                    <div className="relative text-center select-none opacity-40">
                      <Video size={100} className="mx-auto text-slate-400 mb-3" />
                      <p className="font-mono text-lg font-bold tracking-widest text-white">
                        {activeCamera.name.toUpperCase()}
                      </p>
                      <p className="text-xs text-slate-300 font-mono">
                        AI REAL-TIME VISION INFERENCE • 60 FPS • DETECTING ANOMALIES
                      </p>
                    </div>

                    {/* Bounding Boxes suprapuse */}
                    {activeCamera.boxes.map(renderBoundingBox)}
                  </div>

                  {/* HUD Overlay */}
                  <div className="absolute top-4 left-4 flex items-center gap-3 bg-black/75 px-3 py-1.5 rounded-lg border border-white/20 text-white text-xs font-mono">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                    <span>REC: LIVE</span>
                    <span>|</span>
                    <span>{activeCamera.resolution}</span>
                    <span>|</span>
                    <span>FPS: {activeCamera.fps}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        ) : currentView === "feed-split" ? (
          // ==================== VIZUALIZARE DEDICATĂ: SPLIT VIEW (SUS FEED, JOS PROBLEME) ====================
          <div className="flex-1 flex flex-col p-4 overflow-y-auto space-y-4">
            {/* Secțiunea Superioară: Feed-ul Camerei (50%) */}
            <div
              style={{
                backgroundColor: themeStyles.panelBg,
                borderColor: themeStyles.panelBorder
              }}
              className="h-[48%] rounded-xl border p-3 flex flex-col shadow-lg"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold font-mono uppercase tracking-wider flex items-center gap-2">
                  <Video size={16} className="text-indigo-400" />
                  Feed Supraveghere Split: {activeCamera.id} - {activeCamera.name}
                </span>
                <span className="text-[11px] font-mono opacity-75">
                  Rezoluție: {activeCamera.resolution}
                </span>
              </div>
              <div className="flex-1 relative rounded-lg overflow-hidden bg-black border border-slate-700">
                {activeCamera.status === "offline" ? (
                  <div className="w-full h-full flex items-center justify-center text-red-500 font-mono font-bold text-xl">
                    SEMNAL PIERDUT (CAMERA OFFLINE)
                  </div>
                ) : (
                  <div
                    className={`w-full h-full bg-gradient-to-br ${activeCamera.previewBg} relative flex items-center justify-center`}
                  >
                    <p className="text-white/40 font-mono text-sm uppercase">
                      Feed Live Activ: {activeCamera.name}
                    </p>
                    {activeCamera.boxes.map(renderBoundingBox)}
                  </div>
                )}
              </div>
            </div>

            {/* Secțiunea Inferioară: Probleme și Telemetrie AI în timp real (50%) */}
            <div
              style={{
                backgroundColor: themeStyles.panelBg,
                borderColor: themeStyles.panelBorder
              }}
              className="flex-1 rounded-xl border p-4 shadow-lg overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
                  <AlertOctagon size={18} className="text-red-400" />
                  Probleme & Incidente Identificate pe Sector (Split View)
                </h3>
                <span className="text-xs font-mono opacity-80">
                  {filteredIncidents.length} Alerte Înregistrate
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredIncidents.map((inc) => (
                  <div
                    key={inc.id}
                    style={{
                      backgroundColor: themeStyles.cardBg,
                      borderColor: themeStyles.panelBorder
                    }}
                    className="p-3 rounded-lg border shadow-sm space-y-2 hover:border-indigo-400 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs">{inc.title}</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          inc.severity === "critical"
                            ? "bg-red-600 text-white"
                            : inc.severity === "warning"
                            ? "bg-amber-500 text-slate-900"
                            : "bg-emerald-600 text-white"
                        }`}
                      >
                        {inc.severity.toUpperCase()}
                      </span>
                    </div>
                    <p style={{ color: themeStyles.textMuted }} className="text-[11px] line-clamp-2">
                      {inc.reasoning}
                    </p>
                    <div className="flex items-center justify-between pt-1 border-t border-white/10 text-[10px] font-mono">
                      <span>{inc.detectedAt}</span>
                      <button
                        onClick={(e) => handleAcknowledge(inc.id, e)}
                        className="text-emerald-400 hover:underline font-bold"
                      >
                        Rezolvă
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : currentView === "analytics" ? (
          // ==================== VIZUALIZARE DEDICATĂ: ANALYTICS AI ====================
          <div className="flex-1 p-6 overflow-y-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black uppercase">Statistici & Metrici Securitate AI</h2>
                <p style={{ color: themeStyles.textMuted }} className="text-xs">
                  Date agregate din ultimele 24 de ore conforme protocoalelor ICAO Anexa 14
                </p>
              </div>
              <button
                onClick={handleResetData}
                style={{ backgroundColor: themeStyles.cardBg, borderColor: themeStyles.panelBorder }}
                className="px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5"
              >
                <RefreshCw size={14} /> Reîmprospătează Metrici
              </button>
            </div>

            {/* Carduri KPI */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
                className="p-4 rounded-xl border shadow-md space-y-2"
              >
                <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
                  Timp Mediu Reacție (MTTR)
                </p>
                <p className="text-2xl font-black font-mono text-emerald-400">42 sec</p>
                <p className="text-[10px] text-emerald-400">↓ 18% mai rapid decât ieri</p>
              </div>
              <div
                style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
                className="p-4 rounded-xl border shadow-md space-y-2"
              >
                <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
                  Acuratețe Detecție AI
                </p>
                <p className="text-2xl font-black font-mono text-indigo-400">97.8%</p>
                <p className="text-[10px] text-slate-400">Fals-pozitive sub 2.2%</p>
              </div>
              <div
                style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
                className="p-4 rounded-xl border shadow-md space-y-2"
              >
                <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
                  FOD Piste Neutralizate
                </p>
                <p className="text-2xl font-black font-mono text-amber-400">14 Obiecte</p>
                <p className="text-[10px] text-amber-400">0 incidente critice de zbor</p>
              </div>
              <div
                style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
                className="p-4 rounded-xl border shadow-md space-y-2"
              >
                <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
                  Rată Conformitate EIP Sol
                </p>
                <p className="text-2xl font-black font-mono text-purple-400">93.2%</p>
                <p className="text-[10px] text-slate-400">Protecție fonică & veste</p>
              </div>
            </div>

            {/* Listă detecții de securitate antrenate în sistem */}
            <div
              style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
              className="p-5 rounded-xl border shadow-md space-y-4"
            >
              <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck size={18} className="text-emerald-400" />
                Matricea de Detecție AI Antrenată (Computer Vision Airport Safety)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                {[
                  { name: "Fumat lângă Aeronave / Cisterne", status: "Activ", score: "99% Conf" },
                  { name: "Personal Fără Căști Antifonice", status: "Activ", score: "94% Conf" },
                  { name: "FOD (Obiecte Străine) pe Runway", status: "Activ", score: "96% Conf" },
                  { name: "Bagaj Abandonat & Loitering", status: "Activ", score: "98% Conf" },
                  { name: "Manipulare Brutală / Aruncare Bagaj", status: "Activ", score: "89% Conf" },
                  { name: "Distanță Minimă Față de Turbină", status: "Activ", score: "95% Conf" },
                  { name: "Aglomerație Masivă & Panic Flow", status: "Activ", score: "91% Conf" },
                  { name: "Detecție Păsări & Animale Pistă", status: "Activ", score: "93% Conf" },
                  { name: "Intruziune Gard Perimetral PIDS", status: "Activ", score: "97% Conf" }
                ].map((item, idx) => (
                  <div
                    key={idx}
                    style={{ backgroundColor: themeStyles.cardBg }}
                    className="p-3 rounded-lg flex items-center justify-between border border-white/5"
                  >
                    <div>
                      <p className="font-bold">{item.name}</p>
                      <p className="text-[10px] text-emerald-400 font-mono">Modul: {item.status}</p>
                    </div>
                    <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-white/10">
                      {item.score}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : currentView === "settings" ? (
          // ==================== VIZUALIZARE DEDICATĂ: SETĂRI ====================
          <div className="flex-1 p-6 overflow-y-auto space-y-6 max-w-4xl">
            <h2 className="text-xl font-black uppercase">Setări AI & Configurare Camere</h2>
            <div
              style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
              className="p-5 rounded-xl border space-y-4 shadow-md"
            >
              <h3 className="font-bold text-sm uppercase">Praguri de Sensibilitate Modele YOLO / Vision</h3>
              <div className="space-y-4 text-xs">
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Prag Alertă Pericol Iminent (Chenar Roșu)</span>
                    <span className="font-mono font-bold">85%</span>
                  </div>
                  <input type="range" min="50" max="99" defaultValue="85" className="w-full" />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Timp minim abandon bagaj înainte de alertă</span>
                    <span className="font-mono font-bold">5 minute</span>
                  </div>
                  <input type="range" min="1" max="15" defaultValue="5" className="w-full" />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Salvare automată captură foto & 30s buffer video</span>
                    <span className="text-emerald-400 font-bold">ACTIVAT</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // ========================================================
          // C. & D. DASHBOARD PRINCIPAL (ZONA CENTRALĂ + SIDEBAR DREAPTA)
          // ========================================================
          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
            {/* ========================================================
                C. ZONA CENTRALĂ (VIDEO FEED & MINIATURI CAMERE)
                ======================================================== */}
            <main className="flex-1 flex flex-col p-3 md:p-4 overflow-y-auto min-w-0 space-y-3">
              {/* ZONA SUPERIOARĂ: PLAYER-UL VIDEO PRINCIPAL */}
              <div
                style={{
                  backgroundColor: themeStyles.panelBg,
                  borderColor: themeStyles.panelBorder
                }}
                className="rounded-xl border p-3 flex flex-col shadow-lg flex-1 min-h-[360px] md:min-h-[440px]"
              >
                {/* Header-ul Player-ului Video */}
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-3 h-3 rounded-full ${
                        activeCamera.status === "online"
                          ? "bg-emerald-500 animate-pulse"
                          : "bg-red-500"
                      }`}
                    />
                    <span className="font-bold text-sm tracking-wide">
                      {activeCamera.id} - {activeCamera.name}
                    </span>
                    <span
                      style={{ backgroundColor: themeStyles.cardBg }}
                      className="text-[10px] font-mono px-2 py-0.5 rounded border border-white/10 hidden sm:inline"
                    >
                      {activeCamera.zone}
                    </span>
                  </div>

                  {/* Butoane Acțiuni Player */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleManualCapture}
                      style={{ backgroundColor: themeStyles.accentColor }}
                      className={`px-2.5 py-1 rounded text-xs font-bold flex items-center gap-1 shadow hover:scale-105 transition-transform ${
                        isDarkMode ? "text-white" : "text-slate-950"
                      }`}
                      title="Realizează captură manuală instantanee"
                    >
                      <Camera size={14} />
                      <span className="hidden md:inline">Captură</span>
                    </button>

                    <button
                      onClick={() => setCurrentView("feed-fullscreen")}
                      style={{ backgroundColor: themeStyles.cardBg }}
                      className="p-1.5 rounded hover:bg-white/10 border border-white/10 text-xs"
                      title="Deschide în modul Full-Screen"
                    >
                      <Maximize2 size={15} />
                    </button>
                  </div>
                </div>

                {/* ECRANUL VIDEO PROPRIU-ZIS CU BOUNDING BOXES SAU EROARE SEMNAL PIERDUT */}
                <div className="flex-1 relative rounded-lg overflow-hidden bg-black border border-slate-700 flex items-center justify-center select-none shadow-inner">
                  {/* CAZUL 1: CAMERA ESTE OFFLINE -> MESAJ "SEMNAL PIERDUT" */}
                  {activeCamera.status === "offline" ? (
                    <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-zinc-950 text-white relative">
                      {/* Efect static scanlines */}
                      <div
                        className="absolute inset-0 opacity-20 pointer-events-none"
                        style={{
                          backgroundImage:
                            "repeating-linear-gradient(0deg, rgba(255,255,255,0.05), rgba(255,255,255,0.05) 1px, transparent 1px, transparent 2px)"
                        }}
                      />

                      <div className="w-16 h-16 rounded-full bg-red-950/80 border-2 border-red-500/50 flex items-center justify-center mb-3 animate-pulse">
                        <WifiOff size={32} className="text-red-500" />
                      </div>

                      <h2 className="text-2xl md:text-3xl font-black text-red-500 tracking-widest font-mono">
                        SEMNAL PIERDUT
                      </h2>
                      <p className="text-xs text-slate-400 font-mono mt-1 max-w-sm">
                        Fluxul video RTSP/WebRTC nu răspunde. Conexiunea cu camera{" "}
                        <span className="text-white font-bold">{activeCamera.id}</span> a fost
                        întreruptă sau nodul de rețea este inactiv.
                      </p>

                      <div className="mt-4 flex items-center gap-2">
                        <button
                          onClick={() => {
                            showToast(`Reîncercare conexiune pentru ${activeCamera.id}...`);
                          }}
                          className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-700 text-white font-mono text-xs font-bold flex items-center gap-1.5"
                        >
                          <RefreshCw size={13} /> Reîncearcă Conexiunea
                        </button>
                        <button
                          onClick={() => setSelectedCameraId("CAM-04")}
                          className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs font-bold"
                        >
                          Comută pe CAM-04 (Online)
                        </button>
                      </div>
                    </div>
                  ) : (
                    // CAZUL 2: CAMERA ESTE ONLINE -> SIMULARE FEED VIDEO + BOUNDING BOXES AI
                    <div
                      className={`w-full h-full bg-gradient-to-br ${activeCamera.previewBg} relative overflow-hidden flex items-center justify-center`}
                    >
                      {/* Grilă de fundal */}
                      <div
                        className="absolute inset-0 opacity-15 pointer-events-none"
                        style={{
                          backgroundImage:
                            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
                          backgroundSize: "32px 32px"
                        }}
                      />

                      {/* Icon & Detalii scenă */}
                      <div className="relative text-center opacity-40 select-none">
                        <Plane size={80} className="mx-auto text-slate-400 mb-2" />
                        <p className="font-mono font-black text-white text-base md:text-lg tracking-wider">
                          {activeCamera.name.toUpperCase()}
                        </p>
                        <p className="font-mono text-xs text-slate-300">
                          AI COMPUTER VISION ACTIVE • LIVE TRACKING 30 FPS
                        </p>
                      </div>

                      {/* BOUNDING BOXES SUPRAPUSE (PERICOLE IMINENTE, AVERTISMENTE, REMEDIATE) */}
                      {activeCamera.boxes.map(renderBoundingBox)}

                      {/* HUD Video Superior */}
                      <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/75 backdrop-blur-sm px-2.5 py-1 rounded text-[11px] font-mono text-white border border-white/10 shadow">
                        <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                        <span className="font-bold">REC</span>
                        <span>|</span>
                        <span>{activeCamera.resolution}</span>
                        <span>|</span>
                        <span>{activeCamera.fps} FPS</span>
                      </div>

                      {/* HUD Video Inferior: Timestamp live */}
                      <div className="absolute bottom-3 right-3 bg-black/75 backdrop-blur-sm px-2.5 py-1 rounded text-[11px] font-mono text-white border border-white/10 shadow flex items-center gap-2">
                        <Clock size={12} className="text-indigo-400" />
                        <span>LIVE: {new Date().toLocaleTimeString("ro-RO")}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* ZONA INFERIOARĂ: MINIATURI (THUMBNAILS) PENTRU REȚEAUA DE CAMERE CCTV */}
              <div
                style={{
                  backgroundColor: themeStyles.panelBg,
                  borderColor: themeStyles.panelBorder
                }}
                className="rounded-xl border p-3 shadow-md"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Camera size={16} className="text-indigo-400" />
                    <span className="font-bold text-xs md:text-sm uppercase tracking-wide">
                      Rețeaua de Camere CCTV ({cameras.length})
                    </span>
                  </div>
                  <span style={{ color: themeStyles.textMuted }} className="text-[11px]">
                    Click pe o miniatură pentru comutare feed
                  </span>
                </div>

                {/* Lista orizontală scrollabilă de camere */}
                <div className="flex gap-2.5 overflow-x-auto pb-1 pt-1 scrollbar-thin">
                  {cameras.map((cam) => {
                    const isSelected = cam.id === activeCamera.id;
                    const isCamOffline = cam.status === "offline";

                    return (
                      <button
                        key={cam.id}
                        onClick={() => setSelectedCameraId(cam.id)}
                        style={{
                          borderColor: isSelected
                            ? themeStyles.accentColor
                            : themeStyles.panelBorder,
                          backgroundColor: isSelected
                            ? themeStyles.cardBg
                            : "rgba(0,0,0,0.15)"
                        }}
                        className={`min-w-[150px] md:min-w-[170px] p-2 rounded-lg border-2 text-left transition-all relative shrink-0 hover:scale-[1.02] shadow-sm ${
                          isSelected ? "ring-2 ring-indigo-400/50" : ""
                        }`}
                      >
                        {/* Mini-ecran simulare video */}
                        <div
                          className={`h-16 rounded overflow-hidden relative flex items-center justify-center bg-gradient-to-br ${cam.previewBg} mb-1.5 border border-white/10`}
                        >
                          {isCamOffline ? (
                            <div className="text-center">
                              <WifiOff size={16} className="text-red-500 mx-auto" />
                              <span className="text-[9px] font-mono text-red-400 font-bold">
                                OFFLINE
                              </span>
                            </div>
                          ) : (
                            <div className="text-center opacity-60">
                              <Video size={18} className="mx-auto text-slate-300" />
                              <span className="text-[9px] font-mono text-slate-200">
                                {cam.fps} FPS
                              </span>
                            </div>
                          )}

                          {/* Badge număr alerte */}
                          {cam.incidentsCount > 0 && !isCamOffline && (
                            <span className="absolute top-1 right-1 bg-red-600 text-white text-[9px] font-bold px-1.5 rounded-full">
                              {cam.incidentsCount}
                            </span>
                          )}

                          {/* Indicator status online/offline */}
                          <span
                            className={`absolute top-1 left-1 w-2 h-2 rounded-full ${
                              isCamOffline ? "bg-red-500" : "bg-emerald-400 animate-pulse"
                            }`}
                          />
                        </div>

                        {/* Titlu & Id Cameră */}
                        <p className="font-bold text-xs truncate leading-tight">{cam.name}</p>
                        <p
                          style={{ color: themeStyles.textMuted }}
                          className="text-[10px] font-mono truncate"
                        >
                          {cam.id} • {cam.status.toUpperCase()}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>
            </main>

            {/* ========================================================
                D. SIDEBAR DREAPTA (ALERTE INCIDENTE & EXPLAINABLE AI)
                ======================================================== */}
            <aside
              style={{
                backgroundColor: themeStyles.panelBg,
                borderColor: themeStyles.panelBorder
              }}
              className="w-full lg:w-96 border-t lg:border-t-0 lg:border-l p-3 md:p-4 flex flex-col shrink-0 overflow-hidden shadow-lg"
            >
              {/* Header-ul listei de alerte */}
              <div className="flex items-center justify-between pb-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={20} className="text-red-400 animate-pulse" />
                  <div>
                    <h2 className="font-bold text-sm uppercase tracking-wider">
                      Alerte Incidente AI
                    </h2>
                    <p style={{ color: themeStyles.textMuted }} className="text-[10px]">
                      Explainable AI (XAI) & Live Detection
                    </p>
                  </div>
                </div>

                <span
                  style={{ backgroundColor: themeStyles.accentColor }}
                  className={`text-xs font-black px-2 py-0.5 rounded-full ${
                    isDarkMode ? "text-white" : "text-slate-950"
                  }`}
                >
                  {filteredIncidents.length} Active
                </span>
              </div>

              {/* Filtre rapide pe severitate */}
              <div className="flex gap-1.5 my-2.5">
                {[
                  { key: "all", label: "Toate" },
                  { key: "critical", label: "Critice (Roșu)" },
                  { key: "warning", label: "Avertismente" },
                  { key: "resolved", label: "Remediate" }
                ].map((f) => (
                  <button
                    key={f.key}
                    onClick={() => setSeverityFilter(f.key)}
                    style={{
                      backgroundColor:
                        severityFilter === f.key
                          ? themeStyles.accentColor
                          : themeStyles.cardBg,
                      color:
                        severityFilter === f.key && !isDarkMode
                          ? "#0F172A"
                          : themeStyles.textColor
                    }}
                    className="flex-1 py-1 text-[10px] font-bold rounded transition-colors"
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* LISTA VERTICALĂ DE CARDURI CU INCIDENTE */}
              <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
                {filteredIncidents.length === 0 ? (
                  <div
                    style={{ backgroundColor: themeStyles.cardBg }}
                    className="p-6 rounded-xl text-center space-y-3 mt-4"
                  >
                    <CheckCircle2 size={36} className="mx-auto text-emerald-400" />
                    <p className="font-bold text-sm">Niciun incident activ!</p>
                    <p style={{ color: themeStyles.textMuted }} className="text-xs">
                      {searchQuery
                        ? "Niciun rezultat nu corespunde căutării."
                        : "Toate alertele au fost rezolvate cu succes."}
                    </p>
                    <button
                      onClick={handleResetData}
                      style={{ backgroundColor: themeStyles.accentColor }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold ${
                        isDarkMode ? "text-white" : "text-slate-950"
                      }`}
                    >
                      Reîncarcă Incidentele Demo
                    </button>
                  </div>
                ) : (
                  filteredIncidents.map((incident) => {
                    const isCritical = incident.severity === "critical";
                    const isWarning = incident.severity === "warning";
                    const isResolved = incident.severity === "resolved";

                    return (
                      <div
                        key={incident.id}
                        style={{
                          backgroundColor: themeStyles.cardBg,
                          borderColor: isCritical
                            ? "rgba(239, 68, 68, 0.4)"
                            : isWarning
                            ? "rgba(245, 158, 11, 0.4)"
                            : "rgba(16, 185, 129, 0.4)"
                        }}
                        className="rounded-xl border p-3 shadow-sm space-y-2.5 transition-all hover:scale-[1.01] hover:shadow-md relative overflow-hidden"
                      >
                        {/* Linie superioară de severitate */}
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-1.5">
                              {isCritical && (
                                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                              )}
                              <span
                                className={`text-[10px] font-black uppercase px-2 py-0.5 rounded tracking-wider ${
                                  isCritical
                                    ? "bg-red-600 text-white"
                                    : isWarning
                                    ? "bg-amber-500 text-slate-900"
                                    : "bg-emerald-600 text-white"
                                }`}
                              >
                                {isCritical
                                  ? "PERICOL IMINENT"
                                  : isWarning
                                  ? "AVERTISMENT"
                                  : "REMEDIAT / CONFORM"}
                              </span>
                              <span className="text-[10px] font-mono opacity-70">
                                {incident.id}
                              </span>
                            </div>
                            <h3 className="font-bold text-xs md:text-sm mt-1 leading-tight">
                              {incident.title}
                            </h3>
                          </div>

                          {/* Buton să comute camera la camera acestui incident */}
                          <button
                            onClick={() => setSelectedCameraId(incident.cameraId)}
                            style={{
                              backgroundColor:
                                activeCamera.id === incident.cameraId
                                  ? themeStyles.accentColor
                                  : "transparent"
                            }}
                            className="p-1 rounded text-[10px] font-mono flex items-center gap-1 border border-white/10 hover:bg-white/10"
                            title={`Comută vizualizarea pe ${incident.cameraId}`}
                          >
                            <Eye size={12} />
                            <span>{incident.cameraId}</span>
                          </button>
                        </div>

                        {/* Detalii Locație & Timp */}
                        <div
                          style={{ color: themeStyles.textMuted }}
                          className="flex items-center justify-between text-[10px] font-mono"
                        >
                          <span>{incident.cameraName}</span>
                          <span>{incident.detectedAt}</span>
                        </div>

                        {/* ========================================================
                            CONFIDENCE SCORE CU GRADIENT ROȘU - PORTOCALIU - VERDE
                            (Cerință specifică: tranzitie de la situatii critice la situatii ok)
                            ======================================================== */}
                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="font-semibold flex items-center gap-1">
                              <Sparkles size={11} className="text-amber-400" />
                              Confidence Score:
                            </span>
                            <span className="font-mono font-black text-xs">
                              {incident.confidence}%
                            </span>
                          </div>

                          {/* Bara cu Gradient Multi-Stop Roșu -> Portocaliu -> Verde */}
                          <div className="w-full h-2 rounded-full overflow-hidden bg-black/30 relative">
                            {/* Fundal gradient complet */}
                            <div className="absolute inset-0 bg-gradient-to-r from-red-600 via-amber-400 to-emerald-500 opacity-30" />
                            {/* Bară umplută proporțional */}
                            <div
                              style={{ width: `${incident.confidence}%` }}
                              className="h-full bg-gradient-to-r from-red-600 via-amber-400 to-emerald-500 transition-all duration-500 rounded-full"
                            />
                          </div>
                          <div className="flex justify-between text-[8px] font-mono opacity-60">
                            <span>0% Critic (Roșu)</span>
                            <span>50% Avertisment</span>
                            <span>100% Ok / Sigur</span>
                          </div>
                        </div>

                        {/* ========================================================
                            EXPLAINABLE AI (XAI) REASONING
                            ======================================================== */}
                        <div
                          style={{
                            backgroundColor: isDarkMode
                              ? "rgba(0,0,0,0.3)"
                              : "rgba(255,255,255,0.7)"
                          }}
                          className="p-2.5 rounded-lg border border-white/5 space-y-1 text-xs"
                        >
                          <div className="flex items-center gap-1 text-[11px] font-bold text-indigo-400">
                            <Info size={12} />
                            <span>AI Reasoning & Cauză:</span>
                          </div>
                          <p style={{ color: themeStyles.textMuted }} className="text-[11px] leading-relaxed">
                            {incident.reasoning}
                          </p>
                          <div className="pt-1 text-[10px] text-amber-400 font-medium">
                            <span className="font-bold">Măsură sugerată:</span> {incident.actionSuggested}
                          </div>
                        </div>

                        {/* Buton ACKNOWLEDGE / MARCHEAZĂ REZOLVAT */}
                        <div className="pt-1 flex items-center justify-between gap-2">
                          <button
                            onClick={() => {
                              setActiveSnapshot({
                                id: incident.snapshotId,
                                title: incident.title,
                                camera: incident.cameraName,
                                time: incident.detectedAt,
                                reasoning: incident.reasoning
                              });
                              setShowSnapshotModal(true);
                            }}
                            className="text-[10px] font-semibold text-slate-300 hover:text-white flex items-center gap-1 underline"
                          >
                            <Camera size={12} /> Vezi Captura Auto
                          </button>

                          <button
                            onClick={(e) => handleAcknowledge(incident.id, e)}
                            style={{
                              backgroundColor: isDarkMode ? "#4034AD" : "#70ED6E",
                              color: isDarkMode ? "#FFFFFF" : "#0F172A"
                            }}
                            className="px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity shadow-sm"
                          >
                            <Check size={14} />
                            <span>Marchează Rezolvat</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </aside>
          </div>
        )}
      </div>

      {/* ========================================================
          MODAL CAPTURI AUTOMATE (AUTO-SCREENSHOT ON DETECTION)
          ======================================================== */}
      {showSnapshotModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            style={{
              backgroundColor: themeStyles.panelBg,
              borderColor: themeStyles.panelBorder,
              color: themeStyles.textColor
            }}
            className="w-full max-w-2xl rounded-2xl border p-5 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Camera size={22} className="text-indigo-400" />
                <div>
                  <h3 className="font-bold text-base uppercase">
                    Jurnal Capturi Automate AI (Evidence Archive)
                  </h3>
                  <p style={{ color: themeStyles.textMuted }} className="text-xs">
                    Imagini capturate automat la detecția fiecărei anomalii cu timestamp și hash SHA-256
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowSnapshotModal(false);
                  setActiveSnapshot(null);
                }}
                className="p-1 rounded hover:bg-white/10"
              >
                <X size={20} />
              </button>
            </div>

            {/* Vizualizare snapshot curent sau lista de capturi */}
            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Capturi Recente Salvate pe Server:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {capturedScreenshots.map((snap) => (
                  <div
                    key={snap.id}
                    style={{ backgroundColor: themeStyles.cardBg }}
                    className="p-3 rounded-xl border border-white/10 space-y-2"
                  >
                    <div className="h-28 rounded bg-gradient-to-br from-slate-900 to-indigo-950 flex flex-col items-center justify-center relative overflow-hidden border border-white/10">
                      <Camera size={30} className="text-white/40 mb-1" />
                      <span className="text-[10px] font-mono text-red-400 font-bold px-2 py-0.5 rounded bg-black/60">
                        {snap.title}
                      </span>
                      <span className="absolute bottom-1 right-2 text-[9px] font-mono text-slate-400">
                        {snap.time}
                      </span>
                    </div>
                    <div className="text-xs">
                      <p className="font-bold">{snap.title}</p>
                      <p style={{ color: themeStyles.textMuted }} className="text-[10px] font-mono">
                        {snap.camera}
                      </p>
                      <p className="text-[9px] font-mono text-slate-400 mt-1 truncate">
                        SHA-256: {snap.hash}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-white/10">
              <button
                onClick={() => {
                  setShowSnapshotModal(false);
                  setActiveSnapshot(null);
                }}
                style={{ backgroundColor: themeStyles.accentColor }}
                className={`px-4 py-2 rounded-lg text-xs font-bold ${
                  isDarkMode ? "text-white" : "text-slate-950"
                }`}
              >
                Închide Fereastra
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          TOAST DE NOTIFICARE
          ======================================================== */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-2xl border border-indigo-500/50 flex items-center gap-3 animate-fade-in font-sans text-xs md:text-sm">
          <Info size={18} className="text-indigo-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
