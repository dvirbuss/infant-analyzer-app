import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1] / "infant-analyzer-app-1"

# Direct paths to your assets
ASSETS_DIR = BASE_DIR / "assets"

# Icons
PRONE_ICON   = ASSETS_DIR / "infant_prone.png"
SITTING_ICON = ASSETS_DIR / "infant_sitting.png"
SUPINE_ICON  = ASSETS_DIR / "infant_supine.png"

FIXED_RESOLUTION = (640, 480)

CATEGORIES = [
    "Nose", "L_Eye", "R_Eye", "L_Ear", "R_Ear",
    "L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow",
    "L_Wrist", "R_Wrist", "L_Hip", "R_Hip",
    "L_Knee", "R_Knee", "L_Ankle", "R_Ankle"
]

PRONE_SCORE_TEMPLATE   = [True, True] + [False] * 9
SUPINE_SCORE_TEMPLATE  = [True, True] + [False] * 6
SITTING_SCORE_TEMPLATE = [True] + [False] * 6
STANDING_SCORE_TEMPLATE= [True] + [False] * 2

PRONE_MODEL_PATH  = BASE_DIR / "final_models" / "best_prone_1.6.25.pt"
SUPINE_MODEL_PATH = BASE_DIR / "final_models" / "best_supine_16.10.25.pt"

VIDEOS_OUTPUT_DIR = BASE_DIR / "videos_output"
VIDEOS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

