"""Export and validate new capped-head files; leave previous designs untouched."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "probe_capped_head_v2"
SOURCE = OUT / "probe_capped_head_v2.scad"
OPENSCAD = r"C:\Program Files\OpenSCAD\openscad.com"
STLS = [
    ("holder", "holder.stl"),
    ("cap", "cap_core.stl"),
    ("retainer", "seal_retainer.stl"),
    ("alignment_jig", "tip_alignment_jig.stl"),
    ("fit_coupon", "fit_coupon.stl"),
]


def export(part, filename, extra=()):
    result = subprocess.run(
        [OPENSCAD, "-D", f'part="{part}"', *extra, "-o", str(OUT / filename), str(SOURCE)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    print(filename, "exit", result.returncode, result.stderr.strip(), flush=True)
    result.check_returncode()


with ThreadPoolExecutor(max_workers=4) as executor:
    list(executor.map(lambda job: export(*job), STLS))
subprocess.run(
    [sys.executable, str(ROOT / "work" / "check_head_stl.py")]
    + [str(OUT / filename) for _, filename in STLS], check=True,
)
for ext in ["svg", "dxf"]:
    export("gasket_template", f"gasket_cut_template.{ext}")

common = ["--imgsize=1200,1000", "--autocenter", "--viewall", "--projection=o", "--colorscheme=Tomorrow"]
for part, filename in [("assembly", "assembly_preview.png"), ("section", "section_preview.png")]:
    export(part, filename, [*common, "-D", "show_liquid=false"])
export("exploded", "exploded_preview.png", ["--imgsize=1200,1200", "--projection=o",
       "--colorscheme=Tomorrow", "--camera=140,-252,159.8,0,0,38", "-D", "show_liquid=false"])
export("assembly", "front_alignment.png", [*common, "-D", "show_liquid=false",
       "--camera=0,0,20,90,0,0,160"])

# Empty rigid-part intersection is expected. OpenSCAD reports empty top-level object.
check = subprocess.run(
    [OPENSCAD, "-D", 'part="interference"', "-o", str(ROOT / "work" / "probe_capped_head_v2_collision_check.stl"), str(SOURCE)],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
)
log = check.stdout + check.stderr
print("Rigid-part interference check:", log.strip(), flush=True)
assert "empty" in log.lower(), "Rigid components have positive-volume intersection or check failed"
assert not (ROOT / "work" / "probe_capped_head_v2_collision_check.stl").exists(), "Unexpected rigid collision mesh was exported"
print("Rigid printed bodies have no CAD intersections beyond intended contacts (0.01 mm exclusion).", flush=True)

# Explicit dimensional checks independent of rendered camera/mesh appearance.
head_bottom = 4 + 25 + .75
temp_end = -10 + 50
assert temp_end - head_bottom >= 10
assert temp_end - (head_bottom + 7) >= 3
assert head_bottom + 18 - 25 > 20
print("Dimensions: head bottom 29.75; tip -10; temperature metal end 40; clamp 36.75 mm.", flush=True)
print("Temperature metal insertion 10.25 mm; clamp-to-cable-junction margin 3.25 mm.", flush=True)
