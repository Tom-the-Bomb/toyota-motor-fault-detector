"""Reads motor telemetry from the Arduino over UART (USB serial), parses each
line into a dict, and hands it off via a callback. Also provides a simulator
that produces realistic telemetry (with injectable faults) when no hardware is
connected — so the dashboard always has something to show.
"""
from __future__ import annotations

import json
import math
import threading
import time

import config


def list_serial_ports():
    try:
        from serial.tools import list_ports
        return [(p.device, p.description) for p in list_ports.comports()]
    except Exception:
        return []


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
        import serial  # pyserial
        while not self._stop.is_set():
            port = self.port or auto_detect_port()
            if not port:
                print("[serial] No serial port found — retrying in 2s. "
                      "Plug in the Arduino or run with --sim.")
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


class Simulator(threading.Thread):
    """Generates lifelike motor telemetry at ~20 Hz. Cycles through healthy
    operation and periodic fault episodes (stall, overheat) so the dashboard and
    model path can be demoed with zero hardware."""

    def __init__(self, on_reading, on_raw=None, hz=20):
        super().__init__(daemon=True)
        self.on_reading = on_reading
        self.on_raw = on_raw
        self.hz = hz
        self._stop = threading.Event()
        self.connected = True
        self.active_port = "SIMULATOR"
        self._fault = None  # name of active fault episode
        self._fault_until = 0.0
        self._next_event = 0.0

    def stop(self):
        self._stop.set()

    def inject_fault(self, name="stall", seconds=6):
        self._fault = name
        self._fault_until = time.time() + seconds

    def run(self):
        t0 = time.time()
        period = 1.0 / self.hz
        self._next_event = t0 + 12  # first fault episode after 12s
        while not self._stop.is_set():
            now = time.time()
            elapsed = now - t0

            # Auto-schedule occasional fault episodes for an unattended demo.
            if self._fault is None and now >= self._next_event:
                self.inject_fault("stall" if int(elapsed) % 2 == 0 else "overheat", 7)
                self._next_event = now + 22
            if self._fault and now >= self._fault_until:
                self._fault = None

            base_rpm = 1500 + 120 * math.sin(elapsed * 0.6)
            reading = {
                "current": 1.6 + 0.25 * math.sin(elapsed * 1.3) + _noise(0.05),
                "voltage": 12.0 + _noise(0.15),
                "temperature": 42 + 4 * math.sin(elapsed * 0.05) + _noise(0.3),
                "rpm": base_rpm + _noise(20),
                "torque": 0.9 + 0.1 * math.sin(elapsed * 1.1) + _noise(0.03),
                "load": 55 + 8 * math.sin(elapsed * 0.4) + _noise(2),
                "vibration": 0.25 + _noise(0.04),
            }

            if self._fault == "stall":
                reading["current"] = 5.2 + _noise(0.3)   # current spikes
                reading["rpm"] = 60 + _noise(40)          # motor barely turns
                reading["torque"] = 2.6 + _noise(0.1)
                reading["load"] = 98 + _noise(1)
                reading["vibration"] = 1.3 + _noise(0.15)
            elif self._fault == "overheat":
                reading["temperature"] = 82 + _noise(2)
                reading["current"] = 3.2 + _noise(0.2)
                reading["load"] = 90 + _noise(2)

            reading = {k: round(v, 3) for k, v in reading.items()}
            if self.on_raw:
                self.on_raw(",".join(str(reading[f]) for f in config.CSV_FIELDS
                                     if f in reading) + ("  # SIM:" + self._fault if self._fault else ""))
            self.on_reading(reading)
            time.sleep(period)
        self.connected = False


# Deterministic-enough pseudo noise without importing random at module import
# time (keeps the simulator reproducible-ish and avoids surprises).
_seed = [12345]


def _noise(scale):
    _seed[0] = (1103515245 * _seed[0] + 12345) & 0x7FFFFFFF
    return ((_seed[0] / 0x7FFFFFFF) - 0.5) * 2 * scale
