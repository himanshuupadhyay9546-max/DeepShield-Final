"""
XceptionNet deepfake detector.
Originally designed by Facebook AI for face forensics.
Excellent at detecting face swap artifacts.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import timm

TRANSFORM = transforms.Compose([
    transforms.Resize((299, 299)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])


class XceptionNetDetector:
    name = "xceptionnet"

    def __init__(self, weights: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        backbone = timm.create_model("xception", pretrained=True, num_classes=0)
        self.model = nn.Sequential(
            backbone,
            nn.Linear(2048, 512), nn.ReLU(), nn.Dropout(0.35),
            nn.Linear(512, 1), nn.Sigmoid(),
        )
        if weights.exists():
            self.model.load_state_dict(torch.load(weights, map_location=self.device))
        self.model.to(self.device).eval()

    def predict(self, media_path: str, media_type: Any = None) -> dict:
        img = Image.open(media_path).convert("RGB")
        tensor = TRANSFORM(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            score = self.model(tensor).item()
        return {
            "score":      round(score, 6),
            "confidence": round(min(1.0, abs(score - 0.5) * 2.3), 6),
            "regions":    [],
        }
