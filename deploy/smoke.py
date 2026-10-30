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
fresh=req('/api/engine',{'action':'overview'})[1]
assert fresh['readings']==[] and fresh['sources']==[] and fresh['plant']['capacity_dc'] is None and fresh['plant']['latitude'] is None
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
 status,settings,_=req('/api/engine',{'action':'settings','plant':{'name':'Smoke test plant','capacity_dc':14,'location_mode':'gps','latitude':35.756256,'longitude':51.431395},'tariff':25000});assert status==200,(status,settings)
 status,data,_=req('/api/engine',{'action':'forecast'});assert status==200,(status,data)
 result.update(forecast_status=status,calibration=data.get('calibration'),forecast_kwh=data.get('forecast',{}).get('total_kwh'),annual_baseline_kwh=data.get('annual',{}).get('annual_kwh'))
 status,rolling,_=req('/api/engine',{'action':'forecast','horizon':'rolling_30'});assert status==200,(status,rolling)
 assert len(rolling['forecast']['days'])==30 and rolling['forecast']['horizon']=='rolling_30'
 result['rolling_30']={k:rolling['forecast'][k] for k in ['target_start','target_end','total_kwh','api_days','model_days']}
print(json.dumps(result))
