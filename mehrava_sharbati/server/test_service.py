import os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import bridge,service
from calibration import calibrate
class AccountsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name});self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def register(self,email):return service.main({'op':'register','data':{'email':email,'password':'test-password-12345'},'client':email})
 def engine(self,t,**data):return service.main({'op':'engine','token':t,'data':data})
 def test_isolation_persistence_logout(self):
  a=self.register('a@example.org');b=self.register('b@example.org')
  self.engine(a['token'],action='import',csv='date,kwh\n2026-08-01,68.1')
  self.assertEqual(self.engine(a['token'],action='overview')['total_kwh'],68.1)
  self.assertEqual(self.engine(b['token'],action='overview')['readings'],[])
  again=service.main({'op':'login','data':{'email':'A@EXAMPLE.ORG','password':'test-password-12345'}})
  self.assertEqual(self.engine(again['token'],action='overview')['total_kwh'],68.1)
  service.main({'op':'logout','token':a['token']})
  with self.assertRaises(service.ServiceError):self.engine(a['token'],action='overview')
 def test_password_and_token_storage(self):
  a=self.register('a@example.org');db=service.connect()
  user=db.execute('SELECT salt,password_hash FROM users').fetchone();token=db.execute('SELECT token_hash FROM sessions').fetchone()[0];db.close()
  self.assertNotIn('test-password-12345',user);self.assertNotEqual(token,a['token'])
 def test_expiry(self):
  a=self.register('a@example.org');db=service.connect()
  with db:db.execute('UPDATE sessions SET expires_at=0')
  db.close()
  with self.assertRaises(service.ServiceError):self.engine(a['token'],action='overview')
 def test_conflict_atomicity(self):
  a=self.register('a@example.org');self.engine(a['token'],action='import',csv='date,kwh\n2026-08-01,20')
  with self.assertRaisesRegex(service.ServiceError,'CSV_CONFLICT'):self.engine(a['token'],action='import',csv='date,kwh\n2026-08-01,30\n2026-08-02,50')
  self.assertEqual(self.engine(a['token'],action='overview')['total_kwh'],20)
 def test_concurrent_replay(self):
  a=self.register('a@example.org')
  def load(_):return self.engine(a['token'],action='import',csv='date,kwh\n2026-08-01,20')['total_kwh']
  with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(list(pool.map(load,range(2))),[20,20])
  db=service.connect();self.assertEqual(db.execute('SELECT count(*) FROM imports').fetchone()[0],1);db.close()
 def test_rate_limit(self):
  self.register('a@example.org')
  for _ in range(9):
   with self.assertRaises(service.ServiceError):service.main({'op':'login','data':{'email':'a@example.org','password':'incorrect-password'}})
  with self.assertRaisesRegex(service.ServiceError,'RATE_LIMITED'):service.main({'op':'login','data':{'email':'a@example.org','password':'test-password-12345'}})
 def test_no_session(self):
  for action in ['overview','import','forecast','settings']:
   with self.assertRaisesRegex(service.ServiceError,'UNAUTHENTICATED'):self.engine('',action=action)
 def test_settings(self):
  a=self.register('a@example.org');self.engine(a['token'],action='settings',plant={**bridge.DEFAULT_PLANT,'name':'My plant'},tariff=500)
  self.assertEqual(self.engine(a['token'],action='overview')['plant']['name'],'My plant')
  with self.assertRaises(ValueError):self.engine(a['token'],action='settings',plant={'utm_zone':'39INVALID'})
 def test_inverter(self):
  a=self.register('a@example.org')
  for serial,ok in [('one',True),('two',False)]:
   csv=f'Inverter type;Serial number\nKACO;{serial}\nDate;E[Wh]\n01/08/2026;100'
   if ok:self.engine(a['token'],action='import',csv=csv)
   else:
    with self.assertRaisesRegex(service.ServiceError,'INVERTER_MISMATCH'):self.engine(a['token'],action='import',csv=csv)
class CalibrationTests(unittest.TestCase):
 def test_history_fit_and_leakage(self):
  i={m:5. for m in bridge.pe.NASA_MONTH_KEYS};p=bridge.DEFAULT_PLANT;rows=bridge.main({'action':'overview'})['readings']
  f=calibrate(rows,p,i,date(2026,10,1),bridge.pe);self.assertTrue(f['applied'])
  self.assertEqual(f,calibrate(rows+[{'date':'2026-10-01','kwh':9999999}],p,i,date(2026,10,1),bridge.pe))
  with patch.object(bridge.pe,'fetch_nasa_irradiance',return_value=i),patch.object(bridge.pe,'fetch_openmeteo_daily',return_value={}):
   result=bridge.main({'action':'forecast','readings':rows})
  self.assertTrue(result['calibration']['applied']);self.assertNotEqual(result['uncalibrated_kwh'],result['forecast']['total_kwh'])
  self.assertAlmostEqual(result['forecast']['total_kwh'],sum(r['production_kwh'] for r in result['forecast']['days']))
 def test_sparse_stale_zero(self):
  p=bridge.DEFAULT_PLANT;i={m:5. for m in bridge.pe.NASA_MONTH_KEYS};rows=bridge.main({'action':'overview'})['readings']
  self.assertEqual(calibrate(rows,p,i,date(2026,12,1),bridge.pe)['reason'],'STALE_HISTORY')
  self.assertFalse(calibrate(rows[:5],p,i,date(2026,10,1),bridge.pe)['applied'])
  self.assertFalse(calibrate([{**r,'kwh':0} for r in rows],p,i,date(2026,10,1),bridge.pe)['applied'])
