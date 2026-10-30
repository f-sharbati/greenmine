"""Run against a disposable deployment; creates an isolated test account."""
import argparse, http.cookies, json, secrets, urllib.request, urllib.error
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--origin',required=True);p.add_argument('--csv-dir',type=Path,required=True);p.add_argument('--forecast',action='store_true');a=p.parse_args()
cookie=''
def req(path,data=None,origin=None):
 global cookie
 headers={'Origin':origin or a.origin,'Content-Type':'application/json'}
 if cookie: headers['Cookie']=cookie
 r=urllib.request.Request(a.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
 try:
  with urllib.request.urlopen(r,timeout=65) as x:
   if x.headers.get('Set-Cookie'):
    c=http.cookies.SimpleCookie();c.load(x.headers['Set-Cookie']);cookie='; '.join(k+'='+v.value for k,v in c.items())
   return x.status,json.load(x),x.headers
 except urllib.error.HTTPError as e:return e.code,json.load(e),e.headers
email='smoke-'+secrets.token_hex(8)+'@example.org';pw=secrets.token_urlsafe(24)
assert req('/api/engine',{'action':'overview'})[0]==401
status,data,h=req('/api/auth',{'action':'register','email':email,'password':pw});assert status==200,(status,data)
assert 'HttpOnly' in h['Set-Cookie'] and 'SameSite=lax' in h['Set-Cookie'] and 'token' not in data
if a.origin.startswith('https:'):assert 'Secure' in h['Set-Cookie']
assert req('/api/engine',{'action':'overview'})[1]['readings']==[]
for name in ['202608.CSV','202609.CSV']:
 status,data,_=req('/api/engine',{'action':'import','csv':(a.csv_dir/name).read_text(),'filename':name});assert status==200,(status,data)
assert data['total_kwh']==3930.115 and len(data['readings'])==61
assert req('/api/engine',{'action':'overview'},origin='https://invalid.example')[0]==403
assert req('/api/auth',{'action':'logout'})[0]==200
assert req('/api/engine',{'action':'overview'})[0]==401
assert req('/api/auth',{'action':'login','email':email,'password':pw})[0]==200
assert req('/api/engine',{'action':'overview'})[1]['total_kwh']==3930.115
result={'auth_import_csrf_persistence':'passed','days':61,'total_kwh':3930.115}
if a.forecast:
 status,data,_=req('/api/engine',{'action':'forecast'});assert status==200,(status,data)
 result.update(forecast_status=status,calibration=data.get('calibration'),forecast_kwh=data.get('forecast',{}).get('total_kwh'))
print(json.dumps(result))
