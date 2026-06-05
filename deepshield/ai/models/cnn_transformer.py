"""
CNN + Transformer Hybrid Detector.
CNN extracts local texture features; Transformer attends to global context.
Best at detecting subtle GAN artifacts and blending boundaries.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])


class CNNTransformerDetector:
    name = "cnn_transformer_hybrid"

    def __init__(self, weights: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = _CNNTransformerModel().to(self.device)
        if weights.exists():
            self.model.load_state_dict(torch.load(weights, map_location=self.device))
        self.model.eval()

    def predict(self, media_path: str, media_type: Any = None) -> dict:
        img    = Image.open(media_path).convert("RGB")
        tensor = TRANSFORM(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            score = self.model(tensor).item()
        return {
            "score":      round(score, 6),
            "confidence": round(min(1.0, abs(score - 0.5) * 2.2), 6),
            "regions":    [],
        }


class _CNNTransformerModel(nn.Module):
    def __init__(self):
        super().__init__()
        # CNN backbone — ResNet50 feature extractor
        resnet = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        self.cnn = nn.Sequential(*list(resnet.children())[:-2])  # remove avgpool + fc
        # Project CNN features to transformer dim
        self.proj = nn.Conv2d(2048, 256, 1)
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(d_model=256, nhead=8, batch_first=True,
                                                    dim_feedforward=512, dropout=0.1)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=4)
        # Classification head
        self.head = nn.Sequential(
            nn.Linear(256, 64), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(64, 1), nn.Sigmoid(),
        )

    def forward(self, x):
        feat = self.cnn(x)                         # (B, 2048, 7, 7)
        feat = self.proj(feat)                     # (B, 256, 7, 7)
        B, C, H, W = feat.shape
        seq  = feat.flatten(2).permute(0, 2, 1)   # (B, 49, 256)
        out  = self.transformer(seq)               # (B, 49, 256)
        pooled = out.mean(dim=1)                   # (B, 256)
        return self.head(pooled).squeeze(-1)
