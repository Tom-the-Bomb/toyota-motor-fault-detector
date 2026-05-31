import torch
import torch.nn as nn
import pickle
import serial
import pandas as pd
import numpy as np
import time

# ==========================================
# MODEL DEFINITION + LOAD
# ==========================================
class LSTMAutoencoder(nn.Module):
    def __init__(self, input_size=2, hidden_size=32):
        super().__init__()
        self.encoder = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.decoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.fc      = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        _, (hidden, cell) = self.encoder(x)
        decoder_input = hidden.permute(1, 0, 2).repeat(1, x.size(1), 1)
        out, _ = self.decoder(decoder_input)
        return self.fc(out)

model = LSTMAutoencoder(input_size=2, hidden_size=32)
model.load_state_dict(torch.load('lstm_autoencoder.pth', map_location='cpu'))
model.eval()

with open('scaler_current.pkl', 'rb') as f:
    scaler_current = pickle.load(f)
with open('scaler_rise.pkl', 'rb') as f:
    scaler_rise = pickle.load(f)

print("Model loaded and ready.")

# ==========================================
# SETTINGS
# ==========================================
WINDOW_SIZE    = 50
ROLLING_WINDOW = 200
THRESHOLD      = 0.001201
PORT           = 'COM8'
BAUD           = 115200

# ==========================================
# PREDICT FUNCTION
# ==========================================
def predict(df_new):
    df_new = df_new.copy()
    df_new['rolling_mean']        = df_new['current_A'].rolling(ROLLING_WINDOW).mean().bfill()
    df_new['current_rise']        = df_new['current_A'] - df_new['rolling_mean']
    df_new['current_scaled']      = scaler_current.transform(df_new[['current_A']])
    df_new['current_rise_scaled'] = scaler_rise.transform(df_new[['current_rise']])

    results = []
    for i in range(WINDOW_SIZE, len(df_new)):
        window = np.column_stack([
            df_new['current_scaled'].values[i-WINDOW_SIZE:i],
            df_new['current_rise_scaled'].values[i-WINDOW_SIZE:i]
        ])
        tensor = torch.FloatTensor(window).unsqueeze(0)
        with torch.no_grad():
            reconstructed = model(tensor)
            error = torch.mean((tensor - reconstructed) ** 2).item()
            results.append({
                'index': i,
                'error': round(error, 8),
                'fault': int(error > THRESHOLD)
            })
    return results

# ==========================================
# MAIN LOOP
# ==========================================
ser = serial.Serial(PORT, BAUD, timeout=5)
time.sleep(2)
ser.reset_input_buffer()
print(f"Connected to {PORT} — waiting for data...\n")

times    = []
currents = []

try:
    while True:
        line = ser.readline().decode(errors='ignore').strip()

        if line == 'END':
            if len(times) < WINDOW_SIZE:
                print(f"Not enough samples ({len(times)}) — skipping")
                times.clear()
                currents.clear()
                continue

            df_batch = pd.DataFrame({'time_us': times, 'current_A': currents})
            predictions = predict(df_batch)

            errors = [r['error'] for r in predictions]
            faults = [r for r in predictions if r['fault'] == 1]

            print(f"--- Batch: {len(times)} samples ---")
            print(f"Current range: {df_batch['current_A'].min():.5f}A "
                  f"to {df_batch['current_A'].max():.5f}A")
            print(f"Min/Avg/Max error: "
                  f"{min(errors):.8f} / "
                  f"{sum(errors)/len(errors):.8f} / "
                  f"{max(errors):.8f}")

            if faults:
                print(f"⚠️  FAULT DETECTED — "
                      f"{len(faults)}/{len(predictions)} abnormal windows | "
                      f"max error: {max(r['error'] for r in faults):.8f}\n")
            else:
                print(f"✅ Normal operation — "
                      f"{len(predictions)} windows checked\n")

            times.clear()
            currents.clear()

        elif line:
            try:
                parts = line.split(',')
                if len(parts) == 2:
                    times.append(int(parts[0]))
                    currents.append(float(parts[1]))
            except:
                continue

except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    ser.close()
    print("Serial port closed.")