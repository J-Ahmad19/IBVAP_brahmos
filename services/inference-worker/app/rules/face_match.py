from typing import Optional
from app.events.schema import Event, EventType, Severity, EventFactory
from app.models.tracker import Track
from app.models.face import FaceMatch

class FaceMatchRule:
    """
    Evaluates FaceMatch results and generates operator-reviewable events.
    Does NOT implement autonomous enforcement.
    """
    
    @staticmethod
    def evaluate(
        camera_id: str,
        track: Track,
        face_match: Optional[FaceMatch]
    ) -> Optional[Event]:
        """
        Takes a FaceMatch result and generates a FACE_MATCH Event if a match was found.
        """
        if face_match is None or not face_match.matched:
            return None
            
        return EventFactory.create(
            event_type=EventType.FACE_MATCH,
            camera_id=camera_id,
            severity=Severity.HIGH,
            track_id=track.track_id,
            confidence=face_match.confidence,
            metadata={
                "subject_id": face_match.subject_id,
                "face_bbox": face_match.bbox,
                "class_name": track.class_name
            }
        )
