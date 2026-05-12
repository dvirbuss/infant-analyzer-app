import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os
import sys

# Ensure the current directory is in sys.path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from excel_utils import format_data_sheets, format_analytics_sheet

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
    
    # Save to Exams_score_eval folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "Exams_score_eval")
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = os.path.join(output_dir, f"prone_eval_{timestamp}.xlsx")
    
    # Save to Excel
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        import excel_config as conf
        from excel_utils import format_data_sheets, format_analytics_sheet
        
        gt_filtered.to_excel(writer, sheet_name=conf.SHEET_GT, index=False)
        pred_df.to_excel(writer, sheet_name=conf.SHEET_PRED, index=False)
        analytics_df.to_excel(writer, sheet_name=conf.SHEET_ANALYTICS, index=False)
        
        # Apply custom formatting
        format_data_sheets(writer, [conf.SHEET_GT, conf.SHEET_PRED])
        format_analytics_sheet(writer, conf.SHEET_ANALYTICS, gt_filtered, pred_df)
        
    print(f"Evaluation report generated successfully: {output_filename}")
    return output_filename

def run_prone_model_for_eval(video_path: str) -> list:
    """
    Runs the prone model on a specific video and returns the scores array.
    Uses a temporary directory so artifacts are discarded.
    Uses tqdm to show progress.
    """
    import tempfile
    import config
    from ultralytics import YOLO
    from tqdm import tqdm
    from pathlib import Path
    
    from core.video_ops import save_first_frame_keypoints
    from core.pose_infer import infer_video_with_angles
    from core.helpers import knn_impute_keypoints_tsv
    from core.aims_scoring import score_all
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
        
    model = YOLO(config.PRONE_MODEL_PATH)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir)
        pbar = tqdm(total=100, desc=f"Evaluating {os.path.basename(video_path)}")
        
        def update_progress(current_frame, total_frames):
            if total_frames > 0:
                progress = (current_frame / total_frames) * 100
                pbar.update(progress - pbar.n)
                
        save_first_frame_keypoints(model, video_path)
        artifacts = infer_video_with_angles(
            model=model, 
            video_path=video_path, 
            pose="Prone",
            out_dir=out_dir, 
            progress_callback=update_progress
        )
        
        knn_impute_keypoints_tsv(artifacts["keypoints_tsv"])
        scores = score_all(artifacts["keypoints_tsv"], artifacts["angles_tsv"], "Prone")
        
        pbar.close()
        return scores.prone

def cast_array_to_dict(prone_scores_array: list) -> dict:
    """
    Casts the 21-element boolean prone scores array into a dictionary mapping 
    task names to their evaluation values (0 or 1).
    """
    # Initialize the 21 prone task names
    # Using generic names for tasks beyond the 7 we actively score right now
    tasks = [f"Prone Task {i+1}" for i in range(21)]
    
    # Override with specific names for the tasks we know
    tasks[0] = "Prone Lying 1"
    tasks[1] = "Prone Lying 2"
    tasks[2] = "Prone Prop"
    tasks[3] = "Forearm Support 1"
    tasks[4] = "Prone Mobility"
    tasks[5] = "Forearm Support 2"
    tasks[6] = "Extended Arm Support"
    
    # Cast to int (True -> 1, False -> 0)
    return {task: int(score) for task, score in zip(tasks, prone_scores_array)}

if __name__ == "__main__":
    tested_videos = [
        "prone_video_11", 
        "prone_video_13"
    ]
    
    # Evaluation output can be a dictionary mapping video names to task predictions
    evaluation_output = {
    "prone_video_11": {
        "Prone Lying 1": 1, 
        "Prone Lying 2": 0, 
        "Prone Prop": 1,
        "Forearm Support 1": 1, 
        "Prone Mobility": 0,
        "Forearm Support 2": 1,
        "Extended Arm Support": 0,
        "Prone to Supine": 1
    },
    "prone_video_13": {
        "Prone Lying 1": 1, 
        "Prone Lying 2": 1, 
        "Prone Prop": 0,
        "Forearm Support 1": 0, 
        "Prone Mobility": 1,
        "Forearm Support 2": 0,
        "Extended Arm Support": 1,
        "Prone to Supine": 0
    }
}
    
    # Run the function
    create_eval_report(tested_videos, evaluation_output)
