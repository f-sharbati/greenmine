import unittest
from unittest.mock import patch
import mail_delivery

class MailDeliveryTests(unittest.TestCase):
 def settings(self,**extra):return {'SMTP_HOST':'smtp.gmail.com','SMTP_PORT':'587','SMTP_TLS':'starttls','SMTP_USER':'sender@example.org','SMTP_PASSWORD':'private-test-password','SMTP_FROM':'sender@example.org',**extra}
 def test_activation_and_login_use_authenticated_starttls(self):
  for purpose in ['activation','login','recovery']:
   with patch('mail_delivery.config',return_value=self.settings()),patch('mail_delivery.smtplib.SMTP') as factory:
    mail_delivery.send_otp('owner@example.org','123456',purpose)
    smtp=factory.return_value.__enter__.return_value
    smtp.starttls.assert_called_once();smtp.login.assert_called_once_with('sender@example.org','private-test-password')
    message=smtp.send_message.call_args.args[0]
    self.assertEqual(message['To'],'owner@example.org');self.assertIn('123456',message.get_content())
    self.assertNotIn('private-test-password',str(message))
 def test_external_plaintext_smtp_rejected(self):
  with patch('mail_delivery.config',return_value=self.settings(SMTP_TLS='none')):
   with self.assertRaisesRegex(ValueError,'TLS_REQUIRED'):mail_delivery.send_otp('owner@example.org','123456','login')
 def test_setup_required_is_not_bypassed_by_environment_defaults(self):
  with patch('mail_delivery.config',return_value={}):self.assertFalse(mail_delivery.available())
