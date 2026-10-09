import os
import json
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

try:
    import albumentations as A
except Exception as e:
    raise SystemExit("Please install albumentations: pip install albumentations")

# Config
DATASET_ROOT = r"c:/Users/AYUSH/OneDrive/Documents/Project EPICS/microplastic_100.v2i.yolov8"
SPLIT = "train"  # train|valid|test
N_PER_IMAGE = 3  # how many augmented variants per source image
OUTPUT_ROOT = Path(DATASET_ROOT)
IMG_DIR = OUTPUT_ROOT / SPLIT / "images"
LBL_DIR = OUTPUT_ROOT / SPLIT / "labels"
AUG_DIR = OUTPUT_ROOT / f"{SPLIT}_aug"
AUG_IMG = AUG_DIR / "images"
AUG_LBL = AUG_DIR / "labels"

AUG_DIR.mkdir(parents=True, exist_ok=True)
AUG_IMG.mkdir(parents=True, exist_ok=True)
AUG_LBL.mkdir(parents=True, exist_ok=True)

# Albumentations pipeline (safe for detection)
transform = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.2),
    A.RandomRotate90(p=0.3),
    A.Affine(scale=(0.9, 1.1), translate_percent=(0.0, 0.05), rotate=(-10, 10), shear=(-4, 4), p=0.5),
    A.RandomBrightnessContrast(p=0.5),
    A.GaussNoise(p=0.25),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.2))


def read_yolo_labels(lbl_path):
    boxes = []
    labels = []
    if not lbl_path.exists():
        return boxes, labels
    with open(lbl_path, 'r') as f:
        for line in f.read().strip().splitlines():
            if not line:
                continue
            parts = line.split()
            if len(parts) != 5:
                continue
            cls = int(parts[0])
            x, y, w, h = map(float, parts[1:])
            boxes.append([x, y, w, h])
            labels.append(cls)
    return boxes, labels


def write_yolo_labels(lbl_path, boxes, labels):
    with open(lbl_path, 'w') as f:
        for b, c in zip(boxes, labels):
            f.write(f"{c} {b[0]:.6f} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f}\n")


def augment_one(img_path: Path):
    lbl_path = LBL_DIR / (img_path.stem + '.txt')
    boxes, labels = read_yolo_labels(lbl_path)

    # Albumentations expects abs coords for image dims? For YOLO we pass normalized with format='yolo'.
    image = cv2.imread(str(img_path))
    if image is None:
        return 0

    success = 0
    for i in range(N_PER_IMAGE):
        try:
            transformed = transform(image=image, bboxes=boxes, class_labels=labels)
            img2 = transformed['image']
            bxs = transformed['bboxes']
            cls2 = transformed['class_labels']
            if len(bxs) == 0:
                continue
            out_name = f"{img_path.stem}_aug{i}.jpg"
            cv2.imwrite(str(AUG_IMG / out_name), img2)
            write_yolo_labels(AUG_LBL / (Path(out_name).stem + '.txt'), bxs, cls2)
            success += 1
        except Exception:
            continue
    return success


def main():
    img_files = [p for p in IMG_DIR.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
    total_added = 0
    for p in tqdm(img_files, desc=f"Augmenting {SPLIT}"):
        total_added += augment_one(p)
    print(f"Added {total_added} augmented images to {AUG_IMG}")

if __name__ == '__main__':
    main()
