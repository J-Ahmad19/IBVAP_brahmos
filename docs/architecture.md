# IBVAP Architecture Contract

This document serves as the absolute source of truth for the Intelligent Border Video Analytics Platform (IBVAP). It freezes the architecture boundaries, module responsibilities, and deployment constraints.

## 1. Core Architecture Modules (Frozen)

1. **Camera Abstraction**
   Every camera source (webcam, file, RTSP) must be abstracted via a unified `CameraSource` interface (`read()`, `health()`, `close()`). Downstream components must never care about the underlying source type.

2. **Shared CPU-aware Scheduler**
   Inference is managed by a single shared worker pool. It round-robins across active cameras, capping the global frame rate to protect the CPU. Do not spin up one heavyweight inference loop per camera.

3. **Detection**
   Detection utilizes **YOLO11n** or **YOLOv8n**, exported to OpenVINO IR (for Intel) or ONNX Runtime (fallback). It produces normalized bounding boxes and confidences for humans and vehicles.

4. **Tracking**
   Multi-object tracking utilizes **ByteTrack**. It persists identities across frames using IoU and motion cues, prioritizing low-cost tracking without requiring a separate deep appearance network for Phase 1.

5. **Conditional AI**
   Expensive AI models must branch conditionally from upstream detection:
   - **Person Path:** YOLO person box -> InsightFace (`buffalo_s`) -> Qdrant search.
   - **Vehicle Path:** YOLO vehicle box -> Plate Localizer -> PaddleOCR (Mobile) -> Regex Validator.
   - **Low Light Path:** Low confidence + pixel change -> CLAHE -> fallback motion detection.

6. **Rules**
   Activity rules are explainable and geometric:
   - **Virtual Fence:** Point-in-polygon tracking (Shapely), debounced over N frames.
   - **Loitering:** Stationary track bounding box exceeding a dwell time threshold.
   - **Suspicious Movement:** Track trajectory analysis (rapid approach).

7. **Normalized Event**
   Every analytics and rule module must produce the exact same JSON Event schema:
   `{ event_id, type, camera_id, timestamp, track_id, confidence, severity, media_ref, metadata }`

8. **Event Transport**
   The internal event bus utilizes **Redis**. Producers use an `EventPublisher` abstraction, ensuring zero tight coupling between the inference worker and the consumer logic.

9. **Persistence**
   The persistence layer is composed of:
   - **PostgreSQL + TimescaleDB**: The system of record for events, tracks, cameras, and metadata.
   - **Qdrant**: Vector storage for face and plate embeddings.
   - **MinIO**: Object storage for alert evidence (snapshots, clips).

10. **API**
    A **FastAPI** service sits between the persistence layer and the frontend. It provides REST endpoints for configuration/history and WebSocket endpoints for real-time live alerts.

11. **Frontend**
    A React-based operator dashboard focused on operational clarity (dark mode, mission-control styling). It consumes the FastAPI layer and visualizes live camera tiles, event feeds, and telemetry.

---

## 2. Deployment Modes

### MODE A — SIH CPU PROTOTYPE
*This is the immediate implementation target.*
- **Hardware:** Laptop (CPU-only inference).
- **Sources:** Webcam and pre-recorded video files (looping to simulate continuous feed).
- **Orchestration:** Docker Compose (single host).
- **Compute Constraints:** Shared round-robin inference scheduling with nano/small models (OpenVINO/ONNX).

### MODE B — FUTURE FIELD DEPLOYMENT
*This defines the upgrade path but must NOT be implemented in Phase 1.*
- **Hardware:** Edge compute boxes (Jetson/GPU acceleration).
- **Sources:** Live RTSP/IP cameras via hardware-accelerated GStreamer.
- **Orchestration:** Kubernetes (central) / Remote Edge Gateways.
- **Transport:** MQTT/Kafka for WAN-tolerant store-and-forward syncing to a Central Command (C2) platform.
- **Intelligence:** Neo4j cross-camera entity graph, DeepStream pipelines, TensorRT optimization.

---

## 3. Architecture Decision Rules

To ensure system integrity, the following rules are non-negotiable:

- **Frontend never talks directly to databases.** All database queries (Postgres, Qdrant, MinIO) must be routed through the FastAPI layer.
- **Every analytics module emits the same Event schema.** No custom event JSON shapes are allowed.
- **Camera source is hardware-agnostic.** The pipeline must accept frames without caring if they originated from a webcam, an MP4 file, or an RTSP stream.
- **Inference-worker owns AI compute.** The FastAPI container and frontend must never run heavy AI models.
- **API owns persistence/orchestration.** The inference-worker writes events to Redis; it does not directly write to Postgres.
- **Expensive AI is conditional.** OCR and Face Recognition must only trigger on localized object crops. They must never scan the full 1080p frame.
- **No unsupported benchmark claims.** Inference metrics (FPS, drop rate) must be genuine measurements from the running machine.
- **No fake demo metrics.** If the system is offline, the UI must show "NO DATA", not a fabricated 98% uptime or random alert count.
