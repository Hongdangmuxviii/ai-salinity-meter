import hashlib,json,os,re,shutil
from pathlib import Path

DEST=Path(r'C:\Users\Yeon\Documents\Codex\repositories\ai-salinity-meter')
BASE=Path(r'C:\Users\Yeon\Documents\Codex')
ORIGINAL=Path(r'C:\Users\Yeon\OneDrive - 한국공학대학교\문서\ChatGPT\ai창업프로젝트')
PRUNE={'.git','node_modules','toolchain','__pycache__','.venv','venv'}
NOISE={'.DS_Store','Thumbs.db','desktop.ini'}
BUILD_SUFFIXES={'.bin','.elf','.map'}
BUILD_NAMES={'build.options.json','partitions.csv','sdkconfig','flash_args'}
TEXT={'.md','.txt','.json','.ndjson','.py','.js','.ts','.ino','.h','.csv','.yaml','.yml','.scad','.svg','.ps1','.sh','.conf','.cfg'}
SECRET=[('github_token',re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})')),
        ('openai_style_key',re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{35,}')),
        ('aws_key',re.compile(r'AKIA[0-9A-Z]{16}')),
        ('private_key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'))]
SOURCES=[
 (ORIGINAL,'project-workspace'),
 (BASE/'2026-10-10'/'referenced-chatgpt-conversation-this-is-an','history/2026-10-10/initial-head'),
 (BASE/'2026-10-30'/'salinity-team-handoff','history/2026-10-30/team-handoff'),
 (BASE/'2026-11-14'/'head-test','history/2026-11-14/head-test'),
 (BASE/'2026-11-19'/'cup90-stand','history/2026-11-19/cup90-stand'),
 (BASE/'2026-11-20'/'cup90-stand-10mm','history/2026-11-20/cup90-stand-10mm'),
 (BASE/'2026-11-20'/'final-mvp-design','history/2026-11-20/final-mvp-design'),
 (BASE/'2026-11-20'/'assembly-request','history/2026-11-20/assembly-request'),
 (BASE/'2026-11-23'/'ai-review-handoff','history/2026-11-23/ai-review-handoff'),
 (BASE/'2026-11-23'/'sensor-recheck','history/2026-11-23/sensor-recheck'),
 (BASE/'2026-11-24'/'salinity-calibration','history/2026-11-24/salinity-calibration'),
]
DEST.mkdir(parents=True,exist_ok=False)
manifest=[];excluded=[];missing=[];secret_hits=[]

def copy_file(src,relative,category):
    relative=Path(relative)
    target=DEST/relative
    if src.name in {'.env','.env.local','credentials.json','hosts.yml'}:
        excluded.append(dict(source=str(src),reason='credential/config filename'))
        return
    if src.suffix.lower() in TEXT:
        content=src.read_text(encoding='utf-8-sig',errors='replace')
        for label,pattern in SECRET:
            if pattern.search(content):secret_hits.append(dict(source=str(src),kind=label))
    if src.stat().st_size>=100_000_000:
        raise ValueError(f'File needs separate large-file handling: {src}')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,target)
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError(f'Copy mismatch: {relative}')
    manifest.append(dict(repository_path=relative.as_posix(),source=str(src),bytes=src.stat().st_size,sha256=digest,category=category))

for source,prefix in SOURCES:
    if not source.exists():missing.append(str(source));continue
    for folder,dirs,files in os.walk(source,followlinks=False):
        here=Path(folder)
        kept=[]
        for d in dirs:
            p=here/d
            if d in PRUNE or p.is_symlink():
                excluded.append(dict(source=str(p),reason='dependency/toolchain/cache/git metadata'))
            elif (d in {'core','libraries','sketch'} and
                  any(part=='build' or part.startswith('build-') for part in p.relative_to(source).parts)):
                excluded.append(dict(source=str(p),reason='compiled object/dependency cache'))
            else:kept.append(d)
        dirs[:]=kept
        for name in files:
            p=here/name;rel=p.relative_to(source)
            if name in NOISE:continue
            if any(part=='build' or part.startswith('build-') for part in rel.parts):
                if p.suffix.lower() not in BUILD_SUFFIXES and name not in BUILD_NAMES:
                    excluded.append(dict(source=str(p),reason='build cache/intermediate'));continue
            copy_file(p,Path(prefix)/rel,'original_archive')

photo_dir=Path(r'C:\Users\Yeon\AppData\Local\Temp')
for original,name in [
 ('codex-clipboard-987718e1-ac6a-4767-ad81-db6bce6b55b6.png','prototype_head_and_breadboard.png'),
 ('codex-clipboard-e9092592-61db-45ee-b71b-9cd07c5ff32d.png','prototype_xiao_ads1115.png'),
 ('codex-clipboard-3d3482e9-42a2-424e-bc93-24f52582161d.png','prototype_breadboard_closeup.png'),
 ('codex-clipboard-ae225f1f-7586-48cb-9a0e-c31108e14001.png','historical_ads1115_pin_diagram.png')]:
    p=photo_dir/original
    if p.exists():copy_file(p,Path('reference-photos')/name,'user_supplied_photo')
    else:missing.append(str(p))
for p in Path(r'C:\Users\Yeon\OneDrive - 한국공학대학교\바탕 화면\새 폴더 (3)').glob('KakaoTalk_20261120_*.png'):
    copy_file(p,Path('hardware/original-R4-P2-images')/p.name,'user_supplied_diagram')

latest=BASE/'2026-11-24'/'salinity-calibration'
for p in (latest/'SalinityMeterCalibrated').iterdir():
    if p.is_file():copy_file(p,Path('firmware/SalinityMeterCalibrated')/p.name,'current_firmware')
for name in ['calibration_model.json','calibration_references.csv','completion_verification.json','보정표_저장완료_기록.txt']:
    copy_file(latest/name,Path('calibration/current')/name,'current_calibration')
for p in latest.glob('*_raw.txt'):copy_file(p,Path('calibration/current/raw')/p.name,'calibration_raw')
for name in ['SalinityMeterCalibrated.ino.bin','SalinityMeterCalibrated.ino.merged.bin']:
    copy_file(latest/'build'/name,Path('firmware/releases/2026-11-24')/name,'current_binary')
if secret_hits:
    (DEST/'SECRET_SCAN_BLOCKED.json').write_text(json.dumps(secret_hits,ensure_ascii=False,indent=2),encoding='utf-8')
    raise ValueError('Potential credentials detected; inspect path-only report before committing')
result=dict(export_date='2026-11-24',files=manifest,excluded=excluded,unavailable_sources=missing,
            note='Original project-specific files are preserved byte-for-byte. Dependencies, compiler installations, object caches, OS files and Git internals are excluded. Current firmware/calibration copies are convenience entry points; history is retained.')
(DEST/'SOURCE_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(destination=str(DEST),files=len(manifest),MB=round(sum(f['bytes'] for f in manifest)/1048576,2),excluded_entries=len(excluded),missing=missing,potential_credentials=0),ensure_ascii=False,indent=2))
