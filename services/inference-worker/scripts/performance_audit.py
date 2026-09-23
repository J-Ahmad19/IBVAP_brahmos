import asyncio
import time
import psutil
import os
import sys
import numpy as np

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import InferenceWorker
from app.sources.camera_source import CameraConfig, CameraSource
from app.rules.face_match import FaceMatchRule
from app.rules.anpr_match import ANPRMatchRule

class MockCameraSource(CameraSource):
    """Generates synthetic frames rapidly for max-load benchmarking."""
    def __init__(self, config: CameraConfig):
        super().__init__(config)
        self.frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        
    def read(self):
        return True, self.frame.copy()
        
    def health(self) -> dict:
        return {"status": "ok"}
        
    def close(self):
        pass

class AuditWorker(InferenceWorker):
    def __init__(self):
        super().__init__()
        self.stats = {
            "yolo_ms": [],
            "tracker_ms": [],
            "face_anpr_ms": [],
            "rules_ms": [],
            "total_ms": [],
            "events": 0
        }

    def setup_mock_cameras(self, count=1):
        for i in range(count):
            cam_id = f"cam_{i:02d}"
            config = CameraConfig(camera_id=cam_id, name=f"Camera {i}", source_type="mock", source_uri="mock", enabled=True, priority=1)
            self.scheduler.add_camera(config)
            self.camera_sources[cam_id] = MockCameraSource(config)

    async def run_audit(self, num_cameras, duration=10):
        self.running = True
        self.setup_mock_cameras(count=num_cameras)
        
        # Start capture tasks
        for cam_id in self.camera_sources:
            task = asyncio.create_task(self._capture_loop(cam_id))
            self.capture_tasks.append(task)
            
        start_time = time.time()
        frames_processed = 0
        
        while time.time() - start_time < duration:
            cam_and_frame = self.scheduler.next_camera()
            if not cam_and_frame:
                await asyncio.sleep(0.01)
                continue
                
            camera_id, frame = cam_and_frame
            t0 = time.time()
            
            try:
                processed_frame = self._preprocess(frame)
                
                t1 = time.time()
                detections = self.detector.detect(processed_frame)
                self.stats["yolo_ms"].append((time.time() - t1) * 1000)
                
                t2 = time.time()
                tracks = self.tracker.update(detections)
                self.stats["tracker_ms"].append((time.time() - t2) * 1000)
                
                track_features = {}
                for t in tracks:
                    track_features[t.track_id] = self.trajectory_analyzer.extract(t)
                generated_events = []
                
                t3 = time.time()
                for t in tracks:
                    x1, y1, x2, y2 = map(int, t.bbox)
                    h, w = processed_frame.shape[:2]
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
                    
                    if t.class_name == "person" and (x2 - x1) > 0 and (y2 - y1) > 0:
                        person_crop = processed_frame[y1:y2, x1:x2]
                        face_match = self.face_module.process(person_crop, face_analysis_enabled=True)
                        if face_match:
                            evt = FaceMatchRule.evaluate(camera_id, t, face_match)
                            if evt: generated_events.append(evt)
                    elif t.class_name in ["car", "truck", "motorcycle"] and (x2 - x1) > 0 and (y2 - y1) > 0:
                        vehicle_crop = processed_frame[y1:y2, x1:x2]
                        plate_match = self.anpr_module.process(vehicle_crop)
                        if plate_match:
                            evt = ANPRMatchRule.evaluate(camera_id, t, plate_match)
                            if evt: generated_events.append(evt)
                self.stats["face_anpr_ms"].append((time.time() - t3) * 1000)
                
                t4 = time.time()
                for t in tracks:
                    features = track_features.get(t.track_id)
                    loitering_evt = self.loitering_rule.evaluate(camera_id, t, features)
                    if loitering_evt: generated_events.append(loitering_evt)
                    fence_evts = self.fence_rule.evaluate(camera_id, t, features)
                    generated_events.extend(fence_evts)
                    act_evt = self.activity_rule.evaluate(camera_id, t, features)
                    if act_evt: generated_events.append(act_evt)
                self.stats["rules_ms"].append((time.time() - t4) * 1000)
                
                self.stats["events"] += len(generated_events)
                frames_processed += 1
                
                self.stats["total_ms"].append((time.time() - t0) * 1000)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                
        await self.shutdown()
        
        # Calculate stats
        cpu_percent = psutil.cpu_percent()
        mem_info = psutil.virtual_memory()
        
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0
            
        return {
            "cameras": num_cameras,
            "duration": duration,
            "frames": frames_processed,
            "fps": frames_processed / duration,
            "cpu_percent": cpu_percent,
            "mem_percent": mem_info.percent,
            "yolo_avg_ms": avg(self.stats["yolo_ms"]),
            "tracker_avg_ms": avg(self.stats["tracker_ms"]),
            "face_anpr_avg_ms": avg(self.stats["face_anpr_ms"]),
            "rules_avg_ms": avg(self.stats["rules_ms"]),
            "total_avg_ms": avg(self.stats["total_ms"]),
        }

async def run_all_audits():
    results = []
    # Warmup psutil
    psutil.cpu_percent()
    for num_cams in [1, 2, 3, 4]:
        print(f"Running audit with {num_cams} cameras...")
        worker = AuditWorker()
        res = await worker.run_audit(num_cams, duration=5) # 5 seconds per test for speed
        results.append(res)
        print(f"FPS: {res['fps']:.2f}, CPU: {res['cpu_percent']}%")
        
    with open("performance_report.md", "w") as f:
        f.write("# CPU Performance Audit\\n\\n")
        f.write("| Cameras | FPS | CPU % | Mem % | YOLO (ms) | Tracker (ms) | Face/ANPR (ms) | Total (ms) |\\n")
        f.write("|---|---|---|---|---|---|---|---|\\n")
        for r in results:
            f.write(f"| {r['cameras']} | {r['fps']:.1f} | {r['cpu_percent']:.1f} | {r['mem_percent']:.1f} | {r['yolo_avg_ms']:.1f} | {r['tracker_avg_ms']:.1f} | {r['face_anpr_avg_ms']:.1f} | {r['total_avg_ms']:.1f} |\\n")
    print("Report saved to performance_report.md")

if __name__ == "__main__":
    asyncio.run(run_all_audits())
