import os,collections,hashlib,json,pathlib,shutil,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];data=ROOT/'.data';target=data/'image-source';target.mkdir(exist_ok=True)
allowed={'.jpg','.jpeg','.png','.gif','.svg','.pdf','.ogg','.mp3','.wav','.webm','.zip'};counts=collections.Counter();entries=[];skipped=[]
def store(name,stream,size,origin):
 name=pathlib.PurePosixPath(name).name
 if pathlib.Path(name).suffix.lower() not in allowed:return
 if os.name == 'nt' and any(x in name for x in '<>:"/\\|?*'):
  skipped.append(name);return
 dest=target/name.replace(' ','_')
 with dest.open('wb') as out:shutil.copyfileobj(stream,out)
 entries.append({'name':dest.name,'bytes':size,'origin':origin});counts[pathlib.Path(name).suffix.lower()]+=1
 if len(entries)%5000==0:print('Staged',len(entries),'image/media files',flush=True)
with tarfile.open(data/'downloads/acpediaorg-20180217-imagedump.tar.gz','r:gz') as t:
 for m in t:
  if m.isfile():store(m.name,t.extractfile(m),m.size,'2018-02-17 base')
supp=ROOT/'.data/downloads/acpediaorg-2018-to-2024-images.zip'
if not supp.exists():supp=ROOT.parent/'ultimate-wiki/research/acpedia-2018-to-2024-images.zip'
with zipfile.ZipFile(supp) as z:
 for m in z.infolist():
  if m.filename.endswith('.xml'):(data/'image-supplement.xml').write_bytes(z.read(m))
  elif not m.is_dir():
   with z.open(m) as src:store(m.filename,src,m.file_size,'2024-01-14 supplement')
(data/'image-manifest.json').write_text(json.dumps({'files':entries,'types':dict(counts),'skipped_unsafe_windows_names':skipped},indent=2),encoding='utf-8')
print('Ready',len(entries),'media records; skipped filenames:',len(skipped),flush=True)
