import pytest
from app.validators.plate_format import validate_and_correct_plate

def test_whitespace_and_separator_normalization():
    # It should remove spaces and hyphens
    plate, valid, reason = validate_and_correct_plate("MH 12 AB 1234")
    assert plate == "MH12AB1234"
    assert valid is True
    assert reason == "Valid format"

    plate, valid, reason = validate_and_correct_plate("MH-12-AB-1234")
    assert plate == "MH12AB1234"
    assert valid is True
    
def test_valid_indian_formats():
    valid_plates = [
        "MH12AB1234",  # Standard 10 char
        "DL1A1234",    # 8 char (1 digit RTO, 1 char series)
        "DL12A1234",   # 9 char
        "HR261234",    # 8 char (no series)
        "UP14Z9999",   # 9 char
        "MP09CX0001",  # 10 char
        "KA011",       # 5 char - wait, KA(2) 01(2) 1(1) = 5
    ]
    for p in valid_plates:
        plate, valid, reason = validate_and_correct_plate(p)
        assert valid is True, f"Failed on {p}"
        assert plate == p

def test_position_aware_corrections():
    # 0 -> O in state code
    plate, valid, reason = validate_and_correct_plate("M012AB1234")
    assert valid is True
    assert plate == "MO12AB1234"  # Wait, MO is valid regex ^[A-Z]{2}
    
    # 1 -> I in state code
    plate, valid, reason = validate_and_correct_plate("1N12AB1234")
    assert valid is True
    assert plate == "IN12AB1234"
    
    # 8 -> B in state code
    plate, valid, reason = validate_and_correct_plate("M812AB1234")
    assert valid is True
    assert plate == "MB12AB1234"
    
    # O -> 0 in RTO / Number
    plate, valid, reason = validate_and_correct_plate("MHlOABl234") # lower l not supported in map, wait, let's use I
    plate, valid, reason = validate_and_correct_plate("MHIOAB1234")
    assert valid is True
    assert plate == "MH10AB1234"
    
    # B -> 8 in Number
    plate, valid, reason = validate_and_correct_plate("MH12AB123B")
    assert valid is True
    assert plate == "MH12AB1238"
    
def test_no_blind_replacements():
    # B should only be replaced if in a number position, not if in a letter position
    # MH12BB1234 is valid. If we had blindly replaced, BB -> 88
    plate, valid, reason = validate_and_correct_plate("MH12BB1234")
    assert valid is True
    assert plate == "MH12BB1234"  # BB remains BB
    
    # DL1B1234
    plate, valid, reason = validate_and_correct_plate("DL1B1234")
    assert valid is True
    assert plate == "DL1B1234"

def test_invalid_formats():
    # Too short
    plate, valid, reason = validate_and_correct_plate("ABC")
    assert valid is False
    assert reason == "Invalid length (3)"
    
    # Too long
    plate, valid, reason = validate_and_correct_plate("MH12AB123456")
    assert valid is False
    assert reason == "Invalid length (12)"
    
    # Completely jumbled string that can't match any mask
    plate, valid, reason = validate_and_correct_plate("XYZ123ABC999")
    # Mask LLNNLNNNN?
    # X Y Z(N?) 1 2 A(N) B(N) C(N) 9(N) 9(N) 9(N) -> too long anyway
    assert valid is False

def test_special_characters():
    plate, valid, reason = validate_and_correct_plate("MH-12_!AB@1234")
    # _!@ are removed
    assert plate == "MH12AB1234"
    assert valid is True
