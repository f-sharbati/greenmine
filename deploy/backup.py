"""Run inside the app container: consistent backup and restore-read validation."""
import os, sqlite3
from pathlib import Path
from datetime import datetime, timezone
root=Path(os.environ.get('GREENMINE_DATA_DIR','/data'));folder=root/'backups';folder.mkdir(mode=0o700,exist_ok=True)
name='accounts-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite3';target=folder/name
with sqlite3.connect(root/'accounts.sqlite3') as source, sqlite3.connect(target) as dest:source.backup(dest)
os.chmod(target,0o600)
with sqlite3.connect(target) as backup,sqlite3.connect(':memory:') as restored:
 backup.backup(restored)
 assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 print('verified_backup',name,'users',restored.execute('SELECT count(*) FROM users').fetchone()[0])
