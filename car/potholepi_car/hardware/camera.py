"""
Camera sources. Each one keeps the latest JPEG frame in memory so the MJPEG
stream, the snapshot endpoint and the reporter all share a single capture.

    PiCamera     CSI camera through Picamera2 (hardware MJPEG encoder)
    UsbCamera    any V4L2/USB webcam through OpenCV
    TestPattern  generated frames (simulation, no camera attached)

``get_frame()`` returns an RGB numpy array for the pothole detector (or None
when the source cannot provide one).
"""
from __future__ import annotations

import io
import logging
import threading
import time

from ..config import Settings

log = logging.getLogger(__name__)


class FrameBuffer(io.BufferedIOBase):
    """Latest JPEG + a condition so stream readers wake on each new frame."""

    def __init__(self):
        self.frame: bytes | None = None
        self.count = 0
        self.updated = 0.0
        self.cond = threading.Condition()

    def write(self, buf) -> int:  # called by the Picamera2 FileOutput
        with self.cond:
            self.frame = bytes(buf)
            self.count += 1
            self.updated = time.monotonic()
            self.cond.notify_all()
        return len(buf)

    def wait_next(self, last_count: int, timeout: float = 2.0) -> tuple[bytes | None, int]:
        with self.cond:
            self.cond.wait_for(lambda: self.count != last_count, timeout=timeout)
            return self.frame, self.count


class BaseCamera:
    name = "none"

    def __init__(self, settings: Settings):
        self.s = settings
        self.buffer = FrameBuffer()
        self.error: str | None = None

    def start(self) -> None: ...
    def stop(self) -> None: ...

    @property
    def ok(self) -> bool:
        return self.buffer.frame is not None and time.monotonic() - self.buffer.updated < 3

    def get_jpeg(self) -> bytes | None:
        return self.buffer.frame

    def get_frame(self):
        return None

    def stream(self):
        """Yields multipart MJPEG chunks forever (one per new frame)."""
        count = -1
        while True:
            frame, count = self.buffer.wait_next(count)
            if frame is None:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                   + frame + b"\r\n")


class PiCamera(BaseCamera):
    name = "picamera2"

    def start(self) -> None:
        from picamera2 import Picamera2
        from picamera2.encoders import MJPEGEncoder, Quality
        from picamera2.outputs import FileOutput

        self.cam = Picamera2()
        cfg = self.cam.create_video_configuration(
            main={"size": (self.s.CAMERA_WIDTH, self.s.CAMERA_HEIGHT), "format": "RGB888"},
            controls={"FrameRate": self.s.CAMERA_FPS},
        )
        self.cam.configure(cfg)
        self.cam.start_recording(MJPEGEncoder(), FileOutput(self.buffer), quality=Quality.HIGH)
        log.info("Picamera2 streaming %dx%d", self.s.CAMERA_WIDTH, self.s.CAMERA_HEIGHT)

    def stop(self) -> None:
        try:
            self.cam.stop_recording()
            self.cam.close()
        except Exception:
            pass

    def get_frame(self):
        # Picamera2 "RGB888" is BGR in memory; flip to RGB for the model.
        return self.cam.capture_array("main")[:, :, ::-1]


class UsbCamera(BaseCamera):
    name = "opencv"

    def start(self) -> None:
        import cv2

        self.cv2 = cv2
        self.cap = cv2.VideoCapture(self.s.CAMERA_USB_INDEX)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open USB camera {self.s.CAMERA_USB_INDEX}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.s.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.s.CAMERA_HEIGHT)
        self._last = None
        self._running = True
        threading.Thread(target=self._loop, name="usb-camera", daemon=True).start()

    def _loop(self) -> None:
        params = [self.cv2.IMWRITE_JPEG_QUALITY, self.s.CAMERA_JPEG_QUALITY]
        period = 1 / max(self.s.CAMERA_FPS, 1)
        while self._running:
            ok, img = self.cap.read()
            if not ok:
                time.sleep(0.5)
                continue
            self._last = img
            ok, jpg = self.cv2.imencode(".jpg", img, params)
            if ok:
                self.buffer.write(jpg.tobytes())
            time.sleep(period)

    def stop(self) -> None:
        self._running = False
        self.cap.release()

    def get_frame(self):
        return None if self._last is None else self._last[:, :, ::-1]


class TestPattern(BaseCamera):
    """Moving test frames with a clock, so the whole video path can be tested."""

    name = "test-pattern"

    def start(self) -> None:
        self._running = True
        threading.Thread(target=self._loop, name="test-camera", daemon=True).start()

    def _loop(self) -> None:
        from PIL import Image, ImageDraw

        w, h = self.s.CAMERA_WIDTH, self.s.CAMERA_HEIGHT
        period = 1 / max(self.s.CAMERA_FPS, 1)
        n = 0
        while self._running:
            img = Image.new("RGB", (w, h), (24, 28, 36))
            d = ImageDraw.Draw(img)
            for i in range(0, w, 40):                      # perspective "road" lines
                d.line([(i, h), (w // 2, h // 3)], fill=(44, 52, 66))
            x = int((n * 6) % (w + 80)) - 40
            d.ellipse([x, h * 0.65, x + 80, h * 0.65 + 30], fill=(90, 70, 50))  # a "pothole"
            d.rectangle([0, 0, w, 28], fill=(0, 0, 0))
            d.text((10, 8), f"POTHOLE PI  SIMULATION  {time.strftime('%H:%M:%S')}  #{n}",
                   fill=(255, 196, 0))
            out = io.BytesIO()
            img.save(out, "JPEG", quality=self.s.CAMERA_JPEG_QUALITY)
            self.buffer.write(out.getvalue())
            self._last = img
            n += 1
            time.sleep(period)

    def stop(self) -> None:
        self._running = False

    def get_frame(self):
        import numpy as np  # optional; only needed by a real detector

        return np.asarray(self._last) if getattr(self, "_last", None) else None


class NoCamera(BaseCamera):
    name = "disabled"


def create_camera(settings: Settings) -> BaseCamera:
    """Pick the best available source; never raise (the car must still drive)."""
    if not settings.CAMERA_ENABLED:
        return NoCamera(settings)
    candidates = [TestPattern] if settings.SIMULATE else [PiCamera, UsbCamera]
    errors = []
    for cls in candidates:
        cam = cls(settings)
        try:
            cam.start()
            return cam
        except Exception as e:
            errors.append(f"{cls.name}: {e}")
            log.warning("camera %s unavailable: %s", cls.name, e)
    cam = NoCamera(settings)
    cam.error = "; ".join(errors)
    return cam
