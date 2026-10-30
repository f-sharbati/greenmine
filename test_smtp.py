"""Explicit operator-only SMTP authentication check; sends no messages."""
import os
import smtplib
import ssl

def main():
    host = os.environ['SMTP_HOST']
    port = int(os.environ.get('SMTP_PORT', '587'))
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
    print('SMTP authentication passed; no messages sent')

if __name__ == '__main__':
    main()
