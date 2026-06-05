"""
Frequency Domain Detector.
GAN-generated images leave characteristic artifacts in DCT/FFT spectrum.
This model analyzes frequency-domain features that spatial CNNs miss entirely.
"""
from __future__ import annotations
from typing import Any

import numpy as np
import cv2
import torch
import torch.nn as nn
from PIL import Image


class FrequencyFeatureExtractor:
    """Extracts DCT and FFT features from an image."""

    @staticmethod
    def dct_features(img_gray: np.ndarray, patch_size: int = 8) -> np.ndarray:
        h, w = img_gray.shape
        h = (h // patch_size) * patch_size
        w = (w // patch_size) * patch_size
        img_gray = img_gray[:h, :w].astype(np.float32)
        dct_map = np.zeros_like(img_gray)
        for i in range(0, h, patch_size):
            for j in range(0, w, patch_size):
                patch = img_gray[i:i+patch_size, j:j+patch_size]
                dct_map[i:i+patch_size, j:j+patch_size] = cv2.dct(patch)
        return dct_map

    @staticmethod
    def fft_spectrum(img_gray: np.ndarray) -> np.ndarray:
        f = np.fft.fft2(img_gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.log(np.abs(fshift) + 1)
        return magnitude / magnitude.max()

    def extract(self, img_path: str) -> np.ndarray:
        img = np.array(Image.open(img_path).convert("L").resize((256, 256)))
        dct = self.dct_features(img.astype(np.float32))
        fft = self.fft_spectrum(img.astype(np.float32))
        # Stack DCT + FFT as 2-channel feature map
        features = np.stack([
            cv2.resize(dct, (64, 64)),
            cv2.resize(fft, (64, 64)),
        ], axis=0)
        return features.astype(np.float32)


class FrequencyClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(2, 32, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 16, 256),
            nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.fc(self.conv(x)).squeeze(-1)


class FrequencyDomainDetector:
    name = "frequency_domain"

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.extractor = FrequencyFeatureExtractor()
        self.classifier = FrequencyClassifier().to(self.device)
        self.classifier.eval()

    def predict(self, media_path: str, media_type: Any = None) -> dict:
        features = self.extractor.extract(media_path)
        tensor = torch.from_numpy(features).unsqueeze(0).to(self.device)
        with torch.no_grad():
            score = self.classifier(tensor).item()
        return {
            "score": round(score, 6),
            "confidence": round(min(1.0, abs(score - 0.5) * 2.2), 6),
            "regions": [],
        }
