"""
Vision Transformer (ViT-Base/16) deepfake detector.
Captures global inconsistencies that CNNs miss — ideal for subtle face swaps.
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
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


class ViTDetector:
    name = "vit_base_16"

    def __init__(self, weights: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        backbone = timm.create_model("vit_base_patch16_224", pretrained=True, num_classes=0)
        self.model = nn.Sequential(
            backbone,
            nn.Linear(768, 256),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(256, 1),
            nn.Sigmoid(),
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
            "score": round(score, 6),
            "confidence": round(min(1.0, abs(score - 0.5) * 2.5), 6),
            "regions": [],
        }
