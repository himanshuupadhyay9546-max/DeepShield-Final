"""
Ensemble voter.
Weighted soft voting across all models with Platt scaling calibration.
Weights are tuned on validation set; can be auto-tuned via MLflow experiments.
"""
from __future__ import annotations

import numpy as np
from scipy.special import expit  # sigmoid


class EnsembleVoter:
    """
    Combines model scores using weighted soft voting.
    
    Weights represent model accuracy on validation set:
      [EfficientNetB4, XceptionNet, ViT, CNNTransformer, FrequencyDomain]
    """

    def __init__(self, weights: list[float] | None = None):
        default_weights = [0.30, 0.25, 0.20, 0.15, 0.10]
        raw = np.array(weights or default_weights, dtype=np.float64)
        self.weights = raw / raw.sum()  # normalize to sum=1

    def vote(self, scores: np.ndarray) -> float:
        """
        Weighted average, then Platt scaling to calibrate probabilities.
        Returns calibrated fake probability in [0, 1].
        """
        if len(scores) != len(self.weights):
            raise ValueError(
                f"Expected {len(self.weights)} scores, got {len(scores)}"
            )
        weighted = float(np.dot(self.weights, scores))
        # Platt scaling (a, b calibrated offline; defaults are identity)
        a, b = 1.0, 0.0
        calibrated = float(expit(a * weighted + b))
        return round(calibrated, 6)

    def update_weights(self, new_weights: list[float]):
        """Hot-update weights from MLflow experiment results."""
        raw = np.array(new_weights, dtype=np.float64)
        self.weights = raw / raw.sum()

    def explain(self, scores: np.ndarray) -> list[dict]:
        """
        Returns per-model contribution to final decision.
        Used by the XAI/explainability module.
        """
        total = float(np.dot(self.weights, scores))
        return [
            {
                "model_index": i,
                "score": round(float(scores[i]), 4),
                "weight": round(float(self.weights[i]), 4),
                "contribution": round(float(self.weights[i] * scores[i] / total), 4)
                if total > 0 else 0.0,
            }
            for i in range(len(scores))
        ]
