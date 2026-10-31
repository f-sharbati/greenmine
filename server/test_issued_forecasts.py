import json,sqlite3,unittest
from issued_forecasts import record_and_score

class IssuedForecastTests(unittest.TestCase):
 def test_original_values_scored_and_other_accounts_hidden(self):
  db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
  db.execute('CREATE TABLE forecast_runs(id INTEGER PRIMARY KEY,user_id INTEGER,issued_at TEXT,days TEXT)')
  old=[{'gregorian_date':'2025-01-01','production_kwh':12}]
  db.execute('INSERT INTO forecast_runs VALUES (1,1,?,?)',('2024-12-15',json.dumps(old)))
  db.execute('INSERT INTO forecast_runs VALUES (2,2,?,?)',('2024-12-15',json.dumps(old)))
  future={'forecast':{'days':[{'gregorian_date':'2099-01-01','production_kwh':99}]}}
  scores=record_and_score(db,1,future,[{'date':'2025-01-01','kwh':10}])
  self.assertEqual(len(scores),2);self.assertEqual(scores[0]['status'],'pending');self.assertIsNone(scores[0]['score'])
  self.assertEqual(scores[1]['score']['predicted_kwh'],12);self.assertEqual(scores[1]['score']['absolute_error_pct'],20)
  db.close()
 def test_scenario_never_presented_as_measured_forecast_accuracy(self):
  db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
  db.execute('CREATE TABLE forecast_runs(id INTEGER PRIMARY KEY,user_id INTEGER,issued_at TEXT,days TEXT)')
  result={'calibration':{'scenario_changed':True},'forecast':{'days':[{'gregorian_date':'2025-01-01','production_kwh':12}]}}
  scores=record_and_score(db,1,result,[{'date':'2025-01-01','kwh':10}])
  self.assertEqual(scores[0]['status'],'scenario');self.assertIsNone(scores[0]['score']);db.close()
