# IBVAP — Intelligent Border Video Analytics Platform
### End-to-End Technical Approach for SIH 2026

---

## 1. Problem Reframed in Engineering Terms

Strip away the domain language and this is a **software-defined video intelligence platform** problem:

> Given N unreliable/heterogeneous IP-CCTV RTSP feeds at remote, bandwidth-constrained sites, run a fixed set of CV models on each frame in real time, turn raw detections into *events* (human crossed line, vehicle plate read, face matched to watchlist, loitering, night motion), and deliver those events to a human operator and to other command-and-control (C2) systems — reliably, cheaply, and without proprietary smart-camera hardware.

That reframing drives every architectural decision below: **the hard part is not any single AI model (detection/OCR/face-match are all solved problems with strong open-source models); the hard part is the systems engineering** — stream ingestion at scale, GPU scheduling across many cameras, event de-duplication, offline-tolerant edge operation, and a data model that lets an operator ask "who/what crossed Fence-3 between 2–4 AM last Tuesday" in under a second.

Keep that framing in your SIH presentation — judges will have seen five "YOLO + Flask" surveillance demos; what differentiates a winning solution is the **platform thinking** (multi-camera scale, edge/offline resilience, alert fusion, C2 integration).

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EDGE / BOP SITE (per site)                       │
│                                                                           │
│  IP CCTV (RTSP) ──► Stream Gateway ──► Inference Workers ──► Local Event │
│   (existing,          (ingest,          (Docker, GPU/CPU)     Store      │
│    unmodified)         decode,           - detection                    │
│                        health-check,     - tracking             │       │
│                        reconnect)        - ANPR                 │       │
│                                          - face embed            │       │
│                                          - rules/zones           │       │
│                                                    │              │       │
│                                                    ▼              ▼       │
│                                          Local Alert Bus (MQTT/Redis)    │
│                                                    │                      │
│                                          Edge Cache (SQLite/Postgres +   │
│                                          MinIO) — survives WAN outage    │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │  (async sync, resumable, bandwidth-capped)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CENTRAL / COMMAND PLATFORM (regional HQ / cloud)     │
│                                                                           │
│  Ingress API (FastAPI) → Message Queue (Kafka/RabbitMQ) → Stream          │
│  Processors → Postgres+TimescaleDB (events/telemetry) → Vector DB        │
│  (Qdrant, face/plate embeddings) → Graph DB (Neo4j, entity relationships) │
│  → Object Store (MinIO, clips/snapshots) → Alerting Engine → C2/VMS      │
│  Integration Layer (REST/MQTT/CAP) → React Ops Dashboard                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why edge + central, not pure cloud:** BOPs are remote, bandwidth is limited/intermittent, and 24/7 continuous video upload for dozens of cameras is neither affordable nor resilient. So the AI inference **must run at or near the camera** (edge box per site), and only **compact event metadata + short clips/snapshots** should traverse the WAN to the central platform. This is the single most important design decision for the border-deployment context, and it should be stated explicitly in your presentation as the answer to "cost-effective, scalable, remote-deployable."

---

## 3. Recommended Tech Stack

You said Python + Docker are fixed; everything below is chosen to compose cleanly with that.

| Layer | Choice | Why |
|---|---|---|
| Stream ingestion | **GStreamer** (via `gst-python` or FFmpeg subprocess) + **RTSP** | Industry-standard, hardware-accelerated decode (VAAPI/NVDEC), handles reconnect/jitter far better than raw OpenCV `VideoCapture` at scale |
| Inference orchestration | **NVIDIA DeepStream** if a Jetson/GPU box is available at the edge; else a custom **Python + ONNX Runtime / TensorRT** pipeline | DeepStream gives hardware-accelerated decode→infer→track in one pipeline and is purpose-built for exactly this multi-camera IVA use case; the ONNX/TensorRT fallback covers CPU-only or lower-budget sites |
| Object detection | **YOLO11 / YOLO26** (Ultralytics, AGPL — fine for a government/non-commercial deployment) or **RF-DETR** (Apache-2.0) if you want a permissive license and best-in-class accuracy-per-FPS | YOLO family remains the standard for real-time edge detection; RF-DETR is the newest model to break 60 mAP on COCO in real time and transfers well to unusual domains (useful for camouflage/terrain-heavy border scenes) |
| Multi-object tracking | **ByteTrack** (default) with **BoT-SORT** for crowded/occlusion-heavy zones | ByteTrack matches every detection box (even low-confidence) using only motion, so it stays cheap and fast (170+ FPS reported) while handling most surveillance scenes; BoT-SORT adds appearance re-ID + camera-motion compensation for harder cases |
| Vehicle classification | Fine-tuned YOLO head (car/truck/motorcycle/military-pattern classes) | Same detector, extra output classes — no separate model needed |
| ANPR | **YOLO-tiny plate localizer + PaddleOCR (or EasyOCR)** for character recognition, with a rule-based post-processor for Indian plate formats (state code + RTO code + series + number, incl. HSRP hologram cues) | This detector+OCR combination is the standard open-source ANPR pattern and is well documented for Indian plates specifically |
| Face detection & recognition | **InsightFace** (RetinaFace detector + ArcFace/buffalo_l embeddings), MIT-licensed | State-of-the-art open-source accuracy (near NIST-FRVT top ranks), ONNX-exportable, INT8-quantizable for edge, ~30fps on modest GPUs — ideal for a watchlist-matching use case |
| Face/plate similarity search | **Qdrant** (vector DB) | You already know this stack — store ArcFace/plate embeddings, do sub-second nearest-neighbor watchlist matching at scale |
| Night / low-light | Frame-level **CLAHE / Zero-DCE / gamma-adaptive preprocessing** before detection, IR-camera awareness, plus a **motion-heatmap + low-confidence-detector fusion** rule for "movement detected but unclassifiable" alerts | Standard low-light enhancement techniques recover usable signal from existing IR/low-lux CCTV without new hardware; research shows nighttime detection also benefits from dedicated NIR-aware augmentation during training |
| Virtual fence / intrusion | Polygon/line ROI defined per camera in a config UI; tracked object centroid/foot-point crossing test each frame, debounced over N frames to cut false triggers | Classic, cheap, camera-agnostic — no extra model needed, just geometry over tracker output |
| Suspicious activity | Rule layer first (loitering = same track ID stationary > T seconds in ROI; running toward fence; group clustering near fence at night) + optional lightweight action-recognition model (e.g., a small 3D-CNN or pose-based heuristic using **MediaPipe/RTMPose** keypoints) as a stretch goal | Rules alone go a long way and are explainable/auditable — important for a security context where false positives have consequences; add ML action-recognition only once the rule layer is solid |
| Event bus (edge) | **MQTT (Mosquitto)** or **Redis Streams** | Lightweight, works over flaky links, natural pub/sub for "camera → event → alert" |
| Event bus (central) | **Kafka or RabbitMQ** | Durable, replayable, decouples ingestion from processing/alerting/storage fan-out |
| Relational + time-series store | **PostgreSQL + TimescaleDB** | You already use this — perfect for event streams, per-camera health telemetry, alert history, retention/rollup policies |
| Entity relationship store | **Neo4j** | Answers "which vehicles/faces were seen at which BOPs together" — graph queries for pattern-of-life / co-occurrence analysis across cameras and time, which is exactly the kind of intelligence a border-security C2 wants |
| Object/blob storage | **MinIO** | Snapshots, alert video clips, model artifacts — S3-compatible, self-hostable in an air-gapped/on-prem border network |
| Backend API | **FastAPI** | Matches your existing stack; async-native, great for streaming websocket alerts to the dashboard |
| Frontend / Ops dashboard | **React** (+ a map/GIS layer — Leaflet/Mapbox for BOP geolocation, live camera tiles, alert timeline) | Matches your stack |
| Containerization / deployment | **Docker + Docker Compose** for a single edge box; **Kubernetes (K3s)** optional for the central multi-GPU cluster if scaling beyond a handful of servers | K3s is lightweight enough to still run at a regional hub while Compose suffices at a single BOP edge box |
| Model serving (central, batch/multi-model) | **NVIDIA Triton Inference Server** | Lets you version, batch, and GPU-share multiple models (detector, tracker embedder, ANPR OCR, face embedder) efficiently if you consolidate inference centrally for lower-tier sites without local GPUs |
| LLM-assisted layer (optional, differentiator) | A small LLM (via API or local) that turns structured event logs into a natural-language shift summary / incident report | You already integrate LLM APIs in your current work — this is a strong "wow factor" add for the judges: "Generate today's incident report for Sector 4" in plain English |

---

## 4. Functional Modules — Design Detail

### 4.1 Stream Ingestion & Health Management
- Each RTSP camera gets a dedicated lightweight consumer process/thread (not one giant loop) so one dead camera doesn't stall others.
- Auto-reconnect with exponential backoff; heartbeat table in Postgres (`camera_id, last_frame_ts, status`) drives a "camera health" panel on the dashboard — border ops care as much about "is my camera even alive" as about AI alerts.
- Adaptive frame sampling: run detection at 5–10 fps (not the CCTV's native 25/30 fps) — sufficient for humans/vehicles, saves massive compute, and is the standard trade-off in production video analytics.

### 4.2 Human Detection & Tracking
- Detector → ByteTrack assigns persistent track IDs → track IDs feed the virtual-fence and loitering rules.
- Track metadata (bbox trail, first-seen/last-seen, camera_id) written to TimescaleDB as a hypertable for fast time-range queries.

### 4.3 Vehicle Detection & Classification
- Same detector, vehicle-class outputs (car/truck/2-wheeler/military/unknown) — feed directly into the ANPR trigger (only run OCR on frames where a vehicle box is confidently detected, to save compute).

### 4.4 Face Detection & Recognition (Watchlist Matching)
- RetinaFace detects + aligns faces from any frame containing a person; ArcFace embeds each face (512-d vector).
- Embeddings are queried against a **Qdrant** watchlist collection (BOLO / persons-of-interest); a match above a similarity threshold raises a `face_match` alert with confidence score, never an auto-block — always human-in-the-loop for anything with legal/civil-liberties weight.
- Log unmatched faces as anonymized embeddings only (not raw crops retained long-term) for privacy-by-design — worth stating explicitly to judges, this is a common evaluation criterion.

### 4.5 ANPR
- Plate localizer (small YOLO head) crops candidate plates from vehicle boxes → PaddleOCR reads characters → regex/format validator against the Indian plate schema (state + RTO + series + number) corrects common OCR confusions (0/O, 1/I, 8/B) → result written with confidence + camera + timestamp → cross-referenced against a stolen/watchlist vehicle table.

### 4.6 Virtual Fence / Intrusion Detection
- Per-camera polygon/line drawn once during setup (stored as GeoJSON-like coordinates in Postgres, scaled to that camera's resolution).
- Every tracked object's foot-point tested against the polygon each frame; crossing triggers an alert only after N consecutive frames to suppress single-frame noise (branch sway, birds, camera jitter).
- Direction-aware (inbound vs outbound crossing) using track trajectory.

### 4.7 Suspicious Activity Detection
- Start rule-based (loitering, fence approach speed, after-hours presence in restricted ROI, group formation near fence) — this is fast to build, explainable, and demoable within a hackathon timeline.
- Stretch goal: pose-based heuristics (crouching, crawling, climbing motion) via lightweight keypoint models, or a small temporal-CNN classifier if time allows — call this "Phase 2" in your roadmap rather than over-promising it for the prototype.

### 4.8 Night-Time Movement Detection
- Preprocess low-light frames (CLAHE/gamma correction) before running the same detector; fall back to a motion-heatmap (frame-differencing) alert when the detector confidence is too low to classify but pixel-level motion is significant — better to raise a generic "movement detected, unclassified" alert than to miss an intrusion because the detector couldn't confidently label it in the dark.

### 4.9 Real-Time Alerting & Event Logging
- Every module emits a normalized `Event` object (type, camera_id, timestamp, bbox/track_id, confidence, media_ref) onto the event bus.
- An **Alert Engine** applies business rules for severity/priority (e.g., face match on a national watchlist = critical; single loitering event = low) and fans out via WebSocket (dashboard), MQTT/webhook (external C2 systems), SMS/email (duty officer) — decoupled so adding a new alert channel never touches the detection code.
- All events are immutably logged (append-only) in TimescaleDB with the associated clip/snapshot in MinIO for audit and after-action review.

---

## 5. Data Model Sketch

```
cameras(id, bop_id, name, rtsp_url, lat, lon, status, last_seen)
tracks(id, camera_id, class, first_ts, last_ts, trajectory JSONB)
events(id, ts, camera_id, event_type, track_id, confidence, severity,
       media_ref, metadata JSONB)          -- Timescale hypertable on ts
face_embeddings(id, person_label, watchlist_flag, embedding VECTOR(512))  -- Qdrant
plate_reads(id, event_id, plate_text, confidence, vehicle_class)
watchlist_vehicles(plate_text, reason, added_by, added_ts)
entities_graph                              -- Neo4j: (Person)-[SEEN_AT]->(Camera),
                                             --        (Vehicle)-[SEEN_WITH]->(Person)
```

The Neo4j layer is what elevates this from "an alert dashboard" to genuine **intelligence** — e.g. "show every camera where plate DL01AB1234 and a face-matched individual were co-located in the last 30 days" is a two-hop graph query, not a SQL join nightmare.

---

## 6. Deployment Topology for Remote Border Sites

1. **Edge box per BOP** — a ruggedized mini-PC or Jetson Orin (or a mid-range GPU box where power allows), running Docker Compose with: stream gateway, inference containers, local Postgres/SQLite cache, MQTT broker.
2. **Store-and-forward sync** — the edge box buffers events locally and syncs to the central platform whenever WAN connectivity is available (satellite/microwave links are common at BOPs); never blocks local alerting on WAN availability — **the operator at the post must get the alert even if the link to HQ is down**. This should be a headline design point.
3. **Bandwidth-aware media policy** — only alert-triggering snapshots/short clips (not full raw video) are queued for upload, and lower-priority media can be deferred/dropped under bandwidth pressure while metadata always goes through.
4. **Central platform** at a regional/command HQ aggregates events from many BOPs into the unified dashboard, cross-camera intelligence (Neo4j), and long-term storage/analytics.

---

## 7. Why This Is Cost-Effective & Scalable (the ask in the PS)

- **No proprietary smart-camera hardware** — works with any RTSP-capable IP camera already deployed.
- **Commodity compute** — a single mid-tier GPU box can run several camera streams at reduced-fps inference; scale horizontally by adding boxes, not by replacing cameras.
- **Open-source models throughout** (YOLO, ByteTrack, InsightFace, PaddleOCR) — zero per-camera licensing fees, unlike commercial FRS/ANPR appliances.
- **Containerized (Docker)** — identical deployment artifact from a laptop demo to a hardened edge box to a Kubernetes cluster at HQ; this directly answers the "scalable, deployable across strategic installations" requirement.

---

## 8. Suggested Build Roadmap (for the hackathon prototype)

| Phase | Scope |
|---|---|
| 1. Core pipeline | RTSP ingestion → YOLO detection → ByteTrack → live annotated stream in a React dashboard |
| 2. Rule modules | Virtual fence + loitering rules + night motion fallback, event logging to Postgres |
| 3. Identity modules | ANPR (detector+OCR+validator) and face recognition (InsightFace+Qdrant watchlist) |
| 4. Alerting & C2 | Alert engine, WebSocket live alerts, webhook/MQTT export for external C2 integration demo |
| 5. Polish/differentiators | Multi-camera map view, Neo4j co-occurrence intelligence query, LLM-generated shift summary, edge/offline demo (kill the network, show local alerting still works) |

For the SIH demo itself, **Phase 5's "kill the network and show it still works" moment is the single most persuasive live demo** you can give judges, since it directly answers the border-remoteness constraint that a naive cloud-only competitor won't have thought about.

---

## 9. Known Challenges & Honest Mitigations

- **False positives in dense/vegetated border terrain** → mitigate with debounced multi-frame confirmation, per-camera confidence tuning, and human-in-the-loop review for high-severity alerts rather than auto-escalation.
- **Face recognition in low light / oblique angles / masks** → keep confidence thresholds conservative, always show the matched pair (live crop vs watchlist photo) to the operator rather than auto-acting on it.
- **GPU cost at scale** → mitigate with reduced-fps inference, model quantization (INT8/TensorRT), and shared model serving (Triton) at the central tier for lower-priority cameras.
- **Data sensitivity** (biometric data, PII) → embeddings-only long-term storage, role-based access on the dashboard, audit logs on every watchlist query — worth a slide on its own, since responsible-AI/privacy handling is typically part of the SIH evaluation rubric for surveillance-adjacent problem statements.

---

## 10. Key References Consulted

- Roboflow, "Best Object Detection Models 2026" — RF-DETR / YOLO26 benchmarking (blog.roboflow.com)
- Ultralytics, "Best Object Detection Models in 2026" (ultralytics.com/blog)
- ForaSoft, "Multi-Object Tracking — DeepSORT, ByteTrack, OC-SORT" (forasoft.com)
- Roboflow, "Top 7 Open Source Object Tracking Tools" (blog.roboflow.com)
- NVIDIA, "DeepStream SDK" documentation and "Building Vision AI Pipelines" (docs.nvidia.com, developer.nvidia.com)
- InsightFace project (github.com/deepinsight/insightface, insightface.ai) — ArcFace/RetinaFace
- "A Multi-Task Deep Learning Framework for Real-Time Intelligent Video Surveillance with Temporal Event Validation" (arXiv, 2026) — face+detection system design patterns
- Zbotic / PlateRecognizer / open-source GitHub ANPR repos — Indian number-plate format handling
- "Scaling Real-Time Traffic Analytics on Edge-Cloud Fabrics for City-Scale Camera Networks" (arXiv, 2026) — edge/Jetson multi-camera ingestion patterns

---

### One-line pitch for your slide deck
*"IBVAP turns any existing RTSP CCTV camera into an intelligent sensor by running an edge-first, containerized AI pipeline (detection → tracking → ANPR/face/fence rules → alerting) that keeps working even when the link back to headquarters doesn't — all on open-source models, at commodity hardware cost."*
