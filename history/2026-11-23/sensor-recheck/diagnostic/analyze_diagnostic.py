import csv
import json
import re
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent


def analyze(path, fast=False):
    text = path.read_text(encoding="utf-8-sig")
    marker = "FAST" if fast else "DIAG"
    blocks = re.findall(rf"{marker}_BEGIN (.*?)\n(.*?){marker}_END drive=INPUT", text, re.S)
    rows, summaries = [], []
    for run, (header, body) in enumerate(blocks, 1):
        temp = float(re.search(r"temp_C=([\d.]+)", header)[1])
        first = re.search(r"first=(D[01]\+)", header)[1]
        local = []
        for line in body.splitlines():
            if not line.startswith("FAST " if fast else "DIFF "):
                continue
            fields = dict(re.findall(r"(\w+)=([^ ]+)", line))
            row = {"run": run, "temperature_C": temp, "first": first,
                   "pair": int(fields["pair"]), "phase": fields["phase"]}
            sign = 1 if row["phase"] == "D0+" else -1
            for key, value in fields.items():
                if key not in ("pair", "phase"):
                    row[key] = float(value)
            if fast:
                row["aligned_V"] = sign * row["probe_V"]
                row["retained"] = row["pair"] >= 25
            else:
                row["early_aligned_V"] = sign * row["early_V"]
                row["late_aligned_V"] = sign * row["late_V"]
                row["retained"] = row["pair"] >= 5
            local.append(row)
        expected = 64 if fast else 16
        if len(local) != expected:
            raise ValueError(f"Expected {expected} phase samples, got {len(local)}")
        retained = [r for r in local if r["retained"]]
        metric = "aligned_V" if fast else "late_aligned_V"
        summary = {"run": run, "temperature_C": temp, "first": first,
                   "retained_mean_aligned_V": mean(r[metric] for r in retained),
                   "max_pulse_us": max(r["pulse_us"] for r in local)}
        for phase in ("D0+", "D1+"):
            values = [r[metric] for r in retained if r["phase"] == phase]
            summary[phase] = {"mean_aligned_V": mean(values),
                              "sample_stdev_V": stdev(values),
                              "range_V": max(values) - min(values)}
        rows.extend(local)
        summaries.append(summary)
    if not summaries:
        raise ValueError("No completed diagnostic blocks")
    out = path.with_name(path.stem.replace("_raw", "_analysis"))
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {"raw_source": str(path), "user_last_stated_solution_percent": 2.0,
              "calibration_validated": False,
              "geometry_independently_verified": False,
              "note": "Differential voltage and changed timing are diagnostic only. No salinity conversion is asserted.",
              "runs": summaries}
    out.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


for pattern, fast in (("salt_2p0_signed_diff_*_raw.txt", False),
                      ("salt_2p0_fast_diff_*_raw.txt", True)):
    paths = sorted(ROOT.glob(pattern))
    if paths:
        analyze(paths[-1], fast)
