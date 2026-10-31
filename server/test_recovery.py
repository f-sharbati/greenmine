from test_support import call_service
import os,tempfile,unittest,time,sqlite3
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import service,recovery
class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name,'SMTP_HOST':'localhost','SMTP_USER':'test','SMTP_PASSWORD':'test'});self.env.start()
  self.a=call_service({'op':'register','data':{'email':'owner@example.org','password':'Original123!'},'client':'owner'})
  self.messages=[];self.mail=patch.object(recovery,'send_code',side_effect=lambda email,code:self.messages.append((email,code)));self.mail.start()
 def tearDown(self):self.mail.stop();self.env.stop();self.tmp.cleanup()
 def request(self,email='owner@example.org'):return call_service({'op':'forgot','data':{'email':email},'client':'test-ip'})
 def reset(self,challenge,code,password='Changed123!'):return call_service({'op':'reset','data':{'challenge_id':challenge,'code':code,'password':password},'client':'test-ip'})
 def test_request_preserves_password_and_reset_revokes_sessions(self):
  p=self.request();code=self.messages[-1][1]
  call_service({'op':'login','data':{'email':'owner@example.org','password':'Original123!'}})
  self.reset(p['challenge_id'],code)
  with self.assertRaisesRegex(service.ServiceError,'INVALID_LOGIN'):call_service({'op':'login','data':{'email':'owner@example.org','password':'Original123!'}})
  call_service({'op':'login','data':{'email':'owner@example.org','password':'Changed123!'}})
  with self.assertRaisesRegex(service.ServiceError,'UNAUTHENTICATED'):call_service({'op':'me','token':self.a['token']})
  with self.assertRaisesRegex(service.ServiceError,'RECOVERY_INVALID'):self.reset(p['challenge_id'],code)
 def test_five_bad_attempts_block_even_valid_code(self):
  p=self.request();code=self.messages[-1][1];wrong='000000' if code!='000000' else '111111'
  for _ in range(5):
   with self.assertRaisesRegex(service.ServiceError,'RECOVERY_INVALID'):self.reset(p['challenge_id'],wrong)
  with self.assertRaisesRegex(service.ServiceError,'RECOVERY_INVALID'):self.reset(p['challenge_id'],code)
 def test_expiry(self):
  p=self.request();db=service.connect()
  with db:db.execute('UPDATE recovery_challenges SET expires_at=0')
  db.close()
  with self.assertRaisesRegex(service.ServiceError,'RECOVERY_INVALID'):self.reset(p['challenge_id'],self.messages[-1][1])
 def test_nonexistent_account_generic_response_and_no_message(self):
  p=self.request('missing@example.org');self.assertIn('challenge_id',p);self.assertEqual(self.messages,[])
 def test_code_storage_is_keyed_and_no_code_in_response(self):
  p=self.request();code=self.messages[-1][1];db=service.connect();stored=db.execute('SELECT code_hash FROM recovery_challenges').fetchone()[0];db.close()
  self.assertNotEqual(stored,code);self.assertNotIn('code',p)
 def test_concurrent_consumption_succeeds_once(self):
  p=self.request();code=self.messages[-1][1]
  def consume(_):
   try:self.reset(p['challenge_id'],code);return True
   except service.ServiceError:return False
  with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(consume,range(2))),[False,True])
 def test_persian_digits_and_eight_character_password(self):
  p=self.request();code=self.messages[-1][1].translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))
  self.reset(p['challenge_id'],code,password='Test123!')
  call_service({'op':'login','data':{'email':'owner@example.org','password':'Test123!'}})
 def test_delivery_failure_does_not_leave_valid_challenge(self):
  with patch.object(recovery,'send_code',side_effect=OSError):
   with self.assertRaisesRegex(service.ServiceError,'RECOVERY_UNAVAILABLE'):self.request()
  db=service.connect();self.assertEqual(db.execute('SELECT count(*) FROM recovery_challenges').fetchone()[0],0);db.close()
