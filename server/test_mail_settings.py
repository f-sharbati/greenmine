from test_support import call_service
import json,os,stat,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
import service,recovery
from mail_settings import config,path
class MailSettingsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name,'GREENMINE_ADMIN_EMAIL':'admin@example.org','SMTP_REQUIRE_SETUP':'1'});self.env.start()
  self.admin=call_service({'op':'register','data':{'email':'admin@example.org','password':'Test123!'}})
  self.other=call_service({'op':'register','data':{'email':'other@example.org','password':'Test123!'}})
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def run_settings(self,user=None,**kw):return call_service({'op':'engine','token':(user or self.admin)['token'],'data':{'action':'mail_settings',**kw}})
 def good(self):return dict(save=True,host='smtp.example.org',port=587,tls='starttls',username='sender@example.org',password='new-private-app-password')
 def test_admin_only_and_setup_required(self):
  self.assertTrue(self.admin['user']['mail_admin']);self.assertFalse(self.other['user']['mail_admin']);self.assertFalse(recovery.available())
  with self.assertRaisesRegex(service.ServiceError,'FORBIDDEN'):self.run_settings(self.other)
 def test_atomic_save_private_no_secret_in_response_and_restart_reads_it(self):
  with patch('mail_settings.smtplib.SMTP') as smtp:
   result=self.run_settings(**self.good());smtp.return_value.__enter__.return_value.login.assert_called_once_with('sender@example.org','new-private-app-password')
  self.assertTrue(result['configured']);self.assertNotIn('password',json.dumps(result));self.assertTrue(recovery.available());self.assertEqual(config()['SMTP_USER'],'sender@example.org')
  if os.name!='nt':self.assertEqual(stat.S_IMODE(path().stat().st_mode),0o600)
  self.assertNotIn('new-private-app-password',json.dumps(self.run_settings()))
 def test_failed_auth_leaves_existing_config_untouched(self):
  with patch('mail_settings.smtplib.SMTP'):self.run_settings(**self.good())
  before=path().read_bytes()
  with patch('mail_settings.smtplib.SMTP',side_effect=OSError('private-error')):
   with self.assertRaisesRegex(service.ServiceError,'MAIL_AUTH_FAILED'):self.run_settings(**{**self.good(),'password':'wrong'})
  self.assertEqual(path().read_bytes(),before)
 def test_rejects_invalid_ports_tls_and_sender_headers(self):
  for extra in [dict(port=25),dict(tls='none'),dict(username='bad\nheader@example.org'),dict(password='')]:
   with self.assertRaisesRegex(service.ServiceError,'MAIL_SETTINGS_INVALID'):self.run_settings(**{**self.good(),**extra})
 def test_setup_change_preserves_password_history_and_sessions(self):
  d=service.connect();before={t:[tuple(r) for r in d.execute('select * from '+t)] for t in ['users','sessions','workspaces']};d.close()
  with patch('mail_settings.smtplib.SMTP'):self.run_settings(**self.good())
  d=service.connect()
  for t,r in before.items():self.assertEqual([tuple(x) for x in d.execute('select * from '+t)],r)
  d.close()
 def test_recovery_uses_private_config_instead_of_environment(self):
  with patch('mail_settings.smtplib.SMTP'):self.run_settings(**self.good())
  with patch('recovery.smtplib.SMTP') as smtp:recovery.send_code('user@example.org','123456');smtp.return_value.__enter__.return_value.login.assert_called_once_with('sender@example.org','new-private-app-password')
