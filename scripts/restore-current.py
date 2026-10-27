"""Restore captured current text where installer/import placeholders are newer than the archive."""
import os,pathlib,subprocess,xml.etree.ElementTree as E
ROOT=pathlib.Path(__file__).resolve().parents[1];ns='{http://www.mediawiki.org/xml/export-0.6/}';pages=[]
for _,p in E.iterparse(ROOT/'.data/latest.xml',events=('end',)):
 if p.tag!=ns+'page':continue
 if p.findtext(ns+'title')=='Main Page':
  pages.append(('Main Page',p.findtext(ns+'revision/'+ns+'text','')));break
 p.clear()
supplement=ROOT/'.data/image-supplement.xml'
if supplement.exists():
 for p in E.parse(supplement).getroot().findall(ns+'page'):
  if p.findtext(ns+'ns')=='6':
   revisions=p.findall(ns+'revision');latest=max(revisions,key=lambda r:r.findtext(ns+'timestamp',''))
   pages.append((p.findtext(ns+'title'),latest.findtext(ns+'text','')))
web=pathlib.Path(os.environ.get('ACPEDIA_WEBROOT',str(ROOT/'.runtime/mediawiki-1.43.11')))
php=os.environ.get('ACPEDIA_PHP',str(ROOT/'.runtime/php/php.exe'))
for title,text in pages:
 args=[php]+(['-c',str(ROOT/'.runtime/php/php.ini')] if os.name=='nt' else [])+[str(web/'maintenance/run.php'),'edit','--user','RestorationAdmin','--bot','--no-rc','--summary','Restore captured ACPedia current text after import; original history retained',title]
 result=subprocess.run(args,input=text.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=ROOT)
 if result.returncode:raise RuntimeError(result.stdout.decode(errors='replace'))
print('Archived current text verified for',len(pages),'pages; no-op edits are skipped by MediaWiki.')
