import cv2
import os
from datetime import datetime

# === CONFIGURATION ===
USB_MOUNT_PATH = "/media/pi/BEA6-BBCE"  # Update this if your USB drive is mounted elsewhere
FILENAME = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
SAVE_PATH = os.path.join(USB_MOUNT_PATH, FILENAME)

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 20.0
RECORD_DURATION_SEC = 10  # Set how long you want to record (in seconds)

# === CHECK USB MOUNT ===
if not os.path.exists(USB_MOUNT_PATH):
    print(f"USB drive not found at {USB_MOUNT_PATH}")
    exit(1)

# === INITIALIZE CAMERA ===
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

if not cap.isOpened():
    print("Failed to open webcam.")
    exit(1)

# === SETUP VIDEO WRITER ===
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # .avi format
out = cv2.VideoWriter(SAVE_PATH, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))

print(f"Recording started... Saving to {SAVE_PATH}")

frame_count = int(FPS * RECORD_DURATION_SEC)
for _ in range(frame_count):
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break
    out.write(frame)

# === CLEANUP ===
cap.release()
out.release()
print("Recording complete.")
