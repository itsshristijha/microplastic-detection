import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def find_dataset_root(extract_dir: Path) -> Path:
    # Look for a directory containing train/valid (and optional test) with images/labels
    candidates = []
    for p in extract_dir.rglob('data.yaml'):
        root = p.parent
        if (root / 'train' / 'images').exists() and (root / 'train' / 'labels').exists() and \
           (root / 'valid' / 'images').exists() and (root / 'valid' / 'labels').exists():
            candidates.append(root)
    if candidates:
        # Prefer the shortest path (top-most)
        return sorted(candidates, key=lambda x: len(str(x)))[0]
    # Fallback: check immediate children of extract_dir
    for child in extract_dir.iterdir():
        if child.is_dir() and (child / 'train' / 'images').exists():
            return child
    return extract_dir


def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main():
    parser = argparse.ArgumentParser(description='Import a Roboflow YOLOv8 ZIP into project dataset folder')
    parser.add_argument('--zip', required=True, help='Path to Roboflow-exported YOLOv8 ZIP')
    parser.add_argument('--out', required=False, default='microplastic_new.v1.yolov8',
                        help='Name of output dataset folder (created under project root)')
    args = parser.parse_args()

    zip_path = Path(args.zip)
    if not zip_path.exists():
        print('ZIP not found:', zip_path)
        sys.exit(1)

    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / args.out

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print('Extracting to temp:', tmpdir)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)

        ds_root = find_dataset_root(tmpdir)
        print('Detected dataset root:', ds_root)

        # Validate minimal structure
        required = [
            ds_root / 'train' / 'images',
            ds_root / 'train' / 'labels',
            ds_root / 'valid' / 'images',
            ds_root / 'valid' / 'labels',
        ]
        missing = [str(p) for p in required if not p.exists()]
        if missing:
            print('Missing required folders:', missing)
            sys.exit(1)

        # Copy dataset
        print('Copying dataset to:', out_dir)
        copy_tree(ds_root, out_dir)

    # Final report
    def count_imgs(p: Path):
        return sum(1 for _ in p.glob('*.jpg')) + sum(1 for _ in p.glob('*.png')) + sum(1 for _ in p.glob('*.jpeg'))

    train_n = count_imgs(out_dir / 'train' / 'images')
    val_n = count_imgs(out_dir / 'valid' / 'images')
    test_n = count_imgs(out_dir / 'test' / 'images') if (out_dir / 'test' / 'images').exists() else 0
    print('\nImport complete:')
    print('  train images:', train_n)
    print('  valid images:', val_n)
    print('  test  images:', test_n)
    data_yaml = out_dir / 'data.yaml'
    if data_yaml.exists():
        print('  data.yaml   :', data_yaml)
    else:
        print('  WARNING: data.yaml not found in output folder')


if __name__ == '__main__':
    main()
