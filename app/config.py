import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
GHOST_DIR = BASE_DIR / "ghost"
RESULTS_DIR = BASE_DIR / "results"

# GHOST 2.0 checkpoint paths (relative to GHOST_DIR)
ALIGNER_CKPT = GHOST_DIR / "aligner_checkpoints" / "aligner_1020_gaze_final.ckpt"
BLENDER_CKPT = GHOST_DIR / "blender_checkpoints" / "blender_lama.ckpt"

# Python executable — same one running this process (set by start.sh via conda)
# Subprocess inference inherits all packages automatically.
INFERENCE_PYTHON = sys.executable

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Job retention (seconds before result files can be cleaned up)
RESULT_TTL_SECONDS = 3600
