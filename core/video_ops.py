import os
import cv2
from ultralytics import YOLO
from .helpers import extract_keypoints_xy, normalize_coordinates
import config

def mirror_video(input_path, output_path):
    from pathlib import Path
    in_path = Path(input_path)
    out_path = Path(output_path)
    flag = False
    
    cap = cv2.VideoCapture(str(in_path))
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {in_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if in_path.resolve() == out_path.resolve():
        out_path = out_path.with_name(f"{out_path.stem}_tmp{out_path.suffix}")
        flag = True

    out = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(cv2.flip(frame, 1))
    cap.release()
    out.release()

    if flag:
        import os
        os.remove(str(in_path))
        os.rename(str(out_path), str(in_path))

def save_first_frame_keypoints(model, video_path):
    video_path = str(video_path)
    cap = cv2.VideoCapture(video_path)
    
    head_facing_right = None
    for _ in range(60):
        ret, frame = cap.read()
        if not ret: break
        
        results = model(frame, verbose=False)
        if results and results[0].keypoints is not None:
            kps_xy = extract_keypoints_xy(results[0].keypoints)
            nose = kps_xy[config.CATEGORIES.index("Nose")]
            r_ear = kps_xy[config.CATEGORIES.index("R_Ear")]
            l_ear = kps_xy[config.CATEGORIES.index("L_Ear")]
            
            # If we detect the nose cleanly
            if nose[0] > 0:
                # If nose is to the left of the left ear, baby is facing left (profile)
                if l_ear[0] > 0 and nose[0] < l_ear[0]:
                    head_facing_right = False
                    break
                # If nose is to the right of the right ear, baby is facing right
                if r_ear[0] > 0 and nose[0] > r_ear[0]:
                    head_facing_right = True
                    break
                    
    cap.release()

    if head_facing_right is False:
        mirror_video(video_path, video_path)
