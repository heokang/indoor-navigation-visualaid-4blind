import torch
from matplotlib.path import Path
import cv2
import numpy as np
import pickle
# from walkinter.model_loader import model

def calculate_indoor_position(image_paths, polygon_points):
    print("Starting indoor position calculation...")
    print("loading yolo/calibration...")
    with open("C:/Users/ime/capstone/capstone/walkinter/objectdetectmodel/calibration_data_s21.pkl", 'rb') as f:
        calib_data = pickle.load(f)
    mtx = calib_data['mtx']
    dist = calib_data['dist']

    # Object heights in centimeters
    object_heights = {
        'exit': 20.5,
        'toiletsign': 21,
        'sign_du': 18.5,
        'sign_choi': 20,
        'sign_538': 18.5,
        'sign_empty': 18.5,
        'sign_seok': 20
    }

    detected_objects = []  # Redefined as a list to store detected objects and their distances

    # Detect objects in images and calculate distances
    print("Detecting objects in images and calculating distances...")
    for image_path in image_paths:
        print("Processing image:", image_path)
        image = cv2.imread(image_path)
        results = model(image)

        for *xyxy, conf, cls in results.xyxy[0]:
            class_name = model.names[int(cls)]
            if class_name in object_heights:
                known_height = object_heights[class_name]
                bbox_height = xyxy[3] - xyxy[1]
                focal_length_pixel = mtx[0, 0]
                distance_cm = (known_height * focal_length_pixel) / bbox_height
                distance_m = distance_cm / 100
                if isinstance(distance_m, torch.Tensor):
                    distance_m = distance_m.item()
                rounded_distance_m = round(distance_m, 2)

                detected_objects.append({'name': class_name, 'distance': rounded_distance_m})

    if not detected_objects:
        return {"success": False, "message": "No objects detected in any images."}

    # Function to find intersections between two circles
    def find_intersection(center1, radius1, center2, radius2):
        x0, y0 = center1
        x1, y1 = center2
        d = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
        if d > radius1 + radius2 or d < np.abs(radius1 - radius2) or d == 0:
            return None
        a = (radius1**2 - radius2**2 + d**2) / (2 * d)
        h = np.sqrt(abs(radius1**2 - a**2))
        x2 = x0 + a * (x1 - x0) / d
        y2 = y0 + a * (y1 - y0) / d
        x3 = x2 + h * (y1 - y0) / d
        y3 = y2 - h * (x1 - x0) / d
        x4 = x2 - h * (y1 - y0) / d
        y4 = y2 + h * (x1 - x0) / d
        return [(x3, y3), (x4, y4)]

    # Static object locations
    static_objects = {
        'exit': [(37.895, -3.88), (30.735, -1.23), (37.895, -22.26)],
        'toiletsign': [(32.37, -0.12)],
        'sign_seok': [(39.07, -7.13)],
        'sign_538': [(36.72, -10.62)],
        'sign_choi': [(25.45, 0)],
        'sign_empty': [(39.07, -10.15)],
        'sign_du': [(39.07, -19.07)],
        'sign_jung': [(39.07, -13.1)],
        'sign_jung2': [(22.85, 0)],
        'sign_yoon': [(27.65, 0)],
        'sign_chung': [(39.07, -3.8)],
        'sign_534': [(39.07, -15.05)]
    }

    # Floor plan vertex coordinates

    # Draw circles around detected objects and find intersections
    intersections = []
    all_circles = []

    for obj in detected_objects:
        obj_name = obj['name']
        obj_distance = obj['distance']
        if obj_name == 'exit':
            # Draw a circle around the detected exit
            for exit_point in static_objects['exit']:
                circle_center = exit_point
                circle_radius = obj_distance
                all_circles.append((circle_center, circle_radius))
        else:
            # Draw a circle around other detected objects
            for obj_center in static_objects[obj_name]:
                circle_center = obj_center
                circle_radius = obj_distance
                all_circles.append((circle_center, circle_radius))

    # Find intersections of all circles
    for i in range(len(all_circles)):
        for j in range(i+1, len(all_circles)):
            circle1_center, circle1_radius = all_circles[i]
            circle2_center, circle2_radius = all_circles[j]
            intersection_points = find_intersection(circle1_center, circle1_radius, circle2_center, circle2_radius)
            if intersection_points:
                intersections.extend(intersection_points)

    # 교차점이 없는 경우
    if not intersections:
        return {"success": False, "message": "No intersections found. Positioning failed."}

    # Filter out intersection points outside the floor plan polygon
    floor_plan_path = Path(polygon_points)
    filtered_intersections = [point for point in intersections if floor_plan_path.contains_point(point)]

    if len(filtered_intersections) > 0:
        # Find the circle with the smallest radius
        smallest_circle = min(all_circles, key=lambda x: x[1])
        smallest_circle_center = smallest_circle[0]

        # Find the closest intersection point to the smallest circle's center
        closest_intersection = min(filtered_intersections,
                                   key=lambda point: np.linalg.norm(np.array(point) - np.array(smallest_circle_center)))
    else:
        return {"success": False, "message": "No valid intersections within the floor plan."}

    # 성공적으로 위치를 계산한 경우
    return {"success": True, "Closest_intersection": closest_intersection, "message": "Positioning successful."}

    # Print valid intersection points and generated circles
    # print("Valid intersection points:", filtered_intersections)
    # print("Generated circles:", all_circles)