# IBVAP — Repository Architecture

This maps 1:1 onto the CPU-prototype architecture already agreed: `inference-worker` (capture→detect→track→ANPR/face/rules→publish), `api` (FastAPI), `frontend` (React), plus Postgres/TimescaleDB, Redis, Qdrant, MinIO as infra containers. Each service is its own Docker-buildable folder so any one of them can be developed, tested, and deployed independently.

```
ibvap/
│
├── docker-compose.yml            # Orchestrates all services + infra containers (postgres, redis,
│                                  #   qdrant, minio, inference-worker, api, frontend) for local/dev run
├── .env.example                  # Template for secrets/config (DB creds, ports, model paths) — copy to .env
├── .gitignore                    # Excludes model weights, .env, __pycache__, node_modules, video test data
├── README.md                     # Setup instructions, architecture summary, how to run `docker compose up`
├── Makefile                      # Shortcuts: `make up`, `make export-models`, `make seed`, `make test`
│
├── services/
│   │
│   ├── inference-worker/         # THE core AI pipeline service — capture, detect, track, analyze, publish
│   │   ├── Dockerfile            # Python + OpenVINO/onnxruntime + OpenCV base image
│   │   ├── requirements.txt      # ultralytics, openvino, onnxruntime, opencv-python, insightface,
│   │   │                         #   paddleocr, shapely, redis, pydantic, etc.
│   │   ├── app/
│   │   │   ├── main.py           # Entry point — boots the scheduler loop, wires camera sources to models
│   │   │   ├── config.py         # Loads env vars: frame budget, model paths, thresholds, camera list
│   │   │   │
│   │   │   ├── sources/
│   │   │   │   ├── camera_source.py   # Uniform abstraction: reads webcam / video file / (future) RTSP
│   │   │   │   │                      #   via one interface — `source_type` decides the branch internally
│   │   │   │   └── registry.py        # Loads the `cameras` table/config, exposes list of active sources
│   │   │   │
│   │   │   ├── scheduler.py      # Round-robins across camera sources under a global frame/sec budget so
│   │   │   │                     #   CPU load stays bounded no matter how many "cameras" are simulated
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── detector.py        # YOLO11n/YOLOv8n wrapper — loads OpenVINO IR, returns person/
│   │   │   │   │                      #   vehicle boxes for a frame
│   │   │   │   ├── tracker.py         # ByteTrack wrapper — assigns/maintains persistent track IDs from
│   │   │   │   │                      #   detector output, no separate DNN
│   │   │   │   ├── face.py            # InsightFace (buffalo_s) wrapper — detect+align+embed faces found
│   │   │   │   │                      #   inside person boxes, queries Qdrant watchlist
│   │   │   │   ├── anpr.py            # Plate localizer (YOLO head) + PaddleOCR wrapper — runs only on
│   │   │   │   │                      #   frames with a confident vehicle box
│   │   │   │   └── night.py           # CLAHE preprocessing + frame-differencing motion heatmap for
│   │   │   │                          #   low-light/unclassifiable-movement fallback
│   │   │   │
│   │   │   ├── rules/
│   │   │   │   ├── fence.py           # Shapely polygon-crossing test per camera, debounced over N frames
│   │   │   │   ├── loitering.py       # Flags a track ID stationary in an ROI beyond a time threshold
│   │   │   │   └── activity.py        # Rule-based suspicious-activity heuristics (fast approach, grouping)
│   │   │   │
│   │   │   ├── events/
│   │   │   │   ├── schema.py          # Pydantic `Event` model — the single normalized shape every module
│   │   │   │   │                      #   above emits into (type, camera_id, ts, track_id, confidence, media_ref)
│   │   │   │   └── publisher.py       # Publishes Event objects onto Redis — the only place that knows
│   │   │   │                          #   about the transport, so swapping Redis→Kafka later is isolated here
│   │   │   │
│   │   │   ├── validators/
│   │   │   │   └── plate_format.py    # Regex/rule validator for Indian plate schema + OCR-confusion fixes
│   │   │   │                          #   (0/O, 1/I, 8/B corrections)
│   │   │   │
│   │   │   └── utils/
│   │   │       ├── geometry.py        # Shared bbox/foot-point/polygon helper functions
│   │   │       └── logging.py         # Structured logging setup shared across the worker
│   │   │
│   │   ├── weights/              # (gitignored) Exported OpenVINO/ONNX model files live here at runtime
│   │   └── tests/
│   │       ├── test_detector.py       # Unit tests against sample frames — checks boxes/classes returned
│   │       ├── test_tracker.py        # Verifies ID persistence across a short synthetic frame sequence
│   │       ├── test_fence.py          # Polygon-crossing logic tested with synthetic track trajectories
│   │       └── test_anpr.py           # Plate validator regex tests against known Indian plate formats
│   │
│   ├── api/                      # FastAPI backend — REST + WebSocket, the only service that talks to
│   │   │                         #   Postgres/Qdrant/MinIO on behalf of the frontend
│   │   ├── Dockerfile             # Python + FastAPI + uvicorn base image
│   │   ├── requirements.txt      # fastapi, uvicorn, sqlalchemy, psycopg2, qdrant-client, minio, redis
│   │   ├── app/
│   │   │   ├── main.py           # FastAPI app instance, router registration, startup/shutdown hooks
│   │   │   ├── core/
│   │   │   │   ├── config.py          # Env-driven settings (DB URL, Redis URL, Qdrant/MinIO endpoints)
│   │   │   │   └── security.py        # Placeholder for auth/API-key handling (future, not prototype-critical)
│   │   │   │
│   │   │   ├── routers/
│   │   │   │   ├── cameras.py         # CRUD for the `cameras` table (register webcam/file/RTSP sources)
│   │   │   │   ├── events.py          # Query/filter event history (by camera, time range, type, severity)
│   │   │   │   ├── watchlist.py       # CRUD for watchlisted faces/plates, writes embeddings into Qdrant
│   │   │   │   ├── fences.py          # Save/retrieve per-camera virtual-fence polygons drawn in the UI
│   │   │   │   └── alerts_ws.py       # WebSocket endpoint — subscribes to Redis, pushes live alerts to UI
│   │   │   │
│   │   │   ├── db/
│   │   │   │   ├── postgres.py        # SQLAlchemy engine/session setup for Postgres+TimescaleDB
│   │   │   │   ├── models.py          # ORM models: Camera, Event, Track, WatchlistEntry
│   │   │   │   ├── qdrant_client.py   # Thin wrapper around Qdrant collections (faces, plates)
│   │   │   │   └── minio_client.py    # Thin wrapper for snapshot/clip upload+retrieval
│   │   │   │
│   │   │   └── schemas/
│   │   │       ├── camera.py          # Pydantic request/response models for camera endpoints
│   │   │       ├── event.py           # Pydantic request/response models for event endpoints
│   │   │       └── watchlist.py       # Pydantic request/response models for watchlist endpoints
│   │   │
│   │   └── tests/
│   │       ├── test_cameras_api.py    # Endpoint tests for camera CRUD
│   │       ├── test_events_api.py     # Endpoint tests for event querying
│   │       └── test_watchlist_api.py  # Endpoint tests for watchlist CRUD + Qdrant write
│   │
│   └── frontend/                 # React dashboard — operator-facing UI
│       ├── Dockerfile             # Node build stage + nginx/vite-preview serve stage
│       ├── package.json          # React, react-router, a charts lib, a canvas/drawing lib for fence editor
│       ├── src/
│       │   ├── main.jsx          # React app bootstrap
│       │   ├── App.jsx           # Top-level routing between Dashboard / Camera Detail / Watchlist pages
│       │   │
│       │   ├── pages/
│       │   │   ├── Dashboard.jsx      # Grid of live camera tiles + global alert feed
│       │   │   ├── CameraDetail.jsx   # Single-camera view: live stream, track overlays, fence editor
│       │   │   └── Watchlist.jsx      # Manage watchlisted faces/plates (upload photo, add plate + reason)
│       │   │
│       │   ├── components/
│       │   │   ├── CameraTile.jsx     # Thumbnail/live preview card for one camera
│       │   │   ├── AlertFeed.jsx      # Scrolling list of incoming alerts (consumes the WebSocket)
│       │   │   ├── FenceEditor.jsx    # Canvas overlay for drawing/editing a virtual-fence polygon
│       │   │   └── EventTimeline.jsx  # Time-range filterable table/chart of past events
│       │   │
│       │   └── services/
│       │       ├── apiClient.js       # Wraps REST calls to the FastAPI backend
│       │       └── useAlertSocket.js  # React hook managing the WebSocket connection + live alert state
│       │
│       └── tests/
│           └── AlertFeed.test.jsx     # Component test for alert rendering behavior
│
├── db/
│   ├── init.sql                  # Creates database, enables the TimescaleDB extension, base schema
│   └── migrations/                # Alembic migration scripts as schema evolves
│       └── versions/
│
├── data/
│   ├── sample_videos/             # Your pre-recorded video files, registered as simulated camera sources
│   └── watchlist_seed/            # Sample face images / plate list used to pre-populate the demo watchlist
│
├── scripts/
│   ├── export_models.py           # Converts YOLO/.pt and InsightFace models to OpenVINO IR / ONNX once,
│   │                              #   writes them into services/inference-worker/weights/
│   ├── seed_watchlist.py          # Loads data/watchlist_seed/ into Qdrant + Postgres for demo purposes
│   └── register_cameras.py        # Populates the `cameras` table from a simple config file (webcam/files)
│
└── docs/
    ├── architecture.md            # Copy of the system architecture write-up (source of truth for design)
    └── api_reference.md           # Generated/maintained summary of FastAPI endpoints
```

## Why it's split this way

- **`inference-worker` and `api` are fully separate services**, each with their own Dockerfile/requirements — the worker never talks to Postgres/Qdrant/MinIO directly except through the event it publishes; the API owns all persistence. This means you can restart, redeploy, or even swap the inference runtime (OpenVINO → TensorRT later) without touching the API or frontend at all.
- **`events/schema.py` is the one contract** the whole system is built around — every detection module (`models/`) and every rule module (`rules/`) only needs to know how to produce a valid `Event`; nothing downstream needs to know that a face-match event and a fence-crossing event came from completely different code paths.
- **`sources/camera_source.py` is the seam that survives your hardware upgrade path** — webcam and video-file today, real RTSP later, same interface, same downstream code, exactly as planned in the architecture doc.
- **Tests sit next to the code they test**, one folder per service, so each service is independently testable/CI-able rather than one monolithic test suite.

Want me to start scaffolding this for real — actual Dockerfiles, `docker-compose.yml`, and a working `inference-worker/app/main.py` that captures your webcam + a sample video file and runs YOLO detection end-to-end, as the first runnable slice?
