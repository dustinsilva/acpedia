"""Compare a public wiki's wanted targets with checksum-pinned ACPedia backups.

Produces evidence and exact recovery candidates; never edits the live wiki.
"""
import argparse
import collections
import json
from pathlib import Path, PurePosixPath
import tarfile
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from download import sha
from repair_content import repair_wikitext

ROOT = Path(__file__).resolve().parents[1]

def canonical(name):
    name = unicodedata.normalize('NFC', name.replace('_', ' ').strip())
    return name[:1].upper() + name[1:]

def query(server, **params):
    url = server.rstrip('/') + '/api.php?' + urllib.parse.urlencode(dict(action='query', format='json', **params))
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'ACPediaRestoration/1.0'}), timeout=60) as r:
        result = json.load(r)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result

def wanted(server, report):
    rows = []; offset = 0
    while True:
        result = query(server, list='querypage', qppage=report, qplimit=500, qpoffset=offset)
        rows += result['query']['querypage']['results']
        if 'continue' not in result:
            return rows
        offset = result['continue']['qpoffset']

def inspect(output, server, inventory=None):
    output.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT/'sources.lock.json').read_text())
    for key in ('content', 'images', 'image_supplement'):
        path = ROOT/'.data/downloads'/lock[key]['name']
        if sha(path) != lock[key]['sha256']:
            raise RuntimeError('Backup checksum mismatch: ' + str(path))
    if inventory:
        files = json.loads((inventory/'wantedfiles.json').read_text())
        pages = json.loads((inventory/'wantedpages.json').read_text())
    else:
        files = wanted(server, 'Wantedfiles'); pages = wanted(server, 'Wantedpages')
    (output/'wantedfiles.json').write_text(json.dumps(files, indent=2))
    (output/'wantedpages.json').write_text(json.dumps(pages, indent=2))
    binaries = collections.defaultdict(list)
    with tarfile.open(ROOT/'.data/downloads'/lock['images']['name'], 'r:gz') as archive:
        for member in archive:
            if member.isfile() and PurePosixPath(member.name).suffix.lower() in {'.png','.jpg','.jpeg','.gif'}:
                binaries[canonical(PurePosixPath(member.name).name)].append({'archive':'images','member':member.name,'bytes':member.size})
    with zipfile.ZipFile(ROOT/'.data/downloads'/lock['image_supplement']['name']) as archive:
        for member in archive.infolist():
            if not member.is_dir() and PurePosixPath(member.filename).suffix.lower() in {'.png','.jpg','.jpeg','.gif'}:
                binaries[canonical(PurePosixPath(member.filename).name)].append({'archive':'image_supplement','member':member.filename,'bytes':member.file_size})
    stems = collections.defaultdict(set)
    for name in binaries:
        stems[PurePosixPath(name).stem.casefold()].add(name)
    replacements = {}
    for row in files:
        name = canonical(row['title'].split(':',1)[1])
        alternatives = stems.get(PurePosixPath(name).stem.casefold(), set())
        if name not in binaries and len(alternatives) == 1:
            replacements[name] = next(iter(alternatives))
    (output/'backup-media-names.json').write_text(json.dumps(sorted(binaries),indent=2),encoding='utf-8')
    missing_names = {canonical(row['title']):row for row in pages if row['ns'] != 6}
    source_titles = set(); recovered = []; compatibility = []
    with tarfile.open(ROOT/'.data/downloads'/lock['content']['name'], 'r:gz') as archive:
        member = next(m for m in archive if m.name.endswith('-history.xml'))
        with archive.extractfile(member) as stream:
            parser = ET.iterparse(stream, events=('start','end')); _,root = next(parser)
            ns = root.tag.split('}')[0] + '}'
            for event, page in parser:
                if event != 'end' or page.tag != ns+'page':
                    continue
                title = page.findtext(ns+'title', '')
                source_titles.add(canonical(title))
                revisions = page.findall(ns+'revision')
                if revisions:
                    latest = max(revisions, key=lambda r:r.findtext(ns+'timestamp',''))
                    text = latest.findtext(ns+'text','')
                    metadata = {'title':title,'source_revision':latest.findtext(ns+'id'), 'source_timestamp':latest.findtext(ns+'timestamp')}
                    if canonical(title) in missing_names:
                        # Preserve the original XML page and latest archived revision.
                        for revision in revisions:
                            if revision is not latest: page.remove(revision)
                        recovered.append({**metadata,'xml':ET.tostring(page, encoding='unicode')})
                    fixed,changes = repair_wikitext(text, replacements)
                    if fixed != text:
                        compatibility.append({**metadata,'changes':changes})
                page.clear();root.clear()
    recoverable_files = []; unavailable_files = []
    for row in files:
        name = canonical(row['title'].split(':',1)[1])
        candidates = binaries.get(name, [])
        (recoverable_files if candidates else unavailable_files).append({**row,'sources':candidates})
    summary = {
        'server':server,'backup_sha256':{k:lock[k]['sha256'] for k in ('content','images','image_supplement')},
        'archived_page_titles':len(source_titles),'archived_unique_media_names':len(binaries),
        'wanted_files':len(files),'exactly_recoverable_files':len(recoverable_files),
        'files_absent_from_pinned_backups':len(unavailable_files),
        'wanted_non_file_pages':len(missing_names),'exactly_recoverable_pages':len(recovered),
        'pages_absent_from_text_backup':sum(t not in source_titles for t in missing_names),
        'compatibility_candidates':len(compatibility),
        'unique_stem_image_references':len(replacements),
    }
    for name, data in [('comparison',summary),('image-replacements',replacements),('recoverable-files',recoverable_files),('unavailable-files',unavailable_files),('recoverable-pages',recovered),('compatibility-candidates',compatibility)]:
        (output/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',default='https://acpedia.celestro.com')
    parser.add_argument('--output',type=Path,default=ROOT/'.data/repair-report')
    parser.add_argument('--inventory',type=Path,help='Use a previously captured wantedfiles.json/wantedpages.json pair')
    args=parser.parse_args();inspect(args.output,args.server,args.inventory)
