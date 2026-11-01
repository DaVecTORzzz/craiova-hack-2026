import React, { useEffect, useState, useRef } from 'react';
import { PenTool, Save, Trash2, Camera, Shield, Layers, Code, Plus, Move, Edit3, CheckCircle2 } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

function normalizePoint(p) {
  if (Array.isArray(p)) {
    return { x: Number(p[0] ?? 0), y: Number(p[1] ?? 0) };
  }
  return { x: Number(p?.x ?? 0), y: Number(p?.y ?? 0) };
}

function normalizePolygon(poly) {
  return (poly || []).map(normalizePoint);
}

export default function ZoneEditorView() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    cameras,
    selectedCameraId,
    setSelectedCameraId,
    activeCamera,
    zones,
    saveZone,
    captureReferenceFrame,
    showToast
  } = useSecurity();

  // Poligon curent în editare (coordonate normalizate 0-1)
  const [points, setPoints] = useState([
    { x: 0.35, y: 0.25 },
    { x: 0.75, y: 0.25 },
    { x: 0.85, y: 0.75 },
    { x: 0.35, y: 0.75 }
  ]);
  const [isPolygonClosed, setIsPolygonClosed] = useState(true);
  const [showJsonFallback, setShowJsonFallback] = useState(false);
  const [jsonInput, setJsonInput] = useState(JSON.stringify(points, null, 2));

  // Mod de interacțiune: 'drag' (mutare vârfuri) sau 'draw' (desenare de la zero)
  const [editMode, setEditMode] = useState('drag');
  const [draggingIndex, setDraggingIndex] = useState(null);

  // Parametri zonă conform Schemei oficiale backend (ZoneIO)
  const [zoneId, setZoneId] = useState('engine-left');
  const [zoneName, setZoneName] = useState('Motor stâng');
  const [ruleType, setRuleType] = useState('RESTRICTED');
  const [activeWhen, setActiveWhen] = useState('engine_on');
  const [severity, setSeverity] = useState('CRITICAL');
  const [debounceSeconds, setDebounceSeconds] = useState(1.4);
  const [notifyChannel, setNotifyChannel] = useState('slack');
  const [escalateAfterS, setEscalateAfterS] = useState(30);
  const [requiredPpe, setRequiredPpe] = useState(['hi_vis_vest', 'hard_hat']);

  // Aspect ratio cadru de referință
  const [referenceAspect, setReferenceAspect] = useState(null);
  const canvasContainerRef = useRef(null);
  const referenceFileRef = useRef(null);
  const previousCameraRef = useRef(selectedCameraId);

  // Toate zonele camerei selectate
  const cameraZones = zones.filter((z) => z.camera_id === selectedCameraId);

  // Zona activă selectată curent
  const activeZone = cameraZones.find((z) => (z.zone_id || z.id) === zoneId) || cameraZones[0];

  // Sincronizare la schimbarea camerei sau a listei de zone
  useEffect(() => {
    const camChanged = previousCameraRef.current !== selectedCameraId;
    previousCameraRef.current = selectedCameraId;

    if (cameraZones.length === 0) {
      setZoneId('zone-noua-1');
      setZoneName('Zonă Nouă');
      const defaultBox = [
        { x: 0.25, y: 0.25 },
        { x: 0.75, y: 0.25 },
        { x: 0.75, y: 0.75 },
        { x: 0.25, y: 0.75 }
      ];
      setPoints(defaultBox);
      setIsPolygonClosed(true);
      setJsonInput(JSON.stringify(defaultBox, null, 2));
      setRuleType('RESTRICTED');
      setActiveWhen('always');
      setSeverity('CRITICAL');
      setDebounceSeconds(1.0);
      setEscalateAfterS(30);
      return;
    }

    // Dacă s-a schimbat camera sau zona curentă nu mai e validă
    const targetZone = (camChanged ? null : cameraZones.find((z) => (z.zone_id || z.id) === zoneId))
      || cameraZones.find((z) => (z.zone_id || z.id) === 'engine-left')
      || cameraZones[0];

    if (targetZone) {
      loadZoneIntoForm(targetZone);
    }
  }, [selectedCameraId, zones.length]);

  const loadZoneIntoForm = (zone) => {
    const zid = zone.zone_id || zone.id;
    setZoneId(zid);
    setZoneName(zone.name || zid);
    const norm = normalizePolygon(zone.polygon);
    setPoints(norm);
    setIsPolygonClosed(norm.length >= 3);
    setJsonInput(JSON.stringify(norm, null, 2));
    setRuleType(zone.rule_type || 'RESTRICTED');
    setActiveWhen(zone.active_when || 'always');
    setSeverity(zone.severity || 'CRITICAL');
    setDebounceSeconds(zone.debounce_s ?? 1.0);
    setNotifyChannel(zone.notify_channel || 'slack');
    setEscalateAfterS(zone.escalate_after_s ?? 30);
    setRequiredPpe(zone.required_ppe || ['hi_vis_vest', 'hard_hat']);
    setEditMode('drag');
  };

  const handleCreateNewZone = () => {
    const newId = `zona-noua-${cameraZones.length + 1}`;
    setZoneId(newId);
    setZoneName(`Zonă Nouă ${cameraZones.length + 1}`);
    const defaultBox = [
      { x: 0.3, y: 0.3 },
      { x: 0.7, y: 0.3 },
      { x: 0.7, y: 0.7 },
      { x: 0.3, y: 0.7 }
    ];
    setPoints(defaultBox);
    setIsPolygonClosed(true);
    setJsonInput(JSON.stringify(defaultBox, null, 2));
    setRuleType('RESTRICTED');
    setActiveWhen('always');
    setSeverity('CRITICAL');
    setDebounceSeconds(1.0);
    setEscalateAfterS(30);
    setEditMode('drag');
    showToast(`Inițializat ${newId}. Trage punctele pe imagine și apasă Salvează.`);
  };

  // Click pe canvas pentru adăugare punct (doar în mod 'draw')
  const handleCanvasClick = (e) => {
    if (editMode !== 'draw' || isPolygonClosed) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, Number(((e.clientX - rect.left) / rect.width).toFixed(3))));
    const y = Math.max(0, Math.min(1, Number(((e.clientY - rect.top) / rect.height).toFixed(3))));
    const newPoints = [...points, { x, y }];
    setPoints(newPoints);
    setJsonInput(JSON.stringify(newPoints, null, 2));
  };

  // Dublu-click pentru închidere poligon
  const handleDoubleClick = () => {
    if (points.length >= 3) {
      setIsPolygonClosed(true);
      setEditMode('drag');
      showToast('Poligon închis. Punctele pot fi acum repoziționate prin drag & drop.');
    } else {
      showToast('Ai nevoie de cel puțin 3 puncte pentru un perimetru valid.');
    }
  };

  // Drag & drop pentru mutarea nodurilor
  const handlePointPointerDown = (idx, e) => {
    e.stopPropagation();
    setDraggingIndex(idx);
    e.currentTarget.setPointerCapture?.(e.pointerId);
  };

  const handleCanvasPointerMove = (e) => {
    if (draggingIndex === null || !canvasContainerRef.current) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, Number(((e.clientX - rect.left) / rect.width).toFixed(3))));
    const y = Math.max(0, Math.min(1, Number(((e.clientY - rect.top) / rect.height).toFixed(3))));

    setPoints((prev) => {
      const next = [...prev];
      next[draggingIndex] = { x, y };
      return next;
    });
  };

  const handleCanvasPointerUp = () => {
    if (draggingIndex !== null) {
      setDraggingIndex(null);
      setJsonInput(JSON.stringify(points, null, 2));
    }
  };

  const handleResetPoints = () => {
    setPoints([]);
    setIsPolygonClosed(false);
    setEditMode('draw');
    setJsonInput('[]');
    showToast('Canvas golit. Fă click pe imagine pentru a plasa puncte noi.');
  };

  const handleApplyJson = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (Array.isArray(parsed) && parsed.length >= 3) {
        const norm = normalizePolygon(parsed);
        setPoints(norm);
        setIsPolygonClosed(true);
        setEditMode('drag');
        showToast('Coordonate JSON încărcate cu succes în poligon.');
      } else {
        showToast('Eroare: JSON-ul trebuie să fie un array de minimum 3 puncte {x, y}.');
      }
    } catch {
      showToast('Eroare parsare JSON coordonate: format invalid.');
    }
  };

  const cleanZoneId = zoneId.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || 'zona-1';

  const handleSave = () => {
    if (!cleanZoneId) {
      showToast('Completează un ID valid de zonă înainte de salvare.');
      return;
    }
    if (points.length < 3) {
      showToast('Eroare: Poligonul trebuie să aibă minimum 3 puncte.');
      return;
    }
    const zonePayload = {
      id: cleanZoneId,
      zone_id: cleanZoneId,
      camera_id: activeCamera?.id || selectedCameraId,
      name: zoneName.trim() || cleanZoneId,
      rule_type: ruleType,
      active_when: activeWhen,
      required_ppe: ruleType === 'PPE_REQUIRED' ? requiredPpe : [],
      severity,
      debounce_s: Number(debounceSeconds) || 1.0,
      notify_channel: 'slack',
      escalate_after_s: escalateAfterS === null || escalateAfterS === 'null' ? null : Number(escalateAfterS),
      polygon: points.map((p) => [
        Number((p.x != null ? p.x : p[0]).toFixed(3)),
        Number((p.y != null ? p.y : p[1]).toFixed(3))
      ]),
      reference_frame: activeZone?.reference_frame || null
    };

    saveZone(cleanZoneId, zonePayload);
  };

  if (!activeCamera && cameras.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 select-none">
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="max-w-md rounded-2xl border p-6 text-center space-y-3 shadow-lg"
        >
          <Shield size={36} className="mx-auto text-amber-500" />
          <h2 className="font-bold text-sm uppercase">Se încarcă camerele...</h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs">
            Se sincronizează lista de camere și zone cu backend-ul SafeSight.
          </p>
        </div>
      </div>
    );
  }

  const liveStreamSrc = activeCamera?.stream_url || `http://127.0.0.1:8000/stream/${activeCamera?.id || selectedCameraId}.mjpg`;

  return (
    <div className="flex-1 p-3 md:p-5 overflow-y-auto space-y-4 h-full select-none max-w-7xl mx-auto">
      {/* 1. Header Editor Zone */}
      <div className="flex items-center justify-between border-b border-slate-500/15 pb-3 flex-wrap gap-2">
        <div>
          <h2 className="font-black text-lg uppercase tracking-tight flex items-center gap-2">
            <PenTool size={20} className={isDarkMode ? 'text-[#D73833]' : 'text-[#D73833]'} />
            Configurare Zone & Poligoane Perimetru
          </h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs">
            Geofencing AI dinamic • Modificare coordonate și reguli de siguranță fără restart
          </p>
        </div>

        {/* Butoane Acțiuni Header */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowJsonFallback(!showJsonFallback)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-400/30 hover:bg-slate-500/10 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors shadow-sm"
            title="Deschide editorul JSON de coordonate"
          >
            <Code size={14} /> Plan B (JSON)
          </button>

          <input
            ref={referenceFileRef}
            type="file"
            accept="image/jpeg"
            className="hidden"
            disabled={!cleanZoneId}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file && cleanZoneId) captureReferenceFrame(cleanZoneId, file);
              event.target.value = '';
            }}
          />
          <button
            onClick={() => referenceFileRef.current?.click()}
            disabled={!cleanZoneId}
            className="px-3 py-1.5 rounded-lg bg-[#D73833] hover:bg-[#b82e2a] disabled:opacity-50 disabled:cursor-not-allowed text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow"
            title="Încarcă un cadru JPEG de referință pentru această zonă"
          >
            <Camera size={14} /> Încarcă Cadru Referință
          </button>
        </div>
      </div>

      {/* 2. Bara Selector Cameră & Selector Zonă */}
      <div
        style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
        className="p-3 rounded-xl border shadow-sm space-y-2.5"
      >
        {/* Selector Cameră */}
        <div className="flex items-center gap-2 text-xs flex-wrap">
          <span className="font-bold opacity-75 shrink-0">Cameră Activă:</span>
          {cameras.map((c) => {
            const isCamActive = c.id === selectedCameraId;
            return (
              <button
                key={c.id}
                onClick={() => setSelectedCameraId(c.id)}
                style={{
                  backgroundColor: isCamActive ? (isDarkMode ? '#D73833' : '#7EDEED') : 'transparent',
                  color: isCamActive ? (isDarkMode ? '#FFFFFF' : '#1F1F1F') : (isDarkMode ? '#F5F5F5' : '#1F1F1F')
                }}
                className={`px-3 py-1 rounded-lg font-mono font-bold border transition-all ${
                  isCamActive
                    ? 'border-transparent shadow-sm'
                    : isDarkMode
                    ? 'border-white/10 hover:bg-white/5'
                    : 'border-slate-300 hover:bg-slate-100 text-slate-700'
                }`}
              >
                {c.code || c.id}
              </button>
            );
          })}
        </div>

        {/* Selector Zone pe această cameră */}
        <div className="flex items-center gap-2 text-xs flex-wrap pt-2 border-t border-slate-500/10">
          <span className="font-bold opacity-75 shrink-0">Zone Configurate:</span>
          {cameraZones.map((z) => {
            const zid = z.zone_id || z.id;
            const isZoneSelected = zid === cleanZoneId;
            return (
              <button
                key={zid}
                onClick={() => loadZoneIntoForm(z)}
                style={{
                  backgroundColor: isZoneSelected ? (isDarkMode ? '#D73833' : '#7EDEED') : 'transparent',
                  color: isZoneSelected ? (isDarkMode ? '#FFFFFF' : '#1F1F1F') : (isDarkMode ? '#F5F5F5' : '#1F1F1F')
                }}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold border transition-all flex items-center gap-1.5 ${
                  isZoneSelected
                    ? 'border-transparent shadow-sm'
                    : isDarkMode
                    ? 'border-white/10 hover:bg-white/5'
                    : 'border-slate-300 hover:bg-slate-100 text-slate-700'
                }`}
              >
                <span>{z.name || zid}</span>
                <span
                  className={`text-[9px] px-1 py-0.2 rounded font-mono ${
                    z.severity === 'CRITICAL' ? 'bg-[#D73833] text-white' : 'bg-[#FFEB33] text-[#1F1F1F]'
                  }`}
                >
                  {z.rule_type}
                </span>
              </button>
            );
          })}

          <button
            onClick={handleCreateNewZone}
            className="px-2.5 py-1 rounded-lg border border-dashed border-[#FFEB33] text-amber-500 dark:text-[#FFEB33] hover:bg-[#FFEB33]/15 text-xs font-bold flex items-center gap-1 transition-colors"
            title="Adaugă o zonă nouă pe camera curentă"
          >
            <Plus size={13} /> Zonă nouă
          </button>
        </div>
      </div>

      {/* 3. Grila Principală: Canvas Video Interactiv (Stânga) + Parametri Zonă (Dreapta) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* COLOANA 1 & 2: CANVAS VIDEO CU POLIGON INTERACTIV */}
        <div className="lg:col-span-2 space-y-2">
          {/* Bara de Controale Canvas (Mod desenare / repoziționare noduri) */}
          <div className="flex items-center justify-between gap-2 px-1 text-xs">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => {
                  setEditMode('drag');
                  setIsPolygonClosed(true);
                  showToast('Mod activ: trage de punctele roșii pentru a ajusta forma perimetrului.');
                }}
                className={`px-2.5 py-1 rounded-lg font-bold flex items-center gap-1.5 text-xs transition-colors ${
                  editMode === 'drag'
                    ? 'bg-[#FFEB33] text-[#1F1F1F] shadow'
                    : 'bg-slate-500/10 text-slate-400 hover:text-white'
                }`}
              >
                <Move size={13} /> Ajustează Vârfuri
              </button>

              <button
                onClick={() => {
                  setEditMode('draw');
                  setIsPolygonClosed(false);
                  showToast('Mod activ: click pe imagine pentru a plasa vârfuri, dublu-click pentru a închide.');
                }}
                className={`px-2.5 py-1 rounded-lg font-bold flex items-center gap-1.5 text-xs transition-colors ${
                  editMode === 'draw'
                    ? 'bg-[#FFEB33] text-[#1F1F1F] shadow'
                    : 'bg-slate-500/10 text-slate-400 hover:text-white'
                }`}
              >
                <Edit3 size={13} /> Desenează Liber
              </button>
            </div>

            <button
              onClick={handleResetPoints}
              className="px-2 py-1 rounded text-xs font-bold text-red-400 hover:text-red-300 hover:bg-red-500/10 flex items-center gap-1 transition-colors"
            >
              <Trash2 size={13} /> Resetează Poligon
            </button>
          </div>

          {/* Canvas Desenare & Drag Poligon */}
          <div
            ref={canvasContainerRef}
            onClick={handleCanvasClick}
            onDoubleClick={handleDoubleClick}
            onPointerMove={handleCanvasPointerMove}
            onPointerUp={handleCanvasPointerUp}
            style={activeZone?.reference_frame_url && referenceAspect ? { aspectRatio: referenceAspect } : undefined}
            className={`relative rounded-2xl overflow-hidden bg-black border-2 border-[#FFEB33]/70 dark:border-[#FFEB33]/50 shadow-2xl flex items-center justify-center select-none ${
              editMode === 'draw' && !isPolygonClosed ? 'cursor-crosshair' : 'cursor-default'
            } min-h-[380px] md:min-h-[440px]`}
          >
            {/* 1. Imagine de Fundal: Cadrul de referință sau Stream-ul Live al camerei */}
            {activeZone?.reference_frame_url ? (
              <img
                src={activeZone.reference_frame_url}
                alt="Cadru de referință"
                className="absolute inset-0 w-full h-full object-fill pointer-events-none select-none"
                draggable={false}
                onLoad={(e) => {
                  const { naturalWidth, naturalHeight } = e.currentTarget;
                  if (naturalWidth && naturalHeight) setReferenceAspect(naturalWidth / naturalHeight);
                }}
              />
            ) : (
              <>
                <img
                  src={liveStreamSrc}
                  alt={`Live feed ${activeCamera?.id}`}
                  className="absolute inset-0 w-full h-full object-fill pointer-events-none select-none"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900/80 via-black/70 to-slate-900/90 pointer-events-none" />
              </>
            )}

            {/* 2. Poligon SVG Vectorial cu umplere roșie transparentă */}
            <svg
              viewBox="0 0 1000 1000"
              preserveAspectRatio="none"
              className="absolute inset-0 w-full h-full pointer-events-none"
            >
              {points.length > 1 && (
                <polygon
                  points={points.map((p) => `${p.x * 1000},${p.y * 1000}`).join(' ')}
                  fill="rgba(215, 56, 51, 0.28)"
                  stroke="#D73833"
                  strokeWidth="3"
                  vectorEffect="non-scaling-stroke"
                  strokeDasharray={isPolygonClosed ? 'none' : '8,5'}
                />
              )}
            </svg>

            {/* 3. Vârfuri Interactive (Noduri mutabile prin drag & drop) */}
            {points.map((p, idx) => (
              <div
                key={idx}
                onPointerDown={(e) => handlePointPointerDown(idx, e)}
                style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
                className="absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 bg-white border-2 border-[#D73833] rounded-full shadow-2xl ring-4 ring-[#D73833]/30 pointer-events-auto cursor-grab active:cursor-grabbing hover:scale-125 transition-transform"
                title={`Vârf ${idx + 1}: (${p.x.toFixed(2)}, ${p.y.toFixed(2)}) - Trage pentru a repoziționa`}
              />
            ))}

            {/* Notificare de ghidare Canvas */}
            <div className="absolute top-3 left-3 bg-black/85 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/15 text-white text-[11px] font-mono shadow-md pointer-events-none flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>
                {editMode === 'drag'
                  ? `Mod Ajustare: ${points.length} vârfuri active (trage de oricare)`
                  : isPolygonClosed
                  ? '✓ Poligon Închis'
                  : 'Mod Desenare: Click = Punct Nou, Dublu-click = Închide'}
              </span>
            </div>
          </div>

          {/* PLAN B: CÂMP JSON CU COORDONATE (Conform §5.3 Plan B) */}
          {showJsonFallback && (
            <div
              style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
              className="p-3 rounded-xl border space-y-2 text-xs shadow-sm"
            >
              <div className="flex items-center justify-between font-bold font-mono text-[11px]">
                <span style={{ color: themeStyles.textColor }}>Plan B: Coordonate Poligon Normalizate (JSON):</span>
                <button
                  onClick={handleApplyJson}
                  className="px-2.5 py-1 bg-[#D73833] text-white rounded-lg text-[10px] hover:bg-[#b82e2a] font-bold shadow"
                >
                  Aplică pe Cadru
                </button>
              </div>
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                rows={4}
                className="w-full p-2.5 rounded-lg bg-slate-100 dark:bg-black/50 border border-slate-300 dark:border-white/10 font-mono text-[10px] text-emerald-600 dark:text-emerald-400 focus:outline-none focus:ring-1 focus:ring-[#FFEB33]"
              />
            </div>
          )}
        </div>

        {/* COLOANA 3: PARAMETRII REGULII ZONEI (FORMULAR) */}
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="rounded-2xl border p-4 shadow-lg space-y-3.5 text-xs"
        >
          <div className="flex items-center justify-between border-b border-slate-500/10 pb-2">
            <h3 className="font-black text-sm uppercase tracking-wider flex items-center gap-2">
              <Layers size={16} className="text-[#D73833]" />
              Parametri Zonă AI
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-400 font-bold">
              {activeCamera?.code || selectedCameraId}
            </span>
          </div>

          <div>
            <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">
              Nume Zonă (afișat în alerte):
            </label>
            <input
              type="text"
              value={zoneName}
              onChange={(e) => setZoneName(e.target.value)}
              placeholder="Ex: Motor stâng Stand 12"
              className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all shadow-inner"
            />
          </div>

          <div>
            <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">
              ID Zonă (kebab-case):
            </label>
            <input
              type="text"
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              placeholder="Ex: engine-left"
              className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white font-mono text-xs focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all shadow-inner"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block font-mono">
              Salvat ca: <strong className="text-amber-500">{cleanZoneId}</strong>
            </span>
          </div>

          <div>
            <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">
              Tip Regulă (rule_type):
            </label>
            <select
              value={ruleType}
              onChange={(e) => setRuleType(e.target.value)}
              className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white text-xs font-bold focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all"
            >
              <option value="RESTRICTED">RESTRICTED (Zonă Interzisă)</option>
              <option value="PPE_REQUIRED">PPE_REQUIRED (Echipament Obligatoriu EIP)</option>
              <option value="FOD_WATCH">FOD_WATCH (Foreign Object Debris)</option>
              <option value="NO_SMOKING">NO_SMOKING (Fumat Interzis)</option>
            </select>
          </div>

          <div>
            <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">
              Activă Când (active_when):
            </label>
            <select
              value={activeWhen}
              onChange={(e) => setActiveWhen(e.target.value)}
              className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white text-xs font-bold focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all"
            >
              <option value="engine_on">engine_on (Doar când motorul e pornit)</option>
              <option value="always">always (Permanent activă)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">Severitate:</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full p-2 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white text-xs font-bold focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all"
              >
                <option value="CRITICAL">CRITICAL (Roșu)</option>
                <option value="WARNING">WARNING (Galben)</option>
              </select>
            </div>
            <div>
              <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">Debounce (s):</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={debounceSeconds}
                onChange={(e) => setDebounceSeconds(e.target.value)}
                className="w-full p-2 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all"
              />
            </div>
          </div>

          <div>
            <label className="font-bold block mb-1 text-slate-800 dark:text-slate-200">
              Escaladare Operator:
            </label>
            <select
              value={escalateAfterS ?? 'null'}
              onChange={(e) => setEscalateAfterS(e.target.value === 'null' ? null : Number(e.target.value))}
              className="w-full p-2 rounded-lg bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/20 text-[#1F1F1F] dark:text-white text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-[#FFEB33] transition-all"
            >
              <option value="30">30 secunde (Demo Seed)</option>
              <option value="60">60 secunde</option>
              <option value="120">120 secunde (Producție)</option>
              <option value="null">Fără escaladare automată</option>
            </select>
          </div>

          <div className="pt-2">
            <button
              onClick={handleSave}
              disabled={points.length < 3 || !cleanZoneId}
              className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-black text-xs flex items-center justify-center gap-2 shadow-lg transition-transform hover:scale-[1.01] uppercase tracking-wider"
            >
              <Save size={16} />
              <span>Salvează Zona ({points.length} vârfuri)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
