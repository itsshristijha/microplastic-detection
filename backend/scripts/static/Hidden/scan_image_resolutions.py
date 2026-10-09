import os
import json
import cv2
from collections import Counter


def scan_images(base_dir):
    results = []
    for root, _, files in os.walk(base_dir):
        for fn in files:
            if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')):
                p = os.path.join(root, fn)
                img = cv2.imread(p)
                if img is None:
                    continue
                h, w = img.shape[:2]
                results.append({'path': p, 'width': int(w), 'height': int(h)})
    return results


def main():
    # Known dataset directory in this workspace
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dataset_dir = os.path.join(workspace_root, 'microplastic_100.v2i.yolov8')

    if not os.path.isdir(dataset_dir):
        print('Dataset directory not found:', dataset_dir)
        return

    splits = ['train/images', 'valid/images', 'test/images']
    all_results = []
    for s in splits:
        d = os.path.join(dataset_dir, s)
        if os.path.isdir(d):
            print('Scanning:', d)
            res = scan_images(d)
            print('  found', len(res), 'images')
            for r in res:
                r['split'] = s.split('/')[0]
            all_results.extend(res)
        else:
            print('  skip (missing):', d)

    # Aggregate
    total = len(all_results)
    sizes = Counter((r['width'], r['height']) for r in all_results)
    sizes_sorted = sizes.most_common()

    report = {
        'total_images': total,
        'unique_resolutions': [{'width': w, 'height': h, 'count': c} for (w, h), c in sizes_sorted],
        'samples': all_results[:200]
    }

    out_path = os.path.join(workspace_root, 'microplastic-ml', 'results', 'image_resolutions.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Print top 10 resolutions
    print('\nTotal images scanned:', total)
    print('\nTop resolutions:')
    for w_h, c in sizes_sorted[:10]:
        w, h = w_h
        print(f'  {w}x{h}: {c}')

    print('\nDetailed report written to:', out_path)


if __name__ == '__main__':
    main()
