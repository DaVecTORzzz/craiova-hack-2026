import React, { useEffect, useState, useRef } from 'react';
import { PenTool, Save, Trash2, Camera, Info, Shield, Layers, Code } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function ZoneEditorView() {
  const { themeStyles } = useTheme();
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
    { x: 0.3, y: 0.75 }
  ]);
  const [isPolygonClosed, setIsPolygonClosed] = useState(true);
  const [showJsonFallback, setShowJsonFallback] = useState(false);
  const [jsonInput, setJsonInput] = useState(JSON.stringify(points, null, 2));

  // Parametri zonă conform Schemei din B (Decizie N13)
  const [zoneId, setZoneId] = useState('engine-left');
  const [ruleType, setRuleType] = useState('RESTRICTED');
  const [activeWhen, setActiveWhen] = useState('engine_on');
  const [severity, setSeverity] = useState('CRITICAL');
  const [debounceSeconds, setDebounceSeconds] = useState(1.4);
  const [notifyChannel, setNotifyChannel] = useState('slack');
  const [escalateAfterS, setEscalateAfterS] = useState(30);

  const canvasContainerRef = useRef(null);
  const referenceFileRef = useRef(null);
  const previousCameraRef = useRef(selectedCameraId);

  const activeZone = zones.find(
    (zone) => zone.zone_id === zoneId && zone.camera_id === selectedCameraId
  );

  useEffect(() => {
    const cameraZones = zones.filter((zone) => zone.camera_id === selectedCameraId);
    const cameraChanged = previousCameraRef.current !== selectedCameraId;
    previousCameraRef.current = selectedCameraId;

    // Cameră fără zone: editorul se golește, ca Save să nu mute o zonă de pe altă cameră.
    if (cameraZones.length === 0) {
      setZoneId('');
      setPoints([]);
      setIsPolygonClosed(false);
      setJsonInput('[]');
      setRuleType('RESTRICTED');
      setActiveWhen('always');
      setSeverity('CRITICAL');
      setDebounceSeconds(1);
      setEscalateAfterS(null);
      return;
    }

    // La schimbarea camerei preferăm zona motorului; altfel păstrăm zona editată curent.
    const preferred = cameraChanged
      ? null
      : cameraZones.find((item) => item.zone_id === zoneId);
    const zone = preferred
      || cameraZones.find((item) => item.zone_id === 'engine-left')
      || cameraZones[0];

    setZoneId(zone.zone_id);
    setPoints(zone.polygon || []);
    setIsPolygonClosed(true);
    setJsonInput(JSON.stringify(zone.polygon || [], null, 2));
    setRuleType(zone.rule_type || 'RESTRICTED');
    setActiveWhen(zone.active_when || 'always');
    setSeverity(zone.severity || 'CRITICAL');
    setDebounceSeconds(zone.debounce_s ?? 1);
    setNotifyChannel(zone.notify_channel || 'slack');
    setEscalateAfterS(zone.escalate_after_s ?? null);
  }, [selectedCameraId, zones]);

  if (!activeCamera) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="max-w-md rounded-xl border p-5 text-center space-y-2"
        >
          <h2 className="font-bold text-sm uppercase">Nu există camere</h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs">
            Backend-ul nu a returnat camere. Pornește stack-ul cu ./run.sh demo.
          </p>
        </div>
      </div>
    );
  }

  // Click pe canvas pentru adăugare punct
  const handleCanvasClick = (e) => {
    if (isPolygonClosed) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    const newPoints = [...points, { x: Number(x.toFixed(3)), y: Number(y.toFixed(3)) }];
    setPoints(newPoints);
    setJsonInput(JSON.stringify(newPoints, null, 2));
  };

  // Dublu-click pentru închidere poligon
  const handleDoubleClick = () => {
    if (points.length >= 3) {
      setIsPolygonClosed(true);
      showToast('Poligon închis. Punctele pot fi acum repoziționate.');
    } else {
      showToast('Ai nevoie de cel puțin 3 puncte pentru un poligon valid.');
    }
  };

  const handleResetPoints = () => {
    setPoints([]);
    setIsPolygonClosed(false);
    setJsonInput('[]');
  };

  const handleApplyJson = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (Array.isArray(parsed) && parsed.length >= 3) {
        setPoints(parsed);
        setIsPolygonClosed(true);
        showToast('Coordonate JSON încărcate cu succes în poligon.');
      } else {
        showToast('Eroare: JSON-ul trebuie să fie un array de minimum 3 puncte {x, y}.');
      }
    } catch (err) {
      showToast('Eroare parsare JSON coordonate: format invalid.');
    }
  };

  const canSave = Boolean(zoneId) && points.length >= 3;

  const handleSave = () => {
    if (!zoneId) {
      showToast('Completează un ID de zonă înainte de salvare.');
      return;
    }
    if (points.length < 3) {
      showToast('Eroare validare: Poligonul trebuie să aibă minimum 3 puncte.');
      return;
    }
    const zonePayload = {
      zone_id: zoneId,
      camera_id: activeCamera.id,
      name: activeZone?.name || zoneId,
      rule_type: ruleType,
      active_when: activeWhen,
      required_ppe: activeZone?.required_ppe || [],
      severity,
      debounce_s: Number(debounceSeconds),
      notify_channel: 'slack',
      escalate_after_s: escalateAfterS === null ? null : Number(escalateAfterS),
      polygon: points,
      reference_frame: activeZone?.reference_frame || null
    };
    saveZone(zoneId, zonePayload);
  };

  return (
    <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 h-full select-none max-w-7xl mx-auto">
      {/* Header Editor Zone */}
      <div className="flex items-center justify-between border-b border-white/10 pb-3 flex-wrap gap-2">
        <div>
          <h2 className="font-black text-lg uppercase tracking-tight flex items-center gap-2">
            <PenTool size={20} className="text-indigo-400" />
            Editor Zone de Siguranță & Perimetre Tarmac
          </h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-mono">
            Definire poligoane pe cadru • Geofencing dinamic fără restart (§5.3)
          </p>
        </div>

        {/* Buton Cadru de Referință FOD & Buton Plan B JSON */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowJsonFallback(!showJsonFallback)}
            className="px-2.5 py-1.5 rounded-lg border border-white/20 hover:bg-white/10 text-xs font-mono font-bold flex items-center gap-1.5"
            title="Activează Plan B: editare directă JSON coordonate"
          >
            <Code size={14} /> Plan B (JSON)
          </button>

          <input
            ref={referenceFileRef}
            type="file"
            accept="image/jpeg"
            className="hidden"
            disabled={!zoneId}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file && zoneId) captureReferenceFrame(zoneId, file);
              event.target.value = '';
            }}
          />
          <button
            onClick={() => referenceFileRef.current?.click()}
            disabled={!zoneId}
            className="px-3 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow"
            title="Încarcă un JPEG deja blurat ca referință FOD"
          >
            <Camera size={14} /> Încarcă referință FOD
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* COLOANA 1 & 2: CADRUL VIDEO CU POLIGON INTERACTIV */}
        <div className="lg:col-span-2 space-y-2">
          {/* Selector Cameră */}
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold opacity-75">Selectează Camera:</span>
            {cameras.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedCameraId(c.id)}
                className={`px-2.5 py-1 rounded font-mono font-bold border ${
                  c.id === selectedCameraId
                    ? 'bg-indigo-600 text-white border-indigo-400'
                    : 'bg-black/30 text-slate-300 border-white/10'
                }`}
              >
                {c.id}
              </button>
            ))}
          </div>

          {/* Canvas Desenare Poligon */}
          <div
            ref={canvasContainerRef}
            onClick={handleCanvasClick}
            onDoubleClick={handleDoubleClick}
            className={`relative rounded-xl overflow-hidden bg-black border-2 border-indigo-500/40 min-h-[380px] shadow-2xl flex items-center justify-center cursor-${
              isPolygonClosed ? 'default' : 'crosshair'
            }`}
          >
            {/* Fundal Video */}
            <div className={`w-full h-full absolute inset-0 bg-gradient-to-br ${activeCamera.previewBg} opacity-50`} />

            {/* SVG Poligon */}
            <svg
              viewBox="0 0 1000 1000"
              preserveAspectRatio="none"
              className="absolute inset-0 w-full h-full pointer-events-none"
            >
              {points.length > 1 && (
                <polygon
                  points={points.map((p) => `${p.x * 1000},${p.y * 1000}`).join(' ')}
                  fill="rgba(239, 68, 68, 0.25)"
                  stroke="#EF4444"
                  strokeWidth="2.5"
                  vectorEffect="non-scaling-stroke"
                  strokeDasharray={isPolygonClosed ? 'none' : '6,4'}
                />
              )}
            </svg>

            {/* Noduri / Puncte Desenate */}
            {points.map((p, idx) => (
              <div
                key={idx}
                style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
                className="absolute w-3.5 h-3.5 -translate-x-1/2 -translate-y-1/2 bg-white border-2 border-red-600 rounded-full shadow-lg ring-2 ring-red-400/50 pointer-events-auto cursor-move"
                title={`Punct ${idx + 1}: (${p.x.toFixed(2)}, ${p.y.toFixed(2)})`}
              />
            ))}

            {/* Instrucțiuni plutitoare */}
            <div className="absolute top-3 left-3 bg-black/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10 text-white text-[11px] font-mono shadow">
              <span>{isPolygonClosed ? '✓ Poligon Închis' : 'Mod Desenare: Click = Punct, Dublu-click = Închide'}</span>
            </div>

            <div className="absolute bottom-3 right-3 flex items-center gap-2">
              <button
                onClick={handleResetPoints}
                className="px-2.5 py-1 bg-red-900/80 hover:bg-red-800 text-white rounded text-xs font-bold flex items-center gap-1 border border-red-500/40"
              >
                <Trash2 size={13} /> Resetează Poligon
              </button>
            </div>
          </div>

          {/* PLAN B: CÂMP JSON CU COORDONATE (Conform §5.3 Plan B) */}
          {showJsonFallback && (
            <div
              style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
              className="p-3 rounded-xl border space-y-2 text-xs"
            >
              <div className="flex items-center justify-between font-bold font-mono text-[11px]">
                <span>Plan B: Coordonate Poligon Normalizate (JSON):</span>
                <button
                  onClick={handleApplyJson}
                  className="px-2 py-0.5 bg-indigo-600 text-white rounded text-[10px] hover:bg-indigo-500"
                >
                  Aplică pe Cadru
                </button>
              </div>
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                rows={3}
                className="w-full p-2 rounded bg-black/40 border border-white/10 font-mono text-[10px] text-emerald-400"
              />
            </div>
          )}
        </div>

        {/* COLOANA 3: PARAMETRII REGULII ZONEI (FORMULAR) */}
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="rounded-xl border p-4 shadow-lg space-y-3.5 text-xs"
        >
          <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
            <Layers size={16} className="text-indigo-400" />
            Parametri Regulă Zonă
          </h3>

          <div>
            <label className="font-bold block mb-1">ID Zonă (snake_case):</label>
            <input
              type="text"
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              className="w-full p-2 rounded bg-black/30 border border-white/20 font-mono text-xs"
            />
          </div>

          <div>
            <label className="font-bold block mb-1">Tip Regulă (rule_type):</label>
            <select
              value={ruleType}
              onChange={(e) => setRuleType(e.target.value)}
              className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white"
            >
              <option value="RESTRICTED">RESTRICTED (Zonă Interzisă)</option>
              <option value="PPE_REQUIRED">PPE_REQUIRED (Echipament Obligatoriu)</option>
              <option value="FOD_WATCH">FOD_WATCH (Foreign Object Debris)</option>
              <option value="NO_SMOKING">NO_SMOKING (Fumat Interzis)</option>
            </select>
          </div>

          <div>
            <label className="font-bold block mb-1">Activă Când (active_when):</label>
            <select
              value={activeWhen}
              onChange={(e) => setActiveWhen(e.target.value)}
              className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white"
            >
              <option value="engine_on">engine_on (Doar când motorul e pornit)</option>
              <option value="always">always (Permanent activă)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="font-bold block mb-1">Severitate:</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white"
              >
                <option value="CRITICAL">CRITICAL (Roșu)</option>
                <option value="WARNING">WARNING (Galben)</option>
              </select>
            </div>
            <div>
              <label className="font-bold block mb-1">Debounce (secunde):</label>
              <input
                type="number"
                step="0.1"
                value={debounceSeconds}
                onChange={(e) => setDebounceSeconds(e.target.value)}
                className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs font-mono"
              />
            </div>
          </div>

          <div>
            <label className="font-bold block mb-1">Escaladează după (secunde):</label>
            <select
              value={escalateAfterS ?? 'null'}
              onChange={(e) => setEscalateAfterS(e.target.value === 'null' ? null : Number(e.target.value))}
              className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white font-mono"
            >
              <option value="30">30 s (Demo Seed)</option>
              <option value="60">60 s</option>
              <option value="120">120 s (Producție)</option>
              <option value="null">Never (Fără escaladare)</option>
            </select>
          </div>

          <div>
            <label className="font-bold block mb-1">Canal Notificare:</label>
            <select
              value={notifyChannel}
              onChange={(e) => setNotifyChannel(e.target.value)}
              className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white font-mono"
            >
              <option value="slack">slack</option>
            </select>
          </div>

          <div className="pt-2">
            <button
              onClick={handleSave}
              disabled={!canSave}
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg transition-transform hover:scale-[1.02]"
            >
              <Save size={15} />
              <span>Salvează Zona ({points.length} puncte)</span>
            </button>
            {!zoneId && (
              <p className="text-[11px] text-amber-300 font-mono">
                Camera selectată nu are zone. Scrie un ID și desenează un poligon pentru a crea una nouă.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
