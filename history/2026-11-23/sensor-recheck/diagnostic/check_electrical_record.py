"""Record diagnostic evidence without turning a RAW number into salinity."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from statistics import mean

parser = argparse.ArgumentParser()
parser.add_argument("raw_log", type=Path)
parser.add_argument("--dry", action="store_true",
                    help="Use only after user confirms separated electrodes in air")
args = parser.parse_args()
raw = args.raw_log.read_text(encoding="utf-8-sig")
pattern = re.compile(r"PHASE (D[01]\+) A0=(-?[\d.]+) A1=(-?[\d.]+) A2=(-?[\d.]+) A3=(-?[\d.]+)")
rows = []
for index, match in enumerate(pattern.finditer(raw)):
    a0, a1, a2, a3 = map(float, match.groups()[1:])
    rows.append(dict(index=index, phase=match[1], A0=a0, A1=a1, A2=a2, A3=a3,
                     A0_minus_A2_V=a0-a2, A1_minus_A3_V=a1-a3,
                     balance_residual_V=a0+a1-a2-a3))
if not rows or set(r["phase"] for r in rows) != {"D0+", "D1+"}:
    raise ValueError("Both drive polarities are required")

result = {
    "source": str(args.raw_log),
    "source_sha256": hashlib.sha256(args.raw_log.read_bytes()).hexdigest(),
    "phase_samples": len(rows), "dry_state_user_confirmed": args.dry,
    "salinity_accuracy_validated": False,
    "mean_balance_residual_V": mean(r["balance_residual_V"] for r in rows),
    "mean_legacy_response_is_not_a_hardware_health_check": True,
    "record_retained": True,
}
if args.dry:
    # A deliberately broad diagnostic tolerance, not an accuracy specification.
    # With an open cell, sense E1/E2 should track their respective drive nodes.
    tolerance = 0.15
    e0 = max(abs(r["A0_minus_A2_V"]) for r in rows)
    e1 = max(abs(r["A1_minus_A3_V"]) for r in rows)
    drive_ok = all((r["A2"] >= 2.8 and abs(r["A3"]) <= 0.2)
                   if r["phase"] == "D0+" else
                   (r["A3"] >= 2.8 and abs(r["A2"]) <= 0.2) for r in rows)
    result.update(dry_tolerance_V=tolerance, A0_max_tracking_error_V=e0,
                  A1_max_tracking_error_V=e1, drive_validation=drive_ok,
                  classification="DRY_RESPONSE_MATCHES_DRIVE" if drive_ok and max(e0,e1)<=tolerance
                  else "DRY_RESPONSE_MISMATCH",
                  limitation="A dry pass rules out a persistent mismatch at this time; it does not prove wet accuracy or exclude an intermittent fault.")
else:
    result["classification"] = "WET_RECORD_REQUIRES_CONTEXT"
    result["limitation"] = "Balance residual assumes matched drive resistors and no third current path; sequential ADC timing also contributes. This is diagnostic evidence, not a concentration rejection rule."
    if len(rows) >= 30:
        result["same_phase_third_forward_pair_in_first_three_commands"] = {
            f"A{ch}": [rows[i][f"A{ch}"] for i in (4,14,24)] for ch in range(4)}

path = args.raw_log.with_name(args.raw_log.stem.replace("_raw", "_electrical_check")+".json")
path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
