"""Backend-facing wrapper around the LSTM current-anomaly model.

`FaultModel.predict()` takes one telemetry sample and returns the normalized
dict the dashboard consumes. It runs the real PyTorch model when the artifacts
(and torch) are available, and otherwise falls back to a transparent current
threshold so the dashboard still works end-to-end.
"""
from __future__ import annotations


def _health_from_error(error: float, threshold: float) -> dict:
    """Map a reconstruction error onto the dashboard's prediction fields.

    `probability` = error / (error + threshold): a bounded 0..1 anomaly score
    that is exactly 0.5 at the threshold, so it lines up with `prediction`.
    """
    prob = error / (error + threshold) if (error + threshold) > 0 else 0.0
    is_fault = error > threshold
    return {
        "prediction": "fault" if is_fault else "healthy",
        "fault_type": "current anomaly" if is_fault else None,
        "probability": round(prob, 4),
        "health": max(0, min(100, round(100 * (1 - prob)))),
    }


class FaultModel:
    def __init__(self):
        self.detector = None
        self.threshold = None
        self.source = "heuristic"
        self._load()

    def _load(self):
        """Load the LSTM autoencoder + scalers. Falls back to a heuristic if
        torch isn't installed or the artifacts can't be read."""
        try:
            from .ml import CurrentAnomalyDetector, MODEL_PATH

            self.detector = CurrentAnomalyDetector()
            self.threshold = self.detector.threshold
            import os
            self.source = f"loaded:{os.path.basename(MODEL_PATH)}"
            print(f"[model] Loaded LSTM autoencoder (threshold={self.threshold})")
        except Exception as e:  # missing torch, missing/corrupt artifacts, etc.
            print(f"[model] Could not load LSTM model ({e!r}) — using heuristic fallback.")
            self.detector = None

    def predict(self, telemetry: dict) -> dict:
        """Score one telemetry sample. Expects a `current` field (amps)."""
        current = telemetry.get("current")
        if self.detector is not None and current is not None:
            result = self.detector.push(float(current))
            if result is None:
                # Warming up: not enough samples for a window yet.
                return {
                    "prediction": "healthy",
                    "fault_type": None,
                    "probability": None,
                    "health": 100,
                    "source": self.source,
                    "warming_up": True,
                    "current_rise": None,
                    "error": None,
                }
            out = _health_from_error(result["error"], result["threshold"])
            out.update({
                "source": self.source,
                "warming_up": False,
                "current_rise": round(result["current_rise"], 6),
                "error": round(result["error"], 6),
            })
            return out
        return self._heuristic(telemetry)

    def _heuristic(self, telemetry: dict) -> dict:
        """Rule-based stand-in: the trained model treats current above roughly
        5–6 mA as anomalous, so mirror that with a simple threshold."""
        current = float(telemetry.get("current") or 0.0)
        knee = 0.0055  # ~5.5 mA, where the real model crosses its threshold
        prob = round(min(1.0, current / (2 * knee)), 4)
        is_fault = current > knee
        return {
            "prediction": "fault" if is_fault else "healthy",
            "fault_type": "current anomaly" if is_fault else None,
            "probability": prob,
            "health": max(0, min(100, round(100 * (1 - prob)))),
            "source": "heuristic",
            "warming_up": False,
            "current_rise": None,
            "error": None,
        }
