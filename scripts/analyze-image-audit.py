#!/usr/bin/env python3
"""Compare the full image-reference audit with checksum-verified backups, without editing the wiki."""
import argparse
import collections
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import unicodedata
import zipfile
from download import sha

ROOT = Path(__file__).resolve().parents[1]

# Match MediaWiki's first-letter and space/underscore title equivalence only.
def canonical(name):
    name = unicodedata.normalize('NFC', name.replace('_', ' ').strip())
    return name[:1].upper() + name[1:]

# Compare punctuation as word boundaries; never merge different word sequences.
def words(name):
    return tuple(re.findall(r'\w+', name.casefold()))

# Read image names only; candidate matches remain reports, never automatic edits.
def analyze(report, output):
    rows = json.loads(report.read_text())
    if not isinstance(rows, list) or any(not isinstance(x.get('file'), str) or not isinstance(x.get('pages'), list) for x in rows):
        raise ValueError('Expected the missing-image-references.json audit report.')
    lock = json.loads((ROOT / 'sources.lock.json').read_text())
    names = set()
    for key in ('images', 'image_supplement'):
        path = ROOT / '.data/downloads' / lock[key]['name']
        if sha(path) != lock[key]['sha256']:
            raise ValueError('Backup checksum mismatch: ' + str(path))
        if key == 'images':
            with tarfile.open(path, 'r:gz') as archive:
                for member in archive:
                    if member.isfile() and PurePosixPath(member.name).suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif'):
                        names.add(canonical(PurePosixPath(member.name).name))
        else:
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if not member.is_dir() and PurePosixPath(member.filename).suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif'):
                        names.add(canonical(PurePosixPath(member.filename).name))
        print('Verified and indexed:', key, flush=True)
    token_index = collections.defaultdict(list)
    stem_index = collections.defaultdict(list)
    for name in sorted(names):
        token_index[words(name)].append(name)
        stem_index[PurePosixPath(name).stem.casefold()].append(name)
    groups = collections.defaultdict(list)
    for row in rows:
        name = canonical(row['file'])
        entry = dict(row)
        if name in names:
            kind = 'exact-backup-match'; entry['candidates'] = [name]
        elif token_index.get(words(name)):
            kind = 'punctuation-candidates'; entry['candidates'] = token_index[words(name)]
        elif stem_index.get(PurePosixPath(name).stem.casefold()):
            kind = 'extension-candidates'; entry['candidates'] = stem_index[PurePosixPath(name).stem.casefold()]
        else:
            kind = 'no-filename-match'
        groups[kind].append(entry)
    output.mkdir(parents=True, exist_ok=True)
    for kind, entries in groups.items():
        (output / (kind + '.json')).write_text(json.dumps(entries, indent=2, ensure_ascii=False) + '\n')
    summary = dict(missing_names=len(rows), image_names_in_backups=len(names),
        backup_sha256={key:lock[key]['sha256'] for key in ('images','image_supplement')},
        groups={kind:dict(names=len(entries), references=sum(len(set(x['pages'])) for x in entries)) for kind, entries in groups.items()},
        scope='Filename comparison only. Candidate images need live verification and review; nothing is applied.')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / '.data/image-audit/missing-image-references.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.data/image-audit-comparison')
    args = parser.parse_args()
    analyze(args.report, args.output)
