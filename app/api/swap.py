"""
Face-swap API routes.

POST /api/swap        — upload target + source images, enqueue job
GET  /api/status/{id} — poll job status
GET  /api/result/{id} — download result image
"""
import asyncio
import logging
from enum import Enum
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import RESULTS_DIR
from app.services.face_swap import face_swap_service
from app.utils.image import bytes_to_bgr, new_job_id, save_result

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# ── job store (in-memory, single process) ─────────────────────────────────────

class Status(str, Enum):
    PENDING = "pending"
    DONE    = "done"
    FAILED  = "failed"


class Job:
    def __init__(self, job_id: str):
        self.id      = job_id
        self.status  = Status.PENDING
        self.result_path: Optional[str] = None
        self.error:       Optional[str] = None


_jobs: dict[str, Job] = {}

# Ensures only one inference runs at a time (sequential mode)
_swap_lock = asyncio.Lock()


# ── routes ────────────────────────────────────────────────────────────────────

@router.post("/swap")
async def swap(
    background_tasks: BackgroundTasks,
    target: UploadFile = File(..., description="Full image — face will be placed here"),
    source: UploadFile = File(..., description="Image containing the donor face"),
):
    """
    Accept two images, return a job ID immediately.
    Poll /api/status/{job_id} until status == 'done', then fetch /api/result/{job_id}.
    """
    target_bytes = await target.read()
    source_bytes = await source.read()

    job_id = new_job_id()
    job = Job(job_id)
    _jobs[job_id] = job

    background_tasks.add_task(_run_swap, job, target_bytes, source_bytes)

    return {"job_id": job_id, "status": Status.PENDING}


@router.get("/status/{job_id}")
async def status(job_id: str):
    job = _get_job(job_id)
    payload = {"job_id": job_id, "status": job.status}
    if job.error:
        payload["error"] = job.error
    return payload


@router.get("/result/{job_id}")
async def result(job_id: str):
    job = _get_job(job_id)
    if job.status != Status.DONE:
        raise HTTPException(status_code=202, detail=f"Job {job.status}")
    if not job.result_path:
        raise HTTPException(status_code=500, detail="Result path missing")
    return FileResponse(
        job.result_path,
        media_type="image/jpeg",
        filename="swapped.jpg",
    )


# ── background task ───────────────────────────────────────────────────────────

async def _run_swap(job: Job, target_bytes: bytes, source_bytes: bytes) -> None:
    async with _swap_lock:
        loop = asyncio.get_event_loop()
        try:
            result_img = await loop.run_in_executor(
                None, _sync_swap, target_bytes, source_bytes
            )
            path = save_result(result_img, RESULTS_DIR, job.id)
            job.result_path = str(path)
            job.status = Status.DONE
        except Exception as exc:
            log.exception("Swap failed for job %s", job.id)
            job.status = Status.FAILED
            job.error  = str(exc)


def _sync_swap(target_bytes: bytes, source_bytes: bytes):
    target_bgr = bytes_to_bgr(target_bytes)
    source_bgr = bytes_to_bgr(source_bytes)
    return face_swap_service.swap(target_bgr, source_bgr)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_job(job_id: str) -> Job:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]
