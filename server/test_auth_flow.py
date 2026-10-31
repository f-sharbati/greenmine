import hashlib,json,os,secrets,sqlite3,tempfile,time,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import service,auth_flow,captcha
from passwords import hash_password,verify_password

class AuthFlowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name,'SMTP_REQUIRE_SETUP':'1'});self.env.start()
  self.binding=secrets.token_hex(32);self.messages=[]
  self.available=patch('auth_flow.available',return_value=True);self.available.start()
  self.delivery=patch('auth_flow.send_otp',side_effect=lambda email,code,purpose:self.messages.append((email,code,purpose)));self.delivery.start()
 def tearDown(self):self.delivery.stop();self.available.stop();self.env.stop();self.tmp.cleanup()
 def call(self,op,data=None,binding=None):return service.main({'op':op,'data':data or {},'binding':binding or self.binding,'client':'auth-test'})
 def cap(self):
  with patch('captcha.secrets.choice',return_value='4'):return self.call('captcha')
 def begin(self,op='register',email='owner@example.org',password='Original123!'):
  c=self.cap();return self.call(op,{'email':email,'password':password,'password_confirmation':password,'captcha_id':c['captcha_id'],'captcha_answer':'444444'})
 def verify(self,p,code=None,binding=None):return self.call('auth_verify',{'challenge_id':p['challenge_id'],'code':code or self.messages[-1][1]},binding)
 def active(self):self.verify(self.begin())
 def test_full_flow_no_session_before_each_required_verification(self):
  p=self.begin();self.assertEqual(p['stage'],'activation');self.assertNotIn('token',p)
  with service.closing(service.connect()) as db:
   row=db.execute('SELECT * FROM users').fetchone();self.assertEqual(row['active'],0);self.assertTrue(row['password_hash'].startswith('pbkdf2_sha256$600000$'))
   self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],0)
  self.assertEqual(self.verify(p),{'activated':True,'next':'login'})
  p=self.begin('login');self.assertEqual(p['stage'],'login');self.assertNotIn('token',p)
  result=self.verify(p);self.assertIn('token',result)
  self.assertEqual(service.main({'op':'me','token':result['token']})['user']['email'],'owner@example.org')
 def test_inactive_login_guides_activation_not_login_otp(self):
  self.begin();p=self.begin('login');self.assertEqual(p['stage'],'activation');self.assertNotIn('token',p)
 def test_wrong_password_records_failure_sends_no_login_code(self):
  self.active();count=len(self.messages)
  with self.assertRaisesRegex(service.ServiceError,'INVALID_LOGIN'):self.begin('login',password='Incorrect123!')
  self.assertEqual(len(self.messages),count)
  with service.closing(service.connect()) as db:self.assertEqual(db.execute("SELECT count(*) FROM auth_events WHERE event='password_rejected'").fetchone()[0],1)
 def test_captcha_required_single_use_expiry_and_binding(self):
  c=self.cap();data={'email':'owner@example.org','password':'Original123!','password_confirmation':'Original123!','captcha_id':c['captcha_id'],'captcha_answer':'444444'}
  with self.assertRaisesRegex(service.ServiceError,'CAPTCHA_INVALID'):self.call('register',data,binding='f'*64)
  self.call('register',data)
  with self.assertRaisesRegex(service.ServiceError,'CAPTCHA_INVALID'):self.call('register',data)
  c=self.cap();data['captcha_id']=c['captcha_id']
  with service.closing(service.connect()) as db,db:db.execute('UPDATE captcha_challenges SET expires_at=0')
  with self.assertRaisesRegex(service.ServiceError,'CAPTCHA_INVALID'):self.call('register',data)
  self.assertTrue(c['image'].startswith('data:image/png;base64,'));self.assertNotIn('answer',c)
 def test_missing_browser_context_rejected(self):
  with self.assertRaisesRegex(service.ServiceError,'AUTH_CONTEXT_REQUIRED'):service.main({'op':'register','data':{'email':'a@example.org','password':'Original123!'}})
 def test_otp_is_keyed_browser_bound_and_single_use(self):
  p=self.begin();code=self.messages[-1][1]
  self.assertNotIn('code',p)
  with service.closing(service.connect()) as db:
   stored=db.execute('SELECT code_hash FROM auth_challenges').fetchone()[0]
   self.assertNotEqual(stored,code);self.assertNotEqual(stored,hashlib.sha256(code.encode()).hexdigest())
  with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(p,binding='e'*64)
  self.verify(p)
  with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(p,code)
 def test_five_failures_and_expiration(self):
  p=self.begin();real=self.messages[-1][1];wrong='000000' if real!='000000' else '111111'
  for _ in range(5):
   with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(p,wrong)
  with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(p,real)
  with service.closing(service.connect()) as db,db:db.execute('UPDATE auth_challenges SET sent_at=sent_at-61')
  p=self.call('auth_resend',{'challenge_id':p['challenge_id']})
  with service.closing(service.connect()) as db,db:db.execute('UPDATE auth_challenges SET expires_at=0')
  with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(p)
 def test_resend_cooldown_and_old_challenge_invalidated(self):
  old=self.begin();code=self.messages[-1][1]
  with self.assertRaisesRegex(service.ServiceError,'OTP_RESEND_WAIT'):self.call('auth_resend',{'challenge_id':old['challenge_id']})
  with service.closing(service.connect()) as db,db:db.execute('UPDATE auth_challenges SET sent_at=sent_at-61')
  new=self.call('auth_resend',{'challenge_id':old['challenge_id']})
  self.assertNotEqual(old['challenge_id'],new['challenge_id'])
  with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(old,code)
  self.verify(new)
 def test_concurrent_code_redemption_only_one_session(self):
  self.active();p=self.begin('login');code=self.messages[-1][1]
  def consume(_):
   try:return 'token' in self.verify(p,code)
   except service.ServiceError:return False
  with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(consume,range(2))),[False,True])
 def test_mail_failure_leaves_inactive_account_and_no_usable_challenge(self):
  with patch('auth_flow.send_otp',side_effect=OSError):
   with self.assertRaisesRegex(service.ServiceError,'AUTH_MAIL_UNAVAILABLE'):self.begin()
  with service.closing(service.connect()) as db:
   self.assertEqual(db.execute('SELECT active FROM users').fetchone()[0],0);self.assertEqual(db.execute('SELECT count(*) FROM auth_challenges').fetchone()[0],0)
   self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],0)
 def test_no_setup_does_not_create_account(self):
  with patch('auth_flow.available',return_value=False):
   with self.assertRaisesRegex(service.ServiceError,'AUTH_MAIL_UNAVAILABLE'):self.begin()
  with service.closing(service.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)
 def test_legacy_password_upgrade_keeps_account_id_and_requires_otp(self):
  self.active()
  salt=secrets.token_hex(16);old=hashlib.scrypt(b'Original123!',salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=64).hex()
  with service.closing(service.connect()) as db,db:
   uid=db.execute('SELECT id FROM users').fetchone()[0];db.execute('UPDATE users SET salt=?,password_hash=?',(salt,old))
  p=self.begin('login');self.assertNotIn('token',p)
  with service.closing(service.connect()) as db:
   row=db.execute('SELECT * FROM users').fetchone();self.assertEqual(row['id'],uid);self.assertTrue(row['password_hash'].startswith('pbkdf2_sha256$'))
  self.verify(p)
 def test_password_change_invalidates_pending_login_code(self):
  self.active();p=self.begin('login');code=self.messages[-1][1]
  with service.closing(service.connect()) as db,db:db.execute('UPDATE users SET password_hash=?',(hash_password('Changed123!','00'*16),))
  with self.assertRaisesRegex(service.ServiceError,'OTP_INVALID'):self.verify(p,code)
 def test_password_confirmation_and_persian_code_digits(self):
  c=self.cap()
  with self.assertRaisesRegex(service.ServiceError,'PASSWORD_MISMATCH'):self.call('register',{'email':'owner@example.org','password':'Original123!','password_confirmation':'Different123!','captcha_id':c['captcha_id'],'captcha_answer':'444444'})
  p=self.begin();code=self.messages[-1][1].translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'));self.verify(p,code)
 def test_login_follows_password_then_otp_without_extra_captcha(self):
  self.active()
  p=self.call('login',{'email':'owner@example.org','password':'Original123!'})
  self.assertEqual(p['stage'],'login');self.assertNotIn('token',p);self.verify(p)
 def test_existing_five_column_user_schema_migrates_preserving_identity(self):
  salt=secrets.token_hex(16);hashed=hashlib.scrypt(b'Original123!',salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=64).hex()
  db=sqlite3.connect(os.path.join(self.tmp.name,'accounts.sqlite3'))
  db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT NOT NULL UNIQUE,salt TEXT NOT NULL,password_hash TEXT NOT NULL,created_at INTEGER NOT NULL)')
  db.execute('INSERT INTO users VALUES (7,?,?,?,?)',('owner@example.org',salt,hashed,int(time.time())));db.commit();db.close()
  p=self.call('login',{'email':'owner@example.org','password':'Original123!'})
  self.assertEqual(p['stage'],'login');result=self.verify(p);self.assertEqual(result['user']['id'],7)
