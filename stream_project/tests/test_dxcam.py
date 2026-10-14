"""Тест dxcam с разными output_idx"""
import dxcam
import cv2
import numpy as np
import time

print("=" * 60)
print("Тест dxcam с разными output_idx")
print("=" * 60)

# Создаём камеры для разных мониторов
cameras = []
frames = []

for i in range(2):
    print(f"\nСоздаю камеру {i+1} с output_idx={i}...")
    cam = dxcam.create(output_idx=i)
    cameras.append(cam)
    
    if not cam.is_capturing:
        cam.start()
        print(f"  Захват запущен")
    
    time.sleep(0.5)
    
    frame = cam.grab()
    if frame is not None:
        print(f"  frame.shape = {frame.shape}")
        print(f"  frame.mean = {np.mean(frame):.1f}")
        frames.append(frame)
        
        # Сохраняем скриншот
        cv2.imwrite(f'test_mon_{i+1}.jpg', frame)
        print(f"  Сохранено test_mon_{i+1}.jpg")
    else:
        print(f"  frame is None!")

print("\n" + "=" * 60)
print("Проверь test_mon_1.jpg и test_mon_2.jpg")
print("Если они разные — dxcam работает корректно")
print("=" * 60)

# Очистка
for cam in cameras:
    try:
        cam.stop()
    except:
        pass
