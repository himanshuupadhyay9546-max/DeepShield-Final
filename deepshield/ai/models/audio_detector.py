"""
Audio Deepfake + Voice Clone Detector
Detects: AI-synthesized speech, voice cloning, audio splicing, TTS artifacts.
Uses MFCC + spectral features fed into a CNN-LSTM hybrid.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import librosa


class AudioFeatureExtractor:
    """
    Extracts multi-scale audio features:
      - MFCC (40 coefficients)
      - Mel-spectrogram
      - Chroma features
      - Spectral contrast
    """
    SR = 16_000
    N_MFCC = 40
    HOP_LENGTH = 512

    def extract(self, audio_path: str) -> np.ndarray:
        y, sr = librosa.load(audio_path, sr=self.SR, mono=True, duration=30.0)

        mfcc       = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self.N_MFCC, hop_length=self.HOP_LENGTH)
        mel        = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=self.HOP_LENGTH)
        mel_db     = librosa.power_to_db(mel, ref=np.max)
        chroma     = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=self.HOP_LENGTH)
        contrast   = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=self.HOP_LENGTH)

        # Normalize and pad/truncate to fixed width
        T = 300  # time frames
        def fix(x): 
            if x.shape[1] >= T: return x[:, :T]
            return np.pad(x, ((0,0),(0, T - x.shape[1])))

        features = np.vstack([
            fix(mfcc),        # (40, T)
            fix(mel_db[:40]), # (40, T)
            fix(chroma),      # (12, T)
            fix(contrast),    # (7, T)
        ])  # (99, T)
        return features.astype(np.float32)


class CNNLSTMAudioClassifier(nn.Module):
    """CNN extracts local patterns; LSTM captures temporal voice characteristics."""
    def __init__(self):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv1d(99, 128, kernel_size=5, padding=2), nn.BatchNorm1d(128), nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(128, 256, kernel_size=5, padding=2), nn.BatchNorm1d(256), nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(256, 128, kernel_size=3, padding=1), nn.ReLU(),
        )
        self.lstm = nn.LSTM(128, 64, num_layers=2, batch_first=True,
                            bidirectional=True, dropout=0.3)
        self.head = nn.Sequential(
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 1), nn.Sigmoid(),
        )

    def forward(self, x):            # x: (B, 99, T)
        feat = self.cnn(x)            # (B, 128, T//4)
        feat = feat.permute(0, 2, 1) # (B, T//4, 128)
        out, _ = self.lstm(feat)      # (B, T//4, 128)
        pooled = out.mean(dim=1)      # (B, 128)
        return self.head(pooled).squeeze(-1)


class AudioDetector:
    name = "audio_cnn_lstm"

    def __init__(self, weights: Path):
        self.device   = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.extractor = AudioFeatureExtractor()
        self.model     = CNNLSTMAudioClassifier().to(self.device)
        if weights.exists():
            self.model.load_state_dict(torch.load(weights, map_location=self.device))
        self.model.eval()

    def predict(self, audio_path: str, media_type: Any = None) -> dict:
        features = self.extractor.extract(audio_path)
        tensor   = torch.from_numpy(features).unsqueeze(0).to(self.device)
        with torch.no_grad():
            score = self.model(tensor).item()
        return {
            "score":      round(score, 6),
            "confidence": round(min(1.0, abs(score - 0.5) * 2.4), 6),
            "regions":    [],
        }
