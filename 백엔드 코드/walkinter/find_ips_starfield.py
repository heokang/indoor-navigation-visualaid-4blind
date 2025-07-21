import torch
import torchvision
from torchvision import transforms as T
from walkinter.model_load import model, device
from PIL import Image
import numpy as np
import cv2
import pickle
from matplotlib.path import Path

def calculate_indoor_position_star(image_paths):
    print('Calculating indoor position in starfield...')
    print('loading R-Cnn/calibration ... ')
    # Load calibration data
    with open("C:/Users/ime/capstone/capstone/walkinter/objectdetectmodel/calibration_data_s21.pkl", 'rb') as f:
        calib_data = pickle.load(f)
    mtx = calib_data['mtx']
    dist = calib_data['dist']
    def correct_image_rotation(image):
        try:
            exif = image.getexif()
            if exif is not None:
                orientation = exif.get(274)
                if orientation == 3:
                    image = image.rotate(180, expand=True)
                elif orientation == 6:
                    image = image.rotate(270, expand=True)
                elif orientation == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass
        return image

    # Preprocess image
    def preprocess(image_path):
        image = Image.open(image_path).convert("RGB")
        image = correct_image_rotation(image)
        transform = T.Compose([T.ToTensor()])
        tensor_image = transform(image).unsqueeze(0).to(device)
        return tensor_image

    # Get the four corners of the minimum bounding rectangle
    def get_four_corners(contour):
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.intp(box)  # Use np.intp instead of np.int0
        return box

    # Calculate the minimum x distance between two points
    def calculate_min_x_distance(corners):
        sorted_corners = sorted(corners, key=lambda x: x[0])
        point1, point2 = sorted_corners[:2]
        distance = np.linalg.norm(point1 - point2)
        return distance, point1, point2

    # Plot results and estimate distances
    def plot_results(image, outputs, mtx, dist):

        boxes = outputs[0]['boxes'].cpu().detach().numpy()
        labels = outputs[0]['labels'].cpu().detach().numpy()
        scores = outputs[0]['scores'].cpu().detach().numpy()
        masks = outputs[0]['masks'].cpu().detach().numpy()

        detected_objects = []

        for box, label, score, mask in zip(boxes, labels, scores, masks):
            if score > 0.5:  # 신뢰도가 0.5 이상인 경우만 표시
                class_name = list(object_heights.keys())[label - 1]
                mask = mask[0]  # 첫 번째 채널의 마스크 사용
                contours, _ = cv2.findContours((mask > 0.5).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    # 폴리곤의 4개 끝점 찾기
                    corners = get_four_corners(contour)

                    # x좌표가 가장 작은 두 점의 거리 계산
                    min_x_distance, point1, point2 = calculate_min_x_distance(corners)

                    # 폴리곤 중심 계산
                    centroid = np.mean(contour, axis=0).reshape(-1)
                    bbox_center_x = centroid[0]
                    bbox_center_y = centroid[1]

                    # 카메라 좌표로 변환 (왜곡 보정 포함)
                    bbox_center_undistorted = cv2.undistortPoints(
                        np.array([[[bbox_center_x, bbox_center_y]]]), mtx, dist, None, mtx)

                    bbox_center_x = bbox_center_undistorted[0, 0, 0]
                    bbox_center_y = bbox_center_undistorted[0, 0, 1]

                    # 거리 추정 (삼각법 사용)
                    focal_length_pixel = mtx[0, 0]
                    known_height = object_heights[class_name]
                    distance_cm = (known_height * focal_length_pixel) / min_x_distance
                    distance_m = distance_cm / 100

                    detected_objects.append({'name': class_name, 'distance': distance_m})

        return detected_objects

    # Define the object heights
    object_heights = {
        'aquafield': 47,
        'columbia': 53.3,
        '8seconds': 47,
        'descente': 67.5,
        'salomon': 115,
        'sekanskeen': 24.8,
        'phiten': 43.8,
        'le_coq_sportif': 31.8,
        'kary_market': 103.5,
        'north_face': 47,
        'shinsegae': 40,
        'smoothie_king': 34.2,
        'adidas': 160,
        'moimoln': 38.9,
        'boldest': 44,
        'oakley': 34,
        'aqua': 44,
        'new_balance': 41,
        'blackyak': 104,
        'black_diamond': 37.6,
        'capten': 45,
        'i_love_j': 42,
        'toe_box': 80,
        'balloons': 50,
        'milky': 57,
        'new_balance_kids': 90,
    }

    # Define polygons
    outer_polygon = [(0, 36.5), (16.2, 26.6), (23.3, 26.6), (39.5, 35.8), (97.0, 35.8), (115.2, 29.9), (122.8, 29.9),
                     (135.8, 35.6), (147.6, 35.6), (147.6, 52.5), (141, 52.5), (120, 58), (109, 58), (88.4, 52.5),
                     (36.8, 52.5), (26, 58), (9, 58), (1.2, 51.7), (0, 51.7)]

    # Define the coordinates for the inner exclusion polygons
    exclusion_polygons = [
        [(5, 40.2), (6.3, 38.2), (18, 32.4), (22.3, 32.4), (36.4, 40.8), (37.3, 42.8), (37.3, 44.6),
         (36.5, 45.9), (31.6, 49.1), (8.9, 49.1)],
        [(43.8, 41.7), (45, 40.4), (60.7, 40.4), (61.7, 41.4), (61.7, 47), (60.6, 48), (48.1, 48), (43.8, 43.2)],
        [(65.2, 41.2), (66.1, 40.4), (79.7, 40.4), (84.1, 45.1), (84.1, 46.7), (82.7, 47.8), (66.1, 47.8), (65.2, 47)],
        [(97, 45), (97.9, 43.2), (117.9, 36.5), (117.9, 35.6), (127.2, 35.6), (138.2, 41.1), (139.4, 43.1),
         (139.4, 44.7), (138.4, 46.5), (121.2, 52), (109.3, 52), (98.8, 49.5), (97, 47.7)],
        [(9.8, 50), (20.7, 50), (20.7, 52.8), (9.8, 52.8)],
        [(98.4, 39.8), (109.8, 35.6), (110.8, 38), (99.4, 42.1)]
    ]

    outer_polygon_path = Path(outer_polygon)
    exclusion_polygon_paths = [Path(polygon) for polygon in exclusion_polygons]

    # Function to check if a point is valid
    def is_valid_point(point):
        if not outer_polygon_path.contains_point(point):
            return False
        for exclusion_path in exclusion_polygon_paths:
            if exclusion_path.contains_point(point):
                return False
        return True

    # Static objects positions (X, Y) in meters
    static_objects = {
        'salomon': [(8.5, 57.5)],
        'phiten': [(17.5, 58)],
        'descente': [(25, 58)],
        'adidas': [(43, 52.5)],
        'aquafield': [(55, 52.5)],
        'aqua': [(64.5, 52.5)],
        'sekanskeen': [(71.5, 52.5)],
        'moimoln': [(78, 52.5)],
        'kary_market': [(82, 52.5)],
        'aunntieannes': [(91, 53)],
        'capten': [(97, 54.8)],
        'toe_box': [(104, 56.66)],
        'bene_bene': [(110.7, 58)],
        'kangol_kids': [(116.2, 58)],
        'playkiz': [(121, 57.7)],
        'mlb': [(125.8, 56.5)],
        'agabang': [(13.5, 54.5)],
        'new_balance_kids': [(143, 52.5)],
        'balloons': [(143, 35.5)],
        'milky': [(135.8, 35.6)],
        'weeny_beeny': [(130.6, 33.3)],
        'toy_kingdom': [(113, 32.2)],
        'i_love_j': [(101, 34.5)],
        'laughing_child': [(92.3, 35.8)],
        'north_face': [(77, 35.8)],
        'black_yak': [(73, 35.8)],
        'black_diamond': [(60.2, 35.8)],
        'columbia': [(51.7, 35.8)],
        'boldest': [(46.5, 35.8)],
        'oakley': [(39, 35)],
        '8seconds': [(36, 33.8)],
        'new_balance': [(20, 26.6)],
        'le_coq_sportif': [(10.5, 30.1)],
        'smoothie_king': [(4.5, 33.75)]
    }

    # Find intersections of two circles
    def find_intersection(center1, radius1, center2, radius2):
        x0, y0 = center1
        x1, y1 = center2
        d = np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        if d > radius1 + radius2 or d < np.abs(radius1 - radius2) or d == 0:
            return None
        a = (radius1 ** 2 - radius2 ** 2 + d ** 2) / (2 * d)
        h = np.sqrt(abs(radius1 ** 2 - a ** 2))
        x2 = x0 + a * (x1 - x0) / d
        y2 = y0 + a * (y1 - y0) / d
        x3 = x2 + h * (y1 - y0) / d
        y3 = y2 - h * (x1 - x0) / d
        x4 = x2 - h * (y1 - y0) / d
        y4 = y2 + h * (x1 - x0) / d
        return [(x3, y3), (x4, y4)]

    # # Detect objects and estimate distances
    detected_objects = []

    def detect_objects(image):
        with torch.no_grad():
            outputs = model(image)
        return outputs

    for image_path in image_paths:
        image = preprocess(image_path)
        outputs = detect_objects(image)
        detected_objects.extend(plot_results(image[0], outputs, mtx, dist))

    # Sort detected objects by distance
    detected_objects.sort(key=lambda x: x['distance'])

    # Get closest objects
    closest_objects = detected_objects[:3]

    # Store all circles (center and radius)
    all_circles = []

    # Create circles for closest objects and avoid duplicates
    added_objects = set()
    for obj in closest_objects:
        obj_name = obj['name']
        obj_distance = obj['distance']
        if obj_name in static_objects and obj_name not in added_objects:
            for obj_center in static_objects[obj_name]:
                circle_center = obj_center
                circle_radius = obj_distance
                all_circles.append((circle_center, circle_radius))
                added_objects.add(obj_name)

    # Store intersections
    intersections = []

    for i in range(len(all_circles)):
        for j in range(i + 1, len(all_circles)):
            circle1_center, circle1_radius = all_circles[i]
            circle2_center, circle2_radius = all_circles[j]
            intersection_points = find_intersection(circle1_center, circle1_radius, circle2_center, circle2_radius)
            if intersection_points:
                valid_intersections = [point for point in intersection_points if is_valid_point(point)]
                intersections.extend(valid_intersections)

    # Filter intersections within the floor plan
    filtered_intersections = [point for point in intersections if is_valid_point(point)]

    # Calculate the average of filtered_intersections
    if filtered_intersections:
        avg_x = np.mean([point[0] for point in filtered_intersections])
        avg_y = np.mean([point[1] for point in filtered_intersections])
        validation_intersection = (avg_x, avg_y)
    else:
        validation_intersection = None
        return {"success": False, "message": "No valid intersections within the floor plan."}

        # 성공적으로 위치를 계산한 경우
    return {"success": True, "Closest_valid_intersection": validation_intersection, "message": "Positioning successful."}

