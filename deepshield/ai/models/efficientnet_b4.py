"""
EfficientNet-B4 deepfake detector.
Transfer learning from ImageNet, custom binary classification head.
Detects face swaps, GAN artifacts, and texture inconsistencies.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import timm

from core.config import settings


TRANSFORM = transforms.Compose([
    transforms.Resize((380, 380)),  # B4 native resolution
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


class DeepfakeHead(nn.Module):
    """Custom binary classification head replacing EfficientNet classifier."""
    def __init__(self, in_features: int):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.4),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x).squeeze(-1)


class EfficientNetB4Detector:
    name = "efficientnet_b4"

    def __init__(self, weights: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        backbone = timm.create_model("efficientnet_b4", pretrained=True, num_classes=0)
        in_features = backbone.num_features
        self.model = nn.Sequential(backbone, DeepfakeHead(in_features))
        if weights.exists():
            state = torch.load(weights, map_location=self.device)
            self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

    def predict(self, media_path: str, media_type: Any = None) -> dict:
        """
        Returns:
            score: float 0→1 (deepfake probability)
            confidence: float 0→1
            regions: list of bounding box dicts
        """
        img = Image.open(media_path).convert("RGB")
        tensor = TRANSFORM(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            score = self.model(tensor).item()

        # Confidence = distance from 0.5 decision boundary, scaled
        confidence = min(1.0, abs(score - 0.5) * 2.5)

        return {
            "score": round(score, 6),
            "confidence": round(confidence, 6),
            "regions": self._extract_regions(tensor, score),
        }

    def _extract_regions(self, tensor: torch.Tensor, score: float) -> list[dict]:
        """Simplified region detection — full impl uses GradCAM in explainability module."""
        if score < 0.5:
            return []
        return [{"x": 0, "y": 0, "w": 1.0, "h": 1.0, "score": score}]


class EfficientNetB4Trainer:
    """Handles fine-tuning for custom datasets."""

    def __init__(self, base_model: EfficientNetB4Detector):
        self.model = base_model.model
        self.device = base_model.device

    def unfreeze_top_layers(self, n_blocks: int = 3):
        """Unfreeze last N blocks of the backbone for fine-tuning."""
        backbone = self.model[0]
        blocks = list(backbone.children())
        for layer in blocks[:-n_blocks]:
            for param in layer.parameters():
                param.requires_grad = False
        for layer in blocks[-n_blocks:]:
            for param in layer.parameters():
                param.requires_grad = True

    def train_epoch(self, dataloader, optimizer, criterion) -> dict[str, float]:
        self.model.train()
        total_loss, correct, total = 0.0, 0, 0
        for imgs, labels in dataloader:
            imgs, labels = imgs.to(self.device), labels.float().to(self.device)
            optimizer.zero_grad()
            preds = self.model(imgs)
            loss = criterion(preds, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
            correct += ((preds >= 0.5) == labels).sum().item()
            total += imgs.size(0)
        return {"loss": total_loss / total, "accuracy": correct / total}
