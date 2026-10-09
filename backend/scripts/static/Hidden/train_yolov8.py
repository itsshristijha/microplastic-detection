import argparse
import os
from pathlib import Path



def main():
    ap = argparse.ArgumentParser(description='Train YOLOv8 on a dataset')
    ap.add_argument('--data', required=True, help='Path to data.yaml')
    ap.add_argument('--model', default='microplastic-ml/yolov8n.pt', help='Base model weights (e.g., yolov8n.pt)')
    ap.add_argument('--imgsz', type=int, default=640, help='Training image size')
    ap.add_argument('--epochs', type=int, default=100, help='Number of epochs')
    ap.add_argument('--batch', type=int, default=16, help='Batch size')
    ap.add_argument('--name', default='mp_new_v1', help='Run name')
    args = ap.parse_args()

    try:
        from ultralytics import YOLO
    except Exception:
        print('Ultralytics not installed. Install with: pip install ultralytics')
        raise

    model = YOLO(args.model)
    results = model.train(
        data=args.data,
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=args.batch,
        name=args.name,
        project='runs/detect'
    )

    # Copy best weights to models/best.pt for the web app
    best = Path('runs') / 'detect' / args.name / 'weights' / 'best.pt'
    target = Path('microplastic-ml') / 'models' / 'best.pt'
    target.parent.mkdir(parents=True, exist_ok=True)
    if best.exists():
        import shutil
        shutil.copy2(best, target)
        print('Copied best weights to', target)
    else:
        print('WARNING: best.pt not found at', best)


if __name__ == '__main__':
    main()
