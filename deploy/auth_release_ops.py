"""Operator-only rollout for the supplied ZIP. Does not change application source."""
import argparse,json,os,shutil,sqlite3,subprocess,sys,tarfile,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
os.umask(0o077)
IMAGE='greenmine:auth-20261031-6f216e03'
IMAGE_ID='sha256:3fb5583ead0501cae621b4e1dc8f026e1363b4373d7f52139a9fc4a704aa11d1'
VOLUME='greenmine_accounts'
ADMIN='fazi.sharbati@gmail.com'
class Gate(Exception):pass
def command(*args):return subprocess.check_output(args,text=True,stderr=subprocess.PIPE).strip()
def inspect(name):
 try:return json.loads(command('docker','inspect',name))[0]
 except subprocess.CalledProcessError:return None
def image_check():
 r=inspect(IMAGE)
 if not r or r['Id']!=IMAGE_ID:raise Gate('CANDIDATE_IMAGE_MISMATCH')
def volume():return Path(json.loads(command('docker','volume','inspect',VOLUME))[0]['Mountpoint'])
def config():
 p=volume()/'mail.json'
 if not p.exists():raise Gate('FRESH_SMTP_SETUP_REQUIRED')
 if p.stat().st_mode&0o077 or p.stat().st_uid!=1000:raise Gate('PRIVATE_MAIL_PERMISSIONS_INVALID')
 c=json.loads(p.read_text())
 if not all(c.get(k) for k in ['SMTP_HOST','SMTP_USER','SMTP_PASSWORD','verified_at']):raise Gate('FRESH_SMTP_SETUP_REQUIRED')
 if c['SMTP_HOST']!='smtp.gmail.com' or c['SMTP_USER']!='mehrava.sharbati@gmail.com' or str(c.get('SMTP_PORT'))!='587' or c.get('SMTP_TLS')!='starttls':raise Gate('UNEXPECTED_MAIL_CONFIGURATION')
 legacy=envfile(Path('/opt/greenmine/config/mail.env')).get('SMTP_PASSWORD','')
 if legacy and ''.join(c['SMTP_PASSWORD'].split())==''.join(legacy.split()):raise Gate('EXPOSED_LEGACY_PASSWORD_REFUSED')
 return c
def envfile(p):
 if not p.exists():return {}
 return dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
def jsonfile(path,value):path.write_text(json.dumps(value,indent=2)+'\n');os.chmod(path,0o600)
def dbcopy(target):
 with sqlite3.connect(volume()/'accounts.sqlite3') as source,sqlite3.connect(target) as dest:
  source.backup(dest);assert dest.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 os.chmod(target,0o600)
def backup():
 folder=Path('/opt/greenmine/backups')/('pre-auth-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir(mode=0o700)
 dbcopy(folder/'accounts.sqlite3')
 with tarfile.open(folder/'data-private-files.tar.gz','w:gz') as archive:
  for p in volume().iterdir():
   if p.name not in ['accounts.sqlite3','accounts.sqlite3-wal','accounts.sqlite3-shm','backups']:archive.add(p,arcname=p.name)
 if Path('/opt/greenmine/config').exists():shutil.copytree('/opt/greenmine/config',folder/'config')
 shutil.copy2('/opt/greenmine/edge/Caddyfile',folder/'Caddyfile')
 jsonfile(folder/'container-private.json',inspect('greenmine-app'))
 return folder
def same_business_data(baseline):
 with sqlite3.connect(baseline) as before,sqlite3.connect(volume()/'accounts.sqlite3') as after:
  for table in ['users','sessions','workspaces','imports','production_readings','import_sources']:
   columns=[r[1] for r in before.execute('PRAGMA table_info('+table+')')]
   query='SELECT '+','.join(columns)+' FROM '+table+' ORDER BY '+','.join(str(i+1) for i in range(len(columns)))
   if before.execute(query).fetchall()!=after.execute(query).fetchall():return False
 return True
def smtp_auth():
 config();image_check()
 code="""import json,smtplib,ssl\nfrom mail_settings import config\nc=config()\nwith smtplib.SMTP(c['SMTP_HOST'],int(c['SMTP_PORT']),timeout=12) as s:\n s.ehlo();s.starttls(context=ssl.create_default_context());s.ehlo();s.login(c['SMTP_USER'],c['SMTP_PASSWORD'])\nprint('SMTP_AUTHENTICATION_PASSED_NO_EMAIL_SENT')\n"""
 result=subprocess.run(['docker','run','--rm','-i','--user','1000:1000','-e','SMTP_REQUIRE_SETUP=1','-e','GREENMINE_ADMIN_EMAIL='+ADMIN,'-v',VOLUME+':/data:ro','--entrypoint','/opt/venv/bin/python',IMAGE,'-'],input=code,text=True,capture_output=True)
 if result.returncode:raise Gate('SMTP_AUTHENTICATION_FAILED')
 return config()['verified_at']
def bootstrap(path):
 image_check()
 if not path.exists() or path.stat().st_mode&0o077:raise Gate('PRIVATE_ENV_FILE_REQUIRED_MODE_600')
 e=envfile(path)
 if not e.get('SMTP_PASSWORD','').strip():raise Gate('FRESH_SMTP_PASSWORD_EMPTY')
 old=envfile(Path('/opt/greenmine/config/mail.env')).get('SMTP_PASSWORD','')
 if old and ''.join(old.split())==''.join(e['SMTP_PASSWORD'].split()):raise Gate('EXPOSED_LEGACY_PASSWORD_REFUSED')
 required={'SMTP_HOST':'smtp.gmail.com','SMTP_PORT':'587','SMTP_TLS':'starttls','SMTP_USER':'mehrava.sharbati@gmail.com','SMTP_FROM':'mehrava.sharbati@gmail.com'}
 if any(e.get(k)!=v for k,v in required.items()):raise Gate('UNEXPECTED_MAIL_CONFIGURATION')
 folder=backup()
 result=subprocess.run(['docker','run','--rm','--user','1000:1000','--env-file',str(path),'-e','SMTP_REQUIRE_SETUP=1','-e','GREENMINE_ADMIN_EMAIL='+ADMIN,'-v',VOLUME+':/data','--entrypoint','/opt/venv/bin/python',IMAGE,'server/configure_mail.py','--from-env'],capture_output=True,text=True)
 if result.returncode:raise Gate('SMTP_BOOTSTRAP_FAILED_PREVIOUS_RELEASE_RETAINED')
 stamp=smtp_auth();jsonfile(folder/'smtp-bootstrap-result.json',{'smtp_authentication':'passed','verified_at':stamp,'emails_sent':0})
 print(json.dumps({'smtp_authentication':'passed','verified_at':stamp,'backup':str(folder),'production_switched':False,'emails_sent':0}))
def rollback(folder):
 state=json.loads((folder/'promotion-state.json').read_text());old=state['previous_container']
 if not old.startswith('greenmine-app-pre-auth-') or not inspect(old):raise Gate('ROLLBACK_CONTAINER_MISSING')
 if not same_business_data(folder/'accounts-frozen.sqlite3'):raise Gate('ROLLBACK_REFUSED_DATA_OR_PASSWORDS_CHANGED_FORWARD_FIX_REQUIRED')
 current=inspect('greenmine-app')
 if current:
  command('docker','stop','greenmine-app')
  if not same_business_data(folder/'accounts-frozen.sqlite3'):
   command('docker','start','greenmine-app');raise Gate('ROLLBACK_REFUSED_CONCURRENT_WRITES_FORWARD_FIX_REQUIRED')
  command('docker','rename','greenmine-app','greenmine-app-auth-failed-'+str(int(time.time())))
 command('docker','rename',old,'greenmine-app');command('docker','start','greenmine-app')
 print('PREVIOUS_CONTAINER_RESTORED_DATABASE_NOT_REPLACED')
def promote():
 image_check();config();smtp_auth();current=inspect('greenmine-app')
 if not current or current['Config']['Image']!='greenmine:8ff0556':raise Gate('PRODUCTION_BASELINE_CHANGED_REINSPECT_FIRST')
 folder=backup();env=dict(x.split('=',1) for x in current['Config']['Env'])
 env.update(APP_ORIGIN='https://greenmineapp.ir',GREENMINE_DATA_DIR='/data',GREENMINE_PYTHON_ROOT='/opt/greenmine/python',PYTHON_EXECUTABLE='/opt/venv/bin/python',GREENMINE_ADMIN_EMAIL=ADMIN,SMTP_REQUIRE_SETUP='1',SMTP_PASSWORD='')
 if any('\n' in v for v in env.values()):raise Gate('MULTILINE_PRIVATE_ENV_REQUIRES_MANUAL_PRESERVATION')
 private=folder/'runtime-private.env';private.write_text(''.join(k+'='+v+'\n' for k,v in env.items()));os.chmod(private,0o600)
 old='greenmine-app-pre-auth-'+str(int(time.time()));jsonfile(folder/'promotion-state.json',{'previous_container':old,'candidate_image_id':IMAGE_ID})
 command('docker','stop','greenmine-app')
 try:dbcopy(folder/'accounts-frozen.sqlite3');command('docker','rename','greenmine-app',old)
 except Exception:command('docker','start','greenmine-app');raise
 try:
  command('docker','run','-d','--name','greenmine-app','--restart','unless-stopped','--cap-drop','ALL','--security-opt','no-new-privileges:true','--log-opt','max-size=10m','--log-opt','max-file=3','--env-file',str(private),'-v',VOLUME+':/data','-p','127.0.0.1:3001:3000',IMAGE)
  ready=False
  for _ in range(30):
   try:
    with urllib.request.urlopen('http://127.0.0.1:3001/',timeout=2) as r:ready=r.status==200
   except Exception:pass
   if ready:break
   time.sleep(1)
  if not ready:raise Gate('NEW_SERVICE_NOT_READY')
  command('python3','/opt/greenmine/releases/auth-20261031-6f216e03/deploy-smoke.py','--base','http://127.0.0.1:3001','--origin','https://greenmineapp.ir','--require-mail')
 except Exception:
  rollback(folder);raise Gate('PROMOTION_FAILED_PREVIOUS_CONTAINER_RESTORED')
 print(json.dumps({'promotion':'running_pending_public_otp_acceptance','backup':str(folder),'rollback_container':old,'image_id':IMAGE_ID}))
def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--inspect',action='store_true');g.add_argument('--bootstrap-mail',type=Path);g.add_argument('--promote',action='store_true');g.add_argument('--rollback',type=Path,metavar='BACKUP_DIRECTORY');a=p.parse_args()
 if a.bootstrap_mail:bootstrap(a.bootstrap_mail)
 elif a.promote:promote()
 elif a.rollback:rollback(a.rollback)
 else:
  image_check();current=inspect('greenmine-app')
  try:c=config();mail=True;stamp=c['verified_at']
  except Gate:mail=False;stamp=None
  print(json.dumps({'production_image':current['Config']['Image'] if current else None,'candidate_image_id':IMAGE_ID,'fresh_mail_configured':mail,'mail_verified_at':stamp,'inspection_only':True,'next_gate':'SMTP bootstrap, then real designated-mailbox activation/login/recovery acceptance'}))
if __name__=='__main__':
 try:main()
 except Gate as exc:print(str(exc),file=sys.stderr);sys.exit(2)
 except Exception:print('OPERATION_FAILED_PRIVATE_STATE_PRESERVED_INSPECT_LOCALLY',file=sys.stderr);sys.exit(1)
