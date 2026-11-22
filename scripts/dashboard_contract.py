"""Bind rendered assets to their data, builder and semantic PPTX contents."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'dashboards/manifest.json'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def text_sha(path):
    # Git converts CRLF/LF between Windows worktrees and Linux CI.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def deck_sha():
    digest=hashlib.sha256()
    def consume(archive):
        for name in sorted(archive.namelist()):
            if name=='docProps/core.xml':continue
            data=archive.read(name)
            digest.update(name.encode())
            if name.endswith('.xlsx'):
                with zipfile.ZipFile(io.BytesIO(data)) as nested:consume(nested)
            else:digest.update(data)
    with zipfile.ZipFile(ROOT/'dashboards/静态看板.pptx') as archive:
        consume(archive)
    return digest.hexdigest()
def inputs():
    paths=sorted((ROOT/'outputs_public').glob('*.csv'))
    paths += [ROOT/p for p in ['config/experiments.json','scripts/build_static_dashboard.py','scripts/experiment_contract.py','scripts/export_dashboard.py','scripts/dashboard_contract.py']]
    return {p.relative_to(ROOT).as_posix():text_sha(p) for p in paths}
def snapshot():
    paths=sorted((ROOT/'dashboards/images').glob('page??.png'))+[ROOT/'dashboards/看板.pdf']
    return {'inputs':inputs(),'deck_semantic_sha256':deck_sha(),'assets':{p.relative_to(ROOT).as_posix():sha(p) for p in paths}}
def write_manifest():
    MANIFEST.write_text(json.dumps(snapshot(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def verify_manifest():
    if not MANIFEST.exists():raise AssertionError('Missing render manifest; regenerate PNG/PDF')
    expected=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if expected!=snapshot():raise AssertionError('Render inputs/deck/assets changed: regenerate PNG/PDF before publishing')
