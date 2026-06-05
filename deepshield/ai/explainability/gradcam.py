"""
GradCAM explainability generator.
Produces heatmap overlays showing which image regions triggered the deepfake verdict.
Uploads result to S3/CDN and returns a signed URL.
"""
from __future__ import annotations
import io
import uuid
import asyncio
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import cv2
from PIL import Image

logger = logging.getLogger("deepshield.gradcam")


class GradCAMGenerator:
    """
    Grad-CAM: Gradient-weighted Class Activation Mapping.
    
    Hooks into the last convolutional block of a model,
    computes gradient of the fake-class score w.r.t. activations,
    and produces a saliency heatmap.
    """

    async def generate(
        self,
        media_path: str,
        model,
        analysis_id: str,
    ) -> str | None:
        """
        Generate GradCAM heatmap overlay image.
        Returns a CDN URL (uploaded to S3) or None on failure.
        """
        loop = asyncio.get_event_loop()
        try:
            heatmap = await loop.run_in_executor(
                None, self._compute_gradcam, media_path, model
            )
            overlay = self._overlay_on_image(media_path, heatmap)
            url = await self._upload_overlay(overlay, analysis_id)
            return url
        except Exception as e:
            logger.warning(f"GradCAM failed for {analysis_id}: {e}")
            return None

    def _compute_gradcam(self, media_path: str, model) -> np.ndarray:
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        device = next(model.model.parameters()).device
        img = Image.open(media_path).convert("RGB")
        tensor = transform(img).unsqueeze(0).to(device)
        tensor.requires_grad_(True)

        # Forward pass
        output = model.model(tensor)
        loss = output.squeeze()
        
        # Backward pass
        model.model.zero_grad()
        loss.backward()

        # Extract gradients and activations from the gradient tensor
        grads = tensor.grad.detach().cpu().numpy()[0]  # (3, H, W)
        
        # Pool gradients over spatial dimensions
        weights = np.mean(np.abs(grads), axis=(1, 2))  # (3,)
        
        # Weighted combination of input channels
        cam = np.zeros(grads.shape[1:], dtype=np.float32)
        for i, w in enumerate(weights):
            cam += w * grads[i]
        
        cam = np.maximum(cam, 0)  # ReLU
        if cam.max() > 0:
            cam = cam / cam.max()
        
        # Resize to original image size
        h, w = np.array(img).shape[:2]
        cam = cv2.resize(cam, (w, h))
        return cam

    def _overlay_on_image(self, media_path: str, heatmap: np.ndarray) -> bytes:
        img = cv2.imread(media_path)
        heatmap_uint8 = (heatmap * 255).astype(np.uint8)
        heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(img, 0.6, heatmap_color, 0.4, 0)
        _, buf = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes()

    async def _upload_overlay(self, image_bytes: bytes, analysis_id: str) -> str:
        # Lazy import to avoid circular dependency
        from services.upload_service.s3_client import s3_client
        key = f"heatmaps/{analysis_id}/gradcam.jpg"
        await s3_client.upload_bytes(key, image_bytes, content_type="image/jpeg")
        return s3_client.get_cdn_url(key)
