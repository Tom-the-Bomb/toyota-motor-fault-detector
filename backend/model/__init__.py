"""Motor-fault model package.

Exposes the backend-facing :class:`FaultModel` plus the underlying model pieces
(architecture, online detector) for anyone who wants them directly.
"""
from .fault_model import FaultModel
from .ml import CurrentAnomalyDetector, LSTMAutoencoder

__all__ = ["FaultModel", "CurrentAnomalyDetector", "LSTMAutoencoder"]
