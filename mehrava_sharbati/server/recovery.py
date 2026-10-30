"""Email password recovery: expiring, single-use, attempt-limited codes."""
import hashlib,hmac,json,os,secrets,smtplib,ssl,tempfile,time
from pathlib import Path
from email.message import EmailMessage

def available():return all(os.environ.get(k) for k in ['SMTP_HOST','SMTP_USER','SMTP_PASSWORD'])
def key():
 root=Path(os.environ.get('GREENMINE_DATA_DIR',str(Path(__file__).parent.parent/'.local')));root.mkdir(mode=0o700,parents=True,exist_ok=True);p=root/'recovery.key'
 if not p.exists():
  fd,name=tempfile.mkstemp(dir=root,prefix='key-')
  try:
   with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32));f.flush();os.fsync(f.fileno())
   try:os.link(name,p)
   except FileExistsError:pass
  finally:os.unlink(name)
 value=p.read_bytes()
 if len(value)!=32:raise ValueError('RECOVERY_UNAVAILABLE')
 return value

def code_hash(challenge,code):return hmac.new(key(),(challenge+':'+code).encode(),hashlib.sha256).hexdigest()
def send_code(email,code):
 message=EmailMessage();message['Subject']='GreenMine password recovery';message['From']=os.environ.get('SMTP_FROM') or os.environ['SMTP_USER'];message['To']=email
 message.set_content(f'کد بازیابی رمز گرین‌ماین: {code}\n\nاین کد تا ۱۰ دقیقه معتبر است. اگر شما درخواست نداده‌اید، آن را نادیده بگیرید.\n\nGreenMine recovery code: {code}\nValid for 10 minutes. Your password has not changed.')
 host=os.environ['SMTP_HOST'];port=int(os.environ.get('SMTP_PORT','587'));mode=os.environ.get('SMTP_TLS','starttls')
 if mode not in ('ssl','starttls','none'):raise ValueError('TLS_REQUIRED')
 if mode=='none' and host not in ('localhost','127.0.0.1','::1'):raise ValueError('TLS_REQUIRED')
 if mode=='ssl':client=smtplib.SMTP_SSL(host,port,timeout=8,context=ssl.create_default_context())
 else:client=smtplib.SMTP(host,port,timeout=8)
 with client as smtp:
  smtp.ehlo()
  if mode=='starttls':smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
  smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(message)

def run(db,op,data,client,api):
 ServiceError=api['error']
 db.execute('''CREATE TABLE IF NOT EXISTS recovery_challenges(id TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),code_hash TEXT NOT NULL,expires_at INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0)''')
 now=int(time.time())
 if op=='forgot':
  email=str(data.get('email','')).strip().lower()
  import re
  if not re.fullmatch(r'[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+',email) or len(email)>254:raise ServiceError('EMAIL_INVALID')
  if not available():raise ServiceError('RECOVERY_UNAVAILABLE',503)
  api['rate'](db,'recovery-ip:'+api['digest'](client),5);api['rate'](db,'recovery-account:'+api['digest'](email),3)
  row=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone();challenge=secrets.token_hex(24);code=f'{secrets.randbelow(1000000):06d}'
  with db:
   db.execute('DELETE FROM recovery_challenges WHERE expires_at<=?',(now,))
   if row:
    db.execute('DELETE FROM recovery_challenges WHERE user_id=?',(row['id'],))
    db.execute('INSERT INTO recovery_challenges VALUES (?,?,?,?,0)',(challenge,row['id'],code_hash(challenge,code),now+600))
  if row:
   try:send_code(email,code)
   except Exception:
    with db:db.execute('DELETE FROM recovery_challenges WHERE id=?',(challenge,))
    raise ServiceError('RECOVERY_UNAVAILABLE',503)
  return {'challenge_id':challenge,'expires_in':600,'message':'If the account exists, a recovery code has been sent.'}
 api['rate'](db,'recovery-verify-ip:'+api['digest'](client),30)
 password=data.get('password');challenge=data.get('challenge_id');code=data.get('code')
 if not isinstance(password,str) or not 8<=len(password)<=128:raise ServiceError('PASSWORD_INVALID')
 if not isinstance(challenge,str) or len(challenge)!=48 or not isinstance(code,str):raise ServiceError('RECOVERY_INVALID')
 code=code.strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789'))
 if len(code)!=6 or not code.isascii() or not code.isdigit():raise ServiceError('RECOVERY_INVALID')
 failure=False
 with db:
  db.execute('BEGIN IMMEDIATE')
  row=db.execute('SELECT * FROM recovery_challenges WHERE id=?',(challenge,)).fetchone()
  if row is None or row['expires_at']<=now or row['attempts']>=5:failure=True
  elif not hmac.compare_digest(row['code_hash'],code_hash(challenge,code)):
   db.execute('UPDATE recovery_challenges SET attempts=attempts+1 WHERE id=?',(challenge,));failure=True
  else:
   salt=secrets.token_hex(16);hashed=api['password_hash'](password,salt)
   db.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,row['user_id']))
   db.execute('DELETE FROM sessions WHERE user_id=?',(row['user_id'],))
   db.execute('DELETE FROM recovery_challenges WHERE user_id=?',(row['user_id'],))
   email=db.execute('SELECT email FROM users WHERE id=?',(row['user_id'],)).fetchone()['email'];db.execute('DELETE FROM attempts WHERE bucket=?',('account:'+api['digest'](email),))
 if failure:raise ServiceError('RECOVERY_INVALID')
 return {'ok':True}
