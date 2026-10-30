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
