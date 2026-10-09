import argparse
import os
import json
from pathlib import Path

import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import functional as F


def load_yaml(path: Path):
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise SystemExit("PyYAML is required. Install with: pip install pyyaml")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class YoloDetectionDataset(torch.utils.data.Dataset):
    def __init__(self, images_dir: Path, labels_dir: Path, class_names):
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir)
        self.class_names = class_names
        self.image_paths = []
        for p in sorted(self.images_dir.iterdir()):
            if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}:
                self.image_paths.append(p)
        if not self.image_paths:
            raise RuntimeError(f"No images found in {self.images_dir}")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        from PIL import Image
        import numpy as np
        img_path = self.image_paths[idx]
        lbl_path = (self.labels_dir / img_path.stem).with_suffix('.txt')

        img = Image.open(img_path).convert('RGB')
        w, h = img.size

        boxes = []
        labels = []
        if lbl_path.exists():
            for line in lbl_path.read_text().strip().splitlines():
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                cid = int(float(parts[0]))
                x, y, bw, bh = map(float, parts[1:5])
                # Denormalize xywh (center) -> xyxy in pixels
                cx = x * w
                cy = y * h
                bw *= w
                bh *= h
                x1 = cx - bw / 2
                y1 = cy - bh / 2
                x2 = cx + bw / 2
                y2 = cy + bh / 2
                boxes.append([x1, y1, x2, y2])
                labels.append(cid + 1)  # RCNN: background is 0; classes start at 1

        boxes = torch.tensor(boxes, dtype=torch.float32)
        labels = torch.tensor(labels, dtype=torch.int64)
        if boxes.ndim == 1:
            boxes = torch.zeros((0, 4), dtype=torch.float32)
        if labels.ndim == 0:
            labels = torch.zeros((0,), dtype=torch.int64)
        image_id = torch.tensor([idx])
        area = (boxes[:, 2] - boxes[:, 0]).clamp(min=0) * (boxes[:, 3] - boxes[:, 1]).clamp(min=0)
        iscrowd = torch.zeros((labels.shape[0],), dtype=torch.int64)

        target = {
            'boxes': boxes,
            'labels': labels,
            'image_id': image_id,
            'area': area,
            'iscrowd': iscrowd,
        }

        img = F.to_tensor(img)  # [0,1] CHW float32
        return img, target


def collate_fn(batch):
    return tuple(zip(*batch))


def create_model(num_classes: int):
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model


def main():
    ap = argparse.ArgumentParser(description='Train Faster R-CNN on YOLO-format dataset')
    ap.add_argument('--data', required=True, help='Path to data.yaml')
    ap.add_argument('--epochs', type=int, default=60)
    ap.add_argument('--batch', type=int, default=2)
    ap.add_argument('--lr', type=float, default=0.005)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--name', default='rcnn_v1')
    ap.add_argument('--log-file', default=None, help='Optional path to append epoch logs')
    ap.add_argument('--resume', action='store_true', help='Resume from previous run (uses last.pth + state.pt)')
    args = ap.parse_args()

    data = load_yaml(Path(args.data))
    # Resolve paths robustly relative to data.yaml
    data_root = Path(args.data).parent.resolve()

    def resolve_images_path(key_name: str, yaml_value: str):
        candidates = []
        # 1) Use YAML value as-is relative to data_root
        candidates.append((data_root / yaml_value).resolve())
        # 2) If YAML used '../', try dropping one level of '..'
        if yaml_value.startswith('../'):
            candidates.append((data_root / yaml_value.replace('../', '', 1)).resolve())
        # 3) Try conventional layout under data_root
        norm_key = 'valid' if key_name.lower() in ('val', 'valid', 'validation') else 'train'
        candidates.append((data_root / norm_key / 'images').resolve())
        # 4) As an extreme fallback, try data_root.parent (rare)
        candidates.append((data_root.parent / norm_key / 'images').resolve())
        for c in candidates:
            if c.exists():
                return c
        raise SystemExit(f"Could not resolve images path for {key_name}: tried {[str(c) for c in candidates]}")

    train_images = resolve_images_path('train', str(data.get('train', 'train/images')))
    val_key = 'val' if 'val' in data else ('valid' if 'valid' in data else 'validation')
    val_images = resolve_images_path(val_key, str(data.get(val_key, 'valid/images')))

    train_labels = (train_images.parent / 'labels').resolve()
    val_labels = (val_images.parent / 'labels').resolve()

    class_names = data.get('names')
    if class_names is None:
        raise SystemExit('data.yaml must include a names: [...] list')
    num_classes = len(class_names) + 1

    train_ds = YoloDetectionDataset(train_images, train_labels, class_names)
    val_ds = YoloDetectionDataset(val_images, val_labels, class_names)

    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=args.batch, shuffle=True, num_workers=args.workers, collate_fn=collate_fn
    )
    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers, collate_fn=collate_fn
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = create_model(num_classes).to(device)

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.1)

    runs_dir = Path('runs') / 'rcnn' / args.name
    runs_dir.mkdir(parents=True, exist_ok=True)
    best_path = runs_dir / 'best.pth'
    last_path = runs_dir / 'last.pth'

    best_val = float('inf')
    start_epoch = 1
    state_file = runs_dir / 'state.pt'

    log_path = Path(args.log_file).resolve() if args.log_file else None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as lf:
            lf.write(f"# Faster R-CNN training start name={args.name} epochs={args.epochs}\n")

    # Resume logic
    if args.resume and state_file.exists() and (runs_dir / 'last.pth').exists():
        try:
            ckpt = torch.load(runs_dir / 'last.pth', map_location=device)
            model.load_state_dict(ckpt, strict=False)
            state = torch.load(state_file, map_location=device)
            if 'optimizer' in state:
                optimizer.load_state_dict(state['optimizer'])
            if 'best_val' in state:
                best_val = state['best_val']
            if 'epoch' in state:
                start_epoch = int(state['epoch']) + 1
            line = f"Resumed from epoch {start_epoch-1} (best_val={best_val:.4f})"
            print(line)
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as lf:
                    lf.write(line + '\n')
        except Exception as e:
            print('Resume failed, starting fresh:', e)

    for epoch in range(start_epoch, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for images, targets in train_loader:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            loss_dict = model(images, targets)
            loss = sum(loss for loss in loss_dict.values())
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        lr_scheduler.step()

        # Validation: compute loss without updating weights
        val_loss = 0.0
        model.train()  # required to compute losses with targets
        with torch.no_grad():
            for images, targets in val_loader:
                images = [img.to(device) for img in images]
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                loss_dict = model(images, targets)
                loss = sum(loss for loss in loss_dict.values())
                val_loss += loss.item()

        n_train_batches = max(len(train_loader), 1)
        n_val_batches = max(len(val_loader), 1)
        avg_train = total_loss / n_train_batches
        avg_val = val_loss / n_val_batches

        line = f"Epoch {epoch:03d}/{args.epochs} | train_loss: {avg_train:.4f} | val_loss: {avg_val:.4f}"
        print(line, flush=True)
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as lf:
                lf.write(line + '\n')

        # Save checkpoints
        torch.save(model.state_dict(), last_path)
        # Persist state for resume
        torch.save({
            'epoch': epoch,
            'optimizer': optimizer.state_dict(),
            'best_val': best_val
        }, state_file)
        if avg_val < best_val:
            best_val = avg_val
            torch.save(model.state_dict(), best_path)

    # Copy best to models folder for web app usage
    models_dir = Path('microplastic-ml') / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    target = models_dir / 'rcnn_best.pth'
    if best_path.exists():
        import shutil
        shutil.copy2(best_path, target)
        msg = f'Copied best RCNN weights to {target}'
        print(msg, flush=True)
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as lf:
                lf.write(msg + '\n')
    else:
        print('WARNING: best.pth not found at', best_path)


if __name__ == '__main__':
    main()
