import argparse,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1];php=root/'.runtime/php/php.exe';web=root/'.runtime/mediawiki-1.43.11';logfile=root/'.data/refresh-links.log'
parser=argparse.ArgumentParser();parser.add_argument('--start',type=int,default=1);args=parser.parse_args()
with logfile.open('a',encoding='utf-8') as log:
 p=subprocess.run([str(php),'-c',str(root/'.runtime/php/php.ini'),str(web/'maintenance/run.php'),'refreshLinks',str(args.start)],stdout=log,stderr=subprocess.STDOUT,cwd=web)
print('Link rebuild exit:',p.returncode);print(logfile.read_text(encoding='utf-8',errors='replace')[-2000:]);raise SystemExit(p.returncode)
