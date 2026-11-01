"""Authenticate original recovery from its immutable bundle, not evolving code.

All 191 original blobs remain byte-exact. Apache-2.0.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '979a0996299a00d13523ef5277c9b02ef4ad747b'
BUNDLE_SHA256 = '14ddaf3283e96a50d3745d5064435c0cfb52702c9cd552c353e1d38b6770adbc'


def verify(root=ROOT):
    root = Path(root)
    ledger = json.loads((root/'docs/pr36-staged-recovery.json').read_text())
    if ledger['completed_stage'] != 10 or ledger['source_commit'] != SOURCE:
        raise ValueError('Completed original recovery and exact source commit required')
    files = {}
    if len(ledger['stages']) != 10:
        raise ValueError('Original stage coverage mismatch')
    for stage in ledger['stages']:
        for name, expected in stage['files'].items():
            if name in files: raise ValueError('Duplicate staged path: '+name)
            files[name] = expected
    if len(files) != 191: raise ValueError('Original change-set coverage mismatch')
    bundle = ledger['source_bundle']; path = root/bundle['path']
    data = path.read_bytes()
    if (len(data) != bundle['bytes'] or bundle['sha256'] != BUNDLE_SHA256
            or hashlib.sha256(data).hexdigest() != BUNDLE_SHA256):
        raise ValueError('Original bundle length/SHA-256 mismatch')
    with tempfile.TemporaryDirectory(prefix='eft-original-recovery-') as directory:
        def git(*args):
            return subprocess.check_output(['git','-C',directory,*args],stderr=subprocess.PIPE)
        git('init','--bare','--quiet')
        git('bundle','verify',str(path.resolve()))
        git('-c','transfer.fsckObjects=true','fetch','--quiet',str(path.resolve()),SOURCE)
        tree = {}
        for record in git('ls-tree','-rz',SOURCE).split(b'\0'):
            if not record: continue
            header,name = record.split(b'\t',1)
            mode,kind,oid = header.decode().split()
            if kind == 'blob': tree[name.decode()] = oid
        for name, expected in files.items():
            if tree.get(name) != expected: raise ValueError('Original archived blob mismatch: '+name)
            blob = git('cat-file','blob',expected)
            actual = hashlib.sha1(f'blob {len(blob)}\0'.encode()+blob).hexdigest()
            if actual != expected: raise ValueError('Original archived bytes mismatch: '+name)
    return len(files)


if __name__ == '__main__':
    count = verify()
    print(f'Stage 10/10: {count}/191 original archived files verified byte-exact; no scientific acceptance implied.')
    print('Exact original commit and complete-history bundle verified; current development files may evolve.')
