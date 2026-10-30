# ml/ — detecție, tracking, zone, FOD, blur

Responsabil: **Andrei**

- Model: Ultralytics **YOLO26** (`yolo26s.pt`, `yolo26n.pt` dacă FPS < 10), fine-tuned pe un dataset PPE de pe Roboflow. **Nu YOLO11** și nu generații mai vechi; `yolo11s.pt` rămâne doar fallback dacă YOLO26 nu converge sau nu exportă.
- Tracking: încorporat în Ultralytics, `model.track(..., tracker="bytetrack.yaml", persist=True)`.
- Zone: poligoane din `docs/contract.md`, coordonate 0–1; `rule_type`, `active_when`, `debounce_s`.
- FOD: diferență față de cadrul de referință + obiect static peste `debounce_s` (3 s demo / 10 s producție); opțional confirmare cu YOLOE-26.
- Blur fețe: OpenCV YuNet (`cv2.FaceDetectorYN`), aplicat **înainte** de salvare și de upload.
- Ieșire: `FrameResult` este tip intern. Către backend se trimite `POST /edge/snapshots` (primești `snapshot_url`) și apoi `POST /edge/events`, cu `X-Edge-Token`. Pentru demo, A și B pot rula în același container, dar contractul rămâne HTTP.
- `event_id` este unic și idempotent; buffer local la pană de conexiune, retrimitere fără duplicate.

Modelele antrenate nu intră în git (`.pt` e ignorat). Le puneți în folderul comun din Drive.

Verificare: `python -m ml.smoke <video.mp4>` afișează detecțiile în consolă.
