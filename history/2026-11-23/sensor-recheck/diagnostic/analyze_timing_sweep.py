import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent
path = sorted(ROOT.glob("salt_2p0_timing_sweep_*_raw.txt"))[-1]
text = path.read_text(encoding="utf-8-sig")
if "SWEEP_END drive=INPUT" not in text:
    raise ValueError("Incomplete sweep")
rows, groups = [], defaultdict(list)
for line in text.splitlines():
    if not line.startswith("SWEEP width_us="):
        continue
    fields = dict(re.findall(r"(\w+)=([^ ]+)", line))
    row = {key: value if key == "phase" else float(value) for key, value in fields.items()}
    row["aligned_V"] = row["probe_V"] * (1 if row["phase"] == "D0+" else -1)
    rows.append(row)
    if row["pair"] >= 25:
        groups[(row["width_us"], row["offset_us"], row["phase"])].append(row)
if len(rows) != 216 or len(groups) != 24:
    raise ValueError(f"Incomplete blocks: {len(rows)} rows, {len(groups)} groups")
summaries = []
for (width, offset, phase), local in sorted(groups.items()):
    if len(local) != 8:
        raise ValueError("Expected eight retained pairs")
    values = [r["aligned_V"] for r in local]
    summaries.append(dict(width_us=width, offset_us=offset, phase=phase,
                          aligned_mean_V=mean(values), sample_stdev_V=stdev(values),
                          mean_result_end_us=mean(r["sample_end_us"] for r in local),
                          max_pulse_us=max(r["pulse_us"] for r in local)))
base = path.with_name(path.stem.replace("_raw", "_analysis"))
for suffix, data in (("_phases", rows), ("_summary", summaries)):
    with base.with_name(base.name + suffix).with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
report = {
    "raw_source": str(path), "temperature_C": float(re.search(r"temp_C=([\d.]+)", text)[1]),
    "last_user_stated_reference_percent": 2.0, "calibration_validated": False,
    "blocks": summaries,
    "findings": [
        "Steady alternating probe differential changes sign within each drive phase.",
        "Matched polarity-aligned waveforms are approximately symmetric after warmup.",
        "A single absolute voltage or legacy RAW mean is strongly timing-dependent.",
        "Electrode polarization or other circuit dynamics are plausible; this is not an isolated-component diagnosis.",
        "No resistor replacement or salinity accuracy claim follows from this one-sample sweep.",
        "New lower-concentration records can be acquired by diluting the existing solution; no new salt mixture is required.",
        "Conversion-call offsets and completion times are not exact internal ADC integration times."
    ]
}
base.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))

