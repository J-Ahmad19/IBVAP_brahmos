from typing import Optional, Set
from app.events.schema import Event, EventType, Severity, EventFactory
from app.models.anpr import PlateMatch
from app.validators.plate_format import validate_and_correct_plate

class PlateWatchlistProvider:
    """
    Interface for providing watchlist data to the inference worker.
    In the prototype phase, this can be mocked or initialized with a static set,
    or later implemented to query PostgreSQL exactly.
    """
    def __init__(self, enrolled_plates: Set[str] = None):
        self.enrolled_plates = enrolled_plates or set()
        
    def is_enrolled(self, plate_text: str) -> bool:
        return plate_text in self.enrolled_plates

class ANPRMatchRule:
    """
    Evaluates PlateMatch results and generates operator-reviewable events.
    Checks if plate is valid and if watchlist policy matches.
    """
    
    @staticmethod
    def evaluate(
        camera_id: str,
        plate_match: PlateMatch,
        watchlist_provider: PlateWatchlistProvider
    ) -> Optional[Event]:
        """
        Takes a PlateMatch result and generates an ANPR_MATCH Event if:
        1. The plate is a valid format.
        2. The plate exists in the watchlist.
        """
        if plate_match is None or not plate_match.plate_text:
            return None
            
        # Validate format
        normalized_plate, is_valid, reason = validate_and_correct_plate(plate_match.plate_text)
        
        if not is_valid:
            return None
            
        # Check watchlist
        if not watchlist_provider.is_enrolled(normalized_plate):
            return None
            
        # Generate event
        return EventFactory.create(
            event_type=EventType.ANPR_MATCH,
            camera_id=camera_id,
            severity=Severity.HIGH,
            track_id=plate_match.track_id,
            confidence=plate_match.ocr_confidence,
            metadata={
                "plate_text": normalized_plate,
                "plate_bbox": plate_match.global_bbox,
                "validation_reason": reason
            }
        )
