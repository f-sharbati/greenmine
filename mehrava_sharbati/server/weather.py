"""Location-keyed public climate cache with explicit age and bounded requests."""
import hashlib, json, math, os, tempfile, time
from pathlib import Path
TTL=30*86400
MAX_STALE=365*86400

def nasa(pe,lat,lon):
 root=Path(os.environ.get('GREENMINE_DATA_DIR',str(Path(__file__).parent.parent/'.local')))/'climate';root.mkdir(parents=True,exist_ok=True,mode=0o700)
 key=hashlib.sha256(f'{lat:.4f},{lon:.4f}'.encode()).hexdigest();path=root/(key+'.json');cached=None
 def valid(values):
  return isinstance(values,dict) and all(isinstance(values.get(m),(int,float)) and math.isfinite(values[m]) and 0<=values[m]<=15 for m in pe.NASA_MONTH_KEYS)
 try:
  candidate=json.loads(path.read_text());age=time.time()-candidate['fetched_at']
  if 0<=age<=MAX_STALE and valid(candidate['values']):cached=candidate
 except (OSError,ValueError,KeyError,TypeError):pass
 if cached and time.time()-cached['fetched_at']<TTL:return cached['values'],dict(source='cache',fetched_at=cached['fetched_at'],stale=False)
 try:
  values=pe.fetch_nasa_irradiance(lat,lon,timeout=(3,8))
  if not valid(values):raise ValueError('NASA_INVALID')
  payload={'values':values,'fetched_at':time.time()}
  fd,name=tempfile.mkstemp(dir=root,prefix='cache-',suffix='.tmp')
  try:
   with os.fdopen(fd,'w') as f:json.dump(payload,f,allow_nan=False)
   os.replace(name,path)
  finally:
   if os.path.exists(name):os.unlink(name)
  return values,dict(source='live',fetched_at=payload['fetched_at'],stale=False)
 except Exception:
  if cached:return cached['values'],dict(source='cache',fetched_at=cached['fetched_at'],stale=True)
  raise ValueError('WEATHER_UNAVAILABLE') from None

def daily_forecast(pe,lat,lon,start,end):
 """Use forecast_days=16; explicit end_date can reject otherwise available dates."""
 if start>end:return {},{'source':'outside_horizon'}
 from datetime import date,datetime,timezone,timedelta
 import requests
 today=datetime.now(timezone(timedelta(hours=3,minutes=30))).date().isoformat()
 root=Path(os.environ.get('GREENMINE_DATA_DIR',str(Path(__file__).parent.parent/'.local')))/'climate';root.mkdir(parents=True,exist_ok=True,mode=0o700)
 cache=root/('forecast-'+hashlib.sha256(f'{lat:.4f},{lon:.4f},{today}'.encode()).hexdigest()+'.json')
 def select(payload):
  result={}
  for k,v in payload['days'].items():
   d=date.fromisoformat(k)
   if start<=d<=end and isinstance(v,(int,float)) and math.isfinite(v) and v>=0:result[d]=v
  return result
 try:
  payload=json.loads(cache.read_text())
  if 0<=time.time()-payload['fetched_at']<3600:return select(payload),dict(source='cache',fetched_at=payload['fetched_at'])
 except (OSError,ValueError,KeyError,TypeError):pass
 try:
  response=requests.get(pe.OPEN_METEO_URL,params={'latitude':round(lat,4),'longitude':round(lon,4),'daily':'shortwave_radiation_sum','timezone':'Asia/Tehran','forecast_days':16},timeout=(3,6))
  response.raise_for_status();daily=response.json().get('daily',{})
  days={d:float(v)/3.6 for d,v in zip(daily.get('time',[]),daily.get('shortwave_radiation_sum',[])) if v is not None and math.isfinite(float(v)) and float(v)>=0}
  if not days:raise ValueError('WEATHER_UNAVAILABLE')
  payload={'fetched_at':time.time(),'days':days};fd,name=tempfile.mkstemp(dir=root,prefix='forecast-',suffix='.tmp')
  try:
   with os.fdopen(fd,'w') as f:json.dump(payload,f,allow_nan=False)
   os.replace(name,cache)
  finally:
   if os.path.exists(name):os.unlink(name)
  return select(payload),dict(source='live',fetched_at=payload['fetched_at'])
 except Exception:return {},dict(source='unavailable')
