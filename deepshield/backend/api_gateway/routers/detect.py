"""
Detection router — all /detect endpoints.
POST /detect/image   → analyze single image
POST /detect/video   → analyze video (async, returns job_id)
POST /detect/audio   → analyze audio clip
GET  /detect/{id}    → poll analysis status
GET  /detect/{id}/report → download forensic PDF
"""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from services.detection_service.orchestrator import orchestrator, MediaType
from middleware.auth import require_permission
from core.celery_app import celery_app
import logging

logger = logging.getLogger("deepshield.router.detect")
router = APIRouter(prefix="/detect")


class DetectionResponse(BaseModel):
    analysis_id:     str
    status:          str
    verdict:         Optional[str]   = None
    confidence:      Optional[float] = None
    fake_probability:Optional[float] = None
    heatmap_url:     Optional[str]   = None
    processing_ms:   Optional[int]   = None
    report_url:      Optional[str]   = None
    message:         Optional[str]   = None


@router.post("/image", response_model=DetectionResponse,
             dependencies=[require_permission("detect")])
async def detect_image(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Synchronous image analysis — returns result immediately."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    analysis_id = str(uuid.uuid4())

    # Save temp file
    import tempfile, shutil, os
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await orchestrator.analyze(
            analysis_id=analysis_id,
            media_path=tmp_path,
            media_type=MediaType.IMAGE,
            metadata={
                "filename":    file.filename,
                "size_bytes":  file.size,
                "user_id":     request.state.user_id,
                "org_id":      request.state.org_id,
            },
        )
        # Async: save to DB + generate PDF
        background_tasks.add_task(_persist_result, result, tmp_path, request)

        return DetectionResponse(
            analysis_id=     result.analysis_id,
            status=          "completed",
            verdict=         result.verdict.value,
            confidence=      result.confidence,
            fake_probability=result.fake_probability,
            heatmap_url=     result.heatmap_url,
            processing_ms=   result.processing_ms,
        )
    finally:
        import os
        os.unlink(tmp_path)


@router.post("/video", response_model=DetectionResponse,
             dependencies=[require_permission("detect")])
async def detect_video(request: Request, file: UploadFile = File(...)):
    """
    Async video analysis — returns job_id immediately.
    Poll GET /detect/{id} for status.
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(400, "File must be a video")

    analysis_id = str(uuid.uuid4())

    # Save to S3 and dispatch Celery task
    import tempfile, shutil, os
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # Upload to S3
    from services.upload_service.s3_client import s3_client
    s3_key = f"uploads/{request.state.org_id}/{analysis_id}{suffix}"
    await s3_client.upload_file(tmp_path, s3_key)
    os.unlink(tmp_path)

    # Dispatch Celery task
    celery_app.send_task(
        "tasks.analyze_video",
        kwargs={
            "analysis_id": analysis_id,
            "s3_key":      s3_key,
            "user_id":     request.state.user_id,
            "org_id":      request.state.org_id,
        },
        queue="detection",
    )

    return DetectionResponse(
        analysis_id=analysis_id,
        status="queued",
        message="Video analysis queued. Poll GET /detect/{analysis_id} for status.",
    )


@router.post("/audio", response_model=DetectionResponse,
             dependencies=[require_permission("detect")])
async def detect_audio(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Synchronous audio deepfake / voice clone analysis."""
    if not file.content_type.startswith("audio/"):
        raise HTTPException(400, "File must be an audio file")

    analysis_id = str(uuid.uuid4())

    import tempfile, shutil, os
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await orchestrator.analyze(
            analysis_id=analysis_id,
            media_path=tmp_path,
            media_type=MediaType.AUDIO,
            metadata={"filename": file.filename, "user_id": request.state.user_id},
        )
        background_tasks.add_task(_persist_result, result, tmp_path, request)
        return DetectionResponse(
            analysis_id=     result.analysis_id,
            status=          "completed",
            verdict=         result.verdict.value,
            confidence=      result.confidence,
            fake_probability=result.fake_probability,
            processing_ms=   result.processing_ms,
        )
    finally:
        os.unlink(tmp_path)


@router.get("/{analysis_id}", response_model=DetectionResponse,
            dependencies=[require_permission("detect")])
async def get_analysis_status(analysis_id: str, request: Request):
    """Poll analysis status (for async video jobs)."""
    from core.database import get_analysis
    record = await get_analysis(analysis_id, request.state.org_id)
    if not record:
        raise HTTPException(404, "Analysis not found")
    return DetectionResponse(**record)


@router.get("/{analysis_id}/report",
            dependencies=[require_permission("reports")])
async def download_report(analysis_id: str, request: Request):
    """Download forensic PDF report."""
    from core.database import get_report_path
    path = await get_report_path(analysis_id, request.state.org_id)
    if not path:
        raise HTTPException(404, "Report not generated yet")
    return FileResponse(path, media_type="application/pdf",
                        filename=f"deepshield_report_{analysis_id}.pdf")


async def _persist_result(result, media_path, request):
    """Background: save to DB + generate PDF report."""
    try:
        from core.database import save_analysis
        from services.report_service.forensic_report import ForensicReportGenerator
        import tempfile

        await save_analysis(result, request.state.user_id, request.state.org_id)

        out_pdf = f"/tmp/report_{result.analysis_id}.pdf"
        gen = ForensicReportGenerator()
        gen.generate(result, media_path, None, out_pdf,
                     analyst_name=request.state.user_id,
                     org_name=request.state.org_id)
        logger.info(f"Report generated: {out_pdf}")
    except Exception as e:
        logger.error(f"Failed to persist result {result.analysis_id}: {e}")
