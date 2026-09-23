import pytest
from app.rules.anpr_match import ANPRMatchRule, PlateWatchlistProvider
from app.models.anpr import PlateMatch

def test_anpr_match_rule_generates_event():
    # Setup watchlist provider
    provider = PlateWatchlistProvider(enrolled_plates={"MH12AB1234"})
    
    # Valid plate that IS on the watchlist
    plate_match = PlateMatch(
        plate_text="MH-12-AB-1234",  # With hyphens, will be normalized
        ocr_confidence=0.9,
        global_bbox=[0, 0, 100, 50],
        track_id="track_1"
    )
    
    event = ANPRMatchRule.evaluate("camera_1", plate_match, provider)
    
    assert event is not None
    assert event.type.value == "ANPR_MATCH"
    assert event.camera_id == "camera_1"
    assert event.metadata["plate_text"] == "MH12AB1234"

def test_anpr_match_rule_invalid_plate():
    # Setup watchlist provider
    provider = PlateWatchlistProvider(enrolled_plates={"MH12AB1234"})
    
    # Invalid plate that fails regex
    plate_match = PlateMatch(
        plate_text="INVALID_123",
        ocr_confidence=0.9,
        global_bbox=[0, 0, 100, 50],
        track_id="track_1"
    )
    
    event = ANPRMatchRule.evaluate("camera_1", plate_match, provider)
    
    # Event should be None because format is invalid
    assert event is None

def test_anpr_match_rule_not_in_watchlist():
    # Setup watchlist provider
    provider = PlateWatchlistProvider(enrolled_plates={"MH12AB1234"})
    
    # Valid plate that is NOT on the watchlist
    plate_match = PlateMatch(
        plate_text="DL1A1234",
        ocr_confidence=0.9,
        global_bbox=[0, 0, 100, 50],
        track_id="track_1"
    )
    
    event = ANPRMatchRule.evaluate("camera_1", plate_match, provider)
    
    # Event should be None because not in watchlist
    assert event is None
