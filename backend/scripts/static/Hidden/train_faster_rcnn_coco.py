import argparse
import json
import os
from pathlib import Path

import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import functional as F

try:
    from pycocotools.coco import COCO  # type: ignore
except Exception as e:
    raise SystemExit("pycocotools is required. Install with: pip install pycocotools")


class CocoDetectionDataset(torch.utils.data.Dataset):
    def __init__(self, images_dir: Path, annotation_file: Path, class_names=None):
        self.images_dir = Path(images_dir)
        self.coco = COCO(str(annotation_file))
        self.image_ids = list(self.coco.imgs.keys())
        # Build category mapping (sorted by category id)
        cats = self.coco.loadCats(self.coco.getCatIds())
        # If user provided class_names, enforce order; else derive from COCO file
        if class_names:
            self.class_names = class_names
            name_to_index = {n: i for i, n in enumerate(class_names)}
            # Validate all dataset categories present in provided list
            missing = [c['name'] for c in cats if c['name'] not in name_to_index]
            if missing:
                raise RuntimeError(f"COCO categories missing from supplied class list: {missing}")
        else:
            # Use COCO export ordering by category id
            cats_sorted = sorted(cats, key=lambda c: c['id'])
            self.class_names = [c['name'] for c in cats_sorted]
        # Map COCO category id -> contiguous label index +1 (background 0)
        self.cat_id_to_label = {}
        for c in cats:
            if c['name'] not in self.class_names:
                continue
            label_index = self.class_names.index(c['name']) + 1  # background is 0
            self.cat_id_to_label[c['id']] = label_index

    def __len__(self):
        return len(self.image_ids)

    def __getitem__(self, idx):
        from PIL import Image
        image_id = self.image_ids[idx]
        img_info = self.coco.loadImgs([image_id])[0]
        file_name = img_info['file_name']
        path = self.images_dir / file_name
        img = Image.open(path).convert('RGB')
        w, h = img.size

        ann_ids = self.coco.getAnnIds(imgIds=[image_id], iscrowd=None)
        anns = self.coco.loadAnns(ann_ids)

        boxes = []
        labels = []
        areas = []
        iscrowd = []
        for ann in anns:
            if 'bbox' not in ann:
                continue
            x, y, bw, bh = ann['bbox']  # COCO bbox is [x,y,width,height]
            x1 = x
            y1 = y
            x2 = x + bw
            y2 = y + bh
            cat_id = ann['category_id']
            if cat_id not in self.cat_id_to_label:
                continue
            label = self.cat_id_to_label[cat_id]
            boxes.append([x1, y1, x2, y2])
            labels.append(label)
            areas.append(bw * bh)
            iscrowd.append(ann.get('iscrowd', 0))

        boxes = torch.tensor(boxes, dtype=torch.float32)
        labels = torch.tensor(labels, dtype=torch.int64)
        areas = torch.tensor(areas, dtype=torch.float32)
        iscrowd = torch.tensor(iscrowd, dtype=torch.int64)
        if boxes.ndim == 1:
            boxes = torch.zeros((0, 4), dtype=torch.float32)
        if labels.ndim == 0:
            labels = torch.zeros((0,), dtype=torch.int64)
        image_id_tensor = torch.tensor([image_id])

        target = {
            'boxes': boxes,
            'labels': labels,
            'image_id': image_id_tensor,
            'area': areas,
            'iscrowd': iscrowd,
        }
        return F.to_tensor(img), target


def collate_fn(batch):
    return tuple(zip(*batch))


def create_model(num_classes: int, pretrained_backbone: bool):
    if pretrained_backbone:
        # Use COCO pretrained weights for backbone (will replace predictor)
        model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights="DEFAULT")
    else:
        model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model


def parse_args():
    ap = argparse.ArgumentParser(description='Train Faster R-CNN on COCO-format dataset')
    ap.add_argument('--train-images', required=True, help='Path to training images directory')
    ap.add_argument('--train-ann', required=True, help='Path to training annotations JSON (instances_train.json)')
    ap.add_argument('--val-images', required=True, help='Path to validation images directory')
    ap.add_argument('--val-ann', required=True, help='Path to validation annotations JSON (instances_val.json)')
    ap.add_argument('--classes-json', default=None, help='Optional classes.json to enforce class order')
    ap.add_argument('--epochs', type=int, default=40)
    ap.add_argument('--batch', type=int, default=2)
    ap.add_argument('--lr', type=float, default=0.005)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--name', default='rcnn_coco_v1')
    ap.add_argument('--pretrained', action='store_true', help='Use COCO pretrained backbone weights')
    ap.add_argument('--log-file', default=None, help='Optional path to append epoch logs')
    ap.add_argument('--resume', action='store_true', help='Resume from last run (state.pt + last.pth)')
    return ap.parse_args()


def main():
    args = parse_args()

    if args.classes_json and Path(args.classes_json).exists():
        class_names = json.loads(Path(args.classes_json).read_text(encoding='utf-8'))
    else:
        class_names = None  # Will derive from COCO file

    train_ds = CocoDetectionDataset(Path(args.train_images), Path(args.train_ann), class_names)
    if class_names is None:
        class_names = train_ds.class_names  # adopt detected ordering
    val_ds = CocoDetectionDataset(Path(args.val_images), Path(args.val_ann), class_names)

    num_classes = len(class_names) + 1  # background

    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=args.batch, shuffle=True, num_workers=args.workers, collate_fn=collate_fn
    )
    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers, collate_fn=collate_fn
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = create_model(num_classes, pretrained_backbone=args.pretrained).to(device)

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.1)

    runs_dir = Path('runs') / 'rcnn_coco' / args.name
    runs_dir.mkdir(parents=True, exist_ok=True)
    best_path = runs_dir / 'best.pth'
    last_path = runs_dir / 'last.pth'
    state_file = runs_dir / 'state.pt'
    best_val = float('inf')
    start_epoch = 1

    log_path = Path(args.log_file).resolve() if args.log_file else None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as lf:
            lf.write(f"# COCO Faster R-CNN training start name={args.name} epochs={args.epochs} classes={class_names}\n")

    if args.resume and state_file.exists() and last_path.exists():
        try:
            ckpt = torch.load(last_path, map_location=device)
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

        # Validation
        val_loss = 0.0
        model.train()  # still required for loss computation
        with torch.no_grad():
            for images, targets in val_loader:
                images = [img.to(device) for img in images]
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                loss_dict = model(images, targets)
                loss = sum(loss for loss in loss_dict.values())
                val_loss += loss.item()

        avg_train = total_loss / max(len(train_loader), 1)
        avg_val = val_loss / max(len(val_loader), 1)
        line = f"Epoch {epoch:03d}/{args.epochs} | train_loss: {avg_train:.4f} | val_loss: {avg_val:.4f}"
        print(line, flush=True)
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as lf:
                lf.write(line + '\n')

        torch.save(model.state_dict(), last_path)
        torch.save({'epoch': epoch, 'optimizer': optimizer.state_dict(), 'best_val': best_val}, state_file)
        if avg_val < best_val:
            best_val = avg_val
            torch.save(model.state_dict(), best_path)

    # Copy best to models dir
    models_dir = Path('microplastic-ml') / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    target = models_dir / 'rcnn_coco_best.pth'
    if best_path.exists():
        import shutil
        shutil.copy2(best_path, target)
        msg = f'Copied best COCO RCNN weights to {target}'
        print(msg)
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as lf:
                lf.write(msg + '\n')
    else:
        print('WARNING: best.pth not found; no copy performed')

    # Persist class names used for training for reference
    (models_dir / 'rcnn_coco_classes.json').write_text(json.dumps(class_names, indent=2))


if __name__ == '__main__':
    main()
