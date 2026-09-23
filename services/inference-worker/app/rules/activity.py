import datetime
from typing import Optional

from app.events.schema import Event, EventType, Severity, EventFactory
from app.models.tracker import Track
from app.models.behavior import BehaviorFeatures

class SuspiciousActivityRule:
    """
    Independent, explainable rules for Phase 7C.
    Evaluates tracks against behavioral features to flag suspicious activities.
    Does NOT use learned action-recognition models.
    """

    def evaluate(self, camera_id: str, track: Track, features: BehaviorFeatures) -> Optional[Event]:
        # Simple prototype implementation that checks one of the rules
        if not features:
            return None
        
        return self.rapid_approach(
            camera_id=camera_id,
            track=track,
            features=features,
            speed_threshold=100.0,
            distance_threshold=50.0
        )

    @staticmethod
    def rapid_approach(
        camera_id: str,
        track: Track,
        features: BehaviorFeatures,
        speed_threshold: float,
        distance_threshold: float
    ) -> Optional[Event]:
        """
        Flags if an object is moving faster than speed_threshold and 
        is closer to the fence than distance_threshold.
        """
        if features.speed > speed_threshold:
            if features.distance_to_fence is not None and features.distance_to_fence < distance_threshold:
                return EventFactory.create(
                    event_type=EventType.SUSPICIOUS_MOVEMENT,
                    camera_id=camera_id,
                    severity=Severity.HIGH,
                    track_id=track.track_id,
                    confidence=track.confidence,
                    metadata={
                        "rule": "rapid_approach",
                        "speed": features.speed,
                        "distance_to_fence": features.distance_to_fence,
                        "class_name": track.class_name
                    }
                )
        return None

    @staticmethod
    def restricted_after_hours(
        camera_id: str,
        track: Track,
        start_hour: int,
        end_hour: int,
        current_time: Optional[datetime.datetime] = None
    ) -> Optional[Event]:
        """
        Flags activity occurring during restricted hours.
        """
        if current_time is None:
            current_time = datetime.datetime.now(datetime.timezone.utc)
            
        hour = current_time.hour
        
        is_restricted = False
        if start_hour > end_hour:
            # Spans midnight (e.g. 22 to 6)
            if hour >= start_hour or hour < end_hour:
                is_restricted = True
        else:
            # Same day (e.g. 1 to 5)
            if start_hour <= hour < end_hour:
                is_restricted = True
                
        if is_restricted:
            return EventFactory.create(
                event_type=EventType.NIGHT_MOVEMENT,
                camera_id=camera_id,
                severity=Severity.HIGH,
                track_id=track.track_id,
                confidence=track.confidence,
                metadata={
                    "rule": "restricted_after_hours",
                    "hour": hour,
                    "class_name": track.class_name
                }
            )
        return None

    @staticmethod
    def repeated_reentry(
        camera_id: str,
        track: Track,
        features: BehaviorFeatures,
        max_reentry_count: int
    ) -> Optional[Event]:
        """
        Flags if an object repeatedly enters and exits a region (reentry_count >= max_reentry_count).
        """
        if features.reentry_count >= max_reentry_count:
            return EventFactory.create(
                event_type=EventType.SUSPICIOUS_MOVEMENT,
                camera_id=camera_id,
                severity=Severity.MEDIUM,
                track_id=track.track_id,
                confidence=track.confidence,
                metadata={
                    "rule": "repeated_reentry",
                    "reentry_count": features.reentry_count,
                    "class_name": track.class_name
                }
            )
        return None

    @staticmethod
    def prolonged_stationary_activity(
        camera_id: str,
        track: Track,
        features: BehaviorFeatures,
        dwell_threshold: float,
        speed_threshold: float = 0.5
    ) -> Optional[Event]:
        """
        Flags if an object remains in the frame longer than dwell_threshold 
        while moving slower than speed_threshold.
        """
        if features.dwell_time > dwell_threshold and features.speed < speed_threshold:
            return EventFactory.create(
                event_type=EventType.SUSPICIOUS_MOVEMENT,
                camera_id=camera_id,
                severity=Severity.LOW,
                track_id=track.track_id,
                confidence=track.confidence,
                metadata={
                    "rule": "prolonged_stationary_activity",
                    "dwell_time": features.dwell_time,
                    "speed": features.speed,
                    "class_name": track.class_name
                }
            )
        return None
