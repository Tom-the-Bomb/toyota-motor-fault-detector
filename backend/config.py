"""Central configuration for the motor-fault backend.

The fault model is a PyTorch LSTM autoencoder that watches a single signal —
the motor's **current draw** — and flags anomalies (see model/ml.py). Low/idle
current is "normal"; sustained elevated current is the anomaly. Everything you
might want to tweak for your motor/Arduino lives here; values can be overridden
with environment variables.
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
# The model only needs the motor current (amps). Your sketch should print one
# reading per line — either the bare current value (`0.0032`) or, matching the
# reference sketch, `time_us,current` (`12345,0.0032`); the parser takes the
# current from the last numeric field. JSON ({"current":0.0032}) also works.
CSV_FIELDS = ["current"]

# Human-friendly metadata for the dashboard (label + unit + range + display
# precision). `current` is the model input; `current_rise` and `error` are the
# detector's own internals, surfaced so the dashboard shows what it acts on.
METRICS = {
    "current":      {"label": "Current",      "unit": "A", "min": 0.0,   "max": 0.05,  "decimals": 4},
    "current_rise": {"label": "Current Rise", "unit": "A", "min": -0.02, "max": 0.05,  "decimals": 4},
    "error":        {"label": "Recon. Error", "unit": "",  "min": 0.0,   "max": 0.008, "decimals": 5},
}

# --- Server ------------------------------------------------------------------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
STREAM_HZ = float(os.getenv("STREAM_HZ", "20"))  # max websocket push rate
HISTORY_LEN = int(os.getenv("HISTORY_LEN", "600"))  # readings kept for new clients

# --- Simulator ---------------------------------------------------------------
# Used by `python app.py --sim` (or when no Arduino is found). Emits current
# that idles in the healthy band and periodically rises into the fault band, so
# the dashboard cycles between NOMINAL and FAULT against the real model.
SIM_HZ = float(os.getenv("SIM_HZ", "30"))  # simulated samples per second
