"""Persistent, session-authenticated single-plant workspaces. No legacy DB mutation."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
import bridge

SESSION_TTL = 14 * 86400
class ServiceError(Exception):
    def __init__(self, code, status=400): self.code, self.status = code, status

def connect():
    path = Path(os.environ.get('GREENMINE_DATA_DIR', str(Path(__file__).parent.parent / '.local')))
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path / 'accounts.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS workspaces(user_id INTEGER PRIMARY KEY REFERENCES users(id), plant TEXT NOT NULL, tariff REAL NOT NULL, readings TEXT NOT NULL, serial TEXT, updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), digest TEXT NOT NULL, filename TEXT NOT NULL, raw_csv TEXT NOT NULL, created_at INTEGER NOT NULL, UNIQUE(user_id,digest));
      CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at INTEGER NOT NULL);
    ''')
    return db

def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=64).hex()

def digest(value): return hashlib.sha256(value.encode()).hexdigest()

def rate_limit(db, key, maximum=10):
    now = int(time.time())
    with db:
        db.execute('DELETE FROM attempts WHERE reset_at < ?', (now,))
        db.execute('INSERT INTO attempts VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (key, now+900))
        row = db.execute('SELECT count FROM attempts WHERE bucket=?', (key,)).fetchone()
    if row['count'] > maximum: raise ServiceError('RATE_LIMITED',429)

def user_for(db, token):
    if not isinstance(token,str) or len(token) != 64: raise ServiceError('UNAUTHENTICATED',401)
    row = db.execute('SELECT u.id,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?', (digest(token),int(time.time()))).fetchone()
    if row is None: raise ServiceError('UNAUTHENTICATED',401)
    return dict(row)

def main(request):
    if not isinstance(request,dict): raise ServiceError('INVALID_REQUEST')
    op=request.get('op'); data=request.get('data') or {}
    if not isinstance(data,dict): raise ServiceError('INVALID_REQUEST')
    with connect() as db:
        if op in ('register','login'):
            email=str(data.get('email','')).strip().lower(); password=data.get('password')
            if not re.fullmatch(r'[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+',email) or len(email)>254: raise ServiceError('EMAIL_INVALID')
            if not isinstance(password,str) or not 12<=len(password)<=128: raise ServiceError('PASSWORD_INVALID')
            rate_limit(db,'account:'+digest(email));rate_limit(db,'ip:'+digest(str(request.get('client','unknown'))),30)
            if op=='register':
                salt=secrets.token_hex(16)
                try:
                    with db:
                        cur=db.execute('INSERT INTO users(email,salt,password_hash,created_at) VALUES (?,?,?,?)',(email,salt,password_hash(password,salt),int(time.time())))
                        uid=cur.lastrowid
                        db.execute('INSERT INTO workspaces VALUES (?,?,?,?,?,?)',(uid,json.dumps(bridge.DEFAULT_PLANT),25000,'[]',None,int(time.time())))
                except sqlite3.IntegrityError: raise ServiceError('ACCOUNT_EXISTS',409)
            else:
                row=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                computed=password_hash(password,row['salt'] if row else '00'*16)
                if row is None or not hmac.compare_digest(computed,row['password_hash']): raise ServiceError('INVALID_LOGIN',401)
                uid=row['id']
            token=secrets.token_hex(32)
            with db:
                db.execute('DELETE FROM sessions WHERE expires_at<=?',(int(time.time()),))
                db.execute('INSERT INTO sessions VALUES (?,?,?)',(digest(token),uid,int(time.time())+SESSION_TTL))
            return {'user':{'id':uid,'email':email},'token':token}
        user=user_for(db,request.get('token'))
        if op=='me': return {'user':user}
        if op=='logout':
            with db: db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request['token']),))
            return {'ok':True}
        if op!='engine': raise ServiceError('ACTION_INVALID')
        uid=user['id']; workspace=db.execute('SELECT * FROM workspaces WHERE user_id=?',(uid,)).fetchone()
        action=data.get('action')
        if action=='import':
            raw=data.get('csv')
            if not isinstance(raw,str) or len(raw.encode())>1_500_000: raise ServiceError('FILE_TOO_LARGE',413)
            rows=bridge.clean_csv(raw)
            from datetime import date, datetime, timezone, timedelta
            today = datetime.now(timezone(timedelta(hours=3, minutes=30))).date()
            if any(date.fromisoformat(r['date'])>today for r in rows): raise ServiceError('CSV_FUTURE')
            # The UI manages one plant/inverter per account in this release.
            lines=raw.splitlines(); serial=None
            for i,line in enumerate(lines[:-1]):
                if 'Serial number' in line:
                    keys=line.split(';'); values=lines[i+1].split(';')
                    if 'Serial number' in keys and len(values)>keys.index('Serial number'): serial=values[keys.index('Serial number')].strip()
            with db:
                db.execute('BEGIN IMMEDIATE')
                workspace=db.execute('SELECT * FROM workspaces WHERE user_id=?',(uid,)).fetchone()
                if serial and workspace['serial'] and serial!=workspace['serial']: raise ServiceError('INVERTER_MISMATCH')
                existing={r['date']:r for r in json.loads(workspace['readings'])}
                for row in rows:
                    if row['date'] in existing and existing[row['date']]['kwh']!=row['kwh']: raise ServiceError('CSV_CONFLICT')
                    existing[row['date']]=row
                merged=sorted(existing.values(),key=lambda r:r['date'])
                db.execute('UPDATE workspaces SET readings=?,serial=COALESCE(serial,?),updated_at=? WHERE user_id=?',(json.dumps(merged),serial,int(time.time()),uid))
                db.execute('INSERT OR IGNORE INTO imports(user_id,digest,filename,raw_csv,created_at) VALUES (?,?,?,?,?)',(uid,digest(raw),str(data.get('filename','upload.csv'))[:255],raw,int(time.time())))
        if action in ('overview','import'):
            workspace=db.execute('SELECT * FROM workspaces WHERE user_id=?',(uid,)).fetchone()
            return dict(**bridge.summary(json.loads(workspace['readings'])),plant=json.loads(workspace['plant']),tariff=workspace['tariff'],source='Saved production readings',sample=False)
        if action=='settings':
            plant,tariff=bridge.validate_settings(data)
            with db: db.execute('UPDATE workspaces SET plant=?,tariff=?,updated_at=? WHERE user_id=?',(json.dumps(plant),tariff,int(time.time()),uid))
            return {'plant':plant,'tariff':tariff}
        if action=='forecast':
            rate_limit(db,'forecast:'+str(uid),15)
            return bridge.main({'action':'forecast','plant':json.loads(workspace['plant']),'tariff':workspace['tariff'],'readings':json.loads(workspace['readings'])})
        raise ServiceError('ACTION_INVALID')

if __name__=='__main__':
    import sys
    try: result=main(json.load(sys.stdin)); status=200
    except ServiceError as exc: result={'error':exc.code}; status=exc.status
    except ValueError as exc:
        code=str(exc); result={'error':code if re.fullmatch(r'(CSV|PLANT|TARIFF|ACTION|WEATHER)_[A-Z_]+',code) else 'INVALID_REQUEST'}; status=503 if code=='WEATHER_UNAVAILABLE' else 422
    except Exception: result={'error':'SERVICE_UNAVAILABLE'}; status=503
    print(json.dumps({'status':status,'data':result},ensure_ascii=True,allow_nan=False))
