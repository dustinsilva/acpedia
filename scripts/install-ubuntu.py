#!/usr/bin/env python3
"""Restore ACPedia on an existing Ubuntu Apache/MySQL host. Rerunnable; no DB drops."""
import argparse
import getpass
import grp
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

from download import ROOT, download, drive, unpack


def php_string(value):
    return "'"+str(value).replace('\\','\\\\').replace("'","\\'")+"'"


def run(command, **kwargs):
    # Passwords are passed in private files, never as command arguments or output.
    subprocess.run(list(map(str,command)), check=True, **kwargs)


def apache_directory(public):
    path=str(public.resolve())
    if any(c in path for c in ('"','\n','\r','\\')):
        raise ValueError('Unsupported Apache directory path')
    return ('# Managed by ACPedia install.sh; scoped to this checkout only.\n'
            '<Directory "'+path+'">\n'
            '    Options -Indexes +FollowSymLinks\n'
            '    AllowOverride All\n'
            '    Require all granted\n'
            '</Directory>\n')


def setup_apache(public):
    directory=Path('/etc/apache2/conf-available')
    if not directory.is_dir() or not shutil.which('a2enconf'):
        raise RuntimeError('Expected Ubuntu Apache configuration under /etc/apache2')
    conf=directory/'acpedia-restoration.conf'
    before=conf.read_bytes() if conf.exists() else None
    if before and not before.startswith(b'# Managed by ACPedia install.sh;'):
        raise RuntimeError('Existing acpedia-restoration.conf is not owned by this installer')
    enabled=Path('/etc/apache2/conf-enabled/acpedia-restoration.conf')
    was_enabled=enabled.exists()
    conf.write_text(apache_directory(public))
    try:
        run(['a2enmod','rewrite'])
        run(['a2enconf','acpedia-restoration'])
        run(['apache2ctl','configtest'])
    except BaseException:
        if before is None:conf.unlink(missing_ok=True)
        else:conf.write_bytes(before)
        if not was_enabled and enabled.is_symlink():enabled.unlink()
        raise
    run(['systemctl','reload','apache2'])


def ensure_webroot(runtime, public, state):
    if (public/'index.php').exists() and not state.exists():
        raise RuntimeError('public/index.php already exists. Refusing to overwrite an unrecognized site.')
    public.mkdir(exist_ok=True)
    # A failed copy is resumable, but is not marked ready until copied in full.
    pending=state.with_suffix('.copying')
    if not state.exists():
        pending.write_text('Pinned MediaWiki installation in progress\n')
        protection=(public/'.htaccess').read_bytes() if (public/'.htaccess').exists() else None
        shutil.copytree(runtime,public,dirs_exist_ok=True)
        if protection is not None:(public/'.htaccess').write_bytes(protection)
        state.write_text('MediaWiki files installed\n')
        pending.unlink(missing_ok=True)


def prepare_media(webmedia, media):
    """Replace only the distribution's upload skeleton, preserving files on failure."""
    media.mkdir(exist_ok=True,mode=0o2770)
    if webmedia.is_symlink():
        if webmedia.resolve()!=media.resolve():
            raise RuntimeError('Unexpected public/images symlink')
        return
    if webmedia.exists():
        if not webmedia.is_dir():
            raise RuntimeError('Existing public/images is not a directory')
        entries=list(webmedia.iterdir())
        if any(p.name not in ('.htaccess','README') or not p.is_file() or p.is_symlink() for p in entries):
            raise RuntimeError('Existing public/images is not an empty distribution directory; refusing to replace it')
        # Copy everything successfully before removing any originals. A failed run
        # can repeat this step without losing protection files or resetting MySQL.
        for path in entries:shutil.copy2(path,media/path.name)
        for path in entries:path.unlink()
        webmedia.rmdir()
    webmedia.symlink_to(media,target_is_directory=True)


def private_file(path, content):
    # Open with restrictive mode from creation, not after writing the password.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(content)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',default='https://acpedia.celestro.com')
    parser.add_argument('--dbhost',default='localhost')
    parser.add_argument('--dbname',default='acpedia')
    parser.add_argument('--dbuser',default='acpedia')
    parser.add_argument('--full-history',action='store_true',help='Also import every historical revision; slower')
    parser.add_argument('--skip-apache',action='store_true',help='Manage Apache directory settings yourself')
    parser.add_argument('--skip-content',action='store_true',help='Install an empty wiki without downloading content/media')
    args=parser.parse_args()
    if not sys.platform.startswith('linux') or os.geteuid()!=0:
        raise SystemExit('Run sudo ./install.sh on your Ubuntu server.')
    parsed=urlsplit(args.server)
    if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.path not in ('','/') or parsed.query or parsed.fragment or parsed.username:
        raise SystemExit('--server must be an HTTP(S) origin, for example https://acpedia.celestro.com')
    args.server=args.server.rstrip('/')
    os.umask(0o027)
    data=ROOT/'.data';data.mkdir(exist_ok=True,mode=0o750)
    downloads=data/'downloads';downloads.mkdir(exist_ok=True,mode=0o700)
    public=ROOT/'public'
    lock=json.loads((ROOT/'sources.lock.json').read_text())
    ready=data/'ubuntu-webroot.ok'
    if public.joinpath('index.php').exists() and not ready.exists() and not ready.with_suffix('.copying').exists():
        raise SystemExit('public/index.php belongs to another installation; nothing was overwritten.')
    version=lock['mediawiki']['version']
    runtime=ROOT/'.runtime'/('mediawiki-'+version)
    if not ready.exists():
        archive=download(lock['mediawiki']['url'],ROOT/'.runtime/mediawiki.tar.gz',lock['mediawiki']['sha256'])
        if not (runtime/'maintenance/run.php').exists():unpack(archive,ROOT/'.runtime')
        # Allow a partial copy made by our own previous interrupted attempt.
        if ready.with_suffix('.copying').exists() and (public/'index.php').exists():
            protection=(public/'.htaccess').read_bytes()
            shutil.copytree(runtime,public,dirs_exist_ok=True)
            (public/'.htaccess').write_bytes(protection)
            ready.write_text('MediaWiki files installed\n');ready.with_suffix('.copying').unlink()
        else:ensure_webroot(runtime,public,ready)
    for name,extension in lock['extensions'].items():
        target=public/'extensions'/name
        if not target.exists():run(['git','clone','--quiet',extension['url'],target])
        run(['git','-C',target,'checkout','--quiet','--detach',extension['commit']])
    # The compatibility extension remains part of this source checkout.
    shutil.copytree(ROOT/'extensions/ACPediaArchive',public/'extensions/ACPediaArchive',dirs_exist_ok=True)
    assets=public/'restoration-assets';assets.mkdir(exist_ok=True)
    shutil.copy2(public/'wiki.png',assets/'wiki.png')
    settings=data/'LocalSettings.php'
    if not settings.exists():
        print('\nUse an EMPTY MySQL database and a user with privileges on that database. The installer creates MediaWiki tables.')
        args.dbhost=input('MySQL host ['+args.dbhost+']: ').strip() or args.dbhost
        args.dbname=input('Database name ['+args.dbname+']: ').strip() or args.dbname
        args.dbuser=input('Database user ['+args.dbuser+']: ').strip() or args.dbuser
        password=getpass.getpass('MySQL password (not displayed): ')
        password_file=data/'mysql-install-password.tmp'
        admin_password=data/'admin-password.txt'
        if not admin_password.exists():private_file(admin_password,secrets.token_urlsafe(32))
        private_file(password_file,password)
        try:
            run(['php',public/'maintenance/run.php','install','--dbtype','mysql','--dbserver',args.dbhost,
                 '--dbname',args.dbname,'--dbuser',args.dbuser,'--dbpassfile',password_file,
                 '--confpath',data,'--server',args.server,'--scriptpath','','--lang','en',
                 '--skins','Vector','--passfile',admin_password,'AC Community Wiki','RestorationAdmin'],cwd=public)
        finally:password_file.unlink(missing_ok=True)
        settings.chmod(0o640)
    include='require_once '+php_string(ROOT/'config/RestorationSettings.php')+';'
    if include not in settings.read_text():
        with settings.open('a') as stream:stream.write('\n'+include+'\n')
    front=public/'LocalSettings.php'
    if front.is_symlink():
        if front.resolve()!=settings.resolve():raise RuntimeError('Unexpected LocalSettings.php symlink')
    elif front.exists():raise RuntimeError('Unexpected public/LocalSettings.php; not overwriting it')
    else:front.symlink_to(settings)
    media=data/'images'
    prepare_media(public/'images',media)
    # Media must never execute scripts even when symlinked outside public/.
    (media/'.htaccess').write_text('Options -Indexes\n<FilesMatch "(?i)\\.(php[0-9]*|phtml|phar|cgi|pl|py|sh)$">\nRequire all denied\n</FilesMatch>\n')
    gid=grp.getgrnam('www-data').gr_gid
    for path in (ROOT, data):
        if not os.stat(path).st_mode&0o005:
            print('Ensure Apache can traverse the checkout and its parent directories:',ROOT)
    os.chown(data,-1,gid);data.chmod(0o750)
    os.chown(settings,-1,gid);settings.chmod(0o640)
    for folder,dirs,files in os.walk(media):
        os.chown(folder,-1,gid);os.chmod(folder,0o2770)
        for name in files:os.chown(Path(folder)/name,-1,gid);os.chmod(Path(folder)/name,0o660)
    # Distribution directories are read-only to Apache; writable storage is private.
    for folder,dirs,files in os.walk(public,followlinks=False):
        os.chmod(folder,0o755)
        for name in files:
            path=Path(folder)/name
            if not path.is_symlink():path.chmod(0o644)
    if not args.skip_apache:setup_apache(public)
    env=dict(os.environ,ACPEDIA_SERVER=args.server,ACPEDIA_WEBROOT=str(public),ACPEDIA_PHP=shutil.which('php'))
    def maintenance(*options):run(['php',public/'maintenance/run.php',*options],cwd=public,env=env)
    def script(name):run([sys.executable,ROOT/'scripts'/name],cwd=ROOT,env=env)
    if not args.skip_content:
        for key in ('content','images','image_supplement'):
            item=lock[key];drive(item['file_id'],downloads/item['name'],item['sha256'])
        script('prepare-content.py')
        if not (data/'ubuntu-pages-imported.ok').exists():
            maintenance('importDump','--no-updates','--username-prefix','acpedia-archive',data/'latest.xml')
            (data/'ubuntu-pages-imported.ok').touch()
        if not (data/'image-manifest.json').exists():script('prepare-images.py')
        run(['php',ROOT/'scripts/register-images.php','--source',data/'image-source'],cwd=ROOT,env=env)
        if (data/'image-supplement.xml').exists():
            maintenance('importDump','--no-updates','--username-prefix','acpedia-archive',data/'image-supplement.xml')
        if args.full_history and not (data/'ubuntu-history-imported.ok').exists():
            script('import-history.py');(data/'ubuntu-history-imported.ok').touch()
        script('restore-current.py')
        if not (data/'ubuntu-indexes-complete.ok').exists():
            maintenance('rebuildall');maintenance('initSiteStats','--update')
            (data/'ubuntu-indexes-complete.ok').touch()
        # Files created by maintenance jobs must also be readable/writable to Apache.
        for folder,dirs,files in os.walk(media):
            os.chown(folder,-1,gid);os.chmod(folder,0o2770)
            for name in files:os.chown(Path(folder)/name,-1,gid);os.chmod(Path(folder)/name,0o660)
    print('\nReady:',args.server+'/wiki/Home')
    print('Apache DocumentRoot must be:',public)
    print('Database credentials:',settings)
    print('Administrator: RestorationAdmin; password is in',data/'admin-password.txt')
    print('First restoration downloads several GB and imports/indexes the archive. A failed run can be rerun.')


if __name__=='__main__':
    try:main()
    except (RuntimeError,ValueError,subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
