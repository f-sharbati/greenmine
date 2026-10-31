import json
import math
from datetime import date,timedelta
from pathlib import Path
import unittest
from unittest.mock import patch
import bridge
from plant_model import forecast
from pilot_model import PilotCorrection,evidence
from validation import metrics,backtest

class PredictionValidationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.climate=json.loads((Path(__file__).parent/'reference_data'/'tehran_climate.json').read_text())['values']
  cls.data=evidence()
  cls.plant={**bridge.DEFAULT_PLANT,**cls.data['plant'],'forecast_mode':'history_calibrated','calibration_profile':'tehran_kaco_11_4'}
  cls.coords=bridge.plant_coordinates(cls.plant)
  cls.correction=PilotCorrection(cls.climate,bridge.pe)
 def test_source_units_and_correct_capacities(self):
  self.assertEqual(self.plant['capacity_dc'],11.4);self.assertEqual(self.plant['capacity_ac'],15)
  self.assertAlmostEqual(sum(r['kwh'] for r in self.data['azar']),892.209,places=6)
  self.assertAlmostEqual(sum(r['kwh'] for r in self.data['summer'] if r['date'].startswith('2026-08')),2052.741,places=6)
 def test_metrics_zero_days_are_not_dropped(self):
  a={date(2025,1,1):0,date(2025,1,2):10};p={date(2025,1,1):5,date(2025,1,2):5}
  s=metrics(a,p);self.assertEqual(s['absolute_error_pct'],0);self.assertEqual(s['wape_pct'],100);self.assertEqual(s['mae_kwh'],5);self.assertEqual(s['zero_actual_days'],1)
  self.assertIsNone(metrics({date(2025,1,1):0},{date(2025,1,1):1})['absolute_error_pct'])
 def test_calibration_anchors_not_claimed_as_holdout(self):
  for check in self.correction.fit_checks:self.assertAlmostEqual(check['actual_kwh'],check['fitted_kwh'],places=3)
  self.assertEqual(self.correction.fit_checks[1]['role'],'calibration_subset')
  result=backtest(self.plant,self.data['azar'],self.climate,bridge.pe,*self.coords,date(2026,10,31),self.correction)
  self.assertEqual(result['periods'],[])
 def test_september_target_cannot_change_its_prediction(self):
  a=backtest(self.plant,self.data['summer'],self.climate,bridge.pe,*self.coords,date(2026,10,31),self.correction)['latest']
  poisoned=[{**r,'kwh':r['kwh']*10} if r['date']>='2026-09-01' else r for r in self.data['summer']]
  b=backtest(self.plant,poisoned,self.climate,bridge.pe,*self.coords,date(2026,10,31),self.correction)['latest']
  self.assertEqual(a['predicted_kwh'],b['predicted_kwh']);self.assertNotEqual(a['actual_kwh'],b['actual_kwh'])
  self.assertEqual(a['training_end'],'2026-08-31');self.assertEqual(a['training_days'],31)
  self.assertAlmostEqual(a['predicted_kwh'],1907.607,places=3)
  self.assertEqual(a['absolute_error_pct'],1.610);self.assertEqual(a['raw']['absolute_error_pct'],.409)
 def test_partial_or_missing_month_not_scored_as_full(self):
  rows=[r for r in self.data['summer'] if r['date']!='2026-09-10']
  r=backtest(self.plant,rows,self.climate,bridge.pe,*self.coords,date(2026,10,31),self.correction)
  self.assertEqual(r['latest']['start'],'2026-08-01')
 def test_persian_month_has_its_own_exact_dates_and_prior_training(self):
  result=backtest(self.plant,self.data['summer'],self.climate,bridge.pe,*self.coords,date(2026,10,31),self.correction)
  p=next(p for p in result['periods'] if p['calendar']=='persian')
  self.assertEqual(p['start'],'2026-08-23');self.assertEqual(p['end'],'2026-09-22')
  self.assertEqual(p['training_end'],'2026-08-22');self.assertEqual(p['training_days'],22)
  self.assertEqual(p['actual_kwh'],1986.523);self.assertEqual(p['absolute_error_pct'],.879)
 def test_capacity_and_pr_not_cancelled_by_history_refit(self):
  p=self.plant;r=self.data['summer'];args=(date(2026,10,31),self.climate,{},r,bridge.pe,*self.coords)
  base=forecast(p,*args,reference_plant=p)
  double=forecast({**p,'capacity_dc':22.8},*args,reference_plant=p)
  reduced=forecast({**p,'performance_ratio':.6},*args,reference_plant=p)
  self.assertAlmostEqual(double['forecast']['total_kwh']/base['forecast']['total_kwh'],2,places=4)
  self.assertAlmostEqual(reduced['forecast']['total_kwh']/base['forecast']['total_kwh'],.75,places=4)
  self.assertEqual(base['calibration']['factor'],double['calibration']['factor'])
  self.assertTrue(double['calibration']['scenario_changed'])
  self.assertEqual(base['validation'],double['validation'])
 def test_reference_profile_does_not_apply_to_other_sites(self):
  from weather import nasa
  with patch('weather.nasa',return_value=(self.climate,{'source':'test'})),patch('weather.daily_forecast',return_value=({},{})):
   with self.assertRaisesRegex(ValueError,'PLANT_REFERENCE_LOCATION'):
    bridge.main({'action':'forecast','plant':{**self.plant,'latitude':28.,'longitude':50.}})
 def test_unknown_profile_rejected(self):
  with self.assertRaisesRegex(ValueError,'PLANT_INVALID'):bridge.validate_settings({'plant':{**self.plant,'calibration_profile':'unknown'}})
