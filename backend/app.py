"""Flask backend for the motor-fault dashboard.

Pipeline:  Arduino (UART) ─▶ SerialReader ─▶ FaultModel.predict() ─▶ STATE
                                                                      │
                          React frontend ◀── WebSocket /ws ◀──────────┘

Run:
    python app.py            # auto-detect Arduino serial port
    python app.py --sim      # no hardware: stream simulated telemetry
    python app.py --port /dev/cu.usbmodem1101   # force a specific port
"""
from __future__ import annotations

import argparse
import collections
import threading
import time

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_sock import Sock

import config
from model import FaultModel
from serial_reader import SerialReader, Simulator, list_serial_ports

app = Flask(__name__, static_folder=None)
CORS(app)
sock = Sock(app)

model = FaultModel()

# Shared, thread-safe-ish snapshot of the latest sample. A monotonically
# increasing `seq` lets WebSocket clients send only when something is new.
STATE = {
    "seq": 0,
    "latest": None,
    "history": collections.deque(maxlen=config.HISTORY_LEN),
    "source": "starting",
    "connected": False,
    "port": None,
}
_lock = threading.Lock()
_reader = None  # SerialReader or Simulator


def handle_reading(reading: dict):
    """Called for every parsed telemetry sample: run the model, update STATE."""
    pred = model.predict(reading)
    sample = {
        "t": time.time(),
        "telemetry": reading,
        **pred,  # prediction, fault_type, probability, health, source
    }
    with _lock:
        STATE["seq"] += 1
        STATE["latest"] = sample
        STATE["history"].append(sample)
        if _reader is not None:
            STATE["connected"] = getattr(_reader, "connected", False)
            STATE["port"] = getattr(_reader, "active_port", None)


@app.get("/api/health")
def api_health():
    with _lock:
        return jsonify({
            "ok": True,
            "connected": STATE["connected"],
            "port": STATE["port"],
            "model_source": model.source,
            "metrics": config.METRICS,
            "serial_ports": list_serial_ports(),
            "samples": STATE["seq"],
        })


@app.get("/api/latest")
def api_latest():
    with _lock:
        return jsonify(STATE["latest"] or {})


@app.get("/api/history")
def api_history():
    with _lock:
        return jsonify(list(STATE["history"]))


@sock.route("/ws")
def ws(ws):
    """Stream new samples to a connected dashboard. On connect we send a
    `meta` frame (metric config + recent history) so charts populate instantly."""
    import json
    with _lock:
        meta = {
            "type": "meta",
            "metrics": config.METRICS,
            "model_source": model.source,
            "connected": STATE["connected"],
            "port": STATE["port"],
            "history": list(STATE["history"]),
        }
    ws.send(json.dumps(meta))

    last_seq = -1
    min_period = 1.0 / config.STREAM_HZ
    while True:
        with _lock:
            seq = STATE["seq"]
            sample = STATE["latest"]
            connected = STATE["connected"]
            port = STATE["port"]
        if seq != last_seq and sample is not None:
            last_seq = seq
            ws.send(json.dumps({
                "type": "sample",
                "connected": connected,
                "port": port,
                **sample,
            }))
        time.sleep(min_period)


def main():
    global _reader
    parser = argparse.ArgumentParser(description="Motor fault detection backend")
    parser.add_argument("--sim", action="store_true", help="use the simulator (no hardware)")
    parser.add_argument("--port", help="serial port (overrides config / auto-detect)")
    parser.add_argument("--baud", type=int, help="baud rate")
    args = parser.parse_args()

    if args.sim:
        print("[backend] Starting in SIMULATOR mode (no hardware needed).")
        _reader = Simulator(on_reading=handle_reading, hz=config.STREAM_HZ)
    else:
        _reader = SerialReader(
            on_reading=handle_reading,
            port=args.port or config.SERIAL_PORT,
            baud=args.baud or config.BAUD_RATE,
        )
        print("[backend] Starting in SERIAL mode. Available ports:")
        for dev, desc in list_serial_ports():
            print(f"    {dev}  —  {desc}")
    _reader.start()

    print(f"[backend] Model: {model.source}")
    print(f"[backend] Listening on http://{config.HOST}:{config.PORT}  (WebSocket: /ws)")
    # threaded=True so each WebSocket client + the HTTP routes run concurrently
    # alongside the reader thread.
    app.run(host=config.HOST, port=config.PORT, threaded=True)


if __name__ == "__main__":
    main()
