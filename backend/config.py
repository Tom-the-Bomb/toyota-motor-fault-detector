"""Central configuration for the motor-fault backend.

Everything you might want to tweak for your specific motor/Arduino lives here.
Values can be overridden with environment variables (see README).
"""
import os

# --- Serial / UART -----------------------------------------------------------
# The USB serial port your Arduino shows up as.
#   macOS:   /dev/cu.usbmodemXXXX   (run `ls /dev/cu.*` to find it)
#   Linux:   /dev/ttyACM0 or /dev/ttyUSB0
#   Windows: COM3, COM4, ...
# Leave as None to auto-detect the first Arduino-like port.
SERIAL_PORT = os.getenv("SERIAL_PORT") or None
BAUD_RATE = int(os.getenv("BAUD_RATE", "115200"))

# --- Telemetry schema --------------------------------------------------------
# The order of fields your Arduino prints when it sends a bare CSV line, e.g.
#   Serial.println("1.23,12.0,45.6,1450,0.82,62.0,0.31");
# If your Arduino sends JSON ({"current":1.23,...}) this order is ignored.
CSV_FIELDS = ["current", "voltage", "temperature", "rpm", "torque", "load", "vibration"]

# Human-friendly metadata for the dashboard (unit + display label + sane range).
METRICS = {
    "current":     {"label": "Current",     "unit": "A",   "min": 0,   "max": 6},
    "voltage":     {"label": "Voltage",     "unit": "V",   "min": 0,   "max": 15},
    "temperature": {"label": "Temperature", "unit": "°C",  "min": 15,  "max": 90},
    "rpm":         {"label": "Speed",       "unit": "RPM", "min": 0,   "max": 3000},
    "torque":      {"label": "Torque",      "unit": "N·m", "min": 0,   "max": 3},
    "load":        {"label": "Load",        "unit": "%",   "min": 0,   "max": 100},
    "vibration":   {"label": "Vibration",   "unit": "g",   "min": 0,   "max": 2},
}

# --- ML model ----------------------------------------------------------------
# Path to the model you exported from Colab (joblib.dump / pickle).
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "model.pkl"))

# EXACT feature order your model was trained on. The backend builds the feature
# vector in this order before calling model.predict(). EDIT THIS to match your
# training columns. If a feature name isn't in the telemetry, it's filled with 0.
MODEL_FEATURES = ["current", "voltage", "temperature", "rpm", "torque", "load", "vibration"]

# Map your model's integer class outputs -> human label shown on the dashboard.
# For a binary model this is usually {0: "healthy", 1: "fault"}.
CLASS_LABELS = {0: "healthy", 1: "fault"}

# Probability above which we raise a FAULT alert (only used if model exposes
# predict_proba). Tune for your precision/recall trade-off.
FAULT_THRESHOLD = float(os.getenv("FAULT_THRESHOLD", "0.5"))

# --- Server ------------------------------------------------------------------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
STREAM_HZ = float(os.getenv("STREAM_HZ", "20"))  # max websocket push rate
HISTORY_LEN = int(os.getenv("HISTORY_LEN", "600"))  # readings kept for new clients
