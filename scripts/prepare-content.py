import hashlib,json,pathlib,tarfile,xml.etree.ElementTree as E
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/'.data/downloads/acpediaorg-20210615-wikidump.tar.gz'
if not SOURCE.exists():SOURCE=ROOT.parent/'ultimate-wiki/research/acpedia-20210615.tar.gz'
def prepare():
 dest=ROOT/'.data';dest.mkdir(exist_ok=True)
 if (dest/'latest.xml').exists() and (dest/'source-manifest.json').exists():return
 with tarfile.open(SOURCE,'r:gz') as t:
  member=next(m for m in t if m.name.endswith('-history.xml'))
  with t.extractfile(member) as src, (dest/'latest.xml').open('wb') as out:
   it=E.iterparse(src,events=('start','end'));_,root=next(it);ns=root.tag.split('}')[0]+'}';E.register_namespace('',ns[1:-1]);out.write(('<?xml version="1.0" encoding="UTF-8"?>\n<mediawiki xmlns="'+ns[1:-1]+'" version="0.6" xml:lang="en">\n').encode());count=0
   for event,p in it:
    if event!='end':continue
    if p.tag==ns+'siteinfo':out.write(E.tostring(p,encoding='utf-8'))
    if p.tag!=ns+'page':continue
    revs=p.findall(ns+'revision')
    if revs:
     latest=max(revs,key=lambda r:r.findtext(ns+'timestamp',''))
     for r in revs:
      if r is not latest:p.remove(r)
    out.write(E.tostring(p,encoding='utf-8'));count+=1
    title=p.findtext(ns+'title','')
    if title in ['MediaWiki:Common.css','MediaWiki:Sidebar','MediaWiki:Monobook.css','Home'] and revs:
     name=title.replace(':','-')+'.wikitext';(dest/name).write_text(latest.findtext(ns+'text',''),encoding='utf-8')
    p.clear();root.clear()
   out.write(b'</mediawiki>')
 (dest/'source-manifest.json').write_text(json.dumps({'source':'acpediaorg-20210615-wikidump.tar.gz','sha256':'24227485b273eb87812661d431ad03c802b4409ea80fa25eb78705dab72adcb5','pages':count,'mode':'latest revision selected per page; source history retained separately'},indent=2))
 print('Prepared',count,'original ACPedia pages',flush=True)
if __name__=='__main__':prepare()
