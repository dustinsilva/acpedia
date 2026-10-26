from contextlib import closing
import importlib.util,pathlib,sqlite3,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('parallel_index',ROOT/'scripts/parallel-index.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
SCHEMA='''
CREATE TABLE linktarget(lt_id INTEGER PRIMARY KEY,lt_namespace INTEGER,lt_title TEXT,UNIQUE(lt_namespace,lt_title));
CREATE TABLE page(page_id INTEGER PRIMARY KEY,page_links_updated TEXT,page_is_redirect INTEGER);
CREATE TABLE pagelinks(pl_from INTEGER,pl_target_id INTEGER,pl_from_namespace INTEGER);
CREATE TABLE templatelinks(tl_from INTEGER,tl_target_id INTEGER,tl_from_namespace INTEGER);
CREATE TABLE imagelinks(il_from INTEGER,il_to TEXT);
CREATE TABLE categorylinks(cl_from INTEGER,cl_to TEXT,cl_type TEXT);
CREATE TABLE externallinks(el_id INTEGER PRIMARY KEY,el_from INTEGER,el_to_domain_index TEXT,el_to_path TEXT);
CREATE TABLE iwlinks(iwl_from INTEGER,iwl_prefix TEXT,iwl_title TEXT);
CREATE TABLE langlinks(ll_from INTEGER,ll_lang TEXT,ll_title TEXT);
CREATE TABLE redirect(rd_from INTEGER,rd_namespace INTEGER,rd_title TEXT);
CREATE TABLE page_props(pp_page INTEGER,pp_propname TEXT,pp_value TEXT);
'''
class IndexMergeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.main=pathlib.Path(self.temp.name)/'main.sqlite';self.worker=pathlib.Path(self.temp.name)/'worker.sqlite'
  for file in [self.main,self.worker]:
   with closing(sqlite3.connect(file)) as db, db:db.executescript(SCHEMA);db.executemany('INSERT INTO page VALUES (?,?,?)',[(1,'old',0),(2,'old',0)])
  with closing(sqlite3.connect(self.main)) as db, db:
   db.execute("INSERT INTO linktarget VALUES (7,0,'Existing main target')");db.executemany('INSERT INTO pagelinks VALUES (?,?,?)',[(1,7,0),(2,7,0)])
  with closing(sqlite3.connect(self.worker)) as db, db:
   db.execute("INSERT INTO linktarget VALUES (7,0,'Different worker target')");db.execute('INSERT INTO pagelinks VALUES (1,7,0)');db.execute('INSERT INTO templatelinks VALUES (1,7,0)');db.execute("INSERT INTO externallinks VALUES (1,1,'org.example.','/a')");db.execute("UPDATE page SET page_links_updated='new' WHERE page_id=1")
 def test_remaps_target_ids_and_preserves_other_pages(self):
  module.merge_worker(self.main,self.worker,1,1)
  with closing(sqlite3.connect(self.main)) as db, db:
   rows=db.execute('SELECT pl_from,lt_title FROM pagelinks JOIN linktarget ON lt_id=pl_target_id ORDER BY pl_from').fetchall()
   self.assertEqual(rows,[(1,'Different worker target'),(2,'Existing main target')])
   self.assertEqual(db.execute('SELECT lt_title FROM templatelinks JOIN linktarget ON lt_id=tl_target_id').fetchone()[0],'Different worker target')
   self.assertEqual(db.execute('SELECT page_links_updated FROM page WHERE page_id=1').fetchone()[0],'new')
 def test_repeat_merge_is_idempotent(self):
  module.merge_worker(self.main,self.worker,1,1);module.merge_worker(self.main,self.worker,1,1)
  with closing(sqlite3.connect(self.main)) as db, db:
   self.assertEqual(db.execute('SELECT count(*) FROM pagelinks WHERE pl_from=1').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT count(*) FROM externallinks WHERE el_from=1').fetchone()[0],1)
if __name__=='__main__':unittest.main()
