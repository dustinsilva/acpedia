import pathlib
r=pathlib.Path(__file__).resolve().parents[1]/'.runtime/php';ini='[PHP]\nextension_dir="'+str(r/'ext').replace('\\','/')+'"\nmemory_limit=1024M\nmax_execution_time=0\ndate.timezone=UTC\nlog_errors=On\ndisplay_errors=Off\n'
for e in ['openssl','mbstring','intl','fileinfo','sqlite3','pdo_sqlite','curl','gd']:
 ini+='extension='+e+'\n'
ini+='\nzend_extension=opcache\nopcache.enable_cli=1\nopcache.memory_consumption=256\nopcache.max_accelerated_files=40000\nopcache.validate_timestamps=1\nopcache.revalidate_freq=1\n'
(r/'php.ini').write_text(ini)
