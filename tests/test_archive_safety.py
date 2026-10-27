"""Safety checks for archive paths and source integrity (no network access)."""
import importlib.util,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('archive_download',ROOT/'scripts/download.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ArchiveSafety(unittest.TestCase):
 def test_parent_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):module.contained(pathlib.Path(d),'../escape.php')
 def test_absolute_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):module.contained(pathlib.Path(d),str(pathlib.Path(d).parent/'escape.php'))
 def test_checksum_mismatch_preserves_existing_file(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'archive.zip';path.write_bytes(b'existing')
   with self.assertRaises(ValueError):module.download('https://example.invalid/no-network',path,'0'*64)
   self.assertEqual(path.read_bytes(),b'existing')
if __name__=='__main__':unittest.main()
