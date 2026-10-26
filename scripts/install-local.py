import pathlib,secrets,subprocess
root=pathlib.Path(__file__).resolve().parents[1];php=root/'.runtime/php/php.exe';ini=root/'.runtime/php/php.ini';mw=root/'.runtime/mediawiki-1.43.11';data=root/'.data';(data/'db').mkdir(exist_ok=True)
password=data/'admin-password.txt'
if not password.exists():password.write_text(secrets.token_urlsafe(32))
args=[str(php),'-c',str(ini),str(mw/'maintenance/run.php'),'install','--dbtype','sqlite','--dbpath',str(data/'db'),'--dbname','acpedia','--server','http://127.0.0.1:8770','--scriptpath','','--lang','en','--passfile',str(password),'--skins','Vector','AC Community Wiki','RestorationAdmin']
if not (mw/'LocalSettings.php').exists():subprocess.run(args,check=True,cwd=mw)
print('Local wiki installation ready. Administrator credentials remain in ignored local storage.')
