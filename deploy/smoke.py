"""Readiness/security smoke for the OTP release. Sends no mail and creates no users."""
import argparse,http.cookies,json,urllib.request,urllib.error
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--origin',required=True);p.add_argument('--require-mail',action='store_true');p.add_argument('--auth-mode',choices=['email_otp','password'],default='email_otp');a=p.parse_args();cookie=''
def request(path,data=None,origin=None):
 global cookie
 headers={'Origin':origin or a.origin,'Content-Type':'application/json'}
 if cookie:headers['Cookie']=cookie
 r=urllib.request.Request(a.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
 try:
  with urllib.request.urlopen(r,timeout=60) as response:
   if response.headers.get('Set-Cookie'):
    c=http.cookies.SimpleCookie();c.load(response.headers['Set-Cookie']);cookie='; '.join(k+'='+v.value for k,v in c.items())
   return response.status,json.load(response),response.headers
 except urllib.error.HTTPError as e:return e.code,json.load(e),e.headers
with urllib.request.urlopen(a.base,timeout=30) as response:assert response.status==200
status,context,headers=request('/api/auth?action=context');assert status==200,(status,context)
assert context['auth_mode']==a.auth_mode
assert context['registration_verification']==(a.auth_mode=='email_otp') and context['login_email_otp']==(a.auth_mode=='email_otp')
assert context['password_scheme']=='PBKDF2-HMAC-SHA-256'
assert all(x in headers['Set-Cookie'] for x in ['greenmine_auth_flow=','HttpOnly','SameSite=lax','Secure'])
assert 'greenmine_session=' not in headers['Set-Cookie']
if a.require_mail:assert context['auth_email_available'],'Fresh SMTP has not been configured'
status,captcha,_=request('/api/auth?action=captcha');assert status==200 and captcha['image'].startswith('data:image/png;base64,') and 'answer' not in captcha
assert request('/api/engine',{'action':'overview'})[0]==401
assert request('/api/auth',{'action':'login'},origin='https://invalid.example')[0]==403
print(json.dumps({'auth_mode':context['auth_mode'],'readiness':'passed','https_auth_cookie_flags':'passed','captcha_image':'passed','unauthenticated_engine':'rejected','cross_origin_post':'rejected','smtp_configured':context['auth_email_available'],'emails_sent':0,'users_created':0,'live_otp_delivery':'not_tested_by_this_script'}))
