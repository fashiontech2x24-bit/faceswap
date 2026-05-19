"""
FaceSwapService — calls GHOST 2.0 inference.py as a subprocess.
No model weights are held in the API process; each swap job spawns a fresh
subprocess that loads, runs, and exits.
"""
import logging
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.config import (
    GHOST_DIR,
    ALIGNER_CKPT,
    BLENDER_CKPT,
    INFERENCE_PYTHON,
)

log = logging.getLogger(__name__)

_INFERENCE_SCRIPT = GHOST_DIR / "inference.py"


class FaceSwapService:
    def load(self) -> None:
        """Verify checkpoint files exist. Called at server startup."""
        missing = [p for p in (ALIGNER_CKPT, BLENDER_CKPT, _INFERENCE_SCRIPT) if not p.exists()]
        if missing:
            raise FileNotFoundError(
                "GHOST 2.0 assets not found (run ./setup.sh first):\n"
                + "\n".join(f"  {p}" for p in missing)
            )
        log.info("GHOST 2.0 checkpoints verified.")

    def swap(self, target_bgr: np.ndarray, source_bgr: np.ndarray) -> np.ndarray:
        """
        Swap the face from source_bgr onto target_bgr.

        Args:
            target_bgr: Full image whose face(s) will be replaced (BGR).
            source_bgr: Image containing the donor face — GHOST auto-crops it (BGR).

        Returns:
            Result image in BGR with the swapped face.

        Raises:
            RuntimeError: if the subprocess fails or produces no output.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src_path    = tmp / "source.jpg"
            tgt_path    = tmp / "target.jpg"
            result_path = tmp / "result.png"

            cv2.imwrite(str(src_path), source_bgr)
            cv2.imwrite(str(tgt_path), target_bgr)

            cmd = [
                str(INFERENCE_PYTHON),
                str(_INFERENCE_SCRIPT),
                "--source",  str(src_path),
                "--target",  str(tgt_path),
                "--ckpt_a",  str(ALIGNER_CKPT),
                "--ckpt_b",  str(BLENDER_CKPT),
                "--save_path", str(result_path),
            ]

            log.info("Running GHOST 2.0 inference...")
            proc = subprocess.run(
                cmd,
                cwd=str(GHOST_DIR),
                capture_output=True,
                text=True,
                timeout=300,
            )

            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout)[-2000:]
                raise RuntimeError(f"GHOST inference failed:\n{tail}")

            result = cv2.imread(str(result_path))
            if result is None:
                raise RuntimeError(
                    "GHOST inference produced no output file.\n"
                    + (proc.stdout + proc.stderr)[-2000:]
                )

            return result


# Module-level singleton — imported by routes and lifespan handler
face_swap_service = FaceSwapService()
