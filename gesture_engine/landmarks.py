"""
Hand Landmark Extractor using MediaPipe Hands.
Implements Landmark Extraction in Section 5 of the Architecture Blueprint.
"""

import math
from typing import List, Dict, Any, Tuple, Optional

class HandLandmarks:
    """
    Computes geometrical relationships between the 21 MediaPipe hand landmarks.
    """
    # Landmark indices
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4

    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8

    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12

    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16

    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20

    @staticmethod
    def distance(p1: Any, p2: Any) -> float:
        """Euclidean distance between two landmarks (normalized 0.0 - 1.0)."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    @staticmethod
    def is_finger_extended(landmarks: Any, tip_idx: int, pip_idx: int) -> bool:
        """Checks if a finger is extended (tip is higher/further from wrist than PIP)."""
        # In image coordinates, y=0 is top, y=1 is bottom
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    @staticmethod
    def get_finger_states(landmarks: Any) -> Dict[str, bool]:
        """Returns boolean state (extended vs curled) for all 5 fingers."""
        # Thumb: compare x distance to MCP or compare tip to IP
        thumb_extended = landmarks[HandLandmarks.THUMB_TIP].y < landmarks[HandLandmarks.THUMB_IP].y
        index_extended = HandLandmarks.is_finger_extended(landmarks, HandLandmarks.INDEX_TIP, HandLandmarks.INDEX_PIP)
        middle_extended = HandLandmarks.is_finger_extended(landmarks, HandLandmarks.MIDDLE_TIP, HandLandmarks.MIDDLE_PIP)
        ring_extended = HandLandmarks.is_finger_extended(landmarks, HandLandmarks.RING_TIP, HandLandmarks.RING_PIP)
        pinky_extended = HandLandmarks.is_finger_extended(landmarks, HandLandmarks.PINKY_TIP, HandLandmarks.PINKY_PIP)

        return {
            "thumb": thumb_extended,
            "index": index_extended,
            "middle": middle_extended,
            "ring": ring_extended,
            "pinky": pinky_extended
        }

    @staticmethod
    def get_pinch_distance(landmarks: Any) -> float:
        """Calculates distance between Thumb Tip and Index Finger Tip."""
        p_thumb = landmarks[HandLandmarks.THUMB_TIP]
        p_index = landmarks[HandLandmarks.INDEX_TIP]
        return math.sqrt((p_thumb.x - p_index.x)**2 + (p_thumb.y - p_index.y)**2)
