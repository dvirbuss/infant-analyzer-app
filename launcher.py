import sys
import os
import subprocess
from pathlib import Path
from core.requirements_utils import find_missing

project_root = Path(__file__).resolve().parent
os.chdir(project_root)

REQUIREMENTS_FILE = "requirements.txt"
STREAMLIT_APP_FILE = "app.py"   # <-- RUN STREAMLIT UI

def check_requirements() -> bool:
    missing = find_missing(REQUIREMENTS_FILE)
    if missing:
        print("\n❌ Missing required packages:")
        for pkg in missing:
            print(" -", pkg)
        print("\nGo to Terminal (Alt+F12) then run:")
        print("pip install -r requirements.txt")
        return False
    print("✔️ All requirements are satisfied!")
    return True

def run_streamlit():
    app_path = Path(STREAMLIT_APP_FILE)
    if not app_path.exists():
        print(f"❌ Streamlit UI not found: {app_path}")
        sys.exit(1)
    venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    python_exec = venv_python if venv_python.exists() else sys.executable
    cmd = [str(python_exec), "-m", "streamlit", "run", str(app_path), "--server.port", "8505",
    "--server.address", "127.0.0.1"]
    print("\n🚀 Launching Streamlit...")
    subprocess.call(cmd, cwd=str(project_root))

if __name__ == "__main__":
    print("🔍 Checking requirements...")
    if not check_requirements():
        sys.exit(1)

    run_streamlit()
