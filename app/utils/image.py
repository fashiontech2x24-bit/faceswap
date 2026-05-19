"""Helpers for converting between bytes, numpy arrays, and disk files."""
import io
import uuid
from pathlib import Path

import cv2
import numpy as np


def bytes_to_bgr(data: bytes) -> np.ndarray:
    """Decode image bytes (any common format) to a BGR numpy array."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image — unsupported format or corrupt file.")
    return img


def bgr_to_bytes(img: np.ndarray, ext: str = ".jpg") -> bytes:
    """Encode a BGR numpy array to image bytes."""
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return buf.tobytes()


def save_result(img: np.ndarray, results_dir: Path, job_id: str) -> Path:
    """Save result image to results_dir/{job_id}.jpg and return its path."""
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{job_id}.jpg"
    cv2.imwrite(str(path), img)
    return path


def new_job_id() -> str:
    return uuid.uuid4().hex
