from pathlib import Path
import csv
import cv2
import numpy as np
import config
from .helpers import extract_keypoints_xy, normalize_coordinates, calculate_angle, draw_angle_arc

def infer_video_with_angles(model, video_path: str, pose: str, out_dir: Path, frame_callback=None, progress_callback=None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    video_path = str(video_path)
    name = Path(video_path).stem

    out_video = out_dir / f"PE_trained_{name}.mp4"
    kp_tsv    = out_dir / f"Keypoints_{name}.tsv"
    ang_tsv   = out_dir / f"Angles_{name}.tsv"

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")

    fps_val = cap.get(cv2.CAP_PROP_FPS)
    fps = int(fps_val) if fps_val else 30
    fw, fh = config.FIXED_RESOLUTION
    out = cv2.VideoWriter(str(out_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (fw, fh))

    frame_number = 0
    with open(kp_tsv, "w", newline="") as kpf, open(ang_tsv, "w", newline="") as anf:
        kp_writer = csv.writer(kpf, delimiter="\t")
        ang_writer = csv.writer(anf, delimiter="\t")

        kp_writer.writerow(["Frame", "Time"] + [f"{cat}_{axis}" for cat in config.CATEGORIES for axis in ["X","Y"]])
        ang_writer.writerow(["Frame", "Time", "R_Eye-Ear-Vertical", "R_Wrist-Elbow-Shoulder", "R_Hip-Knee-Ankle"])

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        from tqdm import tqdm  # type: ignore

        with tqdm(total=total_frames, desc=f"Inferring {name}") as pbar:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
    
                frame = cv2.resize(frame, (fw, fh))
                frame_number += 1
                t = float(frame_number) / float(fps)
                
                if progress_callback is not None:
                    progress_callback(frame_number, total_frames, pose)
    
                results = model(frame, verbose=False)
                if results and results[0].keypoints is not None:
                    kps_xy = extract_keypoints_xy(results[0].keypoints)
                else:
                    kps_xy = [[0,0]] * len(config.CATEGORIES)
    
                normalized = [normalize_coordinates(x, y, fw, fh) for x, y in kps_xy]
                flat = [v for xy in normalized for v in xy]
    
                # Extract base coords
                def get(name):
                    return kps_xy[config.CATEGORIES.index(name)]
    
                r_shoulder = get("R_Shoulder")
                r_elbow    = get("R_Elbow")
                r_wrist    = get("R_Wrist")
                r_ear      = get("R_Ear")
                r_eye      = get("R_Eye")
                r_hip      = get("R_Hip")
                r_knee     = get("R_Knee")
                r_ankle    = get("R_Ankle")
    
                vertical_sp = [r_ear[0], r_ear[1] + 100]  # pixel vertical ref
                a_neck  = calculate_angle(vertical_sp, r_ear, r_eye)
                a_elbow = calculate_angle(r_wrist, r_elbow, r_shoulder)
                a_knee  = calculate_angle(r_hip, r_knee, r_ankle)
    
                kp_writer.writerow([frame_number, round(t, 3)] + flat)
                ang_writer.writerow([frame_number, round(t, 3), a_neck, a_elbow, a_knee])
    
                annotated = frame.copy()
                if results and len(results[0].boxes) > 0:
                    box = results[0].boxes[0].xyxy[0].cpu().numpy()
                    conf = results[0].boxes[0].conf[0].cpu().numpy()
                    cv2.rectangle(annotated, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255, 0, 0), 2)
                    cv2.putText(annotated, f"person {conf:.2f}", (int(box[0]), int(box[1])-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                def draw_line(p1_name, p2_name, color):
                    p1, p2 = get(p1_name), get(p2_name)
                    if (p1[0] != 0 or p1[1] != 0) and (p2[0] != 0 or p2[1] != 0):
                        cv2.line(annotated, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 2)
                
                def draw_dot(p_name, color):
                    p = get(p_name)
                    if p[0] != 0 or p[1] != 0:
                        cv2.circle(annotated, (int(p[0]), int(p[1])), 5, color, -1)

                
                # ------ MODULAR POSE DRAWING ------
                if pose.lower() == "prone":
                    if results and results[0].keypoints is not None:
                        draw_line("R_Eye", "R_Ear", (0, 255, 0))
                        if r_ear[0] != 0 or r_ear[1] != 0:
                            cv2.line(annotated, (int(r_ear[0]), int(r_ear[1])), (int(vertical_sp[0]), int(vertical_sp[1])), (0, 215, 255), 2)
                        draw_line("R_Shoulder", "R_Elbow", (255, 0, 0))
                        draw_line("R_Elbow", "R_Wrist", (255, 0, 0))
                        draw_line("R_Shoulder", "R_Hip", (255, 0, 255))
                        draw_line("R_Hip", "R_Knee", (0, 165, 255))
                        draw_line("R_Knee", "R_Ankle", (0, 165, 255))
                        
                        for kp, color in [("R_Eye", (0,255,0)), ("R_Ear", (0,255,0)), 
                                          ("R_Shoulder", (0,215,255)), ("R_Elbow", (255,0,0)), ("R_Wrist", (255,0,0)),
                                          ("R_Hip", (255,0,255)), ("R_Knee", (0,165,255)), ("R_Ankle", (0,165,255))]:
                            draw_dot(kp, color)
                            
                        if r_ear[0] != 0 and r_eye[0] != 0:
                            draw_angle_arc(annotated, vertical_sp, r_ear, r_eye, a_neck, (255, 255, 255))
                        if r_shoulder[0] != 0 and r_elbow[0] != 0 and r_wrist[0] != 0:
                            draw_angle_arc(annotated, r_shoulder, r_elbow, r_wrist, a_elbow, (255, 255, 255))
                        if r_hip[0] != 0 and r_knee[0] != 0 and r_ankle[0] != 0:
                            draw_angle_arc(annotated, r_hip, r_knee, r_ankle, a_knee, (255, 255, 255))

                    cv2.putText(annotated, f"Neck:  {a_neck:.1f} deg", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                    cv2.putText(annotated, f"Elbow: {a_elbow:.1f} deg", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                    cv2.putText(annotated, f"Knee:  {a_knee:.1f} deg", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

                elif pose.lower() == "supine":
                    if results and results[0].keypoints is not None:
                        draw_line("R_Eye", "R_Ear", (0, 255, 0))
                        draw_line("R_Shoulder", "R_Elbow", (255, 0, 0))
                        draw_line("R_Elbow", "R_Wrist", (255, 0, 0))
                        draw_line("R_Shoulder", "R_Hip", (255, 0, 255))
                        draw_line("R_Hip", "R_Knee", (0, 165, 255))
                        draw_line("R_Knee", "R_Ankle", (0, 165, 255))
                        
                        for kp, color in [("R_Eye", (0,255,0)), ("R_Ear", (0,255,0)), 
                                          ("R_Shoulder", (0,215,255)), ("R_Elbow", (255,0,0)), ("R_Wrist", (255,0,0)),
                                          ("R_Hip", (255,0,255)), ("R_Knee", (0,165,255)), ("R_Ankle", (0,165,255))]:
                            draw_dot(kp, color)
                            
                        if r_shoulder[0] != 0 and r_elbow[0] != 0 and r_wrist[0] != 0:
                            draw_angle_arc(annotated, r_shoulder, r_elbow, r_wrist, a_elbow, (255, 255, 255))
                        if r_hip[0] != 0 and r_knee[0] != 0 and r_ankle[0] != 0:
                            draw_angle_arc(annotated, r_hip, r_knee, r_ankle, a_knee, (255, 255, 255))

                    cv2.putText(annotated, f"Elbow: {a_elbow:.1f} deg", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                    cv2.putText(annotated, f"Knee:  {a_knee:.1f} deg", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                elif pose.lower() == "sitting":
                    # TODO: Add custom sitting drawing here
                    pass

                out.write(annotated)
                if frame_callback is not None:
                    frame_callback(annotated)
                    
                pbar.update(1)

    cap.release()
    out.release()

    return {
        "video_out": str(out_video),
        "keypoints_tsv": str(kp_tsv),
        "angles_tsv": str(ang_tsv),
    }
