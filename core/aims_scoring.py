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
    prone   = [True, True] + [False]*9
    supine  = [True, True] + [False]*6
    sitting = [True] + [False]*6
    standing= [True] + [False]*2
    return AimsScores(prone, supine, sitting, standing)


def check_prone_prop(angles_df, scores: AimsScores):
    if "R_Eye-Ear-Vertical" not in angles_df.columns:
        return
    above_45 = angles_df["R_Eye-Ear-Vertical"] > 45
    count, max_count = 0, 0
    for value in above_45:
        count = count + 1 if value else 0
        max_count = max(max_count, count)
    scores.prone[2] = (max_count >= 90)

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
    neck_angle_high = angles_df["R_Eye-Ear-Vertical"] > 85
    condition = elbow_off_ground & neck_angle_high
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.prone[4] = (max_count >= 3 * fps)

def check_forearm_support_2(kps_df, angles_df, scores: AimsScores, fps=30):
    if not scores.prone[3]: return
    if "R_Elbow_X" not in kps_df or "R_Shoulder_X" not in kps_df or "R_Eye-Ear-Vertical" not in angles_df: return
    elbow_forward = kps_df["R_Elbow_X"] > kps_df["R_Shoulder_X"]
    head_angle_high = angles_df["R_Eye-Ear-Vertical"] > 60
    condition = elbow_forward & head_angle_high
    count, max_count = 0, 0
    for val in condition:
        count = count + 1 if val else 0
        max_count = max(max_count, count)
    scores.prone[5] = (max_count >= 3 * fps)


def score_all(keypoints_tsv_path: str, angles_tsv_path: str) -> AimsScores:
    scores = init_scores()

    try:
        import os
        if not os.path.exists(keypoints_tsv_path) or not os.path.exists(angles_tsv_path):
            return scores
            
        kps_df = pd.read_csv(keypoints_tsv_path, delimiter="\t")
        angles_df = pd.read_csv(angles_tsv_path, delimiter="\t")
        
        check_prone_prop(angles_df, scores)
        check_forearm_support_1(kps_df, scores)
        check_prone_mobility(kps_df, angles_df, scores)
        check_forearm_support_2(kps_df, angles_df, scores)
        
    except Exception as e:
        print(f"Scoring error: {e}")

    return scores
