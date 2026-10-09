import argparse
from pathlib import Path

import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor


def get_coco_datasets(root: Path):
    try:
        from pycocotools.coco import COCO  # noqa: F401
    except Exception:
        raise SystemExit("pycocotools is required. Install with: pip install pycocotools")

    ann = root / 'annotations'
    train_img = root / 'train'
    val_img = root / 'val'
    train_ann = ann / 'instances_train.json'
    val_ann = ann / 'instances_val.json'
    if not (train_img.exists() and val_img.exists() and train_ann.exists() and val_ann.exists()):
        raise SystemExit("COCO root must contain train/, val/, and annotations/instances_[train|val].json")

    train_ds = torchvision.datasets.CocoDetection(str(train_img), str(train_ann))
    val_ds = torchvision.datasets.CocoDetection(str(val_img), str(val_ann))
    return train_ds, val_ds


def collate_fn(batch):
    return tuple(zip(*batch))


def to_rcnn_targets(target, img_w, img_h):
    import numpy as np
    boxes = []
    labels = []
    masks = []
    anns = target
    for ann in anns:
        if 'bbox' not in ann or 'category_id' not in ann:
            continue
        x, y, w, h = ann['bbox']
        boxes.append([x, y, x + w, y + h])
        labels.append(int(ann['category_id']))
        if 'segmentation' in ann and isinstance(ann['segmentation'], list) and len(ann['segmentation']) > 0:
            import pycocotools.mask as maskUtils
            rles = maskUtils.frPyObjects(ann['segmentation'], img_h, img_w)
            rle = maskUtils.merge(rles)
            m = maskUtils.decode(rle).astype('uint8')
            masks.append(m)
    if len(boxes) == 0:
        boxes = torch.zeros((0, 4), dtype=torch.float32)
        labels = torch.zeros((0,), dtype=torch.int64)
        masks = torch.zeros((0, img_h, img_w), dtype=torch.uint8)
    else:
        import numpy as np
        boxes = torch.tensor(np.array(boxes, dtype='float32'))
        labels = torch.tensor(labels, dtype=torch.int64)
        if masks:
            import numpy as np
            masks = torch.tensor(np.stack(masks, axis=0), dtype=torch.uint8)
        else:
            masks = torch.zeros((0, img_h, img_w), dtype=torch.uint8)

    area = (boxes[:, 2] - boxes[:, 0]).clamp(min=0) * (boxes[:, 3] - boxes[:, 1]).clamp(min=0)
    iscrowd = torch.zeros((labels.shape[0],), dtype=torch.int64)
    return {
        'boxes': boxes,
        'labels': labels,
        'masks': masks,
        'area': area,
        'iscrowd': iscrowd
    }


def create_model(num_classes):
    model = torchvision.models.detection.maskrcnn_resnet50_fpn_v2(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256
    model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)
    return model


def main():
    ap = argparse.ArgumentParser(description='Train Mask R-CNN on COCO-style instance segmentation dataset')
    ap.add_argument('--coco_root', required=True, help='Folder with train/, val/, annotations/instances_[train|val].json')
    ap.add_argument('--epochs', type=int, default=60)
    ap.add_argument('--batch', type=int, default=2)
    ap.add_argument('--lr', type=float, default=0.005)
    ap.add_argument('--name', default='maskrcnn_v1')
    args = ap.parse_args()

    train_ds_raw, val_ds_raw = get_coco_datasets(Path(args.coco_root))

    # Wrap to convert COCO dicts to RCNN targets with masks
    from PIL import Image
    class Wrap(torch.utils.data.Dataset):
        def __init__(self, base):
            self.base = base
        def __len__(self):
            return len(self.base)
        def __getitem__(self, idx):
            img, anns = self.base[idx]
            if not isinstance(img, Image.Image):
                # Some versions return ndarray; convert
                from PIL import Image as PILImage
                img = PILImage.fromarray(img)
            w, h = img.size
            target = to_rcnn_targets(anns, w, h)
            from torchvision.transforms import functional as F
            img = F.to_tensor(img)
            return img, target

    train_ds = Wrap(train_ds_raw)
    val_ds = Wrap(val_ds_raw)

    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2, collate_fn=lambda b: tuple(zip(*b)))
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=2, collate_fn=lambda b: tuple(zip(*b)))

    num_classes = len(train_ds_raw.coco.cats) + 1  # include background
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = create_model(num_classes).to(device)

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=0.0005)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.1)

    runs_dir = Path('runs') / 'maskrcnn' / args.name
    runs_dir.mkdir(parents=True, exist_ok=True)
    best_path = runs_dir / 'best.pth'
    last_path = runs_dir / 'last.pth'
    best_val = float('inf')

    for epoch in range(1, args.epochs + 1):
        model.train()
        tr_loss = 0.0
        for imgs, targs in train_loader:
            imgs = [img.to(device) for img in imgs]
            targs = [{k: v.to(device) for k, v in t.items()} for t in targs]
            loss_dict = model(imgs, targs)
            loss = sum(loss for loss in loss_dict.values())
            optimizer.zero_grad(); loss.backward(); optimizer.step()
            tr_loss += loss.item()
        scheduler.step()

        val_loss = 0.0
        model.train()
        with torch.no_grad():
            for imgs, targs in val_loader:
                imgs = [img.to(device) for img in imgs]
                targs = [{k: v.to(device) for k, v in t.items()} for t in targs]
                loss = sum(model(imgs, targs).values())
                val_loss += loss.item()

        ntr = max(len(train_loader), 1); nva = max(len(val_loader), 1)
        print(f"Epoch {epoch:03d}/{args.epochs} | train_loss {tr_loss/ntr:.4f} | val_loss {val_loss/nva:.4f}")
        torch.save(model.state_dict(), last_path)
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), best_path)

    # Copy best to models folder
    models_dir = Path('microplastic-ml') / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    target = models_dir / 'maskrcnn_best.pth'
    if best_path.exists():
        import shutil
        shutil.copy2(best_path, target)
        print('Copied best Mask R-CNN weights to', target)
    else:
        print('WARNING: best.pth not found at', best_path)


if __name__ == '__main__':
    main()
