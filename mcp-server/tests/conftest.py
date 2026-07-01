import sys
from pathlib import Path

# Ensure tests import the package from source (not any installed copy).
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
