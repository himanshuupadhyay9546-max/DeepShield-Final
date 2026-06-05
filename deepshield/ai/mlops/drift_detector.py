"""
Model drift detector.
Monitors prediction distribution, confidence drift, and accuracy decay.
Triggers automated retraining via MLflow when drift is detected.
Runs as a Celery periodic task (every 6 hours).
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import mlflow
from scipy.stats import ks_2samp, chi2_contingency

logger = logging.getLogger("deepshield.mlops.drift")


@dataclass
class DriftReport:
    model_name: str
    detected: bool
    drift_score: float
    confidence_drift: float
    accuracy_trend: float
    alert_level: str  # "none" | "warning" | "critical"
    recommendation: str
    timestamp: str


class ModelDriftDetector:
    """
    Population Stability Index (PSI) + KS-test for score drift.
    Confidence drift via rolling window mean shift.
    Accuracy decay via sliding window AUC comparison.
    """

    def __init__(
        self,
        reference_window_days: int = 30,
        detection_window_days: int = 7,
        psi_warning_threshold: float = 0.1,
        psi_critical_threshold: float = 0.25,
    ):
        self.ref_days = reference_window_days
        self.det_days = detection_window_days
        self.psi_warn = psi_warning_threshold
        self.psi_crit = psi_critical_threshold

    def compute_psi(self, reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        """Population Stability Index — measures score distribution shift."""
        ref_hist, edges = np.histogram(reference, bins=bins, range=(0, 1), density=True)
        cur_hist, _    = np.histogram(current,   bins=edges,                density=True)
        # Add epsilon to avoid log(0)
        eps = 1e-8
        ref_hist = np.clip(ref_hist / (ref_hist.sum() + eps), eps, None)
        cur_hist = np.clip(cur_hist / (cur_hist.sum() + eps), eps, None)
        psi = float(np.sum((cur_hist - ref_hist) * np.log(cur_hist / ref_hist)))
        return round(abs(psi), 6)

    def ks_test(self, reference: np.ndarray, current: np.ndarray) -> tuple[float, float]:
        """Kolmogorov-Smirnov test for distribution change."""
        stat, pvalue = ks_2samp(reference, current)
        return round(float(stat), 6), round(float(pvalue), 6)

    async def detect(
        self,
        model_name: str,
        reference_scores: np.ndarray,
        current_scores: np.ndarray,
        reference_confs: np.ndarray,
        current_confs: np.ndarray,
        accuracy_history: list[float],
    ) -> DriftReport:
        psi = self.compute_psi(reference_scores, current_scores)
        ks_stat, ks_p = self.ks_test(reference_scores, current_scores)

        conf_drift = float(np.mean(reference_confs) - np.mean(current_confs))
        
        accuracy_trend = 0.0
        if len(accuracy_history) >= 2:
            x = np.arange(len(accuracy_history))
            coeffs = np.polyfit(x, accuracy_history, 1)
            accuracy_trend = round(float(coeffs[0]), 6)  # slope per period

        # Drift score: composite
        drift_score = round(0.5 * psi + 0.3 * ks_stat + 0.2 * abs(conf_drift), 6)

        if psi >= self.psi_crit or drift_score >= 0.3:
            alert_level = "critical"
            recommendation = "Immediate retraining required — model performance severely degraded"
        elif psi >= self.psi_warn or drift_score >= 0.15:
            alert_level = "warning"
            recommendation = "Schedule retraining within 48 hours — moderate drift detected"
        else:
            alert_level = "none"
            recommendation = "Model performance stable — no action required"

        report = DriftReport(
            model_name=model_name,
            detected=alert_level != "none",
            drift_score=drift_score,
            confidence_drift=round(conf_drift, 6),
            accuracy_trend=accuracy_trend,
            alert_level=alert_level,
            recommendation=recommendation,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Log to MLflow
        with mlflow.start_run(run_name=f"drift_check_{model_name}"):
            mlflow.log_metrics({
                "psi": psi,
                "ks_stat": ks_stat,
                "ks_pvalue": ks_p,
                "drift_score": drift_score,
                "conf_drift": conf_drift,
                "accuracy_trend": accuracy_trend,
            })
            mlflow.set_tag("alert_level", alert_level)
            mlflow.set_tag("model_name", model_name)

        if alert_level == "critical":
            await self._trigger_retraining(model_name)

        return report

    async def _trigger_retraining(self, model_name: str):
        """Submit retraining job to Celery queue."""
        from core.celery_app import celery_app
        logger.warning(f"Triggering auto-retraining for {model_name}")
        celery_app.send_task(
            "tasks.retrain_model",
            kwargs={"model_name": model_name, "triggered_by": "drift_detector"},
            queue="ml_training",
        )
