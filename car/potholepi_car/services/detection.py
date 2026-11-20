"""
Pothole detection - integration point for the fine-tuned YOLO model.

The model itself is NOT implemented yet. Everything around it is:

    camera.get_frame() --> PotholeDetector.detect() --> Reporter.report(trigger="model")

To plug the model in:
  1. put the weights in ``car/models/`` (git-ignored),
  2. implement ``YoloPotholeDetector.load()`` / ``detect()`` below
     (ultralytics, ncnn, onnxruntime... whatever runs best on the Pi 4),
  3. set ``POTHOLEPI_DETECTION_ENABLED=1``.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Protocol

from ..config import Settings

log = logging.getLogger(__name__)


@dataclass
class Detection:
    confidence: float
    bbox: list[float]          # [x1, y1, x2, y2] in pixels
    label: str = "pothole"


class PotholeDetector(Protocol):
    name: str

    def load(self) -> None: ...
    def detect(self, frame) -> list[Detection]: ...


class NullDetector:
    """Detects nothing. Used until the model is ready."""

    name = "none"

    def load(self) -> None: ...

    def detect(self, frame) -> list[Detection]:
        return []


class YoloPotholeDetector:
    """Placeholder for the fine-tuned YOLO model (left empty on purpose)."""

    name = "yolo"

    def __init__(self, model_path: str, min_confidence: float):
        self.model_path = model_path
        self.min_confidence = min_confidence

    def load(self) -> None:
        raise NotImplementedError("YOLO pothole model not integrated yet")

    def detect(self, frame) -> list[Detection]:
        raise NotImplementedError


def create_detector(settings: Settings) -> PotholeDetector:
    if not settings.DETECTION_ENABLED:
        return NullDetector()
    det = YoloPotholeDetector(settings.DETECTION_MODEL_PATH, settings.DETECTION_MIN_CONFIDENCE)
    try:
        det.load()
        return det
    except Exception as e:
        log.warning("detector disabled: %s", e)
        return NullDetector()


class DetectionWorker:
    """Runs the detector on camera frames and reports potholes (with a cooldown)."""

    def __init__(self, settings: Settings, detector: PotholeDetector, camera, reporter):
        self.s = settings
        self.detector = detector
        self.camera = camera
        self.reporter = reporter
        self.last_report = 0.0
        self.reports = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="detector", daemon=True)

    @property
    def active(self) -> bool:
        return not isinstance(self.detector, NullDetector)

    def start(self) -> None:
        if self.active:
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(0.05):
            frame = self.camera.get_frame()
            if frame is None:
                continue
            hits = [d for d in self.detector.detect(frame)
                    if d.confidence >= self.s.DETECTION_MIN_CONFIDENCE]
            if not hits or time.monotonic() - self.last_report < self.s.DETECTION_COOLDOWN_S:
                continue
            best = max(hits, key=lambda d: d.confidence)
            try:
                self.reporter.report(None, trigger="model",
                                     confidence=best.confidence, bbox=best.bbox)
                self.last_report = time.monotonic()
                self.reports += 1
            except Exception as e:
                log.warning("automatic report failed: %s", e)
