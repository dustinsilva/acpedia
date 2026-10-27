"""Build native MediaWiki secondary indexes in isolated snapshots, then merge by title.

Never merges revisions, users, credentials or source content. Target IDs from private
snapshots are remapped through (namespace,title), not copied across databases.
"""
from contextlib import closing,contextmanager
import argparse,concurrent.futures,json,math,os,pathlib,shutil,sqlite3,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
TABLES={'pagelinks':'pl_from','templatelinks':'tl_from','imagelinks':'il_from','categorylinks':'cl_from','externallinks':'el_from','iwlinks':'iwl_from','langlinks':'ll_from','redirect':'rd_from','page_props':'pp_page'}

def merge_worker(main,worker,start,end):
    db=sqlite3.connect(main,timeout=60)
    try:
        db.execute('ATTACH DATABASE ? AS worker',(str(worker),))
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR IGNORE INTO linktarget(lt_namespace,lt_title) SELECT lt_namespace,lt_title FROM worker.linktarget')
        for table,key in TABLES.items():
            cols=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
            if table=='externallinks':cols.remove('el_id')
            db.execute('DELETE FROM '+table+' WHERE '+key+' BETWEEN ? AND ?',(start,end))
            if table in ('pagelinks','templatelinks'):
                target='pl_target_id' if table=='pagelinks' else 'tl_target_id'
                selection=','.join('local.lt_id' if c==target else 'x.'+c for c in cols)
                sql='INSERT INTO '+table+'('+','.join(cols)+') SELECT '+selection+' FROM worker.'+table+' x JOIN worker.linktarget remote ON remote.lt_id=x.'+target+' JOIN main.linktarget local ON local.lt_namespace=remote.lt_namespace AND local.lt_title=remote.lt_title WHERE x.'+key+' BETWEEN ? AND ?'
            else:
                sql='INSERT INTO '+table+'('+','.join(cols)+') SELECT '+','.join(cols)+' FROM worker.'+table+' WHERE '+key+' BETWEEN ? AND ?'
            db.execute(sql,(start,end))
        db.execute('UPDATE page SET page_links_updated=(SELECT p.page_links_updated FROM worker.page p WHERE p.page_id=page.page_id),page_is_redirect=(SELECT p.page_is_redirect FROM worker.page p WHERE p.page_id=page.page_id) WHERE page_id BETWEEN ? AND ?',(start,end))
        db.commit()
        db.execute('DETACH DATABASE worker')
    except BaseException:
        db.rollback();raise
    finally:db.close()

def rebuild_categories(db):
    db.execute('INSERT OR IGNORE INTO category(cat_title,cat_pages,cat_subcats,cat_files) SELECT DISTINCT cl_to,0,0,0 FROM categorylinks')
    db.execute("UPDATE category SET cat_pages=(SELECT COUNT(*) FROM categorylinks WHERE cl_to=cat_title),cat_subcats=(SELECT COUNT(*) FROM categorylinks WHERE cl_to=cat_title AND cl_type='subcat'),cat_files=(SELECT COUNT(*) FROM categorylinks WHERE cl_to=cat_title AND cl_type='file')")
    db.commit()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=4);p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int);p.add_argument('--keep-workers',action='store_true');p.add_argument('--batch-size',type=int,default=1000);args=p.parse_args()
    if not 1<=args.workers<=8:raise SystemExit('Choose 1 to 8 workers')
    main_db=ROOT/'.data/db/acpedia.sqlite';work=ROOT/'.data/index-workers';work.mkdir(exist_ok=True)
    snapshot=work/'snapshot.sqlite'
    with closing(sqlite3.connect(main_db,timeout=60)) as src, closing(sqlite3.connect(snapshot)) as dest:
        total_end=src.execute('SELECT MAX(page_id) FROM page').fetchone()[0]
        end=args.end or total_end
        src.backup(dest)
    if args.start<1 or args.batch_size<1 or end<args.start:raise SystemExit('Invalid page range or batch size')
    required=snapshot.stat().st_size*(min(args.workers,len(range(args.start,end+1,args.batch_size)))+1)
    if shutil.disk_usage(work).free<required:raise SystemExit('Insufficient temporary storage for isolated index snapshots')
    print('Consistent index snapshot ready',flush=True)
    chunks=[(n,min(end,n+args.batch_size-1)) for n in range(args.start,end+1,args.batch_size)]
    jobs=[]
    for i in range(min(args.workers,len(chunks))):
        ranges=chunks[i::args.workers]
        directory=work/('worker-'+str(i+1));directory.mkdir(exist_ok=True);database=directory/'acpedia.sqlite'
        for old in [database,pathlib.Path(str(database)+'-wal'),pathlib.Path(str(database)+'-shm')]:
            if old.exists():old.unlink()
        shutil.copyfile(snapshot,database)
        jobs.append((i+1,ranges,directory,database))
    def run(job):
        number,ranges,directory,database=job;env=os.environ.copy();env['ACPEDIA_INDEX_DB']=str(directory)
        log=directory/'refresh.log'
        with log.open('w',encoding='utf-8') as out:
            for start,stop in ranges:
                out.write('Range '+str(start)+' through '+str(stop)+'\n');out.flush()
                command=[str(ROOT/'.runtime/php/php.exe'),'-c',str(ROOT/'.runtime/php/php.ini'),str(ROOT/'.runtime/mediawiki-1.43.11/maintenance/run.php'),'refreshLinks','--e',str(stop),str(start)]
                result=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,env=env,cwd=ROOT)
                if result.returncode:raise RuntimeError('Index worker '+str(number)+' failed; inspect '+str(log))
                print('Worker',number,'indexed',start,'through',stop,flush=True)
        return job
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(run,job) for job in jobs]
        for f in concurrent.futures.as_completed(futures):
            number,ranges,directory,database=f.result()
            for start,stop in ranges:merge_worker(main_db,database,start,stop)
            print('Merged worker',number,'with link target IDs remapped by namespace/title',flush=True)
    with closing(sqlite3.connect(main_db,timeout=60)) as db, db:
        rebuild_categories(db)
        integrity=db.execute('PRAGMA quick_check').fetchone()[0]
        if integrity!='ok':raise RuntimeError(integrity)
    coverage=json.dumps({'start':args.start,'end':end,'workers':args.workers,'integrity':integrity})
    (ROOT/'.data/index-coverage.json').write_text(coverage)
    if args.start==1 and end>=total_end:(ROOT/'.data/links-rebuilt.ok').write_text(coverage)
    if not args.keep_workers:
        for _,_,directory,database in jobs:
            for path in [database,pathlib.Path(str(database)+'-wal'),pathlib.Path(str(database)+'-shm')]:
                if path.exists():path.unlink()
        snapshot.unlink()
    print('Native secondary indexes complete; integrity check passed.',flush=True)
@contextmanager
def index_run_lock():
    directory=ROOT/'.data/index-workers';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'run.lock').open('a+b') as lock:
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise SystemExit('Another index rebuild is already running')
        else:
            import fcntl
            try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:raise SystemExit('Another index rebuild is already running')
        yield
if __name__=='__main__':
    with index_run_lock():main()
