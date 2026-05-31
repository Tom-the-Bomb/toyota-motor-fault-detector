"""Telemetry sources for the backend.

`SerialReader` reads motor telemetry from the Arduino over UART (USB serial),
parses each line into a dict, and hands it off via a callback. `SimulatedReader`
is a drop-in stand-in that synthesizes realistic motor-current telemetry, so the
dashboard works with no hardware (`python app.py --sim`).

Both run as background threads exposing the same interface: `.start()`,
`.stop()`, `.connected`, and `.active_port`.
"""
from __future__ import annotations

import json
import math
import random
import threading
import time

import config


def list_serial_ports():
    from serial.tools import list_ports
    return [(p.device, p.description) for p in list_ports.comports()]


def auto_detect_port():
    """Pick the most Arduino-looking serial port."""
    keywords = ("usbmodem", "usbserial", "ttyacm", "ttyusb", "arduino", "ch340", "wch")
    ports = list_serial_ports()
    for device, desc in ports:
        hay = f"{device} {desc}".lower()
        if any(k in hay for k in keywords):
            return device
    return ports[0][0] if ports else None


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def parse_line(line: str):
    """Parse one telemetry line into a dict of floats, or None if unparseable.

    Accepts JSON (`{"current":0.0032}`), key=value (`current=0.0032`), or CSV.
    For CSV, a single value is the current; if multiple numeric fields are sent
    (e.g. the reference `time_us,current` format) the current is taken from the
    last field. Non-numeric lines (sketch debug output) are ignored.
    """
    line = line.strip()
    if not line:
        return None
    # JSON object
    if line[0] in "{[":
        try:
            obj = json.loads(line)
            return {k: _to_float(v) for k, v in obj.items()}
        except Exception:
            return None
    # key=value pairs
    if "=" in line and "," not in line:
        out = {}
        for tok in line.replace(",", " ").split():
            if "=" in tok:
                k, _, v = tok.partition("=")
                out[k.strip()] = _to_float(v)
        return out or None
    # CSV / single value
    parts = [p for p in line.replace(";", ",").split(",") if p != ""]
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None  # debug/log line from the sketch — ignore
    if not vals:
        return None
    if len(vals) == 1:
        return {"current": vals[0]}
    # Multiple fields: current is the last one (e.g. time_us,current).
    return {"current": vals[-1]}


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
        import serial
        while not self._stop.is_set():
            port = self.port or auto_detect_port()
            if not port:
                print("[serial] No serial port found — retrying in 2s. Plug in the Arduino.")
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


# Simulator current levels, calibrated against the real autoencoder: steady
# current below ~20 mA reads as healthy and above ~30 mA as a fault (the decision
# knee sits near ~27 mA). We idle at 4 mA and fault at 40 mA so each state is
# unambiguous, with brief ramps between them.
_SIM_HEALTHY_A = 0.004
_SIM_FAULT_A = 0.040
_SIM_PERIOD_S = 20.0    # one healthy->fault->healthy cycle
_SIM_HEALTHY_FRAC = 0.70  # fraction of the cycle spent idling (healthy)
_SIM_RAMP_FRAC = 0.04     # fraction spent ramping each direction


class SimulatedReader(threading.Thread):
    """Synthesizes motor-current telemetry calibrated to the real model.

    Idles in the healthy band (~4 mA) and periodically ramps into the fault band
    (~40 mA), straddling the autoencoder's ~27 mA decision knee, so the dashboard
    cycles between NOMINAL and FAULT against the actual model (~⅓ of the time in
    fault, including the transition ramps).
    """

    active_port = "SIMULATOR"

    def __init__(self, on_reading, on_raw=None, hz=None):
        super().__init__(daemon=True)
        self.on_reading = on_reading
        self.on_raw = on_raw
        self.hz = hz or config.SIM_HZ
        self._stop = threading.Event()
        self.connected = True

    def stop(self):
        self._stop.set()

    def _level(self, phase: float) -> float:
        """Current level (amps) for a point in the [0,1) cycle."""
        up0 = _SIM_HEALTHY_FRAC
        up1 = _SIM_HEALTHY_FRAC + _SIM_RAMP_FRAC
        dn0 = 1.0 - _SIM_RAMP_FRAC
        span = _SIM_FAULT_A - _SIM_HEALTHY_A
        if phase < up0:
            return _SIM_HEALTHY_A
        if phase < up1:
            return _SIM_HEALTHY_A + span * ((phase - up0) / _SIM_RAMP_FRAC)
        if phase < dn0:
            return _SIM_FAULT_A
        return _SIM_FAULT_A - span * ((phase - dn0) / _SIM_RAMP_FRAC)

    def run(self):
        period = 1.0 / self.hz
        t = 0.0
        while not self._stop.is_set():
            level = self._level((t % _SIM_PERIOD_S) / _SIM_PERIOD_S)
            # Small sensor noise + a faint mains-frequency ripple.
            current = level + random.gauss(0, 0.0004) + 0.0003 * math.sin(t * 12.0)
            current = max(0.0, current)
            if self.on_raw:
                self.on_raw(f"{current:.6f}")
            self.on_reading({"current": current})
            t += period
            time.sleep(period)