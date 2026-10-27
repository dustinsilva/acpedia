"""Ubuntu deployment contracts, without changing the host or contacting a database."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('ubuntu_installer',ROOT/'scripts/install-ubuntu.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class UbuntuInstaller(unittest.TestCase):
    def test_unknown_webroot_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);public=base/'public';public.mkdir();(public/'index.php').write_text('existing site')
            with self.assertRaises(RuntimeError):installer.ensure_webroot(base/'runtime',public,base/'ready')
            self.assertEqual((public/'index.php').read_text(),'existing site')

    def test_tracked_apache_protection_survives_install(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);runtime=base/'runtime';runtime.mkdir();(runtime/'index.php').write_text('MediaWiki')
            (runtime/'.htaccess').write_text('upstream defaults')
            public=base/'public';public.mkdir();(public/'.htaccess').write_text('local protection')
            installer.ensure_webroot(runtime,public,base/'ready')
            self.assertEqual((public/'.htaccess').read_text(),'local protection')
            self.assertTrue((base/'ready').exists())
            self.assertFalse((base/'ready.copying').exists())
            installer.ensure_webroot(runtime,public,base/'ready')

    def test_upload_skeleton_files_are_preserved_then_linked(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);web=base/'images';web.mkdir();media=base/'private-images'
            (web/'README').write_text('upstream readme')
            (web/'.htaccess').write_text('upstream protection')
            installer.prepare_media(web,media)
            self.assertTrue(web.is_symlink())
            self.assertEqual(web.resolve(),media.resolve())
            self.assertEqual((media/'README').read_text(),'upstream readme')
            self.assertEqual((media/'.htaccess').read_text(),'upstream protection')
            installer.prepare_media(web,media)
            self.assertTrue(web.is_symlink())

    def test_real_uploads_are_not_removed(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);web=base/'images';web.mkdir()
            (web/'README').write_text('keep')
            (web/'user-photo.png').write_bytes(b'uploaded image')
            with self.assertRaises(RuntimeError):installer.prepare_media(web,base/'private')
            self.assertFalse(web.is_symlink())
            self.assertEqual((web/'user-photo.png').read_bytes(),b'uploaded image')
            self.assertEqual((web/'README').read_text(),'keep')

    def test_failed_upload_copy_preserves_originals_for_retry(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);web=base/'images';web.mkdir()
            (web/'README').write_text('keep')
            with patch.object(installer.shutil,'copy2',side_effect=OSError('copy failed')):
                with self.assertRaises(OSError):installer.prepare_media(web,base/'private')
            self.assertEqual((web/'README').read_text(),'keep')
            installer.prepare_media(web,base/'private')
            self.assertTrue(web.is_symlink())

    def test_wrong_upload_symlink_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);other=base/'other';other.mkdir()
            web=base/'images';web.symlink_to(other,target_is_directory=True)
            with self.assertRaises(RuntimeError):installer.prepare_media(web,base/'private')
            self.assertEqual(web.resolve(),other.resolve())

    def test_private_credentials_are_private_from_creation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'password'
            installer.private_file(path,"secret'with$characters")
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertEqual(path.read_text(),"secret'with$characters")

    def test_php_literals_do_not_interpolate_dollars_or_quotes(self):
        self.assertEqual(installer.php_string("/home/a'b/$site"),"'/home/a\\'b/$site'")

    def test_apache_configuration_is_scoped_to_public_only(self):
        text=installer.apache_directory(Path('/srv/acpedia/public'))
        self.assertIn('<Directory "/srv/acpedia/public">',text)
        self.assertNotIn('VirtualHost',text)
        self.assertNotIn('SSLCertificate',text)
        with self.assertRaises(ValueError):installer.apache_directory(Path('/srv/evil"path'))

    def test_rerun_checks_existing_archive_without_network(self):
        from download import drive,sha
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'archive';path.write_bytes(b'known bytes')
            with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')):
                self.assertEqual(drive('unused',path,sha(path)),path)

    def test_public_rules_block_installers_and_credentials(self):
        rules=(ROOT/'public/.htaccess').read_text()
        for name in ('LocalSettings','maintenance','mw-config','vendor'):
            self.assertIn(name,rules)
        self.assertIn('index.php?title=$1',rules)

if __name__=='__main__':unittest.main()
