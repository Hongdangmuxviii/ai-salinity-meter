"""Recover current-based features from existing logs, without requiring A0.

The acquisition timing remains the legacy m protocol. These are response
features for calibration work, not salinity percentages or proven accuracy.
"""
import csv
import json
import re
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
sources = [
    ("original_0p5", 0.5, PARENT/"salt_0p5_20261123_221338_raw.txt", "anchor"),
    ("original_1p1", 1.1, PARENT/"salt_1p1_same_cup_20261123_221952_raw.txt", "anchor"),
    ("original_2p0", 2.0, PARENT/"salt_2p0_same_cup_20261123_222834_raw.txt", "anchor"),
    ("new_0p6", 0.6, ROOT/"salt_0p6_fixed_v3_20261123_231055_raw.txt", "new_solution"),
    ("same_0p6_return", 0.6, ROOT/"salt_0p6_return_after_air_20261123_232742_raw.txt", "same_solution_repeat"),
    ("known_1k_all_trials", None, ROOT/"known_1k_dry_load_20261123_234148_raw.txt", "known_resistor"),
]
phase_re = re.compile(r"PHASE (D[01]\+) A0=(-?[\d.]+) A1=(-?[\d.]+) A2=(-?[\d.]+) A3=(-?[\d.]+)")
result_re = re.compile(r"RESULT temp_C=([\d.]+)\s+response=([\d.]+)")
trials, summaries = [], []
for label, reference, path, role in sources:
    text = path.read_text(encoding="utf-8-sig")
    phase_matches = list(phase_re.finditer(text))
    result_matches = list(result_re.finditer(text))
    if len(phase_matches) != 30 or len(result_matches) != 3:
        raise ValueError(f"Incomplete legacy trials: {path}")
    local = []
    for trial, result in enumerate(result_matches, 1):
        forward, reverse = [], []
        for p in phase_matches[(trial-1)*10:trial*10]:
            # A0 is deliberately not used, even in its initially abnormal samples.
            _, a1, a2, a3 = map(float, p.groups()[1:])
            if abs(a2-a3) < 2.8:
                raise ValueError("Invalid drive voltage")
            index = 200*(a1-a3)/(a2-a3)
            (forward if p[1] == "D0+" else reverse).append(index)
        row = dict(condition=label, role=role, user_reference_percent=reference,
                   trial=trial, temperature_C=float(result[1]),
                   legacy_raw=float(result[2]), forward_current_index=mean(forward),
                   reverse_current_index=mean(reverse),
                   current_index=(mean(forward)+mean(reverse))/2,
                   source=str(path))
        local.append(row)
        trials.append(row)
    values = [r["current_index"] for r in local]
    summaries.append(dict(condition=label, role=role, user_reference_percent=reference,
                          temperature_mean_C=mean(r["temperature_C"] for r in local),
                          current_index_mean=mean(values),
                          trial_sample_stdev=stdev(values),
                          current_index_min=min(values), current_index_max=max(values)))

lo = summaries[0]["current_index_mean"]
hi = summaries[2]["current_index_mean"]
for row in summaries:
    row["normalized_feature_from_0p5_to_2p0"] = (None if row["role"] == "known_resistor" else
                                                100*(row["current_index_mean"]-lo)/(hi-lo))
    row["normalization_is_salinity_percent"] = False

for name, rows in (("current_ratio_reanalysis_trials.csv", trials),
                   ("current_ratio_reanalysis_summary.csv", summaries)):
    with (ROOT/name).open("w", encoding="utf-8-sig", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

report = {
    "formula": "C=100*(R1+R2)/R2 * (A1-A3)/(A2-A3); R1=R2=1k gives C=200*(A1-A3)/(A2-A3)",
    "A0_used_in_calculation": False,
    "assumptions": ["Existing series R1/R2 are matched nominal1k resistors.",
                    "Current through R2 represents the intended two-electrode loop.",
                    "Legacy sequential timing is retained; this is a dynamic response feature."],
    "known_1k_expected_index": 200/3,
    "known_1k_measured_index_mean": summaries[-1]["current_index_mean"],
    "known_1k_includes_initial_bad_A0_records": True,
    "salinity_accuracy_validated": False,
    "normalization": {"low_reference_percent":0.5,"high_reference_percent":2.0,
                      "low_index":lo,"high_index":hi,
                      "formula":"z=100*(C-low_index)/(high_index-low_index)",
                      "do_not_extrapolate_or_clip":True},
    "summaries": summaries,
    "limits": ["One repeated preparation is not an independent accuracy study.",
               "No temperature compensation model has been fitted.",
               "A0 intermittent behavior is bypassed in the calculation, not declared repaired.",
               "Electrode polarization remains in the response; no physical resistivity claim is made.",
               "The newly prepared0.6% records were not used to choose the normalization anchors."]
}
(ROOT/"current_ratio_reanalysis.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(summaries,indent=2))
