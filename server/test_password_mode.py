"""Explicit temporary password mode; SMTP failures never enable this mode."""
import hashlib,os,secrets,tempfile,unittest
from unittest.mock import patch
import service,auth_flow
class PasswordModeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name,'GREENMINE_AUTH_MODE':'password','SMTP_REQUIRE_SETUP':'1'});self.env.start()
  self.binding=secrets.token_hex(32);self.available=patch('auth_flow.available',return_value=False);self.available.start();self.delivery=patch('auth_flow.send_otp');self.mail=self.delivery.start()
 def tearDown(self):self.delivery.stop();self.available.stop();self.env.stop();self.tmp.cleanup()
 def call(self,op,data=None):return service.main({'op':op,'data':data or {},'binding':self.binding,'client':'password-mode-test'})
 def registration(self,**changes):
  with patch('captcha.secrets.choice',return_value='4'):c=self.call('captcha')
  return self.call('register',{'email':'owner@example.org','password':'Original123!','password_confirmation':'Original123!','captcha_id':c['captcha_id'],'captcha_answer':'444444',**changes})
 def test_registration_and_login_work_without_smtp_and_new_account_is_empty(self):
  a=self.registration();self.assertIn('token',a);self.assertNotIn('challenge_id',a);self.mail.assert_not_called()
  s=service.main({'op':'engine','token':a['token'],'data':{'action':'overview'}});self.assertEqual(s['readings'],[]);self.assertIsNone(s['plant']['capacity_dc'])
  b=self.call('login',{'email':'owner@example.org','password':'Original123!'});self.assertEqual(b['user']['id'],a['user']['id']);self.mail.assert_not_called()
  with service.closing(service.connect()) as d:r=d.execute('SELECT * FROM users').fetchone();self.assertEqual(r['active'],1);self.assertTrue(r['password_hash'].startswith('pbkdf2_sha256$600000$'))
 def test_signup_still_requires_captcha_and_matching_passwords(self):
  with self.assertRaisesRegex(service.ServiceError,'CAPTCHA_INVALID'):self.call('register',{'email':'owner@example.org','password':'Original123!','password_confirmation':'Original123!'})
  with self.assertRaisesRegex(service.ServiceError,'PASSWORD_MISMATCH'):self.registration(password_confirmation='Different123!')
  with service.closing(service.connect()) as d:self.assertEqual(d.execute('SELECT count(*) FROM users').fetchone()[0],0)
 def test_wrong_password_does_not_create_a_session(self):
  self.registration()
  with self.assertRaisesRegex(service.ServiceError,'INVALID_LOGIN'):self.call('login',{'email':'owner@example.org','password':'Wrong123!'})
  with service.closing(service.connect()) as d:self.assertEqual(d.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
  self.mail.assert_not_called()
 def test_inactive_account_is_not_silently_activated(self):
  self.registration()
  with service.closing(service.connect()) as d,d:d.execute('UPDATE users SET active=0')
  with self.assertRaisesRegex(service.ServiceError,'ACCOUNT_INACTIVE'):self.call('login',{'email':'owner@example.org','password':'Original123!'})
  with service.closing(service.connect()) as d:self.assertEqual(d.execute('SELECT active FROM users').fetchone()[0],0);self.assertEqual(d.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
 def test_legacy_hash_upgrade_preserves_id_history_and_existing_session(self):
  a=self.registration();salt=secrets.token_hex(16);old=hashlib.scrypt(b'Original123!',salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=64).hex()
  service.main({'op':'engine','token':a['token'],'data':{'action':'import','csv':'date,kwh\n2026-08-01,2','source_name':'test-source'}})
  with service.closing(service.connect()) as d,d:d.execute('UPDATE users SET salt=?,password_hash=?',(salt,old))
  b=self.call('login',{'email':'owner@example.org','password':'Original123!'});self.assertEqual(b['user']['id'],a['user']['id'])
  self.assertEqual(service.main({'op':'engine','token':a['token'],'data':{'action':'overview'}})['total_kwh'],2)
  with service.closing(service.connect()) as d:self.assertTrue(d.execute('SELECT password_hash FROM users').fetchone()[0].startswith('pbkdf2_sha256$600000$'))
 def test_switch_to_otp_requires_mail_and_retains_existing_session(self):
  a=self.registration()
  with patch.dict(os.environ,{'GREENMINE_AUTH_MODE':'email_otp'}):
   with self.assertRaisesRegex(service.ServiceError,'AUTH_MAIL_UNAVAILABLE'):self.call('login',{'email':'owner@example.org','password':'Original123!'})
   self.assertEqual(service.main({'op':'me','token':a['token']})['user']['email'],'owner@example.org')
   with patch('auth_flow.available',return_value=True):p=self.call('login',{'email':'owner@example.org','password':'Original123!'})
   self.assertEqual(p['stage'],'login');self.assertNotIn('token',p)
 def test_request_cannot_enable_password_mode_and_mail_failure_has_no_fallback(self):
  self.registration()
  with patch.dict(os.environ,{'GREENMINE_AUTH_MODE':'email_otp'}),patch('auth_flow.available',return_value=True),patch('auth_flow.send_otp',side_effect=OSError):
   with self.assertRaisesRegex(service.ServiceError,'AUTH_MAIL_UNAVAILABLE'):self.call('login',{'email':'owner@example.org','password':'Original123!','auth_mode':'password'})
  with service.closing(service.connect()) as d:self.assertEqual(d.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
 def test_status_and_invalid_server_configuration_fail_closed(self):
  status=self.call('auth_status');self.assertEqual(status['auth_mode'],'password');self.assertFalse(status['login_email_otp']);self.assertFalse(status['registration_verification']);self.assertFalse(status['auth_email_available'])
  with patch.dict(os.environ,{'GREENMINE_AUTH_MODE':'unknown'}):
   with self.assertRaisesRegex(ValueError,'AUTH_MODE_INVALID'):self.call('auth_status')
