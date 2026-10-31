"""Operator-only SMTP bootstrap before email-gated authentication is enabled."""
import argparse,getpass,os,sqlite3
from mail_settings import run

def main():
    parser=argparse.ArgumentParser(description='Authenticate SMTP and save private mail.json. Sends no email.')
    parser.add_argument('--from-env',action='store_true',help='Read SMTP settings from the already loaded private environment')
    args=parser.parse_args()
    admin=os.environ.get('GREENMINE_ADMIN_EMAIL','').strip().lower()
    if not admin:raise SystemExit('Set GREENMINE_ADMIN_EMAIL before running this command.')
    if args.from_env:
        host=os.environ.get('SMTP_HOST','');username=os.environ.get('SMTP_USER','');password=os.environ.get('SMTP_PASSWORD','')
        port=os.environ.get('SMTP_PORT','587');tls=os.environ.get('SMTP_TLS','starttls')
    else:
        host=input('SMTP host [smtp.gmail.com]: ').strip() or 'smtp.gmail.com'
        username=input('SMTP sender email: ').strip();password=getpass.getpass('New SMTP app password: ')
        port=input('SMTP port [587]: ').strip() or '587';tls='ssl' if port=='465' else 'starttls'
    class Error(Exception):pass
    db=sqlite3.connect(':memory:')
    try:run(db,{'id':0,'email':admin},{'save':True,'host':host,'username':username,'password':password,'port':port,'tls':tls},{'error':Error,'rate':lambda *a:None})
    except Error as exc:raise SystemExit(str(exc)) from None
    finally:db.close()
    print('SMTP authentication passed. Private mail.json saved. No email was sent.')

if __name__=='__main__':main()
