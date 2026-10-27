import os,pathlib,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=ROOT/'.data/downloads/acpediaorg-20210615-wikidump.tar.gz'
if not source.exists():source=ROOT.parent/'ultimate-wiki/research/acpedia-20210615.tar.gz'
web=pathlib.Path(os.environ.get('ACPEDIA_WEBROOT',str(ROOT/'.runtime/mediawiki-1.43.11')));php=os.environ.get('ACPEDIA_PHP',str(ROOT/'.runtime/php/php.exe'))
args=[str(php)]+(['-c',str(ROOT/'.runtime/php/php.ini')] if os.name=='nt' else [])+[str(web/'maintenance/run.php'),'importDump','--no-updates','--report','1000','--username-prefix','acpedia-archive']
with tarfile.open(source,'r:gz') as archive:
 member=next(m for m in archive if m.name.endswith('-history.xml'))
 with archive.extractfile(member) as data,(ROOT/'.data/import-history.log').open('w',encoding='utf-8') as log:
  process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,cwd=web)
  try:
   while chunk:=data.read(1024*1024):process.stdin.write(chunk)
   process.stdin.close();code=process.wait()
  except BaseException:
   process.terminate();raise
print('History import exit:',code)
print((ROOT/'.data/import-history.log').read_text(encoding='utf-8',errors='replace')[-1600:])
raise SystemExit(code)
