import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_SRC = ROOT_DIR / "src"

if PROJECT_SRC.exists():
    sys.path.insert(0, str(ROOT_DIR))
