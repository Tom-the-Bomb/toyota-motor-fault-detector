"""End-to-end verification of the rewired pipeline. Run from backend/."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

# 1. Package imports cleanly (resolves old model.py vs model/ package collision)
import config
from model import FaultModel, CurrentAnomalyDetector, LSTMAutoencoder
from model import ml as mlmod
from serial_reader import SerialReader, SimulatedReader, parse_line, list_serial_ports
check("package imports (config, model pkg, serial_reader)", True)

# 2. FaultModel loads the REAL torch model (not heuristic)
fm = FaultModel()
check("FaultModel loaded real LSTM (source startswith 'loaded:')",
      fm.source.startswith("loaded:"), fm.source)
check("FaultModel.threshold matches ml.THRESHOLD",
      fm.threshold == mlmod.THRESHOLD, f"{fm.threshold} vs {mlmod.THRESHOLD}")

# 3. Online detector vs offline batch agree on the same series
import pandas as pd
rng = np.random.default_rng(7)
series = np.concatenate([
    0.004 + rng.normal(0, 0.0004, 300),   # healthy idle
    0.040 + rng.normal(0, 0.0004, 300),   # fault
])
model = mlmod.load_autoencoder()
sc, sr = mlmod.load_scalers()
offline = mlmod.predict_batch(pd.DataFrame({"current_A": series}), model, sc, sr)
det = CurrentAnomalyDetector(model=model, scaler_current=sc, scaler_rise=sr)
online = [det.push(x) for x in series]
online = [o for o in online if o is not None]
check("online/offline same #windows", len(online) == len(offline),
      f"online={len(online)} offline={len(offline)}")
off_err = np.array([o["error"] for o in offline])
on_err = np.array([o["error"] for o in online])
corr = float(np.corrcoef(off_err, on_err)[0, 1])
check("online vs offline error correlation > 0.95", corr > 0.95, f"corr={corr:.4f}")

# 4. FaultModel end-to-end: warmup, then healthy->healthy, fault->fault
fm2 = FaultModel()
preds = [fm2.predict({"current": float(x)}) for x in series]
warmups = sum(1 for p in preds if p.get("warming_up"))
check("warms up exactly WINDOW_SIZE samples", warmups == mlmod.WINDOW_SIZE, f"warmups={warmups}")
h_rate = np.mean([preds[i]["prediction"] == "healthy" for i in range(250, 300)])
f_rate = np.mean([preds[i]["prediction"] == "fault" for i in range(400, 550)])
check("healthy idle -> 'healthy' (>90%)", h_rate > 0.9, f"{h_rate*100:.0f}%")
check("fault current -> 'fault' (>90%)", f_rate > 0.9, f"{f_rate*100:.0f}%")
p = preds[-1]
need = {"prediction", "fault_type", "probability", "health", "source", "error", "current_rise"}
check("prediction dict has required keys", need <= set(p), str(sorted(set(p))))
check("health in [0,100]", 0 <= p["health"] <= 100, str(p["health"]))
check("probability in [0,1]", 0 <= p["probability"] <= 1, str(p["probability"]))

# 5. parse_line handles supported formats
check("parse_line single value", parse_line("0.0032") == {"current": 0.0032})
check("parse_line time_us,current", parse_line("12345,0.0032") == {"current": 0.0032})
check("parse_line JSON", parse_line('{"current":0.0032}') == {"current": 0.0032})
check("parse_line debug line ignored", parse_line("booting sensors...") is None)

# 6. Heuristic fallback (detector unavailable)
fm3 = FaultModel(); fm3.detector = None; fm3.source = "heuristic"
ch = fm3.predict({"current": 0.004}); cf = fm3.predict({"current": 0.040})
check("heuristic: idle current healthy", ch["prediction"] == "healthy", str(ch["prediction"]))
check("heuristic: high current fault", cf["prediction"] == "fault", str(cf["prediction"]))

# 7. SimulatedReader produces a healthy<->fault cycle through the REAL model
sim_samples = []
sr_reader = SimulatedReader(on_reading=lambda r: sim_samples.append(r["current"]))
# Drive _level/run logic directly without threading/sleep: replicate run() math.
import math as _m
t = 0.0; period = 1.0 / config.SIM_HZ
N = int(20.0 * config.SIM_HZ * 3)  # 3 cycles
for _ in range(N):
    from serial_reader import _SIM_PERIOD_S
    level = sr_reader._level((t % _SIM_PERIOD_S) / _SIM_PERIOD_S)
    cur = max(0.0, level + rng.normal(0, 0.0004) + 0.0003 * _m.sin(t * 12.0))
    sim_samples.append(cur); t += period
det2 = CurrentAnomalyDetector()
flags = [det2.push(x) for x in sim_samples]
flags = [f["fault"] for f in flags if f is not None]
fault_pct = float(np.mean(flags)) * 100
check("simulator yields a mix of healthy AND fault", 0 < fault_pct < 100, f"{fault_pct:.0f}% fault")
check("simulator fault fraction is demo-reasonable (15-45%)", 15 < fault_pct < 45, f"{fault_pct:.0f}%")

print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
if FAIL:
    print("FAILED:", FAIL); raise SystemExit(1)
print("ALL CHECKS PASSED")