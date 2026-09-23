import asyncio
import logging
import time
import os
import cv2

# Internal imports
from app.core.scheduler import CameraScheduler, SchedulerConfig
from app.sources.camera_source import CameraConfig, FileCameraSource, WebcamSource, CameraSource
from app.models.detector import YOLODetector
from app.models.tracker import ByteTracker
from app.models.behavior import BehaviorFeatureExtractor
from app.models.face import FaceModule
from app.models.anpr import ANPRModule, PaddleOCREngine
from app.models.night import NightPipeline
from app.rules.fence import FenceRule
from app.rules.loitering import LoiteringRule
from app.rules.activity import SuspiciousActivityRule
from app.rules.face_match import FaceMatchRule
from app.rules.anpr_match import ANPRMatchRule, PlateWatchlistProvider
from app.events.publisher import EventPublisher
from app.core.evidence import EvidenceService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InferenceWorker:
    def __init__(self):
        # 1. Initialize Scheduler
        config = SchedulerConfig(global_inference_fps=15, queue_size=5)
        self.scheduler = CameraScheduler(config)
        
        # 2. Initialize Models
        self.detector = YOLODetector(model_path="yolov8n.pt", conf_threshold=0.3)
        self.detector.load() # Need to load explicitly for detector.py implementation
        self.tracker = ByteTracker()
        self.trajectory_analyzer = BehaviorFeatureExtractor()
        self.night_enhancer = NightPipeline()
        
        self.face_module = FaceModule()
        self.ocr_engine = PaddleOCREngine()
        self.anpr_module = ANPRModule(ocr_engine=self.ocr_engine)
        
        # 3. Initialize Rules
        self.fence_rule = FenceRule()
        self.loitering_rule = LoiteringRule()
        self.activity_rule = SuspiciousActivityRule()
        
        # Prototype Watchlist Providers
        # self.face_watchlist_provider = WatchlistProvider()
        self.plate_watchlist_provider = PlateWatchlistProvider()
        
        # 4. Initialize Core Services
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
        self.publisher = EventPublisher(redis_url=redis_url)
        self.evidence_service = EvidenceService()
        
        from redis.asyncio import Redis as AsyncRedis
        self.frame_cache = AsyncRedis.from_url(redis_url)
        
        self.running = False
        self.camera_sources: dict[str, CameraSource] = {}
        self.capture_tasks: list[asyncio.Task] = []

    def setup_mock_cameras(self):
        import urllib.request
        import json
        try:
            req = urllib.request.Request("http://localhost:8000/api/v1/cameras/")
            with urllib.request.urlopen(req) as response:
                cameras = json.loads(response.read().decode())
            for c in cameras:
                if c.get("enabled"):
                    config = CameraConfig(camera_id=c["id"], name=c["name"], source_type=c["source_type"], source_uri=c["source_uri"], enabled=True, priority=c["priority"])
                    self.scheduler.add_camera(config)
                    self.camera_sources[config.camera_id] = FileCameraSource(config)
            logger.info(f"Loaded {len(self.camera_sources)} cameras from API.")
        except Exception as e:
            logger.error(f"Failed to fetch cameras from API: {e}")


    async def _capture_loop(self, camera_id: str):
        source = self.camera_sources.get(camera_id)
        if not source:
            return
            
        logger.info(f"Started capture loop for {camera_id}")
        consecutive_failures = 0
        
        while self.running:
            if not source.config.enabled:
                await asyncio.sleep(1.0)
                continue
                
            if not self.scheduler.should_sample(camera_id):
                await asyncio.sleep(0.01)
                continue
                
            success, frame = source.read()
            if success and frame is not None:
                self.scheduler.enqueue(camera_id, frame)
                if consecutive_failures > 0:
                    logger.info(f"Camera {camera_id} recovered after {consecutive_failures} failures")
                consecutive_failures = 0
                await asyncio.sleep(0.01)  # Yield loop
            else:
                consecutive_failures += 1
                logger.warning(f"Failed to read from camera {camera_id} (failure {consecutive_failures}). Marking degraded.")
                # If disconnected, try to close and reconnect (FileCameraSource handles its own reconnect inside read(), but wait longer)
                await asyncio.sleep(1.0) # Wait before retry

    def _preprocess(self, frame):
        # Basic preprocessing (e.g. resize, night enhancement fallback)
        # We can simulate night enhancer conditionally, but for basic prototype:
        enhanced_frame = self.night_enhancer.enhance_frame(frame)
        return enhanced_frame

    async def run(self):
        self.running = True
        self.setup_mock_cameras()
        await self.publisher.connect()
        logger.info("Inference worker started.")
        
        # Start capture tasks
        for cam_id in self.camera_sources:
            task = asyncio.create_task(self._capture_loop(cam_id))
            self.capture_tasks.append(task)
        
        while self.running:
            # 1. Scheduler gets camera frame
            cam_and_frame = self.scheduler.next_camera()
            if not cam_and_frame:
                await asyncio.sleep(0.01)
                continue
                
            camera_id, frame = cam_and_frame
            start_time = time.time()
            events_created = 0
            
            try:
                # 2. Preprocessing
                processed_frame = self._preprocess(frame)
                
                # 3. YOLO detection
                detections = self.detector.detect(processed_frame)
                
                # 4. ByteTrack
                tracks = self.tracker.update(detections)
                
                # 5. Trajectory features
                track_features = {}
                for t in tracks:
                    track_features[t.track_id] = self.trajectory_analyzer.extract(t)
                
                generated_events = []
                
                for t in tracks:
                    # 6. Conditional Face / ANPR
                    x1, y1, x2, y2 = map(int, t.bbox)
                    h, w = processed_frame.shape[:2]
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
                    
                    if t.class_name == "person" and (x2 - x1) > 0 and (y2 - y1) > 0:
                        person_crop = processed_frame[y1:y2, x1:x2]
                        face_match = self.face_module.process(person_crop, face_analysis_enabled=True)
                        if face_match:
                            evt = FaceMatchRule.evaluate(camera_id, t, face_match)
                            if evt:
                                generated_events.append(evt)
                    elif t.class_name in ["car", "truck", "motorcycle"] and (x2 - x1) > 0 and (y2 - y1) > 0:
                        # Process using the new ANPRModule API
                        plate_matches = self.anpr_module.process(processed_frame, [t])
                        for plate_match in plate_matches:
                            evt = ANPRMatchRule.evaluate(camera_id, t, plate_match)
                            if evt:
                                generated_events.append(evt)
                                
                    # 7. Rules (Fence, Loitering, Suspicious)
                    features = track_features.get(t.track_id)
                    
                    # Loitering
                    loitering_evt = self.loitering_rule.evaluate(camera_id, t, features)
                    if loitering_evt: generated_events.append(loitering_evt)
                    
                    # Fence (needs mocked fences per camera, assuming fence_rule handles it)
                    fence_evts = self.fence_rule.evaluate(camera_id, t, features)
                    generated_events.extend(fence_evts)
                    
                    # Activity
                    act_evt = self.activity_rule.evaluate(camera_id, t, features)
                    if act_evt: generated_events.append(act_evt)
                    
                    # Draw bounding box on frame for streaming
                    x1, y1, x2, y2 = map(int, t.bbox)
                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(processed_frame, f"{t.class_name} {t.track_id}", (x1, max(0, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Cache frame to Redis for MJPEG stream
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                if ret:
                    await self.frame_cache.set(f"camera_frame:{camera_id}", buffer.tobytes(), ex=5)
                
                # 8 & 9 & 10. Process events
                for event in generated_events:
                    # 9. Evidence hook
                    event_with_evidence = await self.evidence_service.attach_evidence(event, processed_frame)
                    
                    # 10. Publisher
                    await self.publisher.publish(event_with_evidence)
                    events_created += 1
                
                processing_ms = int((time.time() - start_time) * 1000)
                
                # Structured Logging
                logger.info({
                    "camera_id": camera_id,
                    "frame_id": id(frame),
                    "processing_ms": processing_ms,
                    "events_created": events_created
                })

            except Exception as e:
                logger.error(f"Error processing frame for camera {camera_id}: {e}", exc_info=True)

    async def shutdown(self):
        self.running = False
        for task in self.capture_tasks:
            task.cancel()
        for source in self.camera_sources.values():
            source.close()
        await self.publisher.disconnect()
        if hasattr(self, 'frame_cache'):
            await self.frame_cache.close()

async def main():
    worker = InferenceWorker()
    try:
        await worker.run()
    except asyncio.CancelledError:
        logger.info("Worker run task cancelled.")
    finally:
        logger.info("Shutting down worker.")
        await worker.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # Handled by CancelledError and finally block

