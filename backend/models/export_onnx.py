from ultralytics import YOLO

# Export custom-trained YOLOv8 model to ONNX
model = YOLO('runs/detect/microplastics_v2i/weights/best.pt')
model.export(format='onnx', opset=12, dynamic=True)
