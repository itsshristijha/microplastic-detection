# Abstract Components

1. Abstract
A YOLOv8-based computer vision system for automated detection of microplastics (fiber, film, fragment, pallet) from images. The pipeline covers dataset ingestion, training, evaluation (mAP/PR), export, batch inference, and a local web dashboard for results and metrics. This enables fast, objective screening to support environmental monitoring.

2. Problem Statement
Manual identification under microscopes is slow, subjective, and resource-intensive. Field imagery contains small, low-contrast targets that are difficult to detect at scale.

3. Motivation
Scale microplastic monitoring, reduce human error, and provide rapid feedback for research and policy.

4. Objectives
- Train an image-based detector on open microplastic datasets
- Achieve strong detection metrics (mAP@50 and mAP@50-95)
- Provide automated inference, annotated outputs, and a metrics dashboard

5. Scope
Image-based 2D object detection using YOLOv8 with four classes; spectroscopy and physics-informed models are listed as related and future work.

6. Existing Systems
Microscope-based manual observation; SEM/FTIR/Raman workflows; prior CV models (Faster R-CNN, YOLO, U-Net/Mask R-CNN).

7. Disadvantages of Existing Systems
Manual methods are slow and subjective; spectroscopy is accurate but expensive and slow for large areas.

8. Proposed System
YOLOv8 detection pipeline with training, validation, batch inference, and a local web viewer.

9. Workflow of Proposed System
Data → Train → Validate (mAP/PR) → Export → Batch Inference → Dashboard.

10. Hardware and Software Requirements
- Software: Python 3.12, Ultralytics YOLOv8, Torch, OpenCV, Flask
- Hardware: CPU or GPU; optional NVIDIA Jetson for edge deployment.
