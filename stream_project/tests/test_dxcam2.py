"""Тест dxcam — как обновлять буфер при статичном экране"""
import dxcam
import cv2
import numpy as np
import time

print("=" * 60)
print("Тест dxcam обновлений")
print("=" * 60)

# Создаём камеру
cam = dxcam.create(output_idx=0)
cam.start()

print("\n1. Тест grab() + get_latest_frame():")
for i in range(5):
    result = cam.grab()
    frame = cam.get_latest_frame()
    print(f"  grab()={type(result).__name__}, frame={'None' if frame is None else f'shape={frame.shape}'}")
    time.sleep(0.3)

print("\n2. Тест start(region=...) затем grab():")
region = (0, 0, 1920, 1080)
for i in range(5):
    cam.start(region=region)
    time.sleep(0.05)
    result = cam.grab()
    frame = cam.get_latest_frame()
    print(f"  grab()={type(result).__name__}, frame={'None' if frame is None else f'shape={frame.shape}'}")
    time.sleep(0.3)

print("\n3. Тест stop()/start():")
for i in range(5):
    cam.stop()
    time.sleep(0.05)
    cam.start()
    time.sleep(0.05)
    result = cam.grab()
    frame = cam.get_latest_frame()
    print(f"  grab()={type(result).__name__}, frame={'None' if frame is None else f'shape={frame.shape}'}")
    time.sleep(0.3)

cam.stop()
print("\nТест завершён")
