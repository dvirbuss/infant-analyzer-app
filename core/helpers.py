import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
import config
import cv2

def normalize_coordinates(x, y, frame_width, frame_height):
    return round((x / frame_width) * 100, 2), round((y / frame_height) * 100, 2)

def extract_keypoints_xy(keypoints_object):
    if keypoints_object is None or len(keypoints_object.xy) == 0:
        return [[0, 0]] * len(config.CATEGORIES)
    return keypoints_object.xy.cpu().numpy()[0]

def to_str_list(bool_list):
    return ["1" if val else "0" for val in bool_list]

def calculate_angle(p1, p2, p3):
    a, b, c = map(np.array, (p1, p2, p3))
    ab, cb = a - b, c - b
    if np.linalg.norm(ab) == 0 or np.linalg.norm(cb) == 0:
        return 0.0
    cosang = np.dot(ab, cb) / (np.linalg.norm(ab) * np.linalg.norm(cb))
    return round(np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0))), 2)

def create_curve(x_points, y_points, months):
    return np.interp(months, x_points, y_points)

def knn_impute_keypoints_tsv(tsv_path, n_neighbors=5, threshold=0.6):
    df = pd.read_csv(tsv_path, delimiter="\t")
    df_copy = df.copy()
    keypoint_cols = df.columns[2:]
    df_copy[keypoint_cols] = df_copy[keypoint_cols].replace(0, np.nan)

    missing_ratio = df_copy[keypoint_cols].isna().mean()
    for col in keypoint_cols:
        if missing_ratio[col] > threshold:
            df_copy[col] = 0

    imputer = KNNImputer(n_neighbors=n_neighbors)
    df_copy[keypoint_cols] = imputer.fit_transform(df_copy[keypoint_cols])
    df_copy[keypoint_cols] = df_copy[keypoint_cols].round(2)
    df_copy.to_csv(tsv_path, sep="\t", index=False)

def draw_angle_arc(frame, p1, p2, p3, angle, color, radius=20, arc_text_offset=(10, -10)):
    """
    Draw an arc at point p2 formed by points p1-p2-p3 and print the angle value.
    p1, p2, p3: (x,y) in pixels (NOT normalized %)
    """
    a = np.array(p1, dtype=float)
    b = np.array(p2, dtype=float)
    c = np.array(p3, dtype=float)

    thickness = 2
    start_angle = np.degrees(np.arctan2(a[1] - b[1], a[0] - b[0]))
    end_angle   = np.degrees(np.arctan2(c[1] - b[1], c[0] - b[0]))

    # keep arc direction stable
    if start_angle > end_angle:
        start_angle, end_angle = end_angle, start_angle

    cv2.ellipse(
        frame,
        center=(int(b[0]), int(b[1])),
        axes=(radius, radius),
        angle=0,
        startAngle=start_angle,
        endAngle=end_angle,
        color=color,
        thickness=thickness,
    )

    tx = int(b[0] + arc_text_offset[0])
    ty = int(b[1] + arc_text_offset[1])
    cv2.putText(
        frame,
        f"{int(angle)}",
        (tx, ty),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )