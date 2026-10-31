"""Inactive registration -> email activation; password -> email OTP -> session."""
import hashlib,hmac,json,re,secrets,sqlite3,time
from mail_delivery import available,send_otp
from recovery import key
from passwords import hash_password,verify_password,needs_upgrade
import captcha

def migrate(db):
    columns={r['name'] for r in db.execute('PRAGMA table_info(users)')}
    if 'active' not in columns:
        # Preserve established accounts. New registrations explicitly start inactive.
        try:db.execute('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
        except sqlite3.OperationalError as exc:
            if 'duplicate column' not in str(exc).lower():raise
    db.executescript('''
      CREATE TABLE IF NOT EXISTS captcha_challenges(id TEXT PRIMARY KEY,binding_hash TEXT NOT NULL,answer_hash TEXT NOT NULL,expires_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS auth_challenges(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),purpose TEXT NOT NULL,binding_hash TEXT NOT NULL,code_hash TEXT NOT NULL,credential_fingerprint TEXT NOT NULL,expires_at INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,sent_at INTEGER NOT NULL,delivered INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS auth_events(id INTEGER PRIMARY KEY,event TEXT NOT NULL,email_hash TEXT NOT NULL,client_hash TEXT NOT NULL,created_at INTEGER NOT NULL);
    ''')

def code_hash(cid,code,purpose,binding):
    return hmac.new(key(),f'auth:{purpose}:{cid}:{binding}:{code}'.encode(),hashlib.sha256).hexdigest()

def audit(db,event,email,client,api):
    now=int(time.time())
    db.execute('DELETE FROM auth_events WHERE created_at<?',(now-30*86400,))
    db.execute('INSERT INTO auth_events(event,email_hash,client_hash,created_at) VALUES (?,?,?,?)',(event,api['digest'](email),api['digest'](client),now))

def issue(db,user,purpose,binding,client,api):
    Error=api['error']
    if not available():raise Error('AUTH_MAIL_UNAVAILABLE',503)
    api['rate'](db,'auth-mail-account:'+api['digest'](user['email']),6)
    api['rate'](db,'auth-mail-ip:'+api['digest'](client),30)
    now=int(time.time());cid=secrets.token_hex(24);code=f'{secrets.randbelow(1000000):06d}'
    with db:
        db.execute('DELETE FROM auth_challenges WHERE expires_at<=? OR (user_id=? AND purpose=?)',(now,user['id'],purpose))
        db.execute('INSERT INTO auth_challenges VALUES (?,?,?,?,?,?,?,0,?,0)',(cid,user['id'],purpose,api['digest'](binding),code_hash(cid,code,purpose,binding),api['digest'](user['password_hash']),now+600,now))
    try:send_otp(user['email'],code,purpose)
    except Exception:
        with db:db.execute('DELETE FROM auth_challenges WHERE id=?',(cid,))
        raise Error('AUTH_MAIL_UNAVAILABLE',503) from None
    with db:db.execute('UPDATE auth_challenges SET delivered=1 WHERE id=?',(cid,))
    elapsed=max(0,int(time.time())-now)
    return {'challenge_id':cid,'stage':purpose,'expires_in':max(0,600-elapsed),'resend_after':max(0,60-elapsed)}

def session(db,user,api):
    token=secrets.token_hex(32);now=int(time.time())
    db.execute('DELETE FROM sessions WHERE expires_at<=?',(now,))
    db.execute('INSERT INTO sessions VALUES (?,?,?)',(api['digest'](token),user['id'],now+14*86400))
    from mail_settings import allowed
    return {'user':{'id':user['id'],'email':user['email'],'mail_admin':allowed(user)},'token':token}

def run(db,op,data,binding,client,api):
    Error=api['error']
    if not isinstance(binding,str) or not re.fullmatch('[a-f0-9]{64}',binding):raise Error('AUTH_CONTEXT_REQUIRED',400)
    if op=='captcha':return captcha.create(db,binding,client,api)
    if op in ('register','login'):
        email=str(data.get('email','')).strip().lower();password=data.get('password')
        if not re.fullmatch(r'[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+',email) or len(email)>254:raise Error('EMAIL_INVALID')
        if not isinstance(password,str) or not 8<=len(password)<=128:raise Error('PASSWORD_INVALID')
        api['rate'](db,'account:'+api['digest'](email))
        api['rate'](db,'ip:'+api['digest'](client),30)
        if op=='register':captcha.consume(db,data,binding,api)
        row=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if op=='register':
            if data.get('password_confirmation')!=password:raise Error('PASSWORD_MISMATCH',422)
            if row:raise Error('ACCOUNT_EXISTS',409)
            if not available():raise Error('AUTH_MAIL_UNAVAILABLE',503)
            salt=secrets.token_hex(16);hashed=hash_password(password,salt)
            try:
                with db:
                    cur=db.execute('INSERT INTO users(email,salt,password_hash,created_at,active) VALUES (?,?,?,?,0)',(email,salt,hashed,int(time.time())))
                    db.execute('INSERT INTO workspaces VALUES (?,?,?,?,?,?)',(cur.lastrowid,json.dumps(api['empty_plant']),25000,'[]',None,int(time.time())))
                    row=db.execute('SELECT * FROM users WHERE id=?',(cur.lastrowid,)).fetchone()
            except sqlite3.IntegrityError:raise Error('ACCOUNT_EXISTS',409) from None
            return issue(db,row,'activation',binding,client,api)
        # A dummy KDF avoids a cheap distinguishable path for unknown emails.
        valid=verify_password(password,row['salt'],row['password_hash']) if row else False
        if row is None:hash_password(password,'00'*16)
        if row is None or not valid:
            with db:audit(db,'password_rejected',email,client,api)
            raise Error('INVALID_LOGIN',401)
        if needs_upgrade(row['password_hash']):
            salt=secrets.token_hex(16)
            with db:db.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,hash_password(password,salt),row['id']))
            row=db.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
        # Inactive users are guided back through activation, never granted a login OTP/session.
        return issue(db,row,'login' if row['active'] else 'activation',binding,client,api)
    api['rate'](db,'auth-verify-ip:'+api['digest'](client),40)
    cid=data.get('challenge_id')
    if not isinstance(cid,str) or not re.fullmatch('[a-f0-9]{48}',cid):raise Error('OTP_INVALID',422)
    if op=='auth_resend':
        row=db.execute('SELECT a.*,u.email,u.password_hash,u.active FROM auth_challenges a JOIN users u ON a.user_id=u.id WHERE a.id=? AND a.binding_hash=?',(cid,api['digest'](binding))).fetchone()
        if row is None or not row['delivered'] or row['credential_fingerprint']!=api['digest'](row['password_hash']):raise Error('OTP_INVALID',422)
        if row['purpose']=='login' and not row['active']:raise Error('OTP_INVALID',422)
        wait=60-(int(time.time())-row['sent_at'])
        if wait>0:raise Error('OTP_RESEND_WAIT',429)
        user={'id':row['user_id'],'email':row['email'],'password_hash':row['password_hash']}
        return issue(db,user,row['purpose'],binding,client,api)
    if op!='auth_verify':raise Error('ACTION_INVALID')
    code=captcha.normalized(data.get('code',''))
    if len(code)!=6 or not code.isascii() or not code.isdigit():raise Error('OTP_INVALID',422)
    result=None;now=int(time.time())
    with db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT a.*,u.email,u.password_hash,u.active FROM auth_challenges a JOIN users u ON a.user_id=u.id WHERE a.id=?',(cid,)).fetchone()
        if row and row['binding_hash']==api['digest'](binding) and row['delivered'] and row['expires_at']>now and row['attempts']<5 and row['credential_fingerprint']==api['digest'](row['password_hash']):
            if not hmac.compare_digest(row['code_hash'],code_hash(cid,code,row['purpose'],binding)):
                db.execute('UPDATE auth_challenges SET attempts=attempts+1 WHERE id=?',(cid,))
                audit(db,'otp_rejected',row['email'],client,api)
            elif row['purpose']=='activation':
                db.execute('UPDATE users SET active=1 WHERE id=?',(row['user_id'],))
                db.execute('DELETE FROM auth_challenges WHERE user_id=?',(row['user_id'],))
                audit(db,'email_activated',row['email'],client,api)
                result={'activated':True,'next':'login'}
            elif row['purpose']=='login' and row['active']:
                db.execute('DELETE FROM auth_challenges WHERE id=?',(cid,))
                audit(db,'login_verified',row['email'],client,api)
                result=session(db,{'id':row['user_id'],'email':row['email']},api)
    if result is None:raise Error('OTP_INVALID',422)
    return result
