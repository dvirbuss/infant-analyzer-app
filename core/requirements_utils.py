from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pkg_resources


_VERSION_SPLIT_RE = re.compile(r"\s*(==|>=|<=|~=|!=|>|<)\s*")


def read_requirements(requirements_path: str | Path = "requirements.txt") -> List[str]:
    """
    Read requirements.txt and return raw requirement lines (e.g. 'numpy==1.26.4').
    Ignores empty lines and comments.
    """
    path = Path(requirements_path)
    if not path.exists():
        return []

    reqs: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Remove inline comments: "pkg==1.0  # comment"
        line = line.split("#", 1)[0].strip()
        if line:
            reqs.append(line)
    return reqs


def requirement_to_import_name(req_line: str) -> Tuple[str, str]:
    """
    Convert a requirement line to:
    - pip_name: the package name as used in pip install
    - import_name: best-effort module import name
    """
    pip_name = _VERSION_SPLIT_RE.split(req_line, maxsplit=1)[0].strip()

    # Common pip->import name fixes
    overrides = {
        "opencv-python": "cv2",
        "scikit-learn": "sklearn",
        "tkinterdnd2": "tkinterdnd2",
        "ultralytics": "ultralytics",
        "tkcalendar": "tkcalendar",
    }
    import_name = overrides.get(pip_name, pip_name.replace("-", "_"))
    return pip_name, import_name


def find_missing(requirements_file):
    required = {
        req.project_name.lower(): req
        for req in pkg_resources.parse_requirements(open(requirements_file))
    }

    installed = {pkg.key.lower() for pkg in pkg_resources.working_set}

    missing = [str(req) for name, req in required.items() if name not in installed]
    return missing


def install_missing(missing: List[str]) -> None:
    """
    Install missing packages using the current interpreter.
    """
    if not missing:
        return
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
