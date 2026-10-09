import argparse
import os
import random
import shutil
from pathlib import Path

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}


def list_images(images_dir: Path):
    files = []
    for p in images_dir.rglob('*'):
        if p.suffix.lower() in IMG_EXTS and p.is_file():
            files.append(p)
    return files


def ensure_pair(image_path: Path, labels_dir: Path) -> Path | None:
    label = labels_dir / (image_path.stem + '.txt')
    return label if label.exists() else None


def copy_pair(img: Path, lbl: Path, out_images: Path, out_labels: Path):
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)
    shutil.copy2(img, out_images / img.name)
    shutil.copy2(lbl, out_labels / lbl.name)


def write_data_yaml(root: Path, has_test: bool):
    data_yaml = root / 'data.yaml'
    lines = [
        'train: train/images',
        'val: valid/images',
    ]
    if has_test:
        lines.append('test: test/images')
    # Note: class names should be preserved from original export; if missing, user can edit.
    content = '\n'.join(lines) + '\n'
    data_yaml.write_text(content, encoding='utf-8')
    return data_yaml


def main():
    ap = argparse.ArgumentParser(description='Split a YOLO dataset (images/labels) into train/valid/test')
    ap.add_argument('--src', required=True, help='Path to dataset root containing images/ and labels/ or a Roboflow root')
    ap.add_argument('--train', type=float, default=0.7, help='Train ratio (default 0.7)')
    ap.add_argument('--val', type=float, default=0.2, help='Val ratio (default 0.2)')
    ap.add_argument('--test', type=float, default=0.1, help='Test ratio (default 0.1)')
    ap.add_argument('--seed', type=int, default=42, help='Random seed')
    ap.add_argument('--copy', action='store_true', help='Copy instead of move (default: move)')
    args = ap.parse_args()

    random.seed(args.seed)
    src = Path(args.src).resolve()

    # Detect unsplit or already split structure
    images_dir = src / 'images'
    labels_dir = src / 'labels'
    already_split = (src / 'train' / 'images').exists() and (src / 'valid' / 'images').exists()

    if already_split:
        print('Dataset already has train/valid[/test] folders. Nothing to do.')
        return

    if not images_dir.exists() or not labels_dir.exists():
        raise SystemExit(f'Expected {images_dir} and {labels_dir} to exist')

    imgs = list_images(images_dir)
    pairs = []
    missing_labels = 0
    for img in imgs:
        lbl = ensure_pair(img, labels_dir)
        if lbl is None:
            missing_labels += 1
            continue
        pairs.append((img, lbl))

    if not pairs:
        raise SystemExit('No image/label pairs found')

    print(f'Total images: {len(imgs)} | pairs usable: {len(pairs)} | missing labels: {missing_labels}')

    random.shuffle(pairs)
    n = len(pairs)
    n_train = int(n * args.train)
    n_val = int(n * args.val)
    n_test = n - n_train - n_val if args.test > 0 else 0

    train_pairs = pairs[:n_train]
    val_pairs = pairs[n_train:n_train + n_val]
    test_pairs = pairs[n_train + n_val: n_train + n_val + n_test]

    # Prepare output dirs
    train_img = src / 'train' / 'images'
    train_lbl = src / 'train' / 'labels'
    val_img = src / 'valid' / 'images'
    val_lbl = src / 'valid' / 'labels'
    test_img = src / 'test' / 'images'
    test_lbl = src / 'test' / 'labels'

    op = shutil.copy2 if args.copy else shutil.move

    for img, lbl in train_pairs:
        train_img.mkdir(parents=True, exist_ok=True)
        train_lbl.mkdir(parents=True, exist_ok=True)
        op(img, train_img / img.name)
        op(lbl, train_lbl / lbl.name)

    for img, lbl in val_pairs:
        val_img.mkdir(parents=True, exist_ok=True)
        val_lbl.mkdir(parents=True, exist_ok=True)
        op(img, val_img / img.name)
        op(lbl, val_lbl / lbl.name)

    if n_test > 0:
        for img, lbl in test_pairs:
            test_img.mkdir(parents=True, exist_ok=True)
            test_lbl.mkdir(parents=True, exist_ok=True)
            op(img, test_img / img.name)
            op(lbl, test_lbl / lbl.name)

    data_yaml = write_data_yaml(src, has_test=n_test > 0)

    print('Split complete:')
    print('  train:', len(train_pairs))
    print('  valid:', len(val_pairs))
    print('  test :', len(test_pairs))
    print('data.yaml written to:', data_yaml)


if __name__ == '__main__':
    main()
