"""Project-admin-only private SMTP configuration; never returns saved secrets."""
import json,os,re,smtplib,ssl,tempfile,time
from pathlib import Path

def path():return Path(os.environ.get('GREENMINE_DATA_DIR',str(Path(__file__).parent.parent/'.local')))/'mail.json'
def config():
 p=path()
 if p.exists():return json.loads(p.read_text())
 if os.environ.get('SMTP_REQUIRE_SETUP')=='1':return {}
 return {k:os.environ.get(k,'') for k in ['SMTP_HOST','SMTP_PORT','SMTP_TLS','SMTP_USER','SMTP_PASSWORD','SMTP_FROM']}
def allowed(user):return bool(os.environ.get('GREENMINE_ADMIN_EMAIL')) and user['email']==os.environ['GREENMINE_ADMIN_EMAIL'].strip().lower()
def run(db,user,data,api):
 Error=api['error']
 if not allowed(user):raise Error('FORBIDDEN',403)
 saved=config()
 if data.get('save'):
  api['rate'](db,'mail-settings:'+str(user['id']),5)
  host=data.get('host');username=data.get('username');password=data.get('password');mode=data.get('tls','starttls')
  try:port=int(data.get('port',587))
  except (ValueError,TypeError):raise Error('MAIL_SETTINGS_INVALID')
  if not isinstance(host,str) or not re.fullmatch(r'[A-Za-z0-9.-]{1,253}',host) or port not in (465,587) or mode not in ('ssl','starttls'):raise Error('MAIL_SETTINGS_INVALID')
  if not isinstance(username,str) or not re.fullmatch(r'[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+',username) or len(username)>254:raise Error('MAIL_SETTINGS_INVALID')
  if not isinstance(password,str) or not 1<=len(password)<=256:raise Error('MAIL_SETTINGS_INVALID')
  try:
   if mode=='ssl':client=smtplib.SMTP_SSL(host,port,timeout=8,context=ssl.create_default_context())
   else:client=smtplib.SMTP(host,port,timeout=8)
   with client as smtp:
    smtp.ehlo()
    if mode=='starttls':smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
    smtp.login(username,password)
  except Exception:raise Error('MAIL_AUTH_FAILED',422)
  saved={'SMTP_HOST':host,'SMTP_PORT':str(port),'SMTP_TLS':mode,'SMTP_USER':username,'SMTP_PASSWORD':password,'SMTP_FROM':username,'verified_at':int(time.time())}
  target=path();target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='mail-',dir=target.parent)
  try:
   with os.fdopen(fd,'w') as f:json.dump(saved,f);f.flush();os.fsync(f.fileno())
   os.replace(name,target)
  finally:
   if os.path.exists(name):os.unlink(name)
 return {'configured':all(saved.get(k) for k in ['SMTP_HOST','SMTP_USER','SMTP_PASSWORD']),'host':saved.get('SMTP_HOST') or os.environ.get('SMTP_HOST','smtp.gmail.com'),'port':saved.get('SMTP_PORT','587'),'tls':saved.get('SMTP_TLS','starttls'),'username':saved.get('SMTP_USER') or os.environ.get('SMTP_USER',''),'verified_at':saved.get('verified_at')}
