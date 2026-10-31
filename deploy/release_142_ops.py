"""Version 1.4.2 operator rollout; retains the existing volume and private mail files."""
import argparse,hashlib,importlib.util,json,os,shutil,sqlite3,subprocess,time,urllib.request,urllib.error
from pathlib import Path
os.umask(0o077)
IMAGE='greenmine:1.4.2'
BASE='greenmine:auth-password-20261031'
APK_SHA='6daebcf0760985678cbd32de7465a431dc25f6914162a4c644f192ce1cbb9758'
COMMON='/opt/greenmine/ops/auth-20261031/release-ops.py'
def run(*a):return subprocess.check_output(a,text=True,stderr=subprocess.PIPE).strip()
def inspect(n):return json.loads(run('docker','inspect',n))[0]
def common():
 s=importlib.util.spec_from_file_location('previous_release_operations',COMMON);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def smtp():
 code="""import sys,smtplib,ssl\nsys.path.insert(0,'/app/server')\nfrom mail_settings import config\nc=config();assert c.get('SMTP_TLS')=='starttls'\nwith smtplib.SMTP(c['SMTP_HOST'],int(c['SMTP_PORT']),timeout=12) as s:\n s.ehlo();s.starttls(context=ssl.create_default_context());s.ehlo();s.login(c['SMTP_USER'],c['SMTP_PASSWORD'])\nprint('SMTP_AUTH_PASSED_NO_EMAIL_SENT')\n"""
 p=subprocess.run(['docker','exec','-i','greenmine-app','/opt/venv/bin/python','-'],input=code,text=True,capture_output=True)
 if p.returncode:raise RuntimeError('SMTP_PREFLIGHT_FAILED')
def request(base,path,data=None,origin='https://greenmineapp.ir'):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Origin':origin,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=30) as r:return r.status,r.read(),r.headers
 except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
def smoke(base):
 for path in ['/','/download']:
  st,body,_=request(base,path);assert st==200,path
  if path=='/download':assert b'/downloads/GreenMine-1.4.2.apk' in body
 st,body,h=request(base,'/api/auth?action=context');p=json.loads(body)
 assert st==200 and p['auth_email_available'] and p['registration_verification'] and p['login_email_otp']
 assert all(v in h.get('Set-Cookie','') for v in ['HttpOnly','Secure','SameSite=lax'])
 assert request(base,'/api/engine',{'action':'overview'})[0]==401
 assert request(base,'/api/auth',{'action':'login'},'https://invalid.example')[0]==403
 st,body,_=request(base,'/downloads/GreenMine-1.4.2.apk');assert st==200 and hashlib.sha256(body).hexdigest()==APK_SHA
 return {'readiness':'passed','landing_download':True,'apk_sha256':APK_SHA,'otp_flags':True,'smtp_configured':True,'unauthenticated_engine_rejected':True,'cross_origin_rejected':True}
def preserve(folder):
 m=common();assert m.same_business_data(folder/'accounts-frozen.sqlite3'),'BUSINESS_DATA_CHANGED'
def promote(image_id):
 assert inspect(IMAGE)['Id']==image_id,'IMAGE_ID_MISMATCH'
 current=inspect('greenmine-app');assert current['Config']['Image']==BASE,'CURRENT_RELEASE_CHANGED'
 smtp();m=common();folder=m.backup();old='greenmine-app-pre-142-'+str(int(time.time()))
 env=dict(x.split('=',1) for x in current['Config']['Env']);env['GREENMINE_AUTH_MODE']='email_otp'
 assert all('\n' not in v for v in env.values())
 private=folder/'runtime-private.env';private.write_text(''.join(k+'='+v+'\n' for k,v in env.items()));os.chmod(private,0o600)
 (folder/'promotion-142.json').write_text(json.dumps({'previous_container':old,'image_id':image_id}))
 run('docker','stop','greenmine-app')
 try:m.dbcopy(folder/'accounts-frozen.sqlite3');run('docker','rename','greenmine-app',old)
 except Exception:run('docker','start','greenmine-app');raise
 try:
  run('docker','run','-d','--name','greenmine-app','--restart','unless-stopped','--cap-drop','ALL','--security-opt','no-new-privileges:true','--log-opt','max-size=10m','--log-opt','max-file=3','--env-file',str(private),'-v','greenmine_accounts:/data','-p','127.0.0.1:3001:3000',IMAGE)
  ready=False
  for _ in range(40):
   try:
    if request('http://127.0.0.1:3001','/')[0]==200:ready=True;break
   except Exception:pass
   time.sleep(1)
  assert ready,'START_FAILED'
  result=smoke('http://127.0.0.1:3001');preserve(folder)
 except Exception:
  # Never restore a stale DB. Refuse binary rollback if account/business writes occurred.
  if m.same_business_data(folder/'accounts-frozen.sqlite3'):
   run('docker','stop','greenmine-app')
   if not m.same_business_data(folder/'accounts-frozen.sqlite3'):
    run('docker','start','greenmine-app');raise RuntimeError('FORWARD_FIX_REQUIRED_CONCURRENT_WRITES')
   run('docker','rename','greenmine-app','greenmine-app-142-failed-'+str(int(time.time())))
   run('docker','rename',old,'greenmine-app');run('docker','start','greenmine-app')
  raise
 result.update(version='1.4.2',image_id=image_id,backup=str(folder),previous_container=old,data_preservation='all baseline business rows and hashes unchanged',public_acceptance='pending')
 Path('/opt/greenmine/releases/1.4.2/promotion-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--promote',action='store_true');p.add_argument('--image-id');p.add_argument('--smoke');a=p.parse_args()
 try:
  if a.promote:
   assert a.image_id and a.image_id.startswith('sha256:');promote(a.image_id)
  elif a.smoke:print(json.dumps(smoke(a.smoke)))
 except Exception as e:
  # Do not expose subprocess environments, SMTP responses or private config.
  print(json.dumps({'status':'failed','type':type(e).__name__,'reason':str(e) if isinstance(e,(AssertionError,RuntimeError)) else 'Inspect private server logs'}));raise SystemExit(1)
