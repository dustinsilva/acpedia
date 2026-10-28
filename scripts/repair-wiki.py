"""Preview or apply targeted restoration repairs using current live revisions.

Run compare-backup.py first. No database credentials are read by this program.
Only --apply invokes the local MediaWiki maintenance writer.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from repair_content import repair_wikitext

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compare_backup',ROOT/'scripts/compare-backup.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)

def live_replacements(server, replacements):
    """Only redirect genuinely missing images to registered, existing images."""
    names=list(dict.fromkeys(list(replacements)+list(replacements.values())))
    exists=set()
    for start in range(0,len(names),40):
        result=backup.query(server,prop='imageinfo',titles='|'.join('File:'+n for n in names[start:start+40]),iiprop='url')
        for page in result['query']['pages'].values():
            if page.get('imageinfo'):
                exists.add(backup.canonical(page['title'].split(':',1)[1]))
    return {old:new for old,new in replacements.items() if old not in exists and new in exists}

def build_plan(server, report):
    replacements=live_replacements(server,json.loads((report/'image-replacements.json').read_text()))
    candidates=json.loads((report/'compatibility-candidates.json').read_text())
    edits=[]
    for start in range(0,len(candidates),20):
        titles='|'.join(row['title'] for row in candidates[start:start+20])
        result=backup.query(server,prop='revisions',titles=titles,rvprop='ids|content|timestamp',rvslots='main')
        for page in result['query']['pages'].values():
            revisions=page.get('revisions',[])
            if not revisions:continue
            revision=revisions[0];slot=revision['slots']['main']
            if slot.get('contentmodel')!='wikitext':continue
            before=slot['*'];after,changes=repair_wikitext(before,replacements)
            if after==before:continue
            edits.append({'title':page['title'],'base_revision':revision['revid'],
                'before_sha256':hashlib.sha256(before.encode()).hexdigest(),
                'before':before,'after':after,'changes':changes})
        print('Checked',min(start+20,len(candidates)),'/',len(candidates),'candidates',flush=True)
    return {'server':server,'created_at':datetime.now(timezone.utc).isoformat(),
        'backup_sha256':json.loads((report/'comparison.json').read_text())['backup_sha256'],
        'image_replacements':replacements,'edits':edits}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server',default='https://acpedia.celestro.com')
    p.add_argument('--report',type=Path,default=ROOT/'.data/repair-report')
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    plan=build_plan(args.server,args.report)
    folder=ROOT/'.data/repairs';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    path.write_text(json.dumps(plan,indent=2),encoding='utf-8');path.chmod(0o600)
    print('Plan and original revision backups:',path)
    print('Pages to edit:',len(plan['edits']),'validated image substitutions:',len(plan['image_replacements']))
    if args.apply:
        env=dict(os.environ,ACPEDIA_WEBROOT=os.environ.get('ACPEDIA_WEBROOT',str(ROOT/'public')))
        subprocess.run([os.environ.get('ACPEDIA_PHP','php'),str(ROOT/'scripts/apply-repairs.php'),'--plan',str(path),'--apply'],env=env,check=True)
