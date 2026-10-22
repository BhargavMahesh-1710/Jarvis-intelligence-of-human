"""
Real-Time Camera Hand Detector Service.
Implements Frame Acquisition & Hand Detection in Section 5 of the Blueprint.
Runs as a controlled background thread that can be toggled on/off.
"""

import threading
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("jarvis.gesture_engine.detector")

class GestureDetectorService:
    def __init__(self):
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._cap = None
        self._hands = None
        self._classifier = None
        self._dispatcher = None

    def _lazy_init(self):
        if self._classifier is None:
            from gesture_engine.classifier import GestureClassifier
            from gesture_engine.actions import gesture_dispatcher
            self._classifier = GestureClassifier()
            self._dispatcher = gesture_dispatcher

        if self._hands is None:
            try:
                import mediapipe as mp
                mp_hands = mp.solutions.hands
                self._hands = mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6
                )
            except Exception as e:
                logger.error(f"Failed to initialize MediaPipe Hands: {e}")

    def is_active(self) -> bool:
        return self._is_running

    def start(self, camera_index: int = 0) -> bool:
        """Starts the real-time camera gesture recognition loop in a daemon thread."""
        if self._is_running:
            return True

        self._lazy_init()
        if not self._hands:
            logger.warning("MediaPipe Hands not initialized. Cannot start camera gestures.")
            return False

        try:
            import cv2
            self._cap = cv2.VideoCapture(camera_index)
            if not self._cap.isOpened():
                logger.warning(f"Could not open camera {camera_index}.")
                self._cap = None
                return False
        except Exception as e:
            logger.error(f"Camera open error: {e}")
            return False

        self._is_running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="GestureDetectorThread")
        self._thread.start()
        logger.info("Gesture Detector Service started successfully.")
        return True

    def stop(self) -> None:
        """Stops the camera detection loop and releases hardware."""
        self._is_running = False
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        logger.info("Gesture Detector Service stopped.")

    def _worker_loop(self) -> None:
        import cv2
        while self._is_running and self._cap and self._cap.isOpened():
            success, frame = self._cap.read()
            if not success:
                time.sleep(0.05)
                continue

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    gesture_data = self._classifier.classify(hand_landmarks.landmark)
                    if gesture_data:
                        self._dispatcher.dispatch(gesture_data)

            # Throttle slightly to maintain ~25 FPS and conserve CPU
            time.sleep(0.04)

        if self._cap:
            self._cap.release()
            self._cap = None

gesture_detector = GestureDetectorService()
