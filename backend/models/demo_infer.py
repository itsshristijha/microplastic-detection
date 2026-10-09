import argparse
import os
import cv2
import numpy as np
import json
from infer import load_model, infer

def draw_boxes(image, boxes, class_ids, scores, classes):
    for box, cid, score in zip(boxes, class_ids, scores):
        x1, y1, x2, y2 = map(int, box)
        label = f"{classes[cid]}: {score:.2f}"
        cv2.rectangle(image, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(image, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
    return image

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=str, required=True, help='Image or folder')
    parser.add_argument('--weights', type=str, required=True)
    parser.add_argument('--format', type=str, choices=['pt','onnx'], default='pt')
    parser.add_argument('--classes', type=str, default='classes.json')
    parser.add_argument('--conf', type=float, default=0.25)
    parser.add_argument('--iou', type=float, default=0.5)
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()

    handle = load_model({'weights': args.weights, 'format': 'pt', 'classes_path': args.classes})
    with open(args.classes, 'r') as f:
        classes = json.load(f)

    sources = []
    if os.path.isdir(args.source):
        for fname in os.listdir(args.source):
            if fname.lower().endswith(('.jpg','.png','.jpeg')):
                sources.append(os.path.join(args.source, fname))
    else:
        sources = [args.source]

    for img_path in sources:
        image = cv2.imread(img_path)
        result = infer(handle, image, conf=args.conf, iou=args.iou)
        print(f"{img_path}: counts {result['counts_by_class']}")
        if args.save:
            out_img = draw_boxes(image, result['boxes'], result['class_ids'], result['scores'], classes)
            out_path = os.path.join('annotated', os.path.basename(img_path))
            os.makedirs('annotated', exist_ok=True)
            cv2.imwrite(out_path, out_img)
            print(f"Saved: {out_path}")


if __name__ == '__main__':
    main()

