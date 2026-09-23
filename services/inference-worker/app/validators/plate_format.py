import re
from typing import Tuple, Optional

# Configurable corrections
LTR_MAP = {'0': 'O', '1': 'I', '8': 'B'}
NUM_MAP = {'O': '0', 'I': '1', 'B': '8'}

# Indian plate schema: 
# State (2 letters) + RTO (1-2 digits) + Series (0-2 letters) + Seq (1-4 digits)
INDIAN_PLATE_PATTERN = r'^([A-Z]{2})([0-9]{1,2})([A-Z]{0,2})([0-9]{1,4})$'

# Possible structure masks based on plate length
POSSIBLE_MASKS = {
    10: ["LLNNLLNNNN"],
    9:  ["LLNNLNNNN", "LLNLLNNNN", "LLNNLLNNN"],
    8:  ["LLNNNNNN", "LLNLNNNN", "LLNNLNNN"],
    7:  ["LLNNNNN", "LLNLNNN"],
    6:  ["LLNNNN"]
}

def apply_map(char: str, mapping: dict) -> str:
    return mapping.get(char, char)

def validate_and_correct_plate(
    plate_text: str, 
    character_confidences: Optional[list] = None
) -> Tuple[str, bool, str]:
    """
    Validates and optionally corrects an Indian license plate using position-aware logic.
    
    Returns:
        (normalized_text, format_valid, validation_reason)
    """
    # Whitespace and separator normalization
    raw = re.sub(r'[\s\-]', '', plate_text).upper()
    
    # Strip any completely invalid characters (keep only alphanumeric)
    raw = re.sub(r'[^A-Z0-9]', '', raw)
    
    if not raw:
        return "", False, "Empty or invalid characters only"
        
    # Check if perfectly valid already
    if re.match(INDIAN_PLATE_PATTERN, raw):
        return raw, True, "Valid format"
        
    length = len(raw)
    if length < 4 or length > 10:
        return raw, False, f"Invalid length ({length})"
        
    # Attempt position-aware correction using known mask structures
    if length in POSSIBLE_MASKS:
        for mask in POSSIBLE_MASKS[length]:
            candidate = []
            for i, ch in enumerate(raw):
                if mask[i] == 'L':
                    candidate.append(apply_map(ch, LTR_MAP))
                else:
                    candidate.append(apply_map(ch, NUM_MAP))
            
            candidate_str = "".join(candidate)
            
            if re.match(INDIAN_PLATE_PATTERN, candidate_str):
                return candidate_str, True, "Corrected via position-aware matching"
                
    # If no mask produces a valid match, return the raw normalized text
    return raw, False, "Format mismatch after correction attempts"
