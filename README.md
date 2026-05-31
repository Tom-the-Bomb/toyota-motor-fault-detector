# Motor Fault Detection — Live Dashboard

Real-time predictive-maintenance dashboard for a motor monitored by an Arduino.
A Python (Flask) backend reads the motor's **current** over UART, runs a trained
**PyTorch LSTM autoencoder** that flags anomalous current patterns, and streams
predictions to a React dashboard over WebSocket.

```
Motor ──USB/UART──> Arduino ──serial──> Flask backend ──WebSocket──> React dashboard
                              (current)   (LSTM autoencoder)            (live charts,
                                                                         fault alerts)
```

## How the model works

The detector watches a single signal — motor **current** (amps). It keeps a
rolling baseline of recent current, derives `current_rise = current − baseline`,
scales both channels, and feeds a sliding window of 50 samples to the
autoencoder. A high **reconstruction error** (above `0.001201`) means the current
pattern is unlike the low/idle data the model was trained on — i.e. a fault.
In practice the decision knee sits around **~5.5 mA**: idle current reads as
healthy, sustained higher draw reads as a fault.

The model lives in [`backend/model/`](backend/model/):
`ml.py` (architecture + online detector + offline batch demo),
`lstm_autoencoder.pth`, and the two `scaler_*.pkl` files.

---

## Quick start

You need **two terminals** (backend + frontend).

### 1. Backend

Dependencies are managed with [uv](https://docs.astral.sh/uv/). The project pins
**Python 3.13** (PyTorch has no 3.14 wheels yet); `uv run` builds the
environment from `uv.lock` on first use — no manual venv/activate step.

```bash
cd backend

# No hardware? Run the built-in simulator (cycles healthy <-> fault):
uv run python app.py --sim

# With the Arduino plugged in (auto-detects the port, falls back to --sim):
uv run python app.py

# Force a specific port / baud:
uv run python app.py --port /dev/cu.usbmodem1101 --baud 115200
```

> Don't have uv? `curl -LsSf https://astral.sh/uv/install.sh | sh`

Find your Arduino's serial port:
- **macOS:** `ls /dev/cu.*` → e.g. `/dev/cu.usbmodem1101`
- **Linux:** `/dev/ttyACM0` or `/dev/ttyUSB0`
- **Windows:** `COM3`, `COM4`, …

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default <http://localhost:5173>). The dashboard connects to
the backend WebSocket at `ws://localhost:8000/ws` automatically and reconnects on
its own.

> Node isn't installed system-wide here — it was installed via **nvm**. In a new
> terminal run `nvm use default` (or `source ~/.nvm/nvm.sh`) before `npm`.

---

## Arduino telemetry format

The sketch prints one current reading per line. The parser accepts any of:

| Format | Example |
|--------|---------|
| single value (amps) | `0.0032` |
| `time_us,current` (reference sketch) | `12345,0.0032` |
| JSON | `{"current":0.0032}` |

For multi-field CSV the current is taken from the **last** numeric field.
Non-numeric lines (sketch debug output) are ignored.

The standalone batch demo from the original notebook still works against
hardware that sends `time_us,current` lines terminated by an `END` marker:

```bash
uv run python -m model.ml --port /dev/cu.usbmodem1101
```

---

## Configuration

Everything tunable lives in [`backend/config.py`](backend/config.py) (also
overridable via env vars):

| Setting | What it does |
|---------|--------------|
| `SERIAL_PORT`, `BAUD_RATE` | UART connection |
| `CSV_FIELDS` | telemetry column mapping |
| `METRICS` | labels, units, ranges, and display precision shown in the UI |
| `STREAM_HZ` | max WebSocket push rate |
| `HISTORY_LEN` | readings kept for new clients |
| `SIM_HZ` | simulator sample rate |

Model constants (`WINDOW_SIZE`, `ROLLING_WINDOW`, `THRESHOLD`) live alongside the
artifacts in [`backend/model/ml.py`](backend/model/ml.py).

---

## What you get

- **Flask backend** (`backend/`) — reads current from the Arduino over UART (or
  the simulator), runs the LSTM autoencoder on every sample, and broadcasts
  predictions on a WebSocket. Falls back to a transparent current-threshold
  heuristic if PyTorch/the model artifacts are unavailable.
- **React dashboard** (`frontend/`) — health gauge, fault banner, live metric
  tiles (current, current rise, reconstruction error), signal-history charts
  with the fault threshold marked, and a fault-event log. Auto-reconnects.
