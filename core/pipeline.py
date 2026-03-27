# core/pipeline.py
from __future__ import annotations

from pathlib import Path
import datetime as dt
from ultralytics import YOLO  # type: ignore

import config  # type: ignore
from core.video_ops import save_first_frame_keypoints  # type: ignore
from core.pose_infer import infer_video_with_angles  # type: ignore
from core.helpers import knn_impute_keypoints_tsv  # type: ignore
from core.aims_scoring import score_all, init_scores  # type: ignore
from core.reporting import build_reports  # type: ignore


# --------- lightweight model cache (core-safe, no streamlit import) ---------
_MODEL_CACHE: dict[str, YOLO] = {}


def load_model(model_path: Path) -> YOLO:
    key = str(model_path.resolve())
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = YOLO(str(model_path))
    return _MODEL_CACHE[key]


def process_single_video(pose: str, video_path: str, out_dir: Path, frame_callback=None, progress_callback=None) -> tuple:
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = {
        "Prone": config.PRONE_MODEL_PATH,
        "Supine": config.SUPINE_MODEL_PATH,
        "Sitting": config.PRONE_MODEL_PATH, #todo
    }.get(pose)

    if model_path is None:
        raise ValueError(f"Unsupported pose: {pose}")

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    model = load_model(Path(model_path))

    # 1) mirror if needed (in-place)
    save_first_frame_keypoints(model, video_path)

    # 2) inference -> artifacts
    artifacts = infer_video_with_angles(model=model, video_path=video_path, pose=pose,
        out_dir=out_dir, frame_callback=frame_callback, progress_callback=progress_callback
    )

    # 3) impute keypoints in-place
    knn_impute_keypoints_tsv(artifacts["keypoints_tsv"])

    # 4) scoring
    scores = score_all(artifacts["keypoints_tsv"], artifacts["angles_tsv"])
    
    return scores, artifacts


def run(pose: str, video_path: str, birthdate: dt.date, out_dir: Path, frame_callback=None, progress_callback=None) -> dict:
    """Legacy backward-compatible single-video runner."""
    scores, artifacts = process_single_video(pose, video_path, out_dir, frame_callback, progress_callback)

    baby_age_months = float(f"{((dt.date.today() - birthdate).days) / 30.44:.2f}")

    # FIX: Handle baby_score calculation safely
    if hasattr(scores, "total"):
        baby_score = scores.total()
    elif isinstance(scores, dict):
        keys = ["prone", "supine", "sitting", "standing"]
        baby_score = int(sum(sum(scores[k]) for k in keys if k in scores))
    else:
        baby_score = 0

    # 5) reports (include angles plot!)
    report_files = build_reports(
        baby_age_months=baby_age_months,
        baby_score=baby_score,
        scores=scores,
        out_dir=out_dir,
        angles_tsv_path=artifacts["angles_tsv"],
    )

    return {
        "pose": pose,
        "age_months": baby_age_months,
        "aims_score": baby_score,
        "scores": scores,
        "artifacts": artifacts,
        "reports": report_files,
    }


def process_full_exam(video_paths: dict[str, str], birthdate: dt.date, out_dir: Path, caller: str = "unknown", frame_callback=None, progress_callback=None) -> dict:
    """
    Process up to 3 videos (Prone, Supine, Sitting) jointly.
    video_paths: e.g. {"Prone": "path/to/prone.mp4", "Supine": ...}
    Combines the scores into one final report.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    all_artifacts = {}
    
    # Initialize an empty AimsScores object to accumulate the scores
    combined_scores = init_scores()
    
    stamp = dt.datetime.now().strftime("%d-%m-%y_%H-%M")

    for pose, path in video_paths.items():
        if not path or not Path(path).exists():
            continue
        
        video_name = Path(path).stem
        pose_out_dir = out_dir / f"{pose.lower()}_{video_name}_{stamp}_{caller}"
        scores, artifacts = process_single_video(pose, path, pose_out_dir, frame_callback, progress_callback)
        all_artifacts[pose] = artifacts
        
        # Merge scores
        if hasattr(combined_scores, pose.lower()) and hasattr(scores, pose.lower()):
            setattr(combined_scores, pose.lower(), getattr(scores, pose.lower()))

    baby_age_months = float(f"{float((dt.date.today() - birthdate).days) / 30.44:.2f}")

    if hasattr(combined_scores, "total"):
        baby_score = combined_scores.total()
    elif isinstance(combined_scores, dict):
        keys = ["prone", "supine", "sitting", "standing"]
        baby_score = int(sum(sum(combined_scores[k]) for k in keys if k in combined_scores))
    else:
        baby_score = 0

    report_files = build_reports(
        baby_age_months=baby_age_months,
        baby_score=baby_score,
        scores=combined_scores,
        out_dir=out_dir,
        angles_tsv_path=None, # Only plotting angles for specific videos in their subdirs
    )

    return {
        "age_months": baby_age_months,
        "aims_score": baby_score,
        "scores": combined_scores,
        "all_artifacts": all_artifacts,
        "reports": report_files,
    }
