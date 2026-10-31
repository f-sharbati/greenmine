"""Private SMTP transport shared by activation, sign-in and password recovery."""
import smtplib
import ssl
from email.message import EmailMessage
from mail_settings import config

def available():return all(config().get(k) for k in ('SMTP_HOST','SMTP_USER','SMTP_PASSWORD'))

def send_otp(email,code,purpose):
    labels={'activation':('Verify your email','تأیید ایمیل'),'login':('Sign-in verification','تأیید ورود'),'recovery':('Password recovery','بازیابی رمز عبور')}
    en,fa=labels[purpose];settings=config()
    message=EmailMessage();message['Subject']='GreenMine — '+en
    message['From']=settings.get('SMTP_FROM') or settings['SMTP_USER'];message['To']=email
    message.set_content(f'{fa} گرین‌ماین\n\n{code}\n\nاین کد یک‌بارمصرف تا ۱۰ دقیقه معتبر است. کد را در اختیار کسی نگذارید. اگر درخواست نداده‌اید، این پیام را نادیده بگیرید.\n\nGreenMine: {en}\nCode: {code}\nValid once for 10 minutes. Do not share this code. Ignore this message if you did not request it.')
    host=settings['SMTP_HOST'];port=int(settings.get('SMTP_PORT') or 587);mode=settings.get('SMTP_TLS') or 'starttls'
    if mode not in ('ssl','starttls','none') or mode=='none' and host not in ('localhost','127.0.0.1','::1'):raise ValueError('TLS_REQUIRED')
    client=smtplib.SMTP_SSL(host,port,timeout=8,context=ssl.create_default_context()) if mode=='ssl' else smtplib.SMTP(host,port,timeout=8)
    with client as smtp:
        smtp.ehlo()
        if mode=='starttls':smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
        smtp.login(settings['SMTP_USER'],settings['SMTP_PASSWORD']);smtp.send_message(message)
