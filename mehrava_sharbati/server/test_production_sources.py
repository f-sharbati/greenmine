import json,os,sqlite3,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import bridge,service
class ProductionSourcesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name});self.env.start()
  self.session=service.main({'op':'register','data':{'email':'site@example.org','password':'sample-password-12345'},'client':'test'})
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def engine(self,**data):return service.main({'op':'engine','token':self.session['token'],'data':data})
 def upload(self,serial,body):return self.engine(action='import',csv=f'Brand;Serial number\nAny brand;{serial}\nDate;E[Wh]\n'+body)
 def test_new_user_empty(self):
  s=self.engine(action='overview');self.assertEqual(s['readings'],[]);self.assertEqual(s['sources'],[])
  self.assertIsNone(s['plant']['capacity_dc']);self.assertIsNone(s['plant']['latitude']);self.assertEqual(s['plant']['name'],'')
  with self.assertRaisesRegex(service.ServiceError,'CSV_REQUIRED'):self.engine(action='forecast')
 def test_multi_source_sum_replay_and_partial_coverage(self):
  self.upload('A','01/08/2026;1000\n02/08/2026;2000')
  s=self.upload('B','01/08/2026;3000')
  self.assertEqual(s['total_kwh'],6);self.assertEqual([r['kwh'] for r in s['readings']],[4,2])
  self.assertEqual([r['complete'] for r in s['readings']],[True,False]);self.assertEqual(s['data_quality'],{'complete_days':1,'partial_days':1})
  self.upload('B','01/08/2026;3000');self.assertEqual(self.engine(action='overview')['total_kwh'],6)
 def test_different_brands_can_share_a_serial(self):
  for brand in ['Brand A','Brand B']:
   self.engine(action='import',csv=f'Brand;Serial number\n{brand};123\nDate;E[Wh]\n01/08/2026;1000')
  s=self.engine(action='overview');self.assertEqual(s['total_kwh'],2);self.assertEqual(len(s['sources']),2)
 def test_conflict_rolls_back_whole_file(self):
  self.upload('A','02/08/2026;2000')
  with self.assertRaisesRegex(service.ServiceError,'CSV_CONFLICT'):self.upload('A','01/08/2026;1000\n02/08/2026;3000')
  s=self.engine(action='overview');self.assertEqual(s['total_kwh'],2);self.assertEqual(len(s['readings']),1)
 def test_manual_source_required_and_identical_raw_files_can_be_two_devices(self):
  raw='date,kwh\n2026-08-01,2'
  with self.assertRaisesRegex(service.ServiceError,'CSV_SOURCE_REQUIRED'):self.engine(action='import',csv=raw)
  for name in ['Roof 1','Roof 2']:s=self.engine(action='import',csv=raw,source_name=name)
  self.assertEqual(s['total_kwh'],4);self.assertEqual(len(s['sources']),2)
  db=service.connect();self.assertEqual(db.execute('SELECT count(*) FROM imports').fetchone()[0],1);self.assertEqual(db.execute('SELECT count(*) FROM import_sources').fetchone()[0],2);db.close()
 def test_other_account_source_is_not_selectable(self):
  other=service.main({'op':'register','data':{'email':'other@example.org','password':'sample-password-12345'},'client':'test2'})
  self.upload('A','01/08/2026;1000')
  with self.assertRaisesRegex(service.ServiceError,'CSV_SOURCE_INVALID'):service.main({'op':'engine','token':other['token'],'data':{'action':'import','csv':'date,kwh\n2026-08-01,3','source_id':'serial:A'}})
 def test_combined_export_reimport_does_not_double_count(self):
  self.upload('A','01/08/2026;1000');self.upload('B','01/08/2026;2000')
  self.engine(action='import',csv='Date,Energy (kWh),Scope\n2026-08-01,3,plant_total')
  self.assertEqual(self.engine(action='overview')['total_kwh'],3)
  with self.assertRaisesRegex(service.ServiceError,'CSV_TOTAL_REPORT'):self.engine(action='import',csv='Date,Energy (kWh),Scope\n2026-08-01,6,plant_total')
 def test_only_complete_source_days_reach_calibration(self):
  self.upload('A','01/08/2026;1000\n02/08/2026;2000');self.upload('B','01/08/2026;3000')
  with patch.object(bridge,'main',return_value={}) as model:self.engine(action='forecast')
  passed=model.call_args.args[0]['readings'];self.assertEqual([r['date'] for r in passed],['2026-08-01'])
 def test_concurrent_device_imports_preserve_both_sources(self):
  with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda serial:self.upload(serial,'01/08/2026;1000'),['A','B']))
  self.assertEqual(self.engine(action='overview')['total_kwh'],2)
 def test_legacy_migration_is_additive_and_repeatable(self):
  db=service.connect();uid=self.session['user']['id'];token_hash=service.digest(self.session['token'])
  with db:
   db.execute('DELETE FROM schema_meta');db.execute('UPDATE workspaces SET serial=?,readings=? WHERE user_id=?',('legacy-serial',json.dumps([{'date':'2026-08-01','kwh':5}]),uid))
  before=tuple(db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone());db.close()
  for _ in range(2):
   d=service.connect();self.assertEqual(tuple(d.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()),before);self.assertIsNotNone(d.execute('SELECT 1 FROM sessions WHERE token_hash=?',(token_hash,)).fetchone());self.assertEqual(d.execute('SELECT count(*) FROM production_readings').fetchone()[0],1);d.close()
  self.assertEqual(self.engine(action='overview')['total_kwh'],5)
