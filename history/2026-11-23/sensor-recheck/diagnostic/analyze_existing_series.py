"""Compare retained legacy records; do not claim a salinity calibration."""
import csv
import json
import re
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent
SERIES = [
    (0.5, ROOT.parent / "salt_0p5_20261123_221338_raw.txt"),
    (1.1, ROOT.parent / "salt_1p1_same_cup_20261123_221952_raw.txt"),
    (2.0, ROOT.parent / "salt_2p0_same_cup_20261123_222834_raw.txt"),
]
RE = re.compile(r"RESULT temp_C=([\d.]+)\s+response=([\d.]+) / 100\s+D0\+=([\d.]+)\s+D1\+=([\d.]+)\s+range=([\d.]+)\.\.([\d.]+)")


def read(concentration, path):
    rows = []
    for trial, m in enumerate(RE.finditer(path.read_text(encoding="utf-8-sig")), 1):
        t, raw, f, r, low, high = map(float, m.groups())
        rows.append(dict(reference_percent=concentration, trial=trial,
                         temperature_C=t, mean_raw=raw, forward=f, reverse=r,
                         direction_difference=f-r, within_burst_pair_span=high-low,
                         source=str(path)))
    if len(rows) != 3:
        raise ValueError(f"Expected three trials in {path}")
    summary = {"reference_percent": concentration, "source": str(path)}
    for key in ("temperature_C", "mean_raw", "forward", "reverse", "direction_difference", "within_burst_pair_span"):
        values = [row[key] for row in rows]
        summary[key] = {"mean": mean(values), "sample_stdev": stdev(values)}
    return rows, summary


rows, anchors = [], []
for concentration, path in SERIES:
    local, anchor = read(concentration, path)
    rows.extend(local)
    anchors.append(anchor)
recheck_paths = sorted(ROOT.glob("salt_2p0_legacy_recheck_*_raw.txt"))
if not recheck_paths:
    raise ValueError("Current 2% recheck missing")
local, recheck = read(2.0, recheck_paths[-1])
rows.extend(local)
comparison = {}
for metric in ("mean_raw", "forward", "reverse", "direction_difference"):
    span = anchors[-1][metric]["mean"] - anchors[0][metric]["mean"]
    delta = recheck[metric]["mean"] - anchors[-1][metric]["mean"]
    comparison[metric] = {
        "original_0p5_to_2p0_span": span,
        "same_solution_later_recheck_difference": delta,
        "absolute_recheck_difference_as_percent_of_anchor_span": abs(delta / span) * 100,
    }
report = {
    "anchors": anchors, "later_2p0_recheck": recheck, "comparison": comparison,
    "calibration_validated": False,
    "interpretation": [
        "Legacy forward and reverse records carry information hidden by their mean; retain both.",
        "Direction difference is an exploratory dynamic feature, not a physical resistance estimate.",
        "Three sequential concentrations and repeat commands do not establish independent accuracy.",
        "Temperature, elapsed time, unmeasured geometry and electrode history remain possible contributors.",
        "The new differential protocol has only been tested on the current 2% sample.",
        "Do not merge voltage metrics from the new protocol with legacy RAW anchors or extrapolate concentration."
    ]
}
(ROOT / "existing_series_feature_review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
with (ROOT / "existing_series_features.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps({"comparison": comparison, "later_2p0_temperature_C": recheck["temperature_C"]}, indent=2))
