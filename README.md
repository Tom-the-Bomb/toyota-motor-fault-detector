# Motor Fault Detection — Live Dashboard

Real-time predictive-maintenance dashboard for a motor monitored by an Arduino,
with a Python (Flask) backend that runs your trained ML model and streams
fault predictions to a React frontend over WebSocket.

```
Motor ──USB/UART──> Arduino ──serial──> Flask backend ──WebSocket──> React dashboard
                              (telemetry)  (pyserial + ML model)        (live charts,
                                                                          fault alerts)
```

## What you get

- **Flask backend** (`backend/`) — reads telemetry from the Arduino over UART,
  runs your exported Colab model on every sample, and broadcasts predictions on
  a WebSocket.
- **React dashboard** (`frontend/`) — health gauge, fault banner, live metric
  tiles, signal-history charts, and a fault-event log. Auto-reconnects.

---

## Quick start

You need **two terminals** (backend + frontend).

### 1. Backend

Dependencies are managed with [uv](https://docs.astral.sh/uv/). `uv run` creates
the environment from `uv.lock` on first use — no manual venv/activate step.

```bash
cd backend
uv run python app.py     # reads the Arduino (port/baud from config.py)
```

> Don't have uv? `curl -LsSf https://astral.sh/uv/install.sh | sh`

The port auto-detects. To pin a specific one, set `SERIAL_PORT` in
[`config.py`](backend/config.py). Find your Arduino's port:
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
the backend WebSocket at `ws://localhost:8000/ws` automatically.

> Node isn't installed system-wide here — it was installed via **nvm**. In a new
> terminal run `nvm use default` (or just `source ~/.nvm/nvm.sh`) before `npm`.

---

## Plugging in YOUR ML model

1. In Colab, export your trained model:
   ```python
   import joblib
   joblib.dump(clf, "model.pkl")
   # If you scaled features, save both so the backend applies the same scaling:
   # joblib.dump({"model": clf, "scaler": scaler}, "model.pkl")
   ```
2. Drop `model.pkl` into `backend/`.
3. Open `backend/config.py` and set **`MODEL_FEATURES`** to the *exact* column
   order your model was trained on, and **`CLASS_LABELS`** (e.g.
   `{0: "healthy", 1: "fault"}`).
4. Restart the backend. The header shows **"ML model"** once it's loaded
   (vs **"Heuristic model"** — the built-in rule-based fallback used until then).

The backend calls `model.predict()` (and `predict_proba()` if available) per
sample. Multi-class models work too — the predicted class name is shown as the
fault type.

---

## Arduino telemetry format

Your sketch just needs to `Serial.println()` one sample per line. The backend
parser accepts **any** of these (pick the easiest):

| Format | Example |
|--------|---------|
| CSV (lightest) | `1.23,12.0,45.6,1450,0.82,62.0,0.31` |
| JSON | `{"current":1.23,"temperature":45.6,"rpm":1450}` |
| key=value | `current=1.23 temperature=45.6 rpm=1450` |

For CSV the column order must match `CSV_FIELDS` in `config.py`:
`current, voltage, temperature, rpm, torque, load, vibration`.

A ready-to-edit sketch is in [`backend/arduino_example/motor_telemetry.ino`](backend/arduino_example/motor_telemetry.ino).
Set the baud rate to match `config.py` (default **115200**), and replace the
sensor stubs with your real reads.

> You don't have to send all fields — send what you have. Missing fields are
> shown as `—` and passed to the model as `0`. Edit `METRICS`/`CSV_FIELDS` in
> `config.py` to match your motor's signals.

---

## Configuration

Everything tunable lives in `backend/config.py` (also overridable via env vars):

| Setting | What it does |
|---------|--------------|
| `SERIAL_PORT`, `BAUD_RATE` | UART connection |
| `CSV_FIELDS` | column order for CSV telemetry |
| `METRICS` | labels, units, and gauge ranges shown in the UI |
| `MODEL_FEATURES`, `CLASS_LABELS` | how telemetry maps to your model |
| `FAULT_THRESHOLD` | probability above which a fault alert fires |
| `STREAM_HZ` | max WebSocket push rate |
