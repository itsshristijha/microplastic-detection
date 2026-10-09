import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import cv2
import numpy as np
import sys

# Reuse existing inference (ensure repo root is on sys.path)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from models.infer import load_model, infer as run_infer

UPLOAD_DIR = os.path.join(ROOT, 'uploads')
OUTPUT_DIR = os.path.join(ROOT, 'web_outputs')
MODELS_DIR = os.path.join(ROOT, 'models')
CLASSES_PATH = os.path.join(MODELS_DIR, 'classes.json')
# Load forced class list from disk so we can apply it to any loaded model handles
FORCED_CLASSES = None
try:
    import json as _json
    if os.path.exists(CLASSES_PATH):
        with open(CLASSES_PATH, 'r', encoding='utf-8') as _f:
            FORCED_CLASSES = _json.load(_f)
except Exception:
    FORCED_CLASSES = None
# Optional per-model class list overrides for dual/ensemble modes
CLASSES_PATH_A = os.getenv('CLASSES_PATH_A')
CLASSES_PATH_B = os.getenv('CLASSES_PATH_B')
# Defaults (can be overridden by environment variables)
WEIGHTS_DEFAULT = os.path.join(MODELS_DIR, 'best.pt')
FORMAT_DEFAULT = 'pt'  # 'pt' or 'onnx'

# Allow switching model format/weights via environment variables
WEIGHTS_PATH = os.getenv('INFER_WEIGHTS', WEIGHTS_DEFAULT)
MODEL_FORMAT = os.getenv('INFER_FORMAT', FORMAT_DEFAULT).lower()
# Optional ensemble envs
ENSEMBLE_A_FORMAT = os.getenv('INFER_FORMAT_A')
ENSEMBLE_A_WEIGHTS = os.getenv('INFER_WEIGHTS_A')
ENSEMBLE_B_FORMAT = os.getenv('INFER_FORMAT_B')
ENSEMBLE_B_WEIGHTS = os.getenv('INFER_WEIGHTS_B')

# Per-model confidence thresholds (defaults 0.25)
INFER_CONF_A = float(os.getenv('INFER_CONF_A', '0.25') or 0.25)
INFER_CONF_B = float(os.getenv('INFER_CONF_B', '0.25') or 0.25)
INFER_LINE_WIDTH_A = int(os.getenv('INFER_LINE_WIDTH_A', '2') or 2)
INFER_LINE_WIDTH_B = int(os.getenv('INFER_LINE_WIDTH_B', '2') or 2)
SHOW_B_RAW = os.getenv('SHOW_B_RAW', '0') == '1'
FUSE_IOU = float(os.getenv('FUSE_IOU', '0.55') or 0.55)
# When in 'dual' mode, optionally run Model B on Model A's annotated output
RUN_B_ON_A = os.getenv('RUN_B_ON_A', '0') == '1'

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)

@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# Lazy-load model once
_model_handle = None
_ensemble_handles = None
_ensemble_class_map_b2a = None

def get_model():
    global _model_handle
    global _ensemble_handles
    if MODEL_FORMAT in ('ensemble', 'dual'):
        if _ensemble_handles is None:
            if not (ENSEMBLE_A_FORMAT and ENSEMBLE_A_WEIGHTS and ENSEMBLE_B_FORMAT and ENSEMBLE_B_WEIGHTS):
                raise RuntimeError('Ensemble mode requires INFER_FORMAT_A, INFER_WEIGHTS_A, INFER_FORMAT_B, INFER_WEIGHTS_B')
                
            # Allow separate class files if provided; fallback to shared CLASSES_PATH
            class_path_a = CLASSES_PATH_A if CLASSES_PATH_A else CLASSES_PATH
            class_path_b = CLASSES_PATH_B if CLASSES_PATH_B else CLASSES_PATH
            cfgA = {'weights': ENSEMBLE_A_WEIGHTS, 'format': ENSEMBLE_A_FORMAT.lower(), 'classes_path': class_path_a}
            cfgB = {'weights': ENSEMBLE_B_WEIGHTS, 'format': ENSEMBLE_B_FORMAT.lower(), 'classes_path': class_path_b}
            hA = load_model(cfgA)
            hB = load_model(cfgB)
            # If a forced class list is present, ensure both handles use it
            if FORCED_CLASSES is not None:
                try:
                    hA.classes = list(FORCED_CLASSES)
                    hB.classes = list(FORCED_CLASSES)
                except Exception:
                    pass
            # Validate same classes for ensemble; warn-only for dual
            if MODEL_FORMAT == 'ensemble':
                classesA = hA.classes or []
                classesB = hB.classes or []
                if classesA != classesB:
                    # If sets match but order differs, build a remap for B->A
                    if set(classesA) == set(classesB):
                        global _ensemble_class_map_b2a
                        name_to_a = {n: i for i, n in enumerate(classesA)}
                        _ensemble_class_map_b2a = {j: name_to_a[name] for j, name in enumerate(classesB)}
                        print('NOTE: Remapping Model B class indices to match Model A ordering for ensemble.')
                    else:
                        raise RuntimeError('Ensemble models must share identical class names. Use CLASSES_PATH_A and CLASSES_PATH_B to align.')
            else:
                if (hA.classes or []) != (hB.classes or []):
                    print('WARNING: Dual mode with differing class lists; outputs will be shown separately.')
            _ensemble_handles = (hA, hB)
        return _ensemble_handles
    else:
        if _model_handle is None:
            config = {
                'weights': WEIGHTS_PATH,
                'format': MODEL_FORMAT,
                'classes_path': CLASSES_PATH
            }
            _model_handle = load_model(config)
            # Force classes on single-model handle as well
            if FORCED_CLASSES is not None:
                try:
                    _model_handle.classes = list(FORCED_CLASSES)
                except Exception:
                    pass
        return _model_handle

def iou_xyxy(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter <= 0:
        return 0.0
    areaA = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    areaB = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = areaA + areaB - inter
    return inter / union if union > 0 else 0.0

def fuse_detections(detA, detB, iou_thr=0.55):
    # Class-aware greedy fusion with score-weighted box averaging
    boxes = []
    scores = []
    class_ids = []
    # Combine lists
    all_boxes = detA['boxes'] + detB['boxes']
    all_scores = detA['scores'] + detB['scores']
    all_cids = detA['class_ids'] + detB['class_ids']
    # Sort by score desc
    order = list(range(len(all_scores)))
    order.sort(key=lambda i: all_scores[i], reverse=True)
    used = [False] * len(order)
    for idx in order:
        if used[idx]:
            continue
        base_box = all_boxes[idx]
        base_score = all_scores[idx]
        base_cid = all_cids[idx]
        # Collect matches of same class with IoU >= thr
        group = [(base_box, base_score)]
        used[idx] = True
        for jdx in order:
            if used[jdx] or all_cids[jdx] != base_cid:
                continue
            if iou_xyxy(base_box, all_boxes[jdx]) >= iou_thr:
                group.append((all_boxes[jdx], all_scores[jdx]))
                used[jdx] = True
        # Weighted average box
        ws = sum(s for _, s in group) + 1e-6
        x1 = sum(b[0]*s for b,s in group) / ws
        y1 = sum(b[1]*s for b,s in group) / ws
        x2 = sum(b[2]*s for b,s in group) / ws
        y2 = sum(b[3]*s for b,s in group) / ws
        boxes.append([x1,y1,x2,y2])
        scores.append(max(s for _, s in group))
        class_ids.append(base_cid)
    # Recompute counts
    counts = {}
    for cid in class_ids:
        counts[str(cid)] = counts.get(str(cid), 0) + 1
    return {'boxes': boxes, 'scores': scores, 'class_ids': class_ids, 'counts_by_class': counts}

@app.route('/', methods=['GET'])
def home():
    return render_template('upload.html')

@app.route('/predict', methods=['POST'])
def predict():
    f = request.files.get('image')
    if not f:
        return redirect(url_for('home'))
    ext = os.path.splitext(f.filename)[1].lower() or '.jpg'
    uid = uuid.uuid4().hex
    in_name = f"{uid}{ext}"
    in_path = os.path.join(UPLOAD_DIR, in_name)
    f.save(in_path)

    # Read image
    img_bgr = cv2.imread(in_path)
    if img_bgr is None:
        return "Invalid image", 400

    # Read per-request confidence (allows user to lower threshold to get more detections)
    try:
        conf_in = request.form.get('confidence') or request.form.get('conf')
        if conf_in is not None and str(conf_in).strip() != '':
            conf_val = float(conf_in)
        else:
            conf_val = INFER_CONF_A
    except Exception:
        conf_val = INFER_CONF_A
    # Use same value for both models unless otherwise provided
    confA = conf_val
    confB = conf_val

# Fixed pollution thresholds (do not ask user):
# - >15 : Very Polluted
# - >=10 : Little Pollution
# - <10 : OK
    POLLUTION_THRESH_VERY = 15
    POLLUTION_THRESH_LITTLE = 10

    model_ref = get_model()
    if MODEL_FORMAT == 'ensemble':
        hA, hB = model_ref
        detA = run_infer(hA, img_bgr, conf=confA)
        detB = run_infer(hB, img_bgr, conf=confB)
        rawB = None
        if SHOW_B_RAW and len(detB['boxes']) == 0:
            rawB = run_infer(hB, img_bgr, conf=0.0)
        # If a class remapping exists for B->A, apply it prior to fusion
        if _ensemble_class_map_b2a is not None:
            mapped_cids = [int(_ensemble_class_map_b2a.get(int(cid), int(cid))) for cid in detB['class_ids']]
            detB = {
                'boxes': detB['boxes'],
                'scores': detB['scores'],
                'class_ids': mapped_cids,
                'counts_by_class': None
            }
        result = fuse_detections(detA, detB, iou_thr=FUSE_IOU)
        classes = hA.classes or []
    elif MODEL_FORMAT == 'dual':
        hA, hB = model_ref
        # 1) Run Model A on the original image first
        detA = run_infer(hA, img_bgr, conf=confA)
        rawB = None
        classesA = hA.classes or []
        classesB = hB.classes or []
        # Annotate A
        out_a = img_bgr.copy()
        masks_a = detA.get('masks')
        meas_a = []
        UM_PER_PX = float(os.getenv('UM_PER_PX', '0') or 0)
        if masks_a is not None:
            overlay = out_a.copy()
            for i, (box, score, cid) in enumerate(zip(detA['boxes'], detA['scores'], detA['class_ids'])):
                label = classesA[cid] if classesA and cid < len(classesA) else str(cid)
                color = (int(37 * (cid + 1) % 255), int(17 * (cid + 1) % 255), int(97 * (cid + 1) % 255))
                mask = masks_a[i].astype(bool)
                overlay[mask] = (0.6 * overlay[mask] + 0.4 * np.array(color)).astype(np.uint8)
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 1)
                cv2.putText(overlay, f"{label} {score:.2f}", (x1, max(y1-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                area_px = int(mask.sum())
                if UM_PER_PX > 0:
                    import math
                    area_um2 = area_px * (UM_PER_PX ** 2)
                    eq_diam_um = math.sqrt(4.0 * area_um2 / math.pi)
                else:
                    area_um2 = None; eq_diam_um = None
                meas_a.append({'class': label, 'score': float(score), 'area_px': area_px, 'area_um2': area_um2, 'eq_diam_um': eq_diam_um})
            out_a = overlay
        else:
            for box, score, cid in zip(detA['boxes'], detA['scores'], detA['class_ids']):
                x1, y1, x2, y2 = map(int, box)
                color = (0, 255, 0)
                label = classesA[cid] if classesA and cid < len(classesA) else str(cid)
                cv2.rectangle(out_a, (x1, y1), (x2, y2), color, INFER_LINE_WIDTH_A)
                cv2.putText(out_a, f"{label} {score:.2f}", (x1, max(y1-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 2) Choose the input for Model B
        img_for_b = out_a if RUN_B_ON_A else img_bgr
        detB = run_infer(hB, img_for_b, conf=confB)
        if SHOW_B_RAW and len(detB['boxes']) == 0:
            rawB = run_infer(hB, img_for_b, conf=0.0)

        # Annotate B
        # If RUN_B_ON_A, start from A's annotated image so both overlays appear
        out_b = out_a.copy() if RUN_B_ON_A else img_bgr.copy()
        masks_b = detB.get('masks')
        meas_b = []
        if masks_b is not None:
            overlay = out_b.copy()
            for i, (box, score, cid) in enumerate(zip(detB['boxes'], detB['scores'], detB['class_ids'])):
                label = classesB[cid] if classesB and cid < len(classesB) else str(cid)
                color = (int(37 * (cid + 1) % 255), int(17 * (cid + 1) % 255), int(97 * (cid + 1) % 255))
                mask = masks_b[i].astype(bool)
                overlay[mask] = (0.6 * overlay[mask] + 0.4 * np.array(color)).astype(np.uint8)
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 1)
                cv2.putText(overlay, f"{label} {score:.2f}", (x1, max(y1-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                area_px = int(mask.sum())
                if UM_PER_PX > 0:
                    import math
                    area_um2 = area_px * (UM_PER_PX ** 2)
                    eq_diam_um = math.sqrt(4.0 * area_um2 / math.pi)
                else:
                    area_um2 = None; eq_diam_um = None
                meas_b.append({'class': label, 'score': float(score), 'area_px': area_px, 'area_um2': area_um2, 'eq_diam_um': eq_diam_um})
            out_b = overlay
        else:
            for box, score, cid in zip(detB['boxes'], detB['scores'], detB['class_ids']):
                x1, y1, x2, y2 = map(int, box)
                color = (0, 128, 255)
                label = classesB[cid] if classesB and cid < len(classesB) else str(cid)
                cv2.rectangle(out_b, (x1, y1), (x2, y2), color, 2)
                cv2.putText(out_b, f"{label} {score:.2f}", (x1, max(y1-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        out_name_a = f"{uid}_A_annotated.jpg"; out_path_a = os.path.join(OUTPUT_DIR, out_name_a)
        out_name_b = f"{uid}_B_annotated.jpg"; out_path_b = os.path.join(OUTPUT_DIR, out_name_b)
        cv2.imwrite(out_path_a, out_a)
        cv2.imwrite(out_path_b, out_b)

        # Build per-class count comparison
        counts_a = detA.get('counts_by_class', {}) or {}
        counts_b = detB.get('counts_by_class', {}) or {}
        all_classes = sorted(set(list(counts_a.keys()) + list(counts_b.keys())))
        counts_delta = []
        for cname in all_classes:
            a = int(counts_a.get(cname, 0))
            b = int(counts_b.get(cname, 0))
            counts_delta.append({'class': cname, 'a': a, 'b': b, 'delta': b - a})

        # Build pollution summary (use Model B counts as primary for dual)
        primary_counts = counts_b or counts_a or {}
        total_count = sum(int(v) for v in primary_counts.values()) if primary_counts else 0
        if total_count > POLLUTION_THRESH_VERY:
            status = 'Very Polluted'
        elif total_count >= POLLUTION_THRESH_LITTLE:
            status = 'Little Pollution'
        else:
            status = 'OK'
        pollution = {
            'count': total_count,
            'very_threshold': POLLUTION_THRESH_VERY,
            'little_threshold': POLLUTION_THRESH_LITTLE,
            'status': status,
            'percent': int(min(100, (total_count / POLLUTION_THRESH_VERY * 100) if POLLUTION_THRESH_VERY > 0 else 100))
        }

        return render_template('result.html',
                               input_image=url_for('uploaded_file', filename=in_name),
                               output_image_a=url_for('web_output_file', filename=out_name_a),
                               output_image_b=url_for('web_output_file', filename=out_name_b),
                               model_name_a=f"{ENSEMBLE_A_FORMAT}:{os.path.basename(ENSEMBLE_A_WEIGHTS)}",
                               model_name_b=f"{ENSEMBLE_B_FORMAT}:{os.path.basename(ENSEMBLE_B_WEIGHTS)}",
                               counts_a=counts_a,
                               counts_b=counts_b,
                               counts_delta=counts_delta,
                               detections_a=[{
                                   'box': box,
                                   'score': score,
                                   'class_id': cid,
                                   'class_name': (classesA[cid] if classesA and cid < len(classesA) else str(cid))
                               } for box, score, cid in zip(detA['boxes'], detA['scores'], detA['class_ids'])],
                               detections_b=[{
                                   'box': box,
                                   'score': score,
                                   'class_id': cid,
                                   'class_name': (classesB[cid] if classesB and cid < len(classesB) else str(cid))
                               } for box, score, cid in zip(detB['boxes'], detB['scores'], detB['class_ids'])],
                               measurements_a=meas_a,
                               measurements_b=meas_b,
                               um_per_px=UM_PER_PX,
                               pollution=pollution)
    else:
        handle = model_ref
        # Single model path uses per-request confidence (confA)
        result = run_infer(handle, img_bgr, conf=confA)
        classes = handle.classes or []

    # Draw annotations (boxes or masks) and compute size metrics if available
    # classes already set above
    out_img = img_bgr.copy()
    masks = result.get('masks')
    measurements = []
    UM_PER_PX = float(os.getenv('UM_PER_PX', '0') or 0)

    if masks is not None:
        # Overlay masks and compute sizes
        overlay = out_img.copy()
        for i, (box, score, cid) in enumerate(zip(result['boxes'], result['scores'], result['class_ids'])):
            label = classes[cid] if classes and cid < len(classes) else str(cid)
            color = (0, 255, 0)
            mask = masks[i].astype(bool)
            # Random-ish color per class
            color = (int(37 * (cid + 1) % 255), int(17 * (cid + 1) % 255), int(97 * (cid + 1) % 255))
            overlay[mask] = (0.6 * overlay[mask] + 0.4 * np.array(color)).astype(np.uint8)
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 1)
            cv2.putText(overlay, f"{label} {score:.2f}", (x1, max(y1-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            area_px = int(mask.sum())
            if UM_PER_PX > 0:
                area_um2 = area_px * (UM_PER_PX ** 2)
                # Equivalent diameter from area: d = sqrt(4A/pi)
                import math
                eq_diam_um = math.sqrt(4.0 * area_um2 / math.pi)
            else:
                area_um2 = None
                eq_diam_um = None
            measurements.append({
                'class': label,
                'score': float(score),
                'area_px': area_px,
                'area_um2': area_um2,
                'eq_diam_um': eq_diam_um
            })
        out_img = overlay
    else:
        # Draw bounding boxes only
        for box, score, cid in zip(result['boxes'], result['scores'], result['class_ids']):
            x1, y1, x2, y2 = map(int, box)
            color = (0, 255, 0)
            label = classes[cid] if classes and cid < len(classes) else str(cid)
            cv2.rectangle(out_img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(out_img, f"{label} {score:.2f}", (x1, max(y1-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    out_name = f"{uid}_annotated.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    cv2.imwrite(out_path, out_img)
    # Build pollution summary for single-model results
    primary_counts = result.get('counts_by_class', {}) or {}
    total_count = sum(int(v) for v in primary_counts.values()) if primary_counts else 0
    if total_count > POLLUTION_THRESH_VERY:
        status = 'Very Polluted'
    elif total_count >= POLLUTION_THRESH_LITTLE:
        status = 'Little Pollution'
    else:
        status = 'OK'
    total_area_px = sum(m.get('area_px', 0) for m in measurements) if measurements else None
    total_area_um2 = None
    if total_area_px is not None and UM_PER_PX > 0:
        total_area_um2 = total_area_px * (UM_PER_PX ** 2)
    pollution = {
        'count': total_count,
        'very_threshold': POLLUTION_THRESH_VERY,
        'little_threshold': POLLUTION_THRESH_LITTLE,
        'status': status,
        'percent': int(min(100, (total_count / POLLUTION_THRESH_VERY * 100) if POLLUTION_THRESH_VERY > 0 else 100)),
        'area_px': total_area_px,
        'area_um2': total_area_um2
    }

    return render_template('result.html',
                           input_image=url_for('uploaded_file', filename=in_name),
                           output_image=url_for('web_output_file', filename=out_name),
                           counts=result['counts_by_class'],
                           detections=[{
                               'box': box,
                               'score': score,
                               'class_id': cid,
                               'class_name': classes[cid] if classes and cid < len(classes) else str(cid)
                           } for box, score, cid in zip(result['boxes'], result['scores'], result['class_ids'])],
                           measurements=measurements,
                           um_per_px=UM_PER_PX,
                           pollution=pollution)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/web_outputs/<filename>')
def web_output_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/health', methods=['GET'])
def health():
    info = {
        'mode': MODEL_FORMAT,
        'port': int(os.getenv('PORT', '5001') or 5001),
    }
    try:
        ref = get_model()
        if MODEL_FORMAT in ('ensemble', 'dual'):
            hA, hB = ref
            info.update({
                'model_a': {
                    'format': ENSEMBLE_A_FORMAT,
                    'weights': os.path.basename(ENSEMBLE_A_WEIGHTS or ''),
                    'num_classes': len(hA.classes or [])
                },
                'model_b': {
                    'format': ENSEMBLE_B_FORMAT,
                    'weights': os.path.basename(ENSEMBLE_B_WEIGHTS or ''),
                    'num_classes': len(hB.classes or [])
                },
                'classes_equal': (hA.classes or []) == (hB.classes or []),
                'remap_b2a': bool(_ensemble_class_map_b2a),
            })
        else:
            h = ref
            info.update({
                'single': {
                    'format': MODEL_FORMAT,
                    'weights': os.path.basename(WEIGHTS_PATH or ''),
                    'num_classes': len(h.classes or [])
                }
            })
    except Exception as e:
        info['error'] = str(e)
    return jsonify(info)

## main moved to bottom after routes

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    try:
        port = int(os.getenv('PORT', '5001'))
    except Exception:
        port = 5001
    app.run(host=host, port=port, debug=True)

