# Sensor-Ready Microplastic Detector: ML Deliverable

## Training & Environment

- **Dataset:** Roboflow YOLOv8 export with train/valid/test splits (`microplastic_100.v2i.yolov8`)
- **Training Command:**
  ```powershell
  yolo task=detect mode=train model=yolov8n.pt data="C:\Users\AYUSH\OneDrive\Documents\Project EPICS\microplastic_100.v2i.yolov8\data.yaml" imgsz=640 epochs=50 batch=8 name="microplastics_v2i"
  ```
- **Environment Setup:**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install ultralytics onnxruntime opencv-python numpy
  ```
- **Export ONNX:**
  ```python
  from ultralytics import YOLO
  model = YOLO('models/best.pt')
  model.export(format='onnx', opset=12, dynamic=True)
  ```

## Inference API

- **infer.py**
  - `load_model(config)`: loads model (.pt or .onnx), returns handle
  - `infer(handle, image, conf=0.25, iou=0.5)`: returns dict with boxes, scores, class_ids, counts_by_class
  - Accepts numpy arrays (BGR/RGB)
  - Preprocessing: resize 640x640, letterbox, normalize, BGR→RGB
  - Postprocessing: NMS, class mapping, per-class counts

- **demo_infer.py**
  - CLI: `--source` image/folder, `--weights` path, `--format` onnx/pt, `--conf`, `--iou`, `--save`
  - Saves annotated images and prints per-class counts

## Output Schema

```python
{
  'boxes': [[x1, y1, x2, y2], ...],
  'scores': [float, ...],
  'class_ids': [int, ...],
  'counts_by_class': {'fiber': int, 'film': int, ...}
}
```

## Thresholds
- Default: `conf=0.25`, `iou=0.5` (tunable)

## Integration
- Load model once, keep handle
- For each frame: `result = infer(handle, frame_np)`
- Use `result['boxes']`, `result['class_ids']`, `result['scores']`, `result['counts_by_class']`

## Files
- `best.pt`, `best.onnx`, `classes.json`, `infer.py`, `demo_infer.py`

---
This package is ready for edge deployment and sensor integration. For hardware-specific builds (TensorRT, OpenVINO), see Ultralytics docs.