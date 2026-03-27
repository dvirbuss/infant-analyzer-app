import os
import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from fastapi.concurrency import run_in_threadpool

import config
from core.pipeline import process_full_exam

PROGRESS_STATE = {
    "status": "idle",
    "pose": "None",
    "pose_index": 0,
    "frame": 0,
    "total_frames": 100
}

def update_progress(frame, total, pose):
    PROGRESS_STATE["frame"] = frame
    PROGRESS_STATE["total_frames"] = total
    PROGRESS_STATE["pose"] = pose
    if pose.lower() == "prone": PROGRESS_STATE["pose_index"] = 1
    elif pose.lower() == "supine": PROGRESS_STATE["pose_index"] = 2
    elif pose.lower() == "sitting": PROGRESS_STATE["pose_index"] = 3


app = FastAPI(title="Infant Motor Development Analyzer API")

# Configuration for paths
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
OUTPUTS_DIR = config.VIDEOS_OUTPUT_DIR
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

@app.get("/progress")
def get_progress():
    return JSONResponse(content=PROGRESS_STATE)


@app.post("/analyze")
async def analyze_videos(
    birth_date: str = Form(...),
    prone: UploadFile = File(...),
    supine: UploadFile = File(...),
    sitting: UploadFile = File(...)
):
    try:
        # Parse birth date safely
        bdate = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        
        # Create output directory for this run
        stamp = datetime.datetime.now().strftime("%d-%m-%y_%H-%M")
        out_dir = OUTPUTS_DIR / f"Exam_{stamp}_fastapi"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        video_paths = {}
        for upload, pose in [(prone, "Prone"), (supine, "Supine"), (sitting, "Sitting")]:
            # Save uploaded file
            safe_name = upload.filename.replace(" ", "_") if upload.filename else f"{pose.lower()}.mp4"
            save_path = out_dir / safe_name
            with open(save_path, "wb") as buffer:
                buffer.write(await upload.read())
            video_paths[pose] = save_path

        PROGRESS_STATE["status"] = "processing"
        PROGRESS_STATE["pose_index"] = 0
        PROGRESS_STATE["frame"] = 0
        PROGRESS_STATE["total_frames"] = 100

        # Run unified pipeline in threadpool so the event loop is not blocked
        result = await run_in_threadpool(
            process_full_exam, video_paths, bdate, out_dir, "fastapi", None, update_progress
        )
        PROGRESS_STATE["status"] = "complete"
        
        # Format the paths for the frontend to access via the mounted /outputs URL
        # Result dict has: {'aims_score': X, 'reports': {'expert_plot': Path, 'parent_plot': Path}}
        reports_payload = {}
        if "reports" in result:
            reps = result["reports"]
            if "expert_plot" in reps:
                expert_path = Path(reps["expert_plot"])
                # Extract relative path to output dir
                rel_path = expert_path.relative_to(OUTPUTS_DIR)
                reports_payload["expert_plot_url"] = f"/outputs/{rel_path.as_posix()}"
            if "parent_plot" in reps:
                parent_path = Path(reps["parent_plot"])
                rel_path = parent_path.relative_to(OUTPUTS_DIR)
                reports_payload["parent_plot_url"] = f"/outputs/{rel_path.as_posix()}"
                
        return JSONResponse(content={
            "status": "success",
            "aims_score": result.get("aims_score", "N/A"),
            "reports": reports_payload
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": str(e)})

# Mount frontend directory for everything else
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    print("🚀 Starting modern custom Web App exactly on: http://127.0.0.1:8507")
    uvicorn.run("api:app", host="127.0.0.1", port=8507, reload=True)
