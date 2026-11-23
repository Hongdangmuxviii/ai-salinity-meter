"""Export the authored OpenSCAD prototype without changing existing head files."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "probe_rim_frame_v1"
SOURCE = OUT / "probe_rim_frame_v1.scad"
OPENSCAD = r"C:\Program Files\OpenSCAD\openscad.com"
JOBS = [
    ("bridge", "rim_bridge.stl"),
    ("stop", "rim_stop.stl"),
    ("spacer5", "head_spacer_5mm.stl"),
    ("coupon", "fit_coupon.stl"),
]


def export(job):
    part, filename = job
    result = subprocess.run(
        [OPENSCAD, "-D", f'part="{part}"', "-o", str(OUT / filename), str(SOURCE)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    print(filename, "exit", result.returncode, result.stderr.strip(), flush=True)
    result.check_returncode()


with ThreadPoolExecutor(max_workers=4) as executor:
    list(executor.map(export, JOBS))

subprocess.run(
    ["python", str(ROOT / "work" / "check_head_stl.py")]
    + [str(OUT / filename) for _, filename in JOBS], check=True,
)

preview = subprocess.run(
    [OPENSCAD, "-D", 'part="assembly"', "-D", "show_liquid=false",
     "--imgsize=1200,900", "--autocenter", "--viewall", "--projection=o",
     "--colorscheme=Tomorrow", "-o", str(OUT / "assembly_preview.png"), str(SOURCE)],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
)
print("assembly_preview.png", "exit", preview.returncode, preview.stderr.strip(), flush=True)
preview.check_returncode()
