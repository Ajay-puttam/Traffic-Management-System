import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import deque

# Load the YOLOv8 model
model = YOLO("yolov8s.pt")

# --- Configuration ---
VIDEO_PATH = "traffic.mp4"
# Define the regions of interest (ROIs) for two roads (x1, y1, x2, y2)
# These are placeholder values and should be adjusted for your specific video
ROI1 = (20, 120, 320, 350)
ROI2 = (400, 60, 780, 260)

# Calculate ROI areas
ROI1_AREA = (ROI1[2] - ROI1[0]) * (ROI1[3] - ROI1[1])
ROI2_AREA = (ROI2[2] - ROI2[0]) * (ROI2[3] - ROI2[1])

# Moving average settings
MA_WINDOW = 10  # Number of frames for moving average
road1_counts = deque(maxlen=MA_WINDOW)
road2_counts = deque(maxlen=MA_WINDOW)

# Dynamic green duration settings
MIN_GREEN = 7  # seconds
MAX_GREEN = 25  # seconds
BASE_GREEN = 15  # base green duration

# Traffic light settings
YELLOW_DURATION = 3  # seconds
RED_DURATION = 2  # minimum red duration before switching

# --- Initialization ---
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"Error: Could not open video file {VIDEO_PATH}")
    exit()

# Traffic light state: 0 for Road 1 Green, 1 for Road 2 Green
traffic_light_state = 0
last_switch_time = time.time()
dynamic_green_duration = BASE_GREEN

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # --- Object Detection ---
    results = model(frame, verbose=False)

    # Reset vehicle counts for the current frame
    current_road1_vehicles = 0
    current_road2_vehicles = 0

    # --- Vehicle Counting in ROIs ---
    for r in results:
        boxes = r.boxes
        for box in boxes:
            if box.conf[0] < 0.4:  # Only keep detections with confidence > 0.4
                continue
            cls = int(box.cls[0])
            # Check if the detected object is a vehicle (car, truck, bus, etc.)
            # Common COCO classes for vehicles: 2(car), 3(motorcycle), 5(bus), 7(truck)
            if cls in [2, 7]:  # 2: car, 7: truck
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2

                # Check if the center of the vehicle is within ROI1
                if ROI1[0] < center_x < ROI1[2] and ROI1[1] < center_y < ROI1[3]:
                    current_road1_vehicles += 1
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Check if the center of the vehicle is within ROI2
                elif ROI2[0] < center_x < ROI2[2] and ROI2[1] < center_y < ROI2[3]:
                    current_road2_vehicles += 1
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # --- Moving Average Smoothing ---
    road1_counts.append(current_road1_vehicles)
    road2_counts.append(current_road2_vehicles)
    road1_vehicles = int(np.mean(road1_counts))
    road2_vehicles = int(np.mean(road2_counts))

    # --- Density Calculation ---
    density1 = road1_vehicles / ROI1_AREA
    density2 = road2_vehicles / ROI2_AREA

    # --- Dynamic Green Duration Calculation ---
    # Ratio of densities, clipped to avoid extreme values
    if density1 + density2 > 0:
        ratio = density1 / (density1 + density2)
    else:
        ratio = 0.5  # If both are zero, split evenly
    # Assign green duration based on density ratio
    if traffic_light_state == 0:
        dynamic_green_duration = int(MIN_GREEN + (MAX_GREEN - MIN_GREEN) * ratio)
    else:
        dynamic_green_duration = int(MIN_GREEN + (MAX_GREEN - MIN_GREEN) * (1 - ratio))

    # --- Traffic Light Logic (Density-Based) ---
    current_time = time.time()
    time_since_last_switch = current_time - last_switch_time

    if traffic_light_state == 0:  # Road 1 is Green
        if time_since_last_switch > dynamic_green_duration:
            if density2 > density1:  # Switch if Road 2 is denser
                traffic_light_state = 1  # Switch to Road 2 Green
                last_switch_time = current_time
    elif traffic_light_state == 1:  # Road 2 is Green
        if time_since_last_switch > dynamic_green_duration:
            if density1 > density2:  # Switch if Road 1 is denser
                traffic_light_state = 0  # Switch to Road 1 Green
                last_switch_time = current_time

    # --- Visualization ---
    # Draw ROIs
    cv2.rectangle(frame, (ROI1[0], ROI1[1]), (ROI1[2], ROI1[3]), (255, 0, 0), 2)
    cv2.putText(
        frame,
        f"Road 1",
        (ROI1[0], ROI1[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 0, 0),
        2,
    )
    cv2.rectangle(frame, (ROI2[0], ROI2[1]), (ROI2[2], ROI2[3]), (255, 0, 0), 2)
    cv2.putText(
        frame,
        f"Road 2",
        (ROI2[0], ROI2[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 0, 0),
        2,
    )

    # Display vehicle counts and densities
    cv2.putText(
        frame,
        f"Road 1 Vehicles: {road1_vehicles} (Dens: {density1:.4f})",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
    )
    cv2.putText(
        frame,
        f"Road 2 Vehicles: {road2_vehicles} (Dens: {density2:.4f})",
        (10, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
    )

    # Display traffic light status and dynamic green duration
    if traffic_light_state == 0:  # Road 1 Green, Road 2 Red
        cv2.putText(
            frame,
            "Road 1: GREEN",
            (10, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame, "Road 2: RED", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
        )
        remaining_time = dynamic_green_duration - time_since_last_switch
        cv2.putText(
            frame,
            f"Time Left: {max(0, int(remaining_time))}s",
            (10, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Green Duration: {dynamic_green_duration}s",
            (10, 230),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 128, 0),
            2,
        )
    else:  # Road 1 Red, Road 2 Green
        cv2.putText(
            frame, "Road 1: RED", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
        )
        cv2.putText(
            frame,
            "Road 2: GREEN",
            (10, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        remaining_time = dynamic_green_duration - time_since_last_switch
        cv2.putText(
            frame,
            f"Time Left: {max(0, int(remaining_time))}s",
            (10, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Green Duration: {dynamic_green_duration}s",
            (10, 230),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 128, 0),
            2,
        )

    cv2.imshow("Smart Traffic Management", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
