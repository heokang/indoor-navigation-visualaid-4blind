from matplotlib.path import Path
import numpy as np
import heapq

# Floor plan vertex coordinates -> consumers.py에서 지정함
# polygon_points = np.array([(0, 0), (0,  -2.46), (36.72, -2.46), (36.72, -23.97), (39.07, -23.97), (39.07, 0)])

# Define the function to create a grid overlay on the polygon
def create_grid_for_polygon(polygon_vertices, grid_size=1):
    """
    Creates a grid overlay on a polygon specified by its vertices.

    Parameters:
    - polygon_vertices: A NumPy array of the polygon's vertex coordinates.
    - grid_size: The size of the grid (1m x 1m by default).

    Returns:
    - A list of grid points (x, y) that lie within the polygon.
    """
    # Determine the bounds of the polygon
    min_x, min_y = np.min(polygon_vertices, axis=0)
    max_x, max_y = np.max(polygon_vertices, axis=0)

    # Create the grid points
    grid_points = []
    for x in np.arange(min_x, max_x, grid_size):
        for y in np.arange(min_y, max_y, grid_size):
            grid_points.append((x, y))

    # Filter grid points to keep only those inside the polygon
    path = Path(polygon_vertices)
    inside_points = [point for point in grid_points if path.contains_point(point)]

    return inside_points

def heuristic(a, b):
    """
    휴리스틱 함수: 두 점 사이의 거리를 계산합니다.
    """
    return np.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


def astar(start, goal, neighbors, direction_penalty=10):
    open_set = []
    heapq.heappush(open_set, (0 + heuristic(start, goal), 0, start, None))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    last_direction = {start: None}

    while open_set:
        current = heapq.heappop(open_set)
        current_position = current[2]
        current_direction = current[3]

        if current_position == goal:
            path = []
            while current_position in came_from:
                path.append(current_position)
                current_position = came_from[current_position]
            return path[::-1]

        for neighbor in neighbors[current_position]:
            direction = (neighbor[0] - current_position[0], neighbor[1] - current_position[1])
            tentative_g_score = g_score[current_position] + heuristic(current_position, neighbor)
            if current_direction and direction != current_direction:
                tentative_g_score += direction_penalty

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current_position
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], heuristic(neighbor, goal), neighbor, direction))
                last_direction[neighbor] = direction

    return []


# 기존 A* 알고리즘 오류 나면 사용할 것.
# def astar(start, goal, neighbors):
#     """
#     A* 알고리즘: 시작점부터 목표점까지의 최단 경로를 찾습니다.
#     """
#     open_set = []
#     heapq.heappush(open_set, (0 + heuristic(start, goal), 0, start))
#     came_from = {}
#     g_score = {start: 0}
#     f_score = {start: heuristic(start, goal)}
#
#     while open_set:
#         current = heapq.heappop(open_set)[2]
#
#         if current == goal:
#             path = []
#             while current in came_from:
#                 path.append(current)
#                 current = came_from[current]
#             return path[::-1]  # 경로를 역순으로 반환합니다.
#
#         for neighbor in neighbors[current]:
#             tentative_g_score = g_score[current] + heuristic(current, neighbor)
#             if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
#                 came_from[neighbor] = current
#                 g_score[neighbor] = tentative_g_score
#                 f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
#                 if neighbor not in [i[2] for i in open_set]:
#                     heapq.heappush(open_set, (f_score[neighbor], heuristic(neighbor, goal), neighbor))
#     return []

def generate_grid_and_neighbors(path):
    """
    그리드 노드와 이웃을 생성합니다.
    """
    xmin, ymin, xmax, ymax = path.get_extents().bounds
    neighbors = {}

    for x in np.arange(np.floor(xmin), np.ceil(xmax)+1, 1):
        for y in np.arange(np.floor(ymin), np.ceil(ymax)+1, 1):
            point = (x, y)
            if path.contains_point(point):
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # 4방향
                    neighbor = (x + dx, y + dy)
                    if path.contains_point(neighbor):
                        if point not in neighbors:
                            neighbors[point] = []
                        neighbors[point].append(neighbor)

    return neighbors

def adjust_to_nearest_grid_point(point, path):
    """
    가장 가까운 그리드 노드로 좌표를 조정합니다.
    """
    adjusted_point = (round(point[0]), round(point[1]))
    if path.contains_point(adjusted_point):
        return adjusted_point
    else:
        return point

