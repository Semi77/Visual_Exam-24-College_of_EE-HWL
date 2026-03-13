from ultralytics import YOLO
from multiprocessing import freeze_support


def main():
    model = YOLO("yolov8n.pt")

    model.train(
        data=r"C:\Users\28478\Desktop\Run_Auto\Run_Auto\Works\yolo_dataset\dataset.yaml",
        epochs=80,
        imgsz=640,
        batch=8,
        device=0,
        workers=4,
    )


if __name__ == "__main__":
    freeze_support()
    main()