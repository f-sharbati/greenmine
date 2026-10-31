"""Persistent, session-authenticated single-plant workspaces. No legacy DB mutation."""
from contextlib import closing
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
      CREATE TABLE IF NOT EXISTS calibration_references(user_id INTEGER PRIMARY KEY REFERENCES users(id),plant TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS forecast_runs(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),issued_at TEXT NOT NULL,days TEXT NOT NULL);
    ''')
    migrate_sources(db)
    from auth_flow import migrate
    migrate(db)
    return db

def migrate_sources(db):
    db.executescript("""
      CREATE TABLE IF NOT EXISTS production_readings(user_id INTEGER NOT NULL REFERENCES users(id),device_id TEXT NOT NULL,reading_date TEXT NOT NULL,kwh REAL NOT NULL CHECK(kwh>=0),PRIMARY KEY(user_id,device_id,reading_date));
      CREATE TABLE IF NOT EXISTS import_sources(import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,device_id TEXT NOT NULL,PRIMARY KEY(import_id,device_id));
      CREATE TABLE IF NOT EXISTS schema_meta(name TEXT PRIMARY KEY,value TEXT NOT NULL);
    """)
    if db.execute("SELECT 1 FROM schema_meta WHERE name='production_sources_v1'").fetchone():return
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM schema_meta WHERE name='production_sources_v1'").fetchone():return
        for workspace in db.execute('SELECT user_id,serial,readings FROM workspaces').fetchall():
            device='serial:'+workspace['serial'] if workspace['serial'] else 'manual:legacy'
            for legacy_import in db.execute('SELECT raw_csv FROM imports WHERE user_id=? ORDER BY id',(workspace['user_id'],)).fetchall():
                detected,serial=detected_source(legacy_import['raw_csv'])
                if detected and serial==workspace['serial']:device=detected;break
            for r in json.loads(workspace['readings']):
                db.execute('INSERT OR IGNORE INTO production_readings VALUES (?,?,?,?)',(workspace['user_id'],device,r['date'],r['kwh']))
            db.execute('INSERT OR IGNORE INTO import_sources SELECT id,? FROM imports WHERE user_id=?',(device,workspace['user_id']))
        db.execute("INSERT INTO schema_meta VALUES ('production_sources_v1','1')")

def sources(db,uid):
    return [dict(r) for r in db.execute('SELECT device_id,count(*) AS days,round(sum(kwh),6) AS total_kwh,min(reading_date) AS first_date,max(reading_date) AS last_date FROM production_readings WHERE user_id=? GROUP BY device_id ORDER BY device_id',(uid,))]

def daily_readings(db,uid):
    count=len(sources(db,uid))
    return [dict(date=r['reading_date'],kwh=round(r['energy'],6),source_count=r['source_count'],expected_sources=count,complete=r['source_count']==count) for r in db.execute('SELECT reading_date,sum(kwh) AS energy,count(*) AS source_count FROM production_readings WHERE user_id=? GROUP BY reading_date ORDER BY reading_date',(uid,))]

def is_total_report(raw):
    import csv
    lines=raw.lstrip('\ufeff').splitlines()
    start=next(i for i,line in enumerate(lines) if line.strip().lower().startswith(('date,','date;')))
    reader=csv.DictReader(lines[start:],delimiter=';' if ';' in lines[start] else ',')
    reader.fieldnames=[name.strip().lower() for name in reader.fieldnames]
    return any(str(row.get('scope','')).strip().lower()=='plant_total' for row in reader)

def detected_source(raw):
    import csv
    lines=raw.splitlines()
    for i,line in enumerate(lines[:-1]):
        delimiter=';' if ';' in line else ','
        keys=[x.strip().lower() for x in next(csv.reader([line],delimiter=delimiter))]
        field=next((k for k in ['serial number','serial','inverter serial','device id'] if k in keys),None)
        if not field:continue
        values=next(csv.reader([lines[i+1]],delimiter=delimiter));index=keys.index(field)
        if index>=len(values) or not values[index].strip():continue
        serial=values[index].strip()
        family_key=next((k for k in ['brand','manufacturer','inverter type','device type','inverter model','model'] if k in keys),None)
        family=values[keys.index(family_key)].strip().casefold() if family_key and keys.index(family_key)<len(values) else ''
        if len(serial)>100 or len(family)>100 or any(ord(c)<32 for c in serial+family):raise ServiceError('CSV_SOURCE_INVALID')
        return 'serial:'+(family+'|' if family else '')+serial,serial
    return None,None

def import_source(db,uid,data,raw):
    device,serial=detected_source(raw)
    if device:return device,serial
    selected=data.get('source_id');known={r['device_id'] for r in sources(db,uid)}
    if selected:
        if selected not in known:raise ServiceError('CSV_SOURCE_INVALID')
        return selected,None
    label=data.get('source_name')
    if isinstance(label,str) and 1<=len(label.strip())<=100 and not any(ord(c)<32 for c in label):return 'manual:'+' '.join(label.split()).casefold(),None
    raise ServiceError('CSV_SOURCE_REQUIRED',422)

def password_hash(password, salt):
    from passwords import hash_password
    return hash_password(password,salt)


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
    row = db.execute('SELECT u.id,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1', (digest(token),int(time.time()))).fetchone()
    if row is None: raise ServiceError('UNAUTHENTICATED',401)
    from mail_settings import allowed
    return dict(row,mail_admin=allowed(row))

def main(request):
    if not isinstance(request,dict): raise ServiceError('INVALID_REQUEST')
    op=request.get('op'); data=request.get('data') or {}
    if op=='auth_status':
        from mail_delivery import available
        from auth_flow import mode
        auth_mode=mode()
        return {'auth_mode':auth_mode,'auth_email_available':available(),'password_scheme':'PBKDF2-HMAC-SHA-256','registration_verification':auth_mode=='email_otp','login_email_otp':auth_mode=='email_otp'}
    if op=='recovery_status':
        from recovery import available
        return {'recovery_available':available()}
    if not isinstance(data,dict): raise ServiceError('INVALID_REQUEST')
    with closing(connect()) as db, db:
        if op in ('forgot','reset'):
            from recovery import run
            return run(db,op,data,str(request.get('client','local')),{'rate':rate_limit,'digest':digest,'password_hash':password_hash,'error':ServiceError})
        if op in ('register','login','captcha','auth_verify','auth_resend'):
            from auth_flow import run
            return run(db,op,data,request.get('binding'),str(request.get('client','local')),{'error':ServiceError,'rate':rate_limit,'digest':digest,'empty_plant':bridge.EMPTY_PLANT})
        user=user_for(db,request.get('token'))
        if op=='me': return {'user':user}
        if op=='logout':
            with db: db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request['token']),))
            return {'ok':True}
        if op!='engine': raise ServiceError('ACTION_INVALID')
        uid=user['id']; workspace=db.execute('SELECT * FROM workspaces WHERE user_id=?',(uid,)).fetchone()
        action=data.get('action')
        if action=='mail_settings':
            from mail_settings import run
            return run(db,user,data,{'error':ServiceError,'rate':rate_limit})
        if action=='import':
            raw=data.get('csv')
            if not isinstance(raw,str) or len(raw.encode())>1_500_000: raise ServiceError('FILE_TOO_LARGE',413)
            rows=bridge.clean_csv(raw)
            from datetime import date, datetime, timezone, timedelta
            today = datetime.now(timezone(timedelta(hours=3, minutes=30))).date()
            if any(date.fromisoformat(r['date'])>today for r in rows): raise ServiceError('CSV_FUTURE')
            if is_total_report(raw):
                existing={r['date']:r['kwh'] for r in daily_readings(db,uid)}
                if any(r['date'] not in existing or abs(existing[r['date']]-r['kwh'])>1e-6 for r in rows):raise ServiceError('CSV_TOTAL_REPORT')
                return dict(**bridge.summary(daily_readings(db,uid)),sources=sources(db,uid),data_quality={'complete_days':sum(r['complete'] for r in daily_readings(db,uid)),'partial_days':sum(not r['complete'] for r in daily_readings(db,uid))},plant={**bridge.DEFAULT_PLANT,**json.loads(workspace['plant'])},tariff=workspace['tariff'],source='Saved production readings',sample=False)
            with db:
                db.execute('BEGIN IMMEDIATE')
                device,serial=import_source(db,uid,data,raw)
                existing={r['reading_date']:r['kwh'] for r in db.execute('SELECT reading_date,kwh FROM production_readings WHERE user_id=? AND device_id=?',(uid,device))}
                for row in rows:
                    if row['date'] in existing and existing[row['date']]!=row['kwh']:raise ServiceError('CSV_CONFLICT')
                    db.execute('INSERT OR IGNORE INTO production_readings VALUES (?,?,?,?)',(uid,device,row['date'],row['kwh']))
                merged=daily_readings(db,uid)
                db.execute('UPDATE workspaces SET readings=?,serial=COALESCE(serial,?),updated_at=? WHERE user_id=?',(json.dumps(merged),serial,int(time.time()),uid))
                db.execute('INSERT OR IGNORE INTO imports(user_id,digest,filename,raw_csv,created_at) VALUES (?,?,?,?,?)',(uid,digest(raw),str(data.get('filename','upload.csv'))[:255],raw,int(time.time())))
                import_id=db.execute('SELECT id FROM imports WHERE user_id=? AND digest=?',(uid,digest(raw))).fetchone()[0]
                db.execute('INSERT OR IGNORE INTO import_sources VALUES (?,?)',(import_id,device))
        if action in ('overview','import'):
            workspace=db.execute('SELECT * FROM workspaces WHERE user_id=?',(uid,)).fetchone()
            rows=daily_readings(db,uid)
            return dict(**bridge.summary(rows),sources=sources(db,uid),data_quality={'complete_days':sum(r['complete'] for r in rows),'partial_days':sum(not r['complete'] for r in rows)},plant={**bridge.DEFAULT_PLANT,**json.loads(workspace['plant'])},tariff=workspace['tariff'],source='Saved production readings',sample=False)
        if action=='settings':
            plant,tariff=bridge.validate_settings(data,require_specs=True)
            with db:
                db.execute('UPDATE workspaces SET plant=?,tariff=?,updated_at=? WHERE user_id=?',(json.dumps(plant),tariff,int(time.time()),uid))
                if data.get('set_measured_reference') is True or not daily_readings(db,uid):
                    db.execute('INSERT OR REPLACE INTO calibration_references VALUES (?,?)',(uid,json.dumps(plant)))
                else:
                    old={**bridge.DEFAULT_PLANT,**json.loads(workspace['plant'])}
                    if not old.get('capacity_dc'):old=plant
                    db.execute('INSERT OR IGNORE INTO calibration_references VALUES (?,?)',(uid,json.dumps(old)))
            return {'plant':plant,'tariff':tariff}
        if action=='locations':
            query=data.get('query','')
            if not isinstance(query,str) or not 2<=len(query.strip())<=100:raise ServiceError('LOCATION_QUERY_INVALID')
            rate_limit(db,'locations:'+str(uid),30)
            if query.strip().casefold() in ('tehran','تهران'):
                lat,lon=bridge.plant_coordinates(bridge.DEFAULT_PLANT)
                return {'locations':[{'name':'تهران — موقعیت تقریبی نمونه' if data.get('language')=='fa' else 'Tehran — approximate sample location','latitude':lat,'longitude':lon,'approximate':True}]}
            import requests
            try:
                response=requests.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':query.strip(),'countryCode':'IR','count':8,'language':'fa' if data.get('language')=='fa' else 'en'},timeout=(3,6))
                response.raise_for_status();values=response.json().get('results',[])
                locations=[{'name':', '.join(str(r[k]) for k in ['name','admin1','country'] if r.get(k)),'latitude':float(r['latitude']),'longitude':float(r['longitude'])} for r in values]
            except Exception:raise ServiceError('LOCATION_UNAVAILABLE',503)
            return {'locations':locations}
        if action=='forecast':
            rate_limit(db,'forecast:'+str(uid),15)
            rows=daily_readings(db,uid)
            plant={**bridge.DEFAULT_PLANT,**json.loads(workspace['plant'])}
            if not rows and plant.get('forecast_mode','history_calibrated')!='model_only' and plant['calibration_profile']=='none':raise ServiceError('CSV_REQUIRED',422)
            ref=db.execute('SELECT plant FROM calibration_references WHERE user_id=?',(uid,)).fetchone()
            reference=json.loads(ref['plant']) if ref else plant
            if not ref and plant.get('capacity_dc'):
                with db:db.execute('INSERT OR IGNORE INTO calibration_references VALUES (?,?)',(uid,json.dumps(plant)))
            result=bridge.main({'action':'forecast','plant':plant,'reference_plant':reference,'tariff':workspace['tariff'],'readings':[r for r in rows if r['complete']],'horizon':data.get('horizon','next_month')})
            result['data_quality']={'sources':len(sources(db,uid)),'complete_days':sum(r['complete'] for r in rows),'partial_days':sum(not r['complete'] for r in rows)}
            from issued_forecasts import record_and_score
            if 'validation' in result:result['validation']['issued_forecasts']=record_and_score(db,uid,result,rows)
            return result
        raise ServiceError('ACTION_INVALID')

if __name__=='__main__':
    import sys
    try: result=main(json.load(sys.stdin)); status=200
    except ServiceError as exc: result={'error':exc.code}; status=exc.status
    except ValueError as exc:
        code=str(exc); result={'error':code if re.fullmatch(r'(CSV|PLANT|TARIFF|ACTION|WEATHER)_[A-Z_]+',code) else 'INVALID_REQUEST'}; status=503 if code=='WEATHER_UNAVAILABLE' else 422
    except Exception: result={'error':'SERVICE_UNAVAILABLE'}; status=503
    print(json.dumps({'status':status,'data':result},ensure_ascii=True,allow_nan=False))
