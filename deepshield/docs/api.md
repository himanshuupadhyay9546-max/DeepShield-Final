# DeepShield Enterprise — API Documentation

Base URL: `https://api.deepshield.ai/api/v1`

## Authentication

All endpoints require a Bearer token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

Get a token via `POST /auth/login`.

---

## Endpoints

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login, returns JWT |
| POST | `/auth/logout` | Revoke token |
| POST | `/auth/refresh` | Refresh token |
| GET  | `/auth/me` | Current user info |

**Login example:**
```json
POST /auth/login
{ "email": "analyst@org.com", "password": "secret" }

Response:
{ "access_token": "eyJ...", "expires_in": 3600, "role": "analyst" }
```

---

### Detection

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| POST | `/detect/image` | `detect` | Analyze image (sync) |
| POST | `/detect/video` | `detect` | Analyze video (async) |
| POST | `/detect/audio` | `detect` | Analyze audio (sync) |
| GET  | `/detect/{id}` | `detect` | Poll analysis status |
| GET  | `/detect/{id}/report` | `reports` | Download PDF report |

**Image detection response:**
```json
{
  "analysis_id": "uuid",
  "status": "completed",
  "verdict": "deepfake",
  "confidence": 0.962,
  "fake_probability": 0.941,
  "heatmap_url": "https://cdn.deepshield.ai/heatmaps/...",
  "processing_ms": 187
}
```

---

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/{analysis_id}` | Get report metadata |
| GET | `/reports/{analysis_id}/pdf` | Download forensic PDF |
| POST | `/reports/{analysis_id}/anchor` | Anchor to blockchain |

---

### Admin

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/admin/users` | `admin:org` | List users |
| POST | `/admin/users` | `admin:org` | Create user |
| GET | `/admin/api-keys` | `admin:org` | List API keys |
| POST | `/admin/api-keys` | `admin:org` | Create API key |
| GET | `/admin/audit-logs` | `admin:org` | View audit logs |
| GET | `/admin/usage` | `admin:org` | Usage statistics |

---

### Real-time (WebSocket)

```
WS wss://api.deepshield.ai/api/v1/realtime/ws?token=<jwt>
```

Subscribe to live events:
```json
{ "action": "subscribe", "channels": ["detections", "threats"] }
```

Receive events:
```json
{
  "event": "detection",
  "analysis_id": "uuid",
  "verdict": "deepfake",
  "confidence": 0.94,
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## Rate Limits

| Plan | Requests/min |
|------|-------------|
| Free | 60 |
| Pro | 600 |
| Enterprise | 6,000 |
| Government | Unlimited |

Rate limit headers returned on every response:
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 587
X-RateLimit-Reset: 1735689660
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request — invalid file type or parameters |
| 401 | Unauthorized — missing or expired token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not found — analysis ID does not exist |
| 413 | File too large — exceeds 500MB limit |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## SDKs

Official SDKs available:
- Python: `pip install deepshield-sdk`
- Node.js: `npm install @deepshield/sdk`
- Go: `go get github.com/deepshield/go-sdk`

**Python quick-start:**
```python
from deepshield import DeepShieldClient

client = DeepShieldClient(api_key="ds_live_xxx")
result = client.detect.image("path/to/image.jpg")
print(result.verdict, result.confidence)
# deepfake 0.962
```
