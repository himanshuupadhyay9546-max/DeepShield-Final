"""
Detection orchestrator.
Routes media to correct AI models, runs ensemble voting,
generates GradCAM heatmaps, returns structured DetectionResult.
"""
from __future__ import annotations
import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

from ai.models.efficientnet_b4 import EfficientNetB4Detector
from ai.models.xceptionnet import XceptionNetDetector
from ai.models.vit_detector import ViTDetector
from ai.models.cnn_transformer import CNNTransformerDetector
from ai.models.frequency_domain import FrequencyDomainDetector
from ai.models.audio_detector import AudioDetector
from ai.models.ensemble import EnsembleVoter
from ai.explainability.gradcam import GradCAMGenerator
from core.config import settings

logger = logging.getLogger("deepshield.detection")


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class Verdict(str, Enum):
    AUTHENTIC = "authentic"
    DEEPFAKE  = "deepfake"
    UNCERTAIN = "uncertain"


@dataclass
class ModelResult:
    model_name: str
    score: float          # 0.0 = authentic, 1.0 = deepfake
    confidence: float     # how confident the model is in its prediction
    processing_ms: int
    regions: list[dict] = field(default_factory=list)


@dataclass
class DetectionResult:
    analysis_id: str
    verdict: Verdict
    confidence: float
    fake_probability: float
    model_results: list[ModelResult]
    heatmap_url: Optional[str]
    manipulation_regions: list[dict]
    processing_ms: int
    media_type: MediaType
    metadata: dict


class DetectionOrchestrator:
    """
    Parallel inference across all enabled models + ensemble voting.
    Each model runs in its own thread pool executor for true parallelism.
    """

    _image_models: list | None = None
    _audio_model: AudioDetector | None = None
    _ensemble: EnsembleVoter | None = None
    _gradcam: GradCAMGenerator | None = None

    @classmethod
    async def _load_models(cls):
        if cls._image_models is None:
            logger.info("Loading AI models into memory...")
            cls._image_models = [
                EfficientNetB4Detector(weights=settings.MODEL_DIR / "efficientnet_b4.pt"),
                XceptionNetDetector(weights=settings.MODEL_DIR / "xceptionnet.pt"),
                ViTDetector(weights=settings.MODEL_DIR / "vit_base.pt"),
                CNNTransformerDetector(weights=settings.MODEL_DIR / "cnn_transformer.pt"),
                FrequencyDomainDetector(),
            ]
            cls._audio_model = AudioDetector(weights=settings.MODEL_DIR / "audio_detector.pt")
            cls._ensemble = EnsembleVoter(weights=[0.30, 0.25, 0.20, 0.15, 0.10])
            cls._gradcam = GradCAMGenerator()
            logger.info(f"Loaded {len(cls._image_models)} image models + audio model")

    async def analyze(
        self,
        analysis_id: str,
        media_path: str,
        media_type: MediaType,
        metadata: dict,
    ) -> DetectionResult:
        await self._load_models()
        start = time.perf_counter()

        if media_type == MediaType.AUDIO:
            return await self._analyze_audio(analysis_id, media_path, metadata, start)

        # Run all image/video models in parallel
        tasks = [
            self._run_model(model, media_path, media_type)
            for model in self._image_models
        ]
        model_results: list[ModelResult] = await asyncio.gather(*tasks)

        # Ensemble voting
        scores = np.array([r.score for r in model_results])
        ensemble_score = self._ensemble.vote(scores)

        # Verdict thresholding
        if ensemble_score >= 0.75:
            verdict = Verdict.DEEPFAKE
        elif ensemble_score <= 0.30:
            verdict = Verdict.AUTHENTIC
        else:
            verdict = Verdict.UNCERTAIN

        confidence = abs(ensemble_score - 0.5) * 2  # distance from decision boundary

        # GradCAM heatmap (use EfficientNet as primary explainer)
        heatmap_url = None
        manipulation_regions = []
        if verdict != Verdict.UNCERTAIN:
            primary_result = model_results[0]
            heatmap_url = await self._gradcam.generate(
                media_path=media_path,
                model=self._image_models[0],
                analysis_id=analysis_id,
            )
            manipulation_regions = primary_result.regions

        total_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[{analysis_id}] verdict={verdict.value} "
            f"score={ensemble_score:.3f} conf={confidence:.3f} "
            f"time={total_ms}ms"
        )

        return DetectionResult(
            analysis_id=analysis_id,
            verdict=verdict,
            confidence=round(confidence, 4),
            fake_probability=round(float(ensemble_score), 4),
            model_results=model_results,
            heatmap_url=heatmap_url,
            manipulation_regions=manipulation_regions,
            processing_ms=total_ms,
            media_type=media_type,
            metadata=metadata,
        )

    async def _run_model(self, model, media_path: str, media_type: MediaType) -> ModelResult:
        loop = asyncio.get_event_loop()
        t = time.perf_counter()
        result = await loop.run_in_executor(None, model.predict, media_path, media_type)
        ms = int((time.perf_counter() - t) * 1000)
        return ModelResult(
            model_name=model.name,
            score=result["score"],
            confidence=result["confidence"],
            processing_ms=ms,
            regions=result.get("regions", []),
        )

    async def _analyze_audio(self, analysis_id, media_path, metadata, start) -> DetectionResult:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._audio_model.predict, media_path)
        ms = int((time.perf_counter() - start) * 1000)
        score = result["score"]
        verdict = Verdict.DEEPFAKE if score >= 0.75 else (
            Verdict.AUTHENTIC if score <= 0.30 else Verdict.UNCERTAIN
        )
        return DetectionResult(
            analysis_id=analysis_id,
            verdict=verdict,
            confidence=round(abs(score - 0.5) * 2, 4),
            fake_probability=round(score, 4),
            model_results=[ModelResult("audio_detector", score, result["confidence"], ms)],
            heatmap_url=None,
            manipulation_regions=[],
            processing_ms=ms,
            media_type=MediaType.AUDIO,
            metadata=metadata,
        )


orchestrator = DetectionOrchestrator()
