"""Detections: create (from the car), list/filter, details, status, delete."""
from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas import DetectionIn, DetectionOut, StatusUpdate

router = APIRouter(prefix="/api/detections", tags=["detections"])


@router.post("", status_code=201)
def create(body: DetectionIn, request: Request):
    ctx = request.app.state.ctx
    image = None
    if body.image_b64:
        try:
            image = base64.b64decode(body.image_b64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "image_b64 is not valid base64")
        if len(image) > ctx.settings.MAX_IMAGE_BYTES:
            raise HTTPException(413, "image too large")
        if not image.startswith(b"\xff\xd8"):
            raise HTTPException(400, "image must be a JPEG")

    det_id = ctx.repo.insert(body.model_dump(exclude={"image_b64"}))
    if image:
        name = f"{det_id}.jpg"
        (ctx.settings.images_dir / name).write_bytes(image)
        ctx.repo.set_image(det_id, name)
    ctx.geocoder.enqueue(det_id)
    return {"id": det_id}


@router.get("", response_model=list[DetectionOut])
def list_detections(request: Request,
                    since: float | None = Query(None, description="unix seconds"),
                    until: float | None = Query(None, description="unix seconds"),
                    source: str | None = None, status: str | None = None,
                    limit: int = Query(5000, ge=1, le=50000)):
    return request.app.state.ctx.repo.list(since, until, source, status, limit)


@router.get("/{det_id}", response_model=DetectionOut)
def get_detection(det_id: int, request: Request):
    det = request.app.state.ctx.repo.get(det_id)
    if not det:
        raise HTTPException(404, "detection not found")
    return det


@router.patch("/{det_id}", response_model=DetectionOut)
def update_status(det_id: int, body: StatusUpdate, request: Request):
    repo = request.app.state.ctx.repo
    if not repo.set_status(det_id, body.status):
        raise HTTPException(404, "detection not found")
    return repo.get(det_id)


@router.delete("/{det_id}", status_code=204)
def delete_detection(det_id: int, request: Request):
    ctx = request.app.state.ctx
    det = ctx.repo.delete(det_id)
    if not det:
        raise HTTPException(404, "detection not found")
    if det["image_url"]:
        (ctx.settings.images_dir / det["image_url"].rsplit("/", 1)[-1]).unlink(missing_ok=True)
