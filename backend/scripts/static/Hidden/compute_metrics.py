import json
import os
from datetime import datetime

try:
    from ultralytics import YOLO
except Exception as e:
    raise SystemExit(f"Ultralytics not available: {e}")

# Config
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WEIGHTS = os.path.join(ROOT, 'models', 'best.pt')
# Prefer v1 dataset's data.yaml if available; adjust if you have a different yaml
DATA_YAML_V1 = os.path.join(os.path.dirname(ROOT), 'microplastic_100.v1-initial-v1.yolov8', 'data.yaml')
DATA_YAML_V2 = os.path.join(os.path.dirname(ROOT), 'microplastic_100.v2i.yolov8', 'data.yaml')

if os.path.exists(DATA_YAML_V2):
    DATA = DATA_YAML_V2
else:
    DATA = DATA_YAML_V1

RESULTS_DIR = os.path.join(ROOT, 'results')
STATS_JSON = os.path.join(RESULTS_DIR, 'stats.json')
os.makedirs(RESULTS_DIR, exist_ok=True)

if not os.path.exists(WEIGHTS):
    raise SystemExit(f"Weights not found at {WEIGHTS}")
if not os.path.exists(DATA):
    raise SystemExit(f"data.yaml not found at {DATA}. Please place your dataset yaml there.")

print(f"Evaluating model: {WEIGHTS}\nUsing data: {DATA}")

model = YOLO(WEIGHTS)
metrics = model.val(data=DATA, imgsz=640, save_json=True)

# Best-effort extraction across ultralytics versions
stats = {
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'weights': os.path.relpath(WEIGHTS, ROOT),
    'data': DATA,
    'metrics': {}
}

# Common fields
for key in (
    'box', 'seg', 'pose'
):
    obj = getattr(metrics, key, None)
    if obj is None:
        continue
    entry = {}
    for sub in ('map', 'map50', 'map75'):
        val = getattr(obj, sub, None)
        if val is not None:
            entry[sub] = float(val)
    if hasattr(obj, 'maps'):
        try:
            entry['maps'] = list(map(float, obj.maps))
        except Exception:
            pass
    if entry:
        stats['metrics'][key] = entry

# Speed if available
spd = getattr(metrics, 'speed', None)
if spd:
    try:
        stats['speed_ms'] = {k: float(v) for k, v in spd.items()}
    except Exception:
        pass

# Confusion matrix path if saved
runs_dir = getattr(metrics, 'save_dir', None) or getattr(metrics, 'save_dir', None)
if runs_dir and os.path.isdir(runs_dir):
    stats['runs_dir'] = str(runs_dir)

with open(STATS_JSON, 'w') as f:
    json.dump(stats, f, indent=2)

print(f"Saved metrics to {STATS_JSON}")
