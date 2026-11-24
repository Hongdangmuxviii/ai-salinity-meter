"""USB test client for SalinityMeterApp (no phone app needed).

    python tools/serial_client.py COM5 m              # salinity (legacy lines + EVT json)
    python tools/serial_client.py COM5 scan           # ToF depth map + photo -> captures/*.jpg
    python tools/serial_client.py COM5 "target 1.2" guide

Requires: pip install pyserial
Each EVT line is also appended to captures/events.jsonl.
"""
import base64
import json
import pathlib
import sys
import time
import zlib

import serial

OUT = pathlib.Path("captures")
QUIET_SECONDS = {"m": 15, "measure": 15, "recheck": 20, "cellcal": 15, "scan": 25, "photo": 20}


def run(port: str, commands: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    with serial.Serial(port, 115200, timeout=0.2) as link, open(OUT / "events.jsonl", "a", encoding="utf-8") as log:
        time.sleep(0.3)
        link.reset_input_buffer()
        for command in commands:
            link.write((command + "\n").encode())
            wait = QUIET_SECONDS.get(command.split()[0].lower(), 5)
            deadline = time.time() + wait
            image = None
            while time.time() < deadline:
                raw = link.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", "replace").rstrip()
                deadline = max(deadline, time.time() + 2)  # extend while output flows
                if line.startswith("IMG_B64_BEGIN"):
                    fields = dict(f.split("=", 1) for f in line.split()[1:])
                    image = {"meta": fields, "parts": []}
                    continue
                if line.startswith("IMG_B64 ") and image is not None:
                    image["parts"].append(line.split(" ", 2)[2])
                    continue
                if line.startswith("IMG_B64_END") and image is not None:
                    data = base64.b64decode("".join(image["parts"]))
                    crc = f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"
                    ok = crc == image["meta"]["crc32"] and len(data) == int(image["meta"]["bytes"])
                    path = OUT / f"img_{time.strftime('%Y%m%d_%H%M%S')}_{image['meta']['id']}.jpg"
                    path.write_bytes(data)
                    print(f"IMAGE saved {path} bytes={len(data)} crc_ok={ok}")
                    image = None
                    continue
                print(line)
                if line.startswith("EVT "):
                    try:
                        event = json.loads(line[4:])
                    except json.JSONDecodeError:
                        continue
                    event["_received"] = time.time()
                    log.write(json.dumps(event, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2:])
