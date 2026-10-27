"""Bootstrap the faithful ACPedia restoration on Windows with Python 3 and Git."""
import argparse,json,os,pathlib,shutil,sqlite3,subprocess,sys
from download import drive,runtime,ROOT

def call(script):subprocess.run([sys.executable,str(ROOT/'scripts'/script)],check=True,cwd=ROOT)
def php(*args):subprocess.run([str(ROOT/'.runtime/php/php.exe'),'-c',str(ROOT/'.runtime/php/php.ini'),*map(str,args)],check=True,cwd=ROOT)
def maintenance(*args):php(ROOT/'.runtime/mediawiki-1.43.11/maintenance/run.php',*args)
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--latest-only',action='store_true',help='Skip historical revisions; default restores histories as well');args=parser.parse_args()
 if os.name!='nt':raise SystemExit('This bootstrap targets Windows. See docs/DEPLOYMENT.md for a Linux/PHP host.')
 data=ROOT/'.data';data.mkdir(exist_ok=True);downloads=data/'downloads';downloads.mkdir(exist_ok=True)
 lock=json.loads((ROOT/'sources.lock.json').read_text())
 # Reuse the backups already inspected in the parent project when available.
 for key,old in [('content','acpedia-20210615.tar.gz'),('image_supplement','acpedia-2018-to-2024-images.zip')]:
  item=lock[key];dest=downloads/item['name'];prior=ROOT.parent/'ultimate-wiki/research'/old
  if not dest.exists() and prior.exists():shutil.copyfile(prior,dest)
 for key in ['content','images','image_supplement']:
  item=lock[key];drive(item['file_id'],downloads/item['name'],item.get('sha256'))
 if not (ROOT/'.runtime/runtime-ready.json').exists():
  runtime();(ROOT/'.runtime/runtime-ready.json').write_text(json.dumps({'mediawiki':'1.43.11','php':'8.3.36'}))
 call('configure-php.py')
 web=ROOT/'.runtime/mediawiki-1.43.11'
 for name,ext in lock['extensions'].items():
  dest=web/'extensions'/name
  if not dest.exists():subprocess.run(['git','clone',ext['url'],str(dest)],check=True)
  subprocess.run(['git','-C',str(dest),'checkout','--detach',ext['commit']],check=True)
 call('install-local.py');call('link-settings.py');call('enable-wal.py');call('prepare-content.py')
 if not (data/'pages-imported.ok').exists():
  maintenance('importDump','--no-updates','--username-prefix','acpedia-archive','--report','1000',data/'latest.xml');(data/'pages-imported.ok').touch()
 if not (data/'image-manifest.json').exists():call('prepare-images.py')
 php(ROOT/'scripts/register-images.php','--source',data/'image-source')
 if (data/'image-supplement.xml').exists():maintenance('importDump','--no-updates','--username-prefix','acpedia-archive',data/'image-supplement.xml')
 if not args.latest_only and not (data/'history-imported.ok').exists():
  call('import-history.py');(data/'history-imported.ok').touch()
 call('restore-current.py');maintenance('rebuildtextindex');call('parallel-index.py');maintenance('initSiteStats','--update')
 print('Restored. Run scripts/start.ps1 and open http://127.0.0.1:8770/wiki/Home')
if __name__=='__main__':main()
