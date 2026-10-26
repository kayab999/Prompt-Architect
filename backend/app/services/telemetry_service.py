import time
import json
import logging
import threading
from collections import deque
from pathlib import Path
from typing import Dict, Any, List
from statistics import mean

from ..config import settings, logger

class TelemetryService:
    def __init__(self, max_history: int = 50):
        self._history: deque = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._snapshot_file = settings.DATA_DIR / "telemetry_snapshot.json"
        
        # Load previous state if available (PID Integral Memory)
        self._load_snapshot()
        
        # Start background persister
        self._stop_event = threading.Event()
        self._persister_thread = threading.Thread(target=self._persistence_loop, daemon=True)
        self._persister_thread.start()

    def record_event(self, latency_ms: float, error: bool = False):
        """Records a single inference event."""
        with self._lock:
            self._history.append({
                "timestamp": time.time(),
                "latency_ms": latency_ms,
                "error": error
            })

    def get_current_entropy(self) -> float:
        """
        Calculates system entropy (0.0 to 1.0).
        High entropy = High instability (errors or high latency variance).
        Used as Error Input for PID Controller.
        """
        with self._lock:
            if not self._history:
                return 0.0
            
            events = list(self._history)
            
            # 1. Error Rate Component (0.0 - 1.0)
            error_count = sum(1 for e in events if e["error"])
            error_rate = error_count / len(events)
            
            # 2. Latency Stability Component
            latencies = [e["latency_ms"] for e in events if not e["error"]]
            if not latencies:
                latency_factor = 1.0 # Max instability if all are errors
            else:
                avg_latency = mean(latencies)
                # Normalize latency: Assume > 5000ms is "high stress"
                latency_factor = min(avg_latency / 5000.0, 1.0)
            
            # Weighted Entropy
            # Errors are more critical (0.7 weight) vs Latency (0.3 weight)
            entropy = (error_rate * 0.7) + (latency_factor * 0.3)
            return min(max(entropy, 0.0), 1.0)

    def _persistence_loop(self):
        """Persists health snapshot every 5 minutes."""
        while not self._stop_event.is_set():
            time.sleep(300) # 5 minutes
            self._save_snapshot()

    def _save_snapshot(self):
        try:
            with self._lock:
                data = list(self._history)
            
            with open(self._snapshot_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Telemetry snapshot saved to {self._snapshot_file}")
        except Exception as e:
            logger.error(f"Failed to save telemetry snapshot: {e}")

    def _load_snapshot(self):
        if self._snapshot_file.exists():
            try:
                with open(self._snapshot_file, 'r') as f:
                    data = json.load(f)
                with self._lock:
                    self._history.extend(data)
                logger.info(f"Loaded telemetry snapshot with {len(data)} events.")
            except Exception as e:
                logger.warning(f"Failed to load telemetry snapshot: {e}")

    def shutdown(self):
        self._stop_event.set()
        self._save_snapshot()
        self._persister_thread.join(timeout=1.0)

# Global Instance
telemetry = TelemetryService()
