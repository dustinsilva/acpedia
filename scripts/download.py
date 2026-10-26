"""Public, resumable ACPedia restoration downloads. No credentials are required."""
import argparse,concurrent.futures,hashlib,json,pathlib,re,shutil,urllib.parse,urllib.request,zipfile,tarfile
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Form(HTMLParser):
 def __init__(self):super().__init__();self.action=None;self.fields={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='form' and a.get('id')=='download-form':self.action=a['action']
  if tag=='input' and a.get('type')=='hidden':self.fields[a['name']]=a.get('value','')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def download(url,path,expected=None):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  if expected and sha(path)!=expected:raise ValueError('Existing checksum mismatch: '+str(path))
  return path
 req=urllib.request.Request(url,headers={'User-Agent':'ACPediaRestoration/1.0 (https://github.com/dustinsilva/acpedia)'})
 response=urllib.request.urlopen(req,timeout=60);head=response.read(4096)
 if b'<html' in head[:500] or head.lstrip().startswith(b'<!DOCTYPE'):
  page=(head+response.read(1000000)).decode();response.close();form=Form();form.feed(page)
  if form.action!='https://drive.usercontent.google.com/download':raise ValueError('Unexpected HTML instead of archive')
  response=urllib.request.urlopen(form.action+'?'+urllib.parse.urlencode(form.fields),timeout=60);head=response.read(4096)
  if b'<html' in head[:500]:raise ValueError('Download denied or quota exceeded')
 partial=path.with_suffix(path.suffix+'.partial');size=0;next_notice=100*1024*1024
 try:
  with response,partial.open('wb') as f:
   f.write(head);size=len(head)
   while chunk:=response.read(1024*1024):
    f.write(chunk);size+=len(chunk)
    if size>=next_notice:print(path.name,round(size/1024/1024),'MiB',flush=True);next_notice+=100*1024*1024
  if expected and sha(partial)!=expected:raise ValueError('Downloaded checksum mismatch')
  partial.replace(path);print('Ready',path.name,size,flush=True)
 finally:
  if partial.exists():partial.unlink()
 return path

def drive(fid,path,expected=None):
 page=urllib.request.urlopen('https://drive.google.com/file/d/'+fid+'/view',timeout=40).read().decode()
 url=json.loads('"'+re.search(r'"(https://drive.usercontent.google.com/uc[^" ]+)"',page)[1]+'"')
 return download(url,path,expected)
def contained(base,name):
 target=(base/name).resolve()
 if not target.is_relative_to(base.resolve()):raise ValueError('Unsafe archive path')
 return target

def unpack(path,target):
 target.mkdir(parents=True,exist_ok=True)
 if str(path).endswith('.zip'):
  with zipfile.ZipFile(path) as z:
   for m in z.infolist():contained(target,m.filename)
   z.extractall(target)
 else:
  with tarfile.open(path) as t:
   for m in t:
    if not(m.isfile() or m.isdir()):continue
    dest=contained(target,m.name)
    if m.isdir():dest.mkdir(parents=True,exist_ok=True)
    else:
     dest.parent.mkdir(parents=True,exist_ok=True)
     with t.extractfile(m) as src,dest.open('wb') as out:shutil.copyfileobj(src,out)

def runtime():
 r=ROOT/'.runtime';r.mkdir(exist_ok=True)
 def php():
  p=download('https://downloads.php.net/~windows/releases/archives/php-8.3.36-nts-Win32-vs16-x64.zip',r/'php.zip','3c9242622c7402b47c38d2ec2ed779cef3a290fd6f2bde6c35f9c482699e7900');unpack(p,r/'php')
 def mw():
  p=download('https://releases.wikimedia.org/mediawiki/1.43/mediawiki-1.43.11.tar.gz',r/'mediawiki.tar.gz');unpack(p,r)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for f in [pool.submit(php),pool.submit(mw)]:f.result()

def images():
 r=ROOT/'.data'/'downloads';r.mkdir(parents=True,exist_ok=True)
 drive('11IPYwHyiZpYDXq8jlS32UfrqgV2FMQBE',r/'acpediaorg-20180217-imagedump.tar.gz')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task',choices=['runtime','images']);a=p.parse_args();globals()[a.task]()
