import os
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd


@dataclass
class AimsScores:
    prone: List[bool]
    supine: List[bool]
    sitting: List[bool]
    standing: List[bool]

    def total(self) -> int:
        return sum(map(int, self.prone + self.supine + self.sitting + self.standing))

def init_scores() -> AimsScores:
    # Prone has 21 tasks
    prone   = [True, True] + [False]*19
    supine  = [True, True] + [False]*6
    sitting = [True] + [False]*6
    standing= [True] + [False]*2
    return AimsScores(prone, supine, sitting, standing)


def check_prone_prop(angles_df, scores: AimsScores, fps=30):
    if "R_Eye-Ear-Vertical" not in angles_df.columns:
        return
    above_45 = angles_df["R_Eye-Ear-Vertical"] > 45
    count, max_count = 0, 0
    for value in above_45:
        count = count + 1 if value else 0
        max_count = max(max_count, count)
    scores.prone[2] = (max_count >= 3 * fps)

def check_forearm_support_1(kps_df, scores: AimsScores, fps=30):
    if not scores.prone[2]: return
    if "R_Elbow_X" not in kps_df or "R_Shoulder_X" not in kps_df: return
    condition = kps_df["R_Elbow_X"] >= kps_df["R_Shoulder_X"]
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.prone[3] = (max_count >= 3 * fps)

def check_prone_mobility(kps_df, angles_df, scores: AimsScores, fps=30):
    if not scores.prone[2]: return
    req1 = ["R_Elbow_Y", "R_Knee_Y"]
    if any(c not in kps_df.columns for c in req1) or "R_Eye-Ear-Vertical" not in angles_df: return
    elbow_off_ground = kps_df["R_Elbow_Y"] < (kps_df["R_Knee_Y"] - 3)
    neck_angle_high = angles_df["R_Eye-Ear-Vertical"] >= 90
    condition = elbow_off_ground & neck_angle_high
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.prone[4] = (max_count >= 3 * fps)

def check_forearm_support_2(kps_df, angles_df, scores: AimsScores, fps=30):
    if not scores.prone[3]: return
    required = ["R_Elbow_X", "R_Shoulder_X"]
    if any(c not in kps_df.columns for c in required): return
    if "R_Chin_Angle" not in angles_df: return
    
    elbow_forward = kps_df["R_Elbow_X"] > kps_df["R_Shoulder_X"]
    chin_tuck = angles_df["R_Chin_Angle"] < 90
    
    condition = elbow_forward & chin_tuck
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.prone[5] = (max_count >= 3 * fps)

def check_extended_arm_support(kps_df, angles_df, scores: AimsScores, fps=30):
    if not scores.prone[3]: return
    required_kps = ["R_Elbow_X", "R_Shoulder_X"]
    required_angs = ["R_Wrist-Elbow-Shoulder", "R_Chin_Angle"]
    if any(c not in kps_df.columns for c in required_kps) or any(c not in angles_df.columns for c in required_angs): return

    elbow_forward = kps_df["R_Elbow_X"] > kps_df["R_Shoulder_X"]
    arms_extended = angles_df["R_Wrist-Elbow-Shoulder"] > 155
    chin_tuck = angles_df["R_Chin_Angle"] < 90
    
    condition = elbow_forward & arms_extended & chin_tuck
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.prone[6] = (max_count >= 3 * fps)


def check_supine_lying_3(kps_df, scores: AimsScores, fps=30):
    # Baseline for Supine 3: Baby is supine but does not yet reach hands to midline.
    # We grant this if they are in frame and lying on back. Since the video is classified as supine,
    # we just ensure keypoints are present and they maintain posture for 3 seconds.
    if "R_Shoulder_Y" not in kps_df.columns: return
    
    condition = kps_df["R_Shoulder_Y"] > 0
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    # AIMS item 3 is at index 2 (1-based: 1, 2, 3 -> index 0, 1, 2)
    scores.supine[2] = (max_count >= 3 * fps)

def check_supine_lying_4(kps_df, angles_df, scores: AimsScores, fps=30):
    if not scores.supine[2]: return
    required_kps = ["R_Shoulder_X", "R_Shoulder_Y", "R_Hip_X", "R_Wrist_X", "R_Wrist_Y"]
    if any(c not in kps_df.columns for c in required_kps) or "R_Chin_Angle" not in angles_df.columns: return
    
    # Hands lifted: Wrist Y is higher (smaller value) than Shoulder Y
    hands_lifted = kps_df["R_Wrist_Y"] < (kps_df["R_Shoulder_Y"] - 2)
    
    # Hands midline: Wrist X is between Shoulder X and Hip X
    min_x = kps_df[["R_Shoulder_X", "R_Hip_X"]].min(axis=1)
    max_x = kps_df[["R_Shoulder_X", "R_Hip_X"]].max(axis=1)
    hands_midline = (kps_df["R_Wrist_X"] >= min_x) & (kps_df["R_Wrist_X"] <= max_x)
                    
    # Chin tuck
    chin_tuck = angles_df["R_Chin_Angle"] < 100
    
    condition = hands_lifted & hands_midline & chin_tuck
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.supine[3] = (max_count >= 3 * fps)

def check_supine_hands_to_knees(kps_df, angles_df, scores: AimsScores, fps=30):
    if not scores.supine[3]: return
    required_kps = ["R_Wrist_X", "R_Wrist_Y", "R_Knee_X", "R_Knee_Y", "R_Hip_Y"]
    if any(c not in kps_df.columns for c in required_kps) or "R_Chin_Angle" not in angles_df.columns: return
    
    # Euclidean distance between Wrist and Knee. (Assuming 0-100 normalized coords, ~10 means 10%)
    dist = ((kps_df["R_Wrist_X"] - kps_df["R_Knee_X"])**2 + (kps_df["R_Wrist_Y"] - kps_df["R_Knee_Y"])**2)**0.5
    hands_near_knees = dist < 20.0
    
    # Knees flexed and elevated off ground (Y_knee < Y_hip)
    knee_elevated = kps_df["R_Knee_Y"] < kps_df["R_Hip_Y"]
    
    # Chin tuck
    chin_tuck = angles_df["R_Chin_Angle"] < 100
    
    condition = hands_near_knees & knee_elevated & chin_tuck
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.supine[4] = (max_count >= 3 * fps)

def check_supine_active_extension(kps_df, angles_df, scores: AimsScores, fps=30):
    # Active extension often follows or is concurrent with hands-to-knees era, check independently of hands_to_knees
    if not scores.supine[3]: return 
    
    req_angs = ["R_Chin_Angle", "R_Hip-Knee-Ankle"]
    if any(c not in angles_df.columns for c in req_angs): return
    
    # Neck hyperextension (thrown back) -> opposite of chin tuck
    neck_hyper = angles_df["R_Chin_Angle"] > 110
    
    # Leg extended (pushing against surface)
    leg_extended = angles_df["R_Hip-Knee-Ankle"] > 150
    
    condition = neck_hyper & leg_extended
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.supine[5] = (max_count >= 3 * fps)

def score_all(keypoints_tsv_path: str, angles_tsv_path: str, pose: str = "Prone") -> AimsScores:
    scores = init_scores()

    try:
        if not os.path.exists(keypoints_tsv_path) or not os.path.exists(angles_tsv_path):
            return scores
            
        kps_df = pd.read_csv(keypoints_tsv_path, delimiter="\t")
        angles_df = pd.read_csv(angles_tsv_path, delimiter="\t")
        
        # Assume 30fps if not detectable from metadata (handled in score_all if we had tsv with fps info)
        fps = 30 
        
        if pose.lower() == "prone":
            check_prone_prop(angles_df, scores, fps)
            check_forearm_support_1(kps_df, scores, fps)
            check_prone_mobility(kps_df, angles_df, scores, fps)
            check_forearm_support_2(kps_df, angles_df, scores, fps)
            check_extended_arm_support(kps_df, angles_df, scores, fps)
        elif pose.lower() == "supine":
            check_supine_lying_3(kps_df, scores, fps)
            check_supine_lying_4(kps_df, angles_df, scores, fps)
            check_supine_hands_to_knees(kps_df, angles_df, scores, fps)
            check_supine_active_extension(kps_df, angles_df, scores, fps)
            
    except Exception as e:
        print(f"Scoring error: {e}")

    return scores
