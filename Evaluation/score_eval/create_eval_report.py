import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os
import sys
import tempfile
import shutil
from pathlib import Path
from tqdm import tqdm
from ultralytics import YOLO

# Ensure the current directory is in sys.path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add project root to sys.path to import config and core
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import excel_config as conf
from excel_utils import format_data_sheets, format_analytics_sheet
import config
from core.video_ops import save_first_frame_keypoints
from core.pose_infer import infer_video_with_angles
from core.helpers import knn_impute_keypoints_tsv
from core.aims_scoring import score_all

def create_eval_report(tested_videos, model_predictions, gt_file_path="prone_score_GT.xlsx"):
    """
    Creates an evaluation excel report for prone position.
    
    Args:
        tested_videos (list): A list of video names that were tested.
        model_predictions (dict or pd.DataFrame): The model predictions. 
            If dict: format {"video_name": {"task_name": 1, "task_name_2": 0, ...}}
            If DataFrame: should have 'video_name' column and task columns with 0/1 values.
        gt_file_path (str): Path to the ground truth excel file.
    """
    # If the path is just a filename, assume it's in the same directory as this script
    if not os.path.isabs(gt_file_path) and not os.path.dirname(gt_file_path):
        gt_file_path = os.path.join(os.path.dirname(__file__), gt_file_path)

    # Load GT
    if not os.path.exists(gt_file_path):
        raise FileNotFoundError(f"Ground truth file not found at {os.path.abspath(gt_file_path)}")
        
    gt_df = pd.read_excel(gt_file_path)
    
    # Filter GT for tested videos
    gt_filtered = gt_df[gt_df['video_name'].isin(tested_videos)].copy()
    
    # Process model predictions
    if isinstance(model_predictions, dict):
        # Convert dict to dataframe
        pred_records = []
        for vid in tested_videos:
            record = {'video_name': vid}
            if vid in model_predictions:
                record.update(model_predictions[vid])
            pred_records.append(record)
        pred_df = pd.DataFrame(pred_records)
    elif isinstance(model_predictions, pd.DataFrame):
        pred_df = model_predictions[model_predictions['video_name'].isin(tested_videos)].copy()
    else:
        raise ValueError("model_predictions must be a dict or a pandas DataFrame")

    # Ensure pred_df has the same columns as gt_filtered
    # We add missing columns with NaN and align
    for col in gt_filtered.columns:
        if col not in pred_df.columns:
            pred_df[col] = np.nan
            
    # Align rows based on video_name to ensure order is identical
    gt_filtered = gt_filtered.sort_values(by='video_name').reset_index(drop=True)
    pred_df = pred_df.sort_values(by='video_name').reset_index(drop=True)
    
    # Reorder columns to match GT exactly
    pred_df = pred_df[gt_filtered.columns]
    
    # We no longer calculate metrics in Python, we will let Excel handle it dynamically.
    analytics_df = pd.DataFrame({
        'accuracy': [0],
        'precision': [0],
        'recall': [0],
        'f1': [0]
    })
    
    # Generate timestamp for filename: dd-mm-yy_HH-MM
    timestamp = datetime.now().strftime("%d-%m-%y_%H-%M")
    
    # Determine filename prefix based on GT file
    prefix = "prone"
    if "supine" in gt_file_path.lower():
        prefix = "supine"
    elif "sitting" in gt_file_path.lower():
        prefix = "sitting"
    elif "standing" in gt_file_path.lower():
        prefix = "standing"
        
    # Save to Exams_score_eval folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "Exams_score_eval")
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = os.path.join(output_dir, f"{prefix}_eval_{timestamp}.xlsx")
    
    # Save to Excel
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        gt_filtered.to_excel(writer, sheet_name=conf.SHEET_GT, index=False)
        pred_df.to_excel(writer, sheet_name=conf.SHEET_PRED, index=False)
        analytics_df.to_excel(writer, sheet_name=conf.SHEET_ANALYTICS, index=False)
        
        # Apply custom formatting
        format_data_sheets(writer, [conf.SHEET_GT, conf.SHEET_PRED])
        format_analytics_sheet(writer, conf.SHEET_ANALYTICS, gt_filtered, pred_df)
        
    print(f"Evaluation report generated successfully: {output_filename}")
    return output_filename

def run_model_for_eval(video_path: str, pose: str = "Prone") -> list:
    """
    Runs the model on a specific video for a given pose and returns the scores array.
    Uses a temporary directory so artifacts are discarded.
    Uses tqdm to show progress.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
        
    model_path = config.PRONE_MODEL_PATH if pose.lower() == "prone" else config.SUPINE_MODEL_PATH
    model = YOLO(model_path)
    
    temp_dir = tempfile.mkdtemp()
    try:
        out_dir = Path(temp_dir)
        pbar = tqdm(total=100, desc=f"Evaluating {os.path.basename(video_path)} ({pose})")
        
        def update_progress(current_frame, total_frames, pose=pose):
            if total_frames > 0:
                progress = (current_frame / total_frames) * 100
                pbar.update(progress - pbar.n)
                
        save_first_frame_keypoints(model, video_path)
        artifacts = infer_video_with_angles(
            model=model, 
            video_path=video_path, 
            pose=pose,
            out_dir=out_dir, 
            progress_callback=update_progress
        )
        
        knn_impute_keypoints_tsv(artifacts["keypoints_tsv"])
        scores = score_all(artifacts["keypoints_tsv"], artifacts["angles_tsv"], pose)
        
        pbar.close()
        return getattr(scores, pose.lower())
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def cast_array_to_dict(scores_array: list, pose: str = "Prone") -> dict:
    """
    Casts the scores array into a dictionary mapping task names to evaluation values (0 or 1).
    """
    if pose.lower() == "prone":
        tasks = [
            'Prone Lying 1', 'Prone Lying 2', 'Prone Prop', 'Forearm Support 1', 
            'Prone Mobility', 'Forearm Support 2', 'Extended Arm Support', 
            'Rolling Prone to Supine Without Rotation', 'Swimming', 
            'Reaching from forearm support', 'Pivoting', 
            'Rolling Prone to Supine with Rotation', 'Four Point Kneeling 1', 
            'Propped Lying on Side', 'Reciprocal Crawling', 
            'Four Point Kneeling to Sitting or Half Sitting', 'Reciprocal Creeping 1', 
            'Reaching from Extended Arm support', 'Four Point Kneeling 2', 
            'Modified Four Point Kneeling', 'Reciprocal Creeping 2'
        ]
    else: # Supine
        tasks = [
            'Supine Lying 1', 'Supine Lying 2', 'Supine Lying 3', 'Supine Lying 4', 
            'Hands to Knees', 'Active Extension', 'Hands to Feet', 
            'Rolling Supine to Prone Without Rotation', 'Rolling Supine to Prone With Rotation'
        ]
    
    return {task: int(score) for task, score in zip(tasks, scores_array)}

if __name__ == "__main__":
    # Define video sets for Prone and Supine
    eval_tasks = {
        "Prone": ["prone_video_11"],
        "Supine": ["supine_video_20", "supine_video_21"] # Example supine videos
    }
    
    base_video_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos")
    
    for pose, video_list in eval_tasks.items():
        evaluation_output = {}
        gt_file = "prone_score_GT.xlsx" if pose == "Prone" else "supine_score_GT.xlsx"
        
        for video_name in video_list:
            video_path = os.path.join(base_video_dir, f"{video_name}.mp4")
            
            if not os.path.exists(video_path):
                print(f"Warning: Could not find {pose} video at {video_path}. Skipping.")
                continue
                
            try:
                print(f"\nRunning live {pose} evaluation for {video_name}...")
                scores_array = run_model_for_eval(video_path, pose=pose)
                evaluation_output[video_name] = cast_array_to_dict(scores_array, pose=pose)
                print(f"Successfully evaluated {video_name}")
            except Exception as e:
                print(f"Error evaluating {video_name}: {e}")

        if evaluation_output:
            print(f"Generating {pose} evaluation report...")
            create_eval_report(list(evaluation_output.keys()), evaluation_output, gt_file_path=gt_file)
        else:
            print(f"\nNo {pose} evaluations were successfully generated.")
