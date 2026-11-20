"""Live video: MJPEG stream (for the app / a browser) and single snapshots."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse

router = APIRouter()


@router.get("/stream.mjpg")
def stream(request: Request):
    cam = request.app.state.rt.camera
    if cam.name == "disabled":
        raise HTTPException(503, cam.error or "camera disabled")
    return StreamingResponse(cam.stream(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-cache, private", "Pragma": "no-cache"})


@router.get("/snapshot.jpg")
def snapshot(request: Request):
    jpg = request.app.state.rt.camera.get_jpeg()
    if jpg is None:
        raise HTTPException(503, "no camera frame available")
    return Response(jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/viewer", response_class=HTMLResponse)
def viewer():
    """Full-bleed stream page; the mobile app embeds it in a WebView."""
    return """<!doctype html><html><head><meta name="viewport"
content="width=device-width,initial-scale=1,maximum-scale=1"><style>
html,body{margin:0;height:100%;background:#000;overflow:hidden}
img{width:100%;height:100%;object-fit:contain;display:block}
</style></head><body><img src="/stream.mjpg" alt="camera"></body></html>"""
