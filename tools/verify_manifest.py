import hashlib,json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
failures=[]
for item in manifest['files']:
    path=root/item['repository_path']
    if not path.is_file():failures.append((item['repository_path'],'missing'));continue
    data=path.read_bytes()
    if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
        failures.append((item['repository_path'],'hash/size mismatch'))
if failures:
    for failure in failures:print(*failure)
    raise SystemExit(1)
print(f"Verified {len(manifest['files'])} current source/R6 files against SHA-256 manifest.")

