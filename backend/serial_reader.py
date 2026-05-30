"""Reads motor telemetry from the Arduino over UART (USB serial), parses each
line into a dict, and hands it off via a callback.
"""
from __future__ import annotations

import json
import threading
import time

import serial
from serial.tools import list_ports

import config


def list_serial_ports():
    return [(p.device, p.description) for p in list_ports.comports()]


def auto_detect_port():
    """Pick the most Arduino-looking serial port."""
    keywords = ("usbmodem", "usbserial", "ttyacm", "ttyusb", "arduino", "ch340", "wch")
    for device, desc in list_serial_ports():
        hay = f"{device} {desc}".lower()
        if any(k in hay for k in keywords):
            return device
    ports = list_serial_ports()
    return ports[0][0] if ports else None


def parse_line(line: str):
    """Parse one telemetry line. Accepts JSON objects or bare CSV (mapped onto
    config.CSV_FIELDS). Returns a dict of floats, or None if unparseable."""
    line = line.strip()
    if not line:
        return None
    # JSON: {"current":1.2,"temperature":45,...}
    if line[0] in "{[":
        try:
            obj = json.loads(line)
            return {k: _to_float(v) for k, v in obj.items()}
        except Exception:
            return None
    # key=value pairs:  current=1.2 temp=45 ...
    if "=" in line and "," not in line:
        out = {}
        for tok in line.replace(",", " ").split():
            if "=" in tok:
                k, _, v = tok.partition("=")
                out[k.strip()] = _to_float(v)
        return out or None
    # CSV: 1.2,12.0,45.6,1450,0.8,62,0.3
    parts = [p for p in line.replace(";", ",").split(",") if p != ""]
    if not parts:
        return None
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None  # probably a debug/log line from the sketch — ignore
    return {name: vals[i] for i, name in enumerate(config.CSV_FIELDS) if i < len(vals)}


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


class SerialReader(threading.Thread):
    """Background thread: opens the port and streams parsed readings to `on_reading`."""

    def __init__(self, on_reading, on_raw=None, port=None, baud=None):
        super().__init__(daemon=True)
        self.on_reading = on_reading
        self.on_raw = on_raw
        self.port = port or config.SERIAL_PORT
        self.baud = baud or config.BAUD_RATE
        self._stop = threading.Event()
        self.connected = False
        self.active_port = None

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            port = self.port or auto_detect_port()
            if not port:
                print("[serial] No serial port found — retrying in 2s. "
                      "Plug in the Arduino.")
                time.sleep(2)
                continue
            try:
                with serial.Serial(port, self.baud, timeout=1) as ser:
                    self.connected = True
                    self.active_port = port
                    print(f"[serial] Connected to {port} @ {self.baud} baud")
                    while not self._stop.is_set():
                        raw = ser.readline().decode("utf-8", errors="replace")
                        if not raw:
                            continue
                        if self.on_raw:
                            self.on_raw(raw.rstrip("\r\n"))
                        reading = parse_line(raw)
                        if reading:
                            self.on_reading(reading)
            except Exception as e:
                self.connected = False
                print(f"[serial] {port} error: {e!r} — reconnecting in 2s")
                time.sleep(2)
        self.connected = False
