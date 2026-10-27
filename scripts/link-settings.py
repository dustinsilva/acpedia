import pathlib
root=pathlib.Path(__file__).resolve().parents[1];settings=root/'.runtime/mediawiki-1.43.11/LocalSettings.php'
s=settings.read_text(encoding='utf-8-sig');line='require_once '+repr(str(root/'config/RestorationSettings.php').replace('\\','/'))+';'
if line not in s:settings.write_text(s+'\n'+line+'\n',encoding='utf-8')
