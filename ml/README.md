# ml/ — detecție, tracking, zone, FOD, blur

Responsabil: **Andrei**

- Model: Ultralytics **YOLO26** (`yolo26s.pt`, `yolo26n.pt` dacă FPS < 10), fine-tuned pe un dataset PPE de pe Roboflow.
- Tracking: încorporat în Ultralytics, `model.track(..., tracker="bytetrack.yaml", persist=True)`.
- Zone: poligoane din `docs/contract.md`, coordonate 0–1.
- FOD: diferență față de cadrul de referință + obiect static peste N secunde; opțional confirmare cu YOLOE-26.
- Blur fețe: OpenCV YuNet (`cv2.FaceDetectorYN`), aplicat înainte de orice ieșire.
- Ieșire: `FrameResult` (vezi contractul), trimis backend-ului prin callback.

Modelele antrenate nu intră în git (`.pt` e ignorat). Le puneți în folderul comun din Drive.

Verificare: `python -m ml.smoke <video.mp4>` afișează detecțiile în consolă.
