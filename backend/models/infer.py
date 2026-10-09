import os
import numpy as np
import json
from pathlib import Path

try:
    import torch
    from ultralytics import YOLO
except ImportError:
    torch = None
    YOLO = None
try:
    import onnxruntime as ort
except ImportError:
    ort = None
try:
    import torch
    import torchvision
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
except Exception:
    pass

class ModelHandle:
    def __init__(self, model, format, classes):
        self.model = model
        self.format = format
        self.classes = classes


def _select_state_dict(state):
    """Return a raw state_dict from common checkpoint formats."""
    if isinstance(state, dict):
        for key in ("model", "model_state_dict", "state_dict"):
            if key in state and isinstance(state[key], dict):
                return state[key]
    return state


def _maybe_strip_module_prefix(state_dict):
    """If keys are prefixed with 'module.', strip it for DataParallel checkpoints."""
    if not isinstance(state_dict, dict):
        return state_dict
    sample_key = next(iter(state_dict.keys()), None)
    if sample_key and sample_key.startswith("module."):
        return {k[len("module."):]: v for k, v in state_dict.items()}
    return state_dict


def _load_state_forgiving(model, state):
    """Load a checkpoint while skipping tensors with mismatched shapes.

    Returns list of skipped keys for visibility.
    """
    raw = _select_state_dict(state)
    raw = _maybe_strip_module_prefix(raw)
    if not isinstance(raw, dict):
        # Not a valid state dict; nothing to load
        return []
    current = model.state_dict()
    filtered = {}
    skipped = []
    for k, v in raw.items():
        if k in current and current[k].shape == v.shape:
            filtered[k] = v
        else:
            skipped.append(k)
    # Load what matches; allow missing/unexpected
    model.load_state_dict(filtered, strict=False)
    if skipped:
        print(f"[infer] Skipped {len(skipped)} keys due to shape mismatch or absence:"
              f" e.g., {skipped[:5]}")
    return skipped


def _load_classes_from_path(classes_path: str):
    p = Path(classes_path)
    ext = p.suffix.lower()
    if ext in ('.json', ''):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    if ext in ('.yaml', '.yml'):
        try:
            import yaml  # type: ignore
        except Exception:
            raise SystemExit("PyYAML is required to read YAML classes. Install with: pip install pyyaml")
        data = yaml.safe_load(open(p, 'r', encoding='utf-8'))
        # Roboflow/Ultralytics data.yaml uses either list or dict under 'names'
        names = data.get('names')
        if isinstance(names, dict):
            # sort by key (index) to make contiguous list
            return [names[k] for k in sorted(names.keys(), key=lambda x: int(x))]
        if isinstance(names, list):
            return names
        raise ValueError(f"YAML at {classes_path} missing 'names' field")
    raise ValueError(f"Unsupported classes file extension: {ext}")


def load_model(config):
    """
    Loads a YOLOv8 model (.pt or .onnx) and returns a ModelHandle.
    config: dict with keys 'weights', 'format', 'classes_path'
    """
    weights = config['weights']
    format = config.get('format', 'pt')
    classes_path = config.get('classes_path', None)
    if classes_path:
        classes = _load_classes_from_path(classes_path)
    else:
        classes = None
    if format == 'pt':
        if YOLO is None:
            raise ImportError('Ultralytics YOLO not installed')
        model = YOLO(weights)
        return ModelHandle(model, 'pt', classes)
    elif format == 'onnx':
        if ort is None:
            raise ImportError('onnxruntime not installed')
        session = ort.InferenceSession(weights)
        return ModelHandle(session, 'onnx', classes)
    elif format == 'rcnn':
        # Load Faster R-CNN weights (state_dict). Requires classes length.
        if classes is None:
            raise ValueError('classes_path required for RCNN model to infer num_classes')
        num_classes = len(classes) + 1
        model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=None)
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        state = torch.load(weights, map_location='cpu')
        _load_state_forgiving(model, state)
        model.eval()
        return ModelHandle(model, 'rcnn', classes)
    elif format == 'maskrcnn':
        # Load Mask R-CNN for instance segmentation (requires classes for head size)
        if classes is None:
            raise ValueError('classes_path required for Mask R-CNN to infer num_classes')
        num_classes = len(classes) + 1
        model = torchvision.models.detection.maskrcnn_resnet50_fpn_v2(weights=None)
        # Replace box predictor
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        # Replace mask predictor
        in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
        hidden_layer = 256
        model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)
        state = torch.load(weights, map_location='cpu')
        _load_state_forgiving(model, state)
        model.eval()
        return ModelHandle(model, 'maskrcnn', classes)
    else:
        raise ValueError('Unsupported format: ' + format)


def infer(handle, image, conf=0.25, iou=0.5):
    """
    Runs inference on a numpy image. Returns dict with boxes, scores, class_ids, counts_by_class.
    """
    # Preprocess: resize, letterbox, normalize
    if handle.format == 'pt':
        # Pass raw image to Ultralytics YOLO, it handles preprocessing
        results = handle.model(image, conf=conf, iou=iou)
        boxes, scores, class_ids = [], [], []
        for r in results:
            for b, s, c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), r.boxes.cls.cpu().numpy()):
                boxes.append(b.tolist())
                scores.append(float(s))
                class_ids.append(int(c))
    elif handle.format == 'onnx':
        # ONNX path: letterbox to 640, normalize, then map boxes back to original image size
        input_name = handle.model.get_inputs()[0].name
        img_tensor, ratio, dwdh, orig_shape = preprocess_onnx(image, 640)
        img_batch = np.expand_dims(img_tensor, axis=0).astype(np.float32)
        ort_inputs = {input_name: img_batch}
        outputs = handle.model.run(None, ort_inputs)
        boxes, scores, class_ids = postprocess_onnx(outputs, conf, iou, ratio, dwdh, orig_shape)
    elif handle.format == 'rcnn':
        # TorchVision RCNN expects tensor CHW float in [0,1]
        import cv2
        img = image
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        tensor = torch.from_numpy(img).permute(2, 0, 1)
        with torch.no_grad():
            out = handle.model([tensor])[0]
        b = out['boxes'].cpu().numpy()
        s = out['scores'].cpu().numpy()
        c = out['labels'].cpu().numpy() - 1  # back to 0-based class ids
        m = s >= conf
        boxes = b[m].tolist()
        scores = s[m].tolist()
        class_ids = c[m].astype(int).tolist()
    elif handle.format == 'maskrcnn':
        import cv2
        img = image
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        tensor = torch.from_numpy(img).permute(2, 0, 1)
        with torch.no_grad():
            out = handle.model([tensor])[0]
        b = out['boxes'].cpu().numpy()
        s = out['scores'].cpu().numpy()
        c = out['labels'].cpu().numpy() - 1
        masks = out.get('masks')
        if masks is not None:
            masks = masks.squeeze(1).cpu().numpy()  # (N,H,W) with logits [0..1] after sigmoid
            masks = masks >= 0.5
        m = s >= conf
        boxes = b[m].tolist()
        scores = s[m].tolist()
        class_ids = c[m].astype(int).tolist()
        if masks is not None:
            masks = masks[m]
            # Return masks as uint8 arrays (0/1) to keep size small
            masks = masks.astype(np.uint8)
        else:
            masks = None
    else:
        raise ValueError('Unsupported format')
    # Count per class
    counts = {}
    for cid in class_ids:
        cname = handle.classes[cid] if handle.classes else str(cid)
        counts[cname] = counts.get(cname, 0) + 1
    result = {
        'boxes': boxes,
        'scores': scores,
        'class_ids': class_ids,
        'counts_by_class': counts
    }
    if handle.format == 'maskrcnn' and 'masks' in locals() and masks is not None:
        # Attach masks as list of binary arrays
        result['masks'] = masks
    return result


def letterbox(img, new_shape=(640, 640), color=(114, 114, 114)):
    import cv2
    shape = img.shape[:2]  # (h, w)
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
    dw /= 2
    dh /= 2
    if shape[::-1] != new_unpad:
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return img, r, (dw, dh)


def preprocess_onnx(image, size=640):
    # Letterbox to size x size, BGR->RGB, CHW, [0,1]
    import cv2
    h0, w0 = image.shape[:2]
    img, r, dwdh = letterbox(image, (size, size))
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))  # CHW
    return img, r, dwdh, (h0, w0)


def postprocess_onnx(outputs, conf, iou, ratio, dwdh, orig_shape):
    # Decode YOLOv8 ONNX output. Works for output shape (1, N, C) or (1, C, N)
    import math
    out = outputs[0]
    out = np.squeeze(out)
    if out.ndim == 2:
        # (N, C) or (C, N)
        if out.shape[0] < out.shape[1]:
            # (C, N) -> (N, C)
            out = out.T
    elif out.ndim == 3:
        # (B, C, N) or (B, N, C)
        if out.shape[1] < out.shape[2]:
            out = np.transpose(out, (0, 2, 1))[0]
        else:
            out = out[0]
    else:
        out = out.reshape(-1, out.shape[-1])

    # out: (num_preds, 4+nc) or (num_preds, 5+nc) where col4 may be objectness
    num_cols = out.shape[1]
    # Heuristic: if there's an objectness column, it's at index 4
    if num_cols > 6:  # likely 4 + (1 opt obj) + nc
        # Try to detect presence of objectness by range of 5th column
        obj_col = out[:, 4]
        has_obj = (obj_col.max() <= 1.0 and obj_col.min() >= 0.0)
    else:
        has_obj = False

    if has_obj:
        boxes_xywh = out[:, 0:4]
        obj = out[:, 4:5]
        class_scores = out[:, 5:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = obj[:, 0] * class_scores[np.arange(class_scores.shape[0]), class_ids]
    else:
        boxes_xywh = out[:, 0:4]
        class_scores = out[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(class_scores.shape[0]), class_ids]

    # Filter by confidence
    mask = scores >= conf
    boxes_xywh = boxes_xywh[mask]
    scores = scores[mask]
    class_ids = class_ids[mask]
    if boxes_xywh.size == 0:
        return [], [], []

    # Convert xywh (center) at letterboxed scale to xyxy in original image scale
    dw, dh = dwdh
    r = ratio
    # Undo letterbox and scaling
    cx = boxes_xywh[:, 0]
    cy = boxes_xywh[:, 1]
    w = boxes_xywh[:, 2]
    h = boxes_xywh[:, 3]
    x1 = (cx - w / 2) - dw
    y1 = (cy - h / 2) - dh
    x2 = (cx + w / 2) - dw
    y2 = (cy + h / 2) - dh
    x1 /= r; y1 /= r; x2 /= r; y2 /= r

    # Clip to image
    h0, w0 = orig_shape
    x1 = np.clip(x1, 0, w0 - 1)
    y1 = np.clip(y1, 0, h0 - 1)
    x2 = np.clip(x2, 0, w0 - 1)
    y2 = np.clip(y2, 0, h0 - 1)

    boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

    # NMS
    keep = nms_numpy(boxes_xyxy, scores, iou)
    boxes_xyxy = boxes_xyxy[keep]
    scores = scores[keep]
    class_ids = class_ids[keep]

    return boxes_xyxy.tolist(), scores.tolist(), class_ids.tolist()


def nms_numpy(boxes, scores, iou_thres=0.5):
    if boxes.shape[0] == 0:
        return np.array([], dtype=int)
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= iou_thres)[0]
        order = order[inds + 1]
    return np.array(keep, dtype=int)
