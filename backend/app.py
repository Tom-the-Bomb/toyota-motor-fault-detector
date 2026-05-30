"""Flask backend for the motor-fault dashboard.

Pipeline:  Arduino (UART) ─▶ SerialReader ─▶ FaultModel.predict() ─▶ DashboardState
                                                                          │
                          React frontend ◀── WebSocket /ws ◀──────────────┘

Run:
    python app.py            # auto-detect Arduino serial port
    python app.py --sim      # no hardware: stream simulated telemetry
    python app.py --port /dev/cu.usbmodem1101   # force a specific port
"""
from __future__ import annotations

import argparse
import collections
import json
import threading
import time

from flask import Flask
from flask_sock import Sock

import config
from model import FaultModel
from serial_reader import SerialReader, Simulator, list_serial_ports


class DashboardState:
    """Holds the latest sample + recent history, updated by the reader thread and
    read by WebSocket clients. A monotonically increasing `seq` lets clients send
    only when there's something new."""

    def __init__(self, model: FaultModel):
        self.model = model
        self.reader = None  # set once by main(); read for connection status
        self._seq = 0
        self._latest = None
        self._history = collections.deque(maxlen=config.HISTORY_LEN)
        self._lock = threading.Lock()

    def ingest(self, reading: dict):
        """Run the model on one telemetry sample and record the result."""
        sample = {"t": time.time(), "telemetry": reading, **self.model.predict(reading)}
        with self._lock:
            self._seq += 1
            self._latest = sample
            self._history.append(sample)

    @property
    def connected(self) -> bool:
        return bool(getattr(self.reader, "connected", False))

    @property
    def port(self):
        return getattr(self.reader, "active_port", None)

    def snapshot(self):
        with self._lock:
            return self._seq, self._latest

    def meta_frame(self) -> dict:
        with self._lock:
            history = list(self._history)
        return {
            "type": "meta",
            "metrics": config.METRICS,
            "model_source": self.model.source,
            "connected": self.connected,
            "port": self.port,
            "history": history,
        }


app = Flask(__name__)
sock = Sock(app)
state = DashboardState(FaultModel())


@sock.route("/ws")
def ws(ws):
    """Stream samples to a dashboard. Sends a `meta` frame on connect (metric
    config + recent history so charts populate instantly), then `sample` frames."""
    ws.send(json.dumps(state.meta_frame()))

    last_seq = -1
    period = 1.0 / config.STREAM_HZ
    while True:
        seq, sample = state.snapshot()
        if seq != last_seq and sample is not None:
            last_seq = seq
            ws.send(json.dumps({
                "type": "sample",
                "connected": state.connected,
                "port": state.port,
                **sample,
            }))
        time.sleep(period)


def build_reader(args):
    """Create the telemetry source (real serial port or the simulator)."""
    if args.sim:
        print("[backend] Starting in SIMULATOR mode (no hardware needed).")
        return Simulator(on_reading=state.ingest, hz=config.STREAM_HZ)
    print("[backend] Starting in SERIAL mode. Available ports:")
    for dev, desc in list_serial_ports():
        print(f"    {dev}  —  {desc}")
    return SerialReader(
        on_reading=state.ingest,
        port=args.port or config.SERIAL_PORT,
        baud=args.baud or config.BAUD_RATE,
    )


def main():
    parser = argparse.ArgumentParser(description="Motor fault detection backend")
    parser.add_argument("--sim", action="store_true", help="use the simulator (no hardware)")
    parser.add_argument("--port", help="serial port (overrides config / auto-detect)")
    parser.add_argument("--baud", type=int, help="baud rate")
    args = parser.parse_args()

    state.reader = build_reader(args)
    state.reader.start()

    print(f"[backend] Model: {state.model.source}")
    print(f"[backend] WebSocket: ws://{config.HOST}:{config.PORT}/ws")
    # threaded=True so each WebSocket client runs alongside the reader thread.
    app.run(host=config.HOST, port=config.PORT, threaded=True)


if __name__ == "__main__":
    main()
