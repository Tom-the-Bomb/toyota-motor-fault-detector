"""Fault-prediction model wrapper.

Drop the model you exported from Colab next to this file as `model.pkl`
(e.g. `joblib.dump(clf, "model.pkl")`). On startup the backend loads it and
calls it for every telemetry sample. If no model file is present, a transparent
heuristic fallback is used so the dashboard still works end-to-end.
"""
from __future__ import annotations

import os
import config


class FaultModel:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.source = "heuristic"
        self._load()

    def _load(self):
        """Try to load model.pkl. Supports either a bare estimator or a dict
        like {"model": clf, "scaler": scaler} (handy if you scaled in Colab)."""
        path = config.MODEL_PATH
        if not os.path.exists(path):
            print(f"[model] No model at {path} — using heuristic fallback. "
                  f"Drop your exported model.pkl there to use the real model.")
            return
        try:
            import joblib  # ships with scikit-learn
            obj = joblib.load(path)
            if isinstance(obj, dict):
                self.model = obj.get("model") or obj.get("clf") or obj.get("estimator")
                self.scaler = obj.get("scaler")
            else:
                self.model = obj
            self.source = f"loaded:{os.path.basename(path)}"
            print(f"[model] Loaded {type(self.model).__name__} from {path}"
                  + (" (+scaler)" if self.scaler is not None else ""))
        except Exception as e:  # pragma: no cover - defensive at hackathon
            print(f"[model] Failed to load {path}: {e!r}. Falling back to heuristic.")
            self.model = None

    def _features(self, telemetry: dict):
        return [[float(telemetry.get(name, 0.0) or 0.0) for name in config.MODEL_FEATURES]]

    def predict(self, telemetry: dict) -> dict:
        """Return a normalized prediction dict for one telemetry sample:
        {prediction, fault_type, probability, health, source}."""
        if self.model is None:
            return self._heuristic(telemetry)

        X = self._features(telemetry)
        if self.scaler is not None:
            try:
                X = self.scaler.transform(X)
            except Exception:
                pass

        prob = None
        try:
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X)[0]
                # probability of the "fault" class (highest non-zero label)
                classes = list(getattr(self.model, "classes_", range(len(proba))))
                fault_idx = max(range(len(classes)), key=lambda i: classes[i])
                prob = float(proba[fault_idx])
        except Exception:
            prob = None

        try:
            raw = self.model.predict(X)[0]
        except Exception as e:
            print(f"[model] predict() error: {e!r} — using heuristic")
            return self._heuristic(telemetry)

        label = config.CLASS_LABELS.get(int(raw), str(raw)) if _is_int(raw) else str(raw)
        is_fault = label != "healthy" if prob is None else prob >= config.FAULT_THRESHOLD
        # If model predicted a specific fault class, prefer that as fault_type.
        fault_type = label if (is_fault and label != "healthy") else (
            "fault" if is_fault else None)
        health = round(100 * (1 - prob)) if prob is not None else (40 if is_fault else 95)

        return {
            "prediction": "fault" if is_fault else "healthy",
            "fault_type": fault_type,
            "probability": round(prob, 4) if prob is not None else None,
            "health": health,
            "source": self.source,
        }

    def _heuristic(self, t: dict) -> dict:
        """Simple, explainable rule-based stand-in until the real model is dropped
        in. Uses only directly-measured signals (current, voltage). A DC motor's
        armature current rises toward its stall current under overload/stall, and
        the supply voltage tends to sag under that heavy draw.

        NOTE: the thresholds below are placeholders — tune them to YOUR motor's
        measured no-load and stall currents."""
        cur = float(t.get("current", 0) or 0)
        volt = float(t.get("voltage", 0) or 0)

        penalty = 0.0
        reasons = []
        # Overcurrent: armature current climbing toward the stall current.
        if cur > 4.0:
            penalty += (cur - 4.0) * 30; reasons.append("overcurrent")
        # Voltage sag while drawing heavy current — supply struggling / stall.
        if cur > 3.0 and 0 < volt < 10.0:
            penalty += 25; reasons.append("voltage sag")

        health = max(0, min(100, round(100 - penalty)))
        prob = round(min(1.0, penalty / 100.0), 4)
        is_fault = prob >= config.FAULT_THRESHOLD
        return {
            "prediction": "fault" if is_fault else "healthy",
            "fault_type": (", ".join(reasons) or "fault") if is_fault else None,
            "probability": prob,
            "health": health,
            "source": "heuristic",
        }


def _is_int(x):
    try:
        int(x)
        return True
    except (TypeError, ValueError):
        return False
