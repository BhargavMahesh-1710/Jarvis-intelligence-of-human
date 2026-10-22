"""
Gesture Classifier for JARVIS.
Classifies normalized hand landmarks into intents specified in Section 5 of the Blueprint.
"""

from typing import Optional, Dict, Any, Tuple
from gesture_engine.landmarks import HandLandmarks

class GestureClassifier:
    """
    Classifies MediaPipe Hand Landmarks into high-level normalized gesture intents.
    """
    def __init__(self, pinch_threshold: float = 0.06):
        self.pinch_threshold = pinch_threshold

    def classify(self, landmarks: Any) -> Optional[Dict[str, Any]]:
        """
        Evaluates hand landmarks and returns gesture intent + metadata.
        """
        if not landmarks or len(landmarks) < 21:
            return None

        states = HandLandmarks.get_finger_states(landmarks)
        pinch_dist = HandLandmarks.get_pinch_distance(landmarks)

        thumb = states["thumb"]
        index = states["index"]
        middle = states["middle"]
        ring = states["ring"]
        pinky = states["pinky"]

        # 1. Pinch Gesture (Thumb tip very close to Index tip)
        if pinch_dist < self.pinch_threshold:
            # Map pinch distance to a normalized 0-100 range
            normalized_val = min(100, max(0, int((pinch_dist / self.pinch_threshold) * 100)))
            return {
                "gesture": "PINCH",
                "intent": "VOLUME_CONTROL",
                "value": normalized_val,
                "pinch_distance": round(pinch_dist, 3)
            }

        # 2. Open Palm (All 5 fingers extended)
        if thumb and index and middle and ring and pinky:
            return {
                "gesture": "OPEN_PALM",
                "intent": "PAUSE",
                "confidence": 0.95
            }

        # 3. Two Fingers (Victory / Next - Index and Middle extended, Ring and Pinky curled)
        if index and middle and not ring and not pinky:
            return {
                "gesture": "TWO_FINGERS",
                "intent": "NEXT",
                "confidence": 0.92
            }

        # 4. Index Finger Point (Index extended, others curled)
        if index and not middle and not ring and not pinky:
            return {
                "gesture": "INDEX_FINGER",
                "intent": "SELECT",
                "confidence": 0.90
            }

        # 5. Thumbs Up (Thumb pointing up, other 4 fingers curled)
        wrist_y = landmarks[HandLandmarks.WRIST].y
        thumb_tip_y = landmarks[HandLandmarks.THUMB_TIP].y
        if not index and not middle and not ring and not pinky:
            if thumb_tip_y < wrist_y:
                return {
                    "gesture": "THUMBS_UP",
                    "intent": "CONFIRM",
                    "confidence": 0.94
                }
            else:
                return {
                    "gesture": "THUMBS_DOWN",
                    "intent": "CANCEL",
                    "confidence": 0.94
                }

        return None
