# Paper Outline

1. Abstract
- See `../abstract.md`.

2. Introduction
- Microplastic pollution problem; gaps in automated field detection.

3. Literature Survey
- Image-based: Faster R-CNN, YOLO, U-Net/Mask R-CNN.
- Spectroscopy-based: HSI (SVM/PLS-DA/1D-CNN), Raman (CLS/ResNet).
- Physics-informed ML for environmental behavior.

4. System Analysis
- Problem complexity (tiny objects, cluttered backgrounds, translucency).

5. Requirement Analysis
- Dataset format (YOLO labels), classes, metrics (mAP@50-95), inference throughput.

6. System Design
- Model: YOLOv8 n/s; data pipeline; training configs; validation procedure.

7. Implementation and Results
- Trained weights: `models/best.pt`.
- Metrics in `results/stats.json`; PR/CM in `runs/detect/val`.
- Qualitative results: `annotated/`.

8. System Study and Testing
- Validation set evaluation; error cases; thresholding.

9. Conclusion
- Summary of accuracy and applicability.

10. Future Enhancements and Scope
- Semi-supervised learning; ViT experiments; HSI/Raman integration; Jetson deployment.

11. References
- See `../references.md`.
