# IBVAP — Full Build Architecture (CPU-Only Prototype)
### Constraints locked in: laptop, no GPU · sources = webcam + pre-recorded video files (multi-camera simulated) · build starts after this document

Every technology choice below is justified against your actual constraints (CPU-only inference, multiple simulated "camera" streams from video files/webcam), not the generic GPU-edge-box version from the first document. Where a choice comes from a specific paper/benchmark/doc, it's cited **inline** and listed in full in §9, with a note on exactly what was taken from it — nothing is asserted without a reason.

---

## 1. What changes because you're CPU-only

Running eight AI capabilities across multiple simulated camera streams, on a laptop CPU, in real time is the actual engineering constraint you're designing against — not "which model has the highest mAP." Three decisions follow directly from that:

1. **Model size**: nano/small variants only (YOLO**n**, not YOLO-L/X), and always exported to an inference runtime built for CPU, never run as raw PyTorch `.pt` in production. Benchmarks show YOLOv8n on a CPU (no CUDA) gets ~13 fps in raw PyTorch but jumps to 32–33 fps once exported to ONNX/OpenVINO on the same machine — a >2× free speedup from format alone [Ref 1]. On Intel CPUs specifically, OpenVINO is reported to beat plain ONNX Runtime further, "a 2–3× free lunch" over PyTorch CPU, because it uses kernels tuned to the chip's exact instruction set (AVX2/AVX-512) [Ref 2]. **Decision: export every model to OpenVINO IR (fallback to ONNX Runtime if you're on AMD, since OpenVINO's advantage is Intel-specific [Ref 2]).**
2. **Frame sampling, not full fps**: run inference at 3–8 fps per stream and let OpenCV/GStreamer just display at native fps — this is standard practice and is what makes multi-stream CPU inference survivable at all.
3. **Sequential/rotational inference across streams**, not true-parallel: with N simulated cameras (webcam + video files) on one CPU, a single shared inference worker cycles through streams frame-by-frame rather than spinning one heavyweight model instance per stream (which would thrash CPU cache and RAM). This is a queue-and-worker pattern, not a "camera 1 gets its own YOLO" pattern.

This also means: **drop DeepStream and Triton from the prototype** — both assume NVIDIA GPU hardware and add nothing on CPU. They stay in the doc as a documented "Phase 2 / real deployment" upgrade path (§8), not part of what you build now.

---

## 2. Full System Architecture (CPU Prototype)

```
┌───────────────────────────────────────────────────────────────────────┐
│                         SOURCE LAYER (simulated cameras)                │
│   Webcam (cv2.VideoCapture(0))     Video files (rtsp-sim via loopback   │
│                                     OR read directly as "camera-N")     │
│   Each source registered as a "camera" row in the DB with an id,       │
│   independent of whether it's physically a webcam, a file, or (later)  │
│   a real RTSP URL — this abstraction is what lets you swap in real     │
│   CCTV later without touching downstream code.                         │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ frames (numpy arrays via OpenCV)
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    FRAME SAMPLER / SCHEDULER (Python)                  │
│   Round-robins across active camera sources at a capped global frame   │
│   budget (e.g., 15 total inferences/sec shared across all sources) so  │
│   CPU load stays bounded regardless of camera count.                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                  INFERENCE WORKER POOL (OpenVINO / ONNX Runtime)       │
│                                                                         │
│  Stage 1 — Detection: YOLO11n / YOLOv8n (OpenVINO IR, INT8)            │
│         → person, vehicle classes                                     │
│  Stage 2 — Tracking: ByteTrack (pure Python/NumPy, CPU-cheap, no       │
│         separate DNN — motion + IoU only) [Ref 3, 4]                  │
│  Stage 3a — ANPR (conditional: only on vehicle boxes):                 │
│         small plate-localizer YOLO head → PaddleOCR "mobile"/lightweight│
│         recognition model → Indian-plate-format validator regex        │
│  Stage 3b — Face (conditional: only on person boxes):                  │
│         InsightFace buffalo_s (lightweight RetinaFace+ArcFace bundle,  │
│         CPU-runnable via onnxruntime) → embedding → watchlist lookup   │
│  Stage 3c — Rules engine (pure Python, near-zero cost):                │
│         virtual-fence polygon test, loitering timer, night-motion      │
│         fallback (frame-diff heatmap), suspicious-activity heuristics  │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         EVENT BUS (in-process for prototype)           │
│   Python asyncio.Queue / Redis (single container) — every module       │
│   above emits a normalized Event(type, camera_id, ts, track_id,        │
│   confidence, media_ref) object here. Swappable for Kafka/MQTT later   │
│   without touching producer code (§8).                                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER (all Dockerized)                  │
│  PostgreSQL + TimescaleDB — events, camera health, track history       │
│  Qdrant — face embeddings + plate-watchlist vectors for similarity     │
│  MinIO — alert snapshots / short clips (S3-compatible, local)          │
│  (Neo4j — optional, only if time allows; cross-camera co-occurrence)   │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     BACKEND API (FastAPI, async)                       │
│  REST endpoints (cameras, events, watchlist CRUD) + WebSocket channel   │
│  for live alert push to the dashboard                                  │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                  FRONTEND DASHBOARD (React)                            │
│  Live annotated stream tiles (MJPEG/WebRTC preview per "camera"),      │
│  alert feed (WebSocket), event timeline, watchlist management UI,      │
│  virtual-fence polygon editor (draw-on-canvas over a camera frame)     │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Full Technology Stack — every choice sourced

| Component | Technology | Sourced justification |
|---|---|---|
| Language/runtime | Python 3.11, Docker/Docker Compose | Fixed by you |
| Video capture (webcam + files) | **OpenCV `VideoCapture`** for local webcam/file sources | Standard, zero-dependency way to read both a webcam index and a video file with the same API — no RTSP-specific tooling needed since you have no real IP cameras yet |
| Detection model | **YOLO11n or YOLOv8n**, exported to **OpenVINO IR (INT8)** | Ultralytics' own OpenVINO export docs show yolo11n inference around 32–80ms/frame on an Intel i9 CPU depending on resolution [Ref 5]; a LattePanda Mu CPU benchmark shows YOLOv8n going from raw ~4-7 fps to 7-9 fps after OpenVINO INT8 quantization, and further to 15-20 fps if any integrated GPU is available [Ref 6]; OpenVINO is described as "usually noticeably faster on Intel CPUs" than ONNX Runtime, a "2-3× free lunch" [Ref 2] |
| Inference runtime | **OpenVINO Runtime** (Intel CPU) or **ONNX Runtime** (AMD/other CPU) | Same as above — OpenVINO wins on Intel via AVX2/AVX-512/AMT-tuned kernels; ONNX Runtime is "equal or better" on non-Intel CPUs, so keep both export paths [Ref 2] |
| Multi-object tracking | **ByteTrack** | Associates every detection box (even low-confidence) using only motion — no separate neural network, so it adds almost no CPU cost beyond the detector itself; reported up to ~170 fps standalone in comparative studies, i.e., tracking will never be your bottleneck [Ref 3, 4] |
| ANPR — plate localization | Small YOLO head (same detector family, extra class or a second nano model) | Keeps you on one runtime/toolchain instead of introducing a separate detection framework |
| ANPR — OCR | **PaddleOCR (mobile/lightweight recognition model, PP-OCR series)** | Independent CPU-latency comparisons show real spread across engines — Tesseract is fastest raw (~450ms) but PaddleOCR/EasyOCR trade some speed for materially higher precision on real-world/scene text [Ref 7]; PaddleOCR's own lightweight PP-OCR line is explicitly built to "run on regular CPUs" while staying compact [Ref 8]. **Practical compromise for the prototype:** default to PaddleOCR's lightweight/mobile model for accuracy on Indian plates; keep Tesseract wired in as a fast fallback if a demo machine is too slow |
| ANPR — format correction | Regex/rule validator for Indian plate schema (state + RTO + series + number) | Same as first document — no model needed, pure string logic |
| Face detection + recognition | **InsightFace, `buffalo_s` (lightweight) bundle: RetinaFace detector + ArcFace embeddings**, run via `onnxruntime` (CPU provider) | InsightFace ships ONNX models specifically so they can run without a GPU; ArcFace's angular-margin loss is the reference approach for discriminative face embeddings and remains "dominant in practice" per a 2026 surveillance-systems survey specifically because of its accuracy/robustness/**low inference cost** balance [Ref 9]. `buffalo_l` (the large bundle) is what most tutorials default to, but `buffalo_s` trades a small accuracy drop for materially lower CPU latency — the right trade for your constraint |
| Face/plate similarity search | **Qdrant** | Sub-second nearest-neighbor lookup over embeddings; runs fine as a single Docker container on a laptop for prototype-scale watchlists |
| Virtual fence / loitering / night-motion rules | Pure Python (Shapely for polygon-crossing tests, OpenCV `absdiff` for frame-differencing motion heatmap at night) | Zero additional ML cost — this is exactly the kind of module that should NOT eat your CPU budget, since the AI budget is needed for detection/face/OCR |
| Night-time preprocessing | **CLAHE (`cv2.createCLAHE`)** applied to low-light frames before detection | Classic, cheap, well-established low-light contrast recovery technique that runs in milliseconds on CPU, unlike learned low-light-enhancement networks (e.g., Zero-DCE) which would burn extra inference budget you don't have on this hardware |
| Event bus | **Redis** (single container) for prototype; `asyncio.Queue` in-process if you want zero extra containers for the first working version | Lightweight pub/sub, trivial Docker footprint, and a clean seam to swap for Kafka/MQTT later without touching event-producing code |
| Event/time-series store | **PostgreSQL + TimescaleDB** | You already use this stack; hypertables give fast time-range queries ("all events between 2-4AM") without custom indexing work |
| Object storage | **MinIO** | Local S3-compatible storage for alert snapshots/clips — same container runs unchanged if you later move to a real server |
| Backend API | **FastAPI** | Matches your stack; native async fits the WebSocket live-alert requirement well |
| Frontend | **React** | Matches your stack |
| Containerization | **Docker Compose** (single `docker-compose.yml`, one file per service: ingestion, inference-worker, api, postgres, redis, qdrant, minio, frontend) | Directly matches your stated Docker requirement; Compose (not Kubernetes) is the right scope for a single-laptop prototype — don't over-engineer this for the demo stage |

---

## 4. Docker Compose Service Layout

```
services:
  postgres        # Postgres + TimescaleDB extension
  redis           # event bus
  qdrant          # face/plate embedding search
  minio           # snapshot/clip storage
  inference-worker  # Python: capture -> detect -> track -> ANPR/face/rules -> publish events
  api             # FastAPI: REST + WebSocket, reads/writes postgres+qdrant+minio
  frontend        # React dev/prod build, served via nginx or vite preview
```

`inference-worker` is the one container that actually needs care on CPU: keep it single-process with an internal thread/async pool rather than spinning one container per camera, or you'll oversubscribe the CPU immediately with just 2-3 simulated streams.

---

## 5. Simulating Multiple Cameras from What You Have

Since your sources are a webcam plus pre-recorded video files (and possibly more later):

- Treat every source uniformly as a row in a `cameras` table: `{id, name, source_type: 'webcam'|'file'|'rtsp', source_uri}`. `source_uri` is `0` for the default webcam, a file path for recordings, and (later) an `rtsp://...` URL — the ingestion code only branches on `source_type`, nothing downstream cares.
- For video files, loop playback (`cv2.CAP_PROP_POS_FRAMES = 0` on EOF) so a demo can run indefinitely like a real live feed.
- To simulate several simultaneous "cameras" from a limited number of files, it's completely fair (and common in CV prototyping) to register the same file twice under different camera IDs with different virtual-fence zones drawn on each — the pipeline doesn't know or care that the pixels are duplicated, and it demonstrates true multi-camera load on the scheduler.
- This design is also exactly what makes swapping in real BOP RTSP cameras later a config change, not a rewrite — worth saying explicitly in your SIH pitch.

---

## 6. Per-Module Pipeline Detail (CPU-tuned)

**Human detection & tracking** — YOLO11n(OpenVINO) → person boxes → ByteTrack → persistent IDs → written to `tracks` table.

**Vehicle detection & classification** — same detector, vehicle classes (car/truck/2-wheeler) → feeds ANPR trigger only (don't run OCR on every frame — only on frames with a confident vehicle box, this is the single biggest CPU saver for the ANPR path).

**Face detection & recognition** — only run InsightFace on frames where a `person` box exists (never scan a whole empty frame for faces) → embed → Qdrant nearest-neighbor vs watchlist collection → alert above similarity threshold, always shown to a human, never auto-actioned.

**ANPR** — plate crop from vehicle box → PaddleOCR mobile model → regex validate against Indian plate format → cross-check `watchlist_vehicles` table.

**Virtual fence / intrusion** — Shapely polygon per camera (drawn once via the frontend's canvas editor) → each track's foot-point tested per processed frame → debounce over N consecutive hits to kill single-frame noise (this rule module runs on every processed frame regardless of camera source and costs essentially nothing).

**Suspicious activity** — rule-based first (same-track-ID stationary > T seconds in an ROI = loitering; rapid approach toward a fence line = flagged) — no extra model, reuses the tracker's trajectory data.

**Night-time movement** — CLAHE preprocessing before detection; if detector confidence stays low but `cv2.absdiff`-based frame-differencing shows significant pixel change in an ROI, raise a lower-confidence "unclassified movement" alert rather than silently dropping it.

**Alerting & event logging** — every module above emits one normalized `Event` onto Redis → a lightweight alert-engine consumer assigns severity, writes to TimescaleDB, saves a snapshot to MinIO, and pushes to the FastAPI WebSocket for the dashboard.

---

## 7. What NOT to Build Yet (be explicit about this in your pitch)

- DeepStream / TensorRT / Triton — GPU-only, irrelevant to your current hardware; documented as future path only.
- Kubernetes — Compose is the right scope for one laptop; don't add orchestration complexity you don't need for a demo.
- Kafka — Redis is enough at this scale; swapping it in later is a config change since producers/consumers only ever touch an abstract "publish event" interface.
- Action-recognition ML (pose-based suspicious-activity detection) — rule-based heuristics get you a working, explainable prototype; a learned model here is a stretch goal, not a Phase-1 requirement, and on CPU it would compete for the exact compute budget your core detector needs.

---

## 8. Upgrade Path to Real Deployment (documented, not built now)

When you move beyond a laptop demo to real BOP hardware: swap `inference-worker`'s OpenVINO backend for TensorRT if a GPU/Jetson edge box becomes available; swap RTSP ingestion in via GStreamer for hardware-accelerated decode; swap Redis for Kafka/MQTT for durability across a WAN link; add the store-and-forward edge/central split described in the first architecture document. None of this requires rewriting the module logic — only the runtime/transport layers, because the `Event` object and `cameras` abstraction were designed to be source- and hardware-agnostic from day one.

---

## 9. References — what was taken from each

1. **Ultralytics GitHub Issue #8602**, "Seeking Advice: YOLOv8 Performance – fps CUDA ONNX" (github.com/ultralytics/ultralytics/issues/8602) — used for the concrete CPU vs ONNX vs OpenVINO fps numbers on one real machine (13 fps raw PyTorch CPU → 32-33 fps after ONNX/OpenVINO export), justifying "always export before deploying on CPU."
2. **Ultralytics Academy, "OpenVINO on CPU" (academy.ultralytics.com/courses/yolo-in-production/openvino-on-cpu)** — used for the Intel-specific reasoning (AVX2/AVX-512/AMX-tuned kernels) behind picking OpenVINO over plain ONNX Runtime on Intel CPUs, and the "ONNX Runtime is equal or better on AMD/non-x86" caveat used to justify keeping both export paths.
3. **ForaSoft, "Multi-Object Tracking — DeepSORT, ByteTrack, OC-SORT..." (forasoft.com)** — used for ByteTrack's core design fact (uses no appearance features/no extra deep network, matches every detection box via motion only) and its MOT17 benchmark numbers, justifying it as the near-zero-extra-cost tracker choice for CPU.
4. **Roboflow, "Top 7 Open Source Object Tracking Tools" (blog.roboflow.com)** — used for the practical framing that ByteTrack is "the faster default for counting, zones, and most real-time pipelines," supporting the fence/loitering-rule use case specifically.
5. **OpenVINO documentation, "Convert and Optimize YOLOv11 real-time object detection with OpenVINO" (docs.openvino.ai)** — used for real measured yolo11n CPU inference latency (~32-80ms/frame on an Intel i9) as a sanity-check reference point for what to expect on a laptop CPU.
6. **LattePanda blog, "Optimize Object Detection with YOLOv8 & OpenVINO on LattePanda Mu" (lattepanda.com)** — used for before/after CPU fps numbers under INT8 quantization (4-7 fps → 7-9 fps on CPU alone), the concrete evidence behind recommending INT8 OpenVINO export specifically, not just any export.
7. **arXiv 2603.17357, "WebPII: Benchmarking Visual PII Detection for Computer-Use Agents"** — used for its OCR-engine latency table (Tesseract 453ms, EasyOCR 715ms, PaddleOCR 2143ms on comparable hardware) to justify the accuracy/speed trade-off framing between the three engines and keeping Tesseract wired in as a fast fallback.
8. **DEV Community, "PaddleOCR-VL-0.9B... Ultra-Lightweight Document Parsing Powerhouse"** — used specifically for the claim that PaddleOCR's lightweight models are explicitly designed to "run on regular CPUs," supporting PaddleOCR as the default ANPR OCR engine despite being slower than Tesseract.
9. **arXiv 2607.03131, "A Multi-Task Deep Learning Framework for Real-Time Intelligent Video Surveillance with Temporal Event Validation"** — used for its literature-survey claim that ArcFace-style angular-margin embeddings remain dominant in production face-recognition systems specifically because of their balance of accuracy, robustness, and **low inference cost**, and for its explicit use of InsightFace's smaller `buffalo_s` bundle in a real surveillance system design — directly justifying `buffalo_s` over `buffalo_l` for your CPU constraint.
10. **InsightFace GitHub (github.com/deepinsight/insightface)** — used to confirm the project ships ONNX-exportable models runnable via `onnxruntime` without requiring a GPU, and that the toolkit is MIT-licensed (safe for this kind of deployment).

*(References carried over unchanged from the first document — Roboflow/Ultralytics/JetBrains model-landscape overviews, NVIDIA DeepStream docs, IEEE/arXiv MOT and ANPR papers — remain valid background but are not re-cited here since this document only sources what changed for the CPU-only decision.)*
