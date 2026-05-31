"""LSTM-autoencoder motor-current anomaly model.

This module is the single source of truth for the model: the architecture, the
preprocessing, the saved artifacts, and both an **online** detector (used by the
backend for the live stream) and an **offline** batch scorer (used to reproduce
the original notebook analysis). Run it directly to replay the batch demo over a
serial connection:

    python -m model.ml --port /dev/cu.usbmodem1101

How it works: the motor's current is the only input. We track a rolling mean of
recent current, derive `current_rise = current - rolling_mean`, scale both with
the saved MinMaxScalers, and feed a window of the last WINDOW_SIZE samples (2
channels) to the autoencoder. A high reconstruction error means the current
pattern is unlike the (low/idle) data the model was trained on — i.e. a fault.
"""
from __future__ import annotations

import os
from collections import deque
from typing import Optional

import joblib
import numpy as np
import torch
import torch.nn as nn

# --- Constants (must match how the artifacts were trained) -------------------
WINDOW_SIZE = 50       # timesteps fed to the autoencoder
ROLLING_WINDOW = 200   # samples averaged for the current baseline
THRESHOLD = 0.001201   # reconstruction MSE above this == anomaly/fault

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(_HERE, "lstm_autoencoder.pth")
SCALER_CURRENT_PATH = os.path.join(_HERE, "scaler_current.pkl")
SCALER_RISE_PATH = os.path.join(_HERE, "scaler_rise.pkl")


class LSTMAutoencoder(nn.Module):
    """Sequence-to-sequence LSTM autoencoder over 2 channels (current, rise)."""

    def __init__(self, input_size: int = 2, hidden_size: int = 32):
        super().__init__()
        self.encoder = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.decoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        _, (hidden, cell) = self.encoder(x)
        decoder_input = hidden.permute(1, 0, 2).repeat(1, x.size(1), 1)
        out, _ = self.decoder(decoder_input)
        return self.fc(out)


def load_autoencoder(path: str = MODEL_PATH) -> LSTMAutoencoder:
    model = LSTMAutoencoder(input_size=2, hidden_size=32)
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model


def load_scalers(current_path: str = SCALER_CURRENT_PATH, rise_path: str = SCALER_RISE_PATH):
    return joblib.load(current_path), joblib.load(rise_path)


class CurrentAnomalyDetector:
    """Online detector: feed one current reading at a time via :meth:`push`.

    Maintains the rolling-mean baseline and the sliding model window internally,
    so the backend can call it once per incoming serial sample. Returns ``None``
    until WINDOW_SIZE samples have been seen (warm-up), then a result dict.
    """

    def __init__(
        self,
        model: Optional[LSTMAutoencoder] = None,
        scaler_current=None,
        scaler_rise=None,
        window: int = WINDOW_SIZE,
        rolling: int = ROLLING_WINDOW,
        threshold: float = THRESHOLD,
    ):
        self.model = model if model is not None else load_autoencoder()
        if scaler_current is None or scaler_rise is None:
            scaler_current, scaler_rise = load_scalers()
        self.scaler_current = scaler_current
        self.scaler_rise = scaler_rise
        self.window = window
        self.threshold = threshold
        self._roll = deque(maxlen=rolling)          # raw current, for the baseline
        self._win = deque(maxlen=window)            # (current_scaled, rise_scaled) pairs

    def push(self, current: float) -> Optional[dict]:
        current = float(current)
        self._roll.append(current)
        # Online analogue of pandas' rolling(window).mean().bfill(): the mean of
        # the samples seen so far (capped at ROLLING_WINDOW). Converges to the
        # offline value once the buffer fills.
        baseline = sum(self._roll) / len(self._roll)
        rise = current - baseline

        current_scaled = float(self.scaler_current.transform([[current]])[0, 0])
        rise_scaled = float(self.scaler_rise.transform([[rise]])[0, 0])
        self._win.append((current_scaled, rise_scaled))

        if len(self._win) < self.window:
            return None  # warming up

        window = np.asarray(self._win, dtype="float32")[None, ...]  # (1, window, 2)
        tensor = torch.from_numpy(window)
        with torch.no_grad():
            recon = self.model(tensor)
            error = float(torch.mean((tensor - recon) ** 2))

        return {
            "error": error,
            "current_rise": rise,
            "fault": error > self.threshold,
            "threshold": self.threshold,
        }


def predict_batch(df_new, model: LSTMAutoencoder, scaler_current, scaler_rise):
    """Offline batch scorer over a DataFrame with a ``current_A`` column.

    Mirrors the original notebook: rolling baseline -> rise -> scale -> windowed
    reconstruction error. Kept for reproducing the batch analysis / `__main__`.
    """
    import pandas as pd  # noqa: F401 (offline-only dependency)

    df_new = df_new.copy()
    df_new["rolling_mean"] = df_new["current_A"].rolling(ROLLING_WINDOW).mean().bfill()
    df_new["current_rise"] = df_new["current_A"] - df_new["rolling_mean"]
    df_new["current_scaled"] = scaler_current.transform(df_new[["current_A"]])
    df_new["current_rise_scaled"] = scaler_rise.transform(df_new[["current_rise"]])

    results = []
    cs = df_new["current_scaled"].values
    rs = df_new["current_rise_scaled"].values
    for i in range(WINDOW_SIZE, len(df_new)):
        window = np.column_stack([cs[i - WINDOW_SIZE:i], rs[i - WINDOW_SIZE:i]]).astype("float32")
        tensor = torch.from_numpy(window).unsqueeze(0)
        with torch.no_grad():
            recon = model(tensor)
            error = float(torch.mean((tensor - recon) ** 2))
        results.append({"index": i, "error": round(error, 8), "fault": int(error > THRESHOLD)})
    return results


def _serial_demo(port: str, baud: int = 115200):
    """Replay the original batch demo: read `time_us,current_A` lines until an
    `END` marker, then score the batch and print a summary."""
    import time

    import pandas as pd
    import serial

    model = load_autoencoder()
    scaler_current, scaler_rise = load_scalers()
    print("Model loaded and ready.")

    ser = serial.Serial(port, baud, timeout=5)
    time.sleep(2)
    ser.reset_input_buffer()
    print(f"Connected to {port} — waiting for data...\n")

    times, currents = [], []
    try:
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if line == "END":
                if len(times) < WINDOW_SIZE:
                    print(f"Not enough samples ({len(times)}) — skipping")
                    times.clear(); currents.clear()
                    continue
                df_batch = pd.DataFrame({"time_us": times, "current_A": currents})
                preds = predict_batch(df_batch, model, scaler_current, scaler_rise)
                errors = [r["error"] for r in preds]
                faults = [r for r in preds if r["fault"] == 1]
                print(f"--- Batch: {len(times)} samples ---")
                print(f"Current range: {df_batch['current_A'].min():.5f}A to {df_batch['current_A'].max():.5f}A")
                print(f"Min/Avg/Max error: {min(errors):.8f} / {sum(errors)/len(errors):.8f} / {max(errors):.8f}")
                if faults:
                    print(f"FAULT DETECTED — {len(faults)}/{len(preds)} abnormal windows | "
                          f"max error: {max(r['error'] for r in faults):.8f}\n")
                else:
                    print(f"Normal operation — {len(preds)} windows checked\n")
                times.clear(); currents.clear()
            elif line:
                parts = line.split(",")
                if len(parts) == 2:
                    try:
                        times.append(int(parts[0]))
                        currents.append(float(parts[1]))
                    except ValueError:
                        continue
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        ser.close()
        print("Serial port closed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LSTM autoencoder batch serial demo")
    parser.add_argument("--port", default="COM8", help="serial port (e.g. /dev/cu.usbmodem1101)")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()
    _serial_demo(args.port, args.baud)
