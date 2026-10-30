import unittest,math
from datetime import date
import bridge
from plant_model import DailyModel,forecast
class PlantModelTests(unittest.TestCase):
 def plant(self,**kw):return bridge.validate_settings({'plant':{'capacity_dc':14,**kw}},require_specs=True)[0]
 def test_total_capacity_only_no_panel_or_inverter_inventory(self):
  p=self.plant(capacity_ac=None);self.assertEqual(p['capacity_dc'],14)
  self.assertIsNone(p['capacity_ac']);self.assertNotIn('panel_count',p)
 def test_dc_capacity_changes_model_only_output(self):
  day=date(2026,12,15);i={day:3.0};p=self.plant(forecast_mode='model_only');lat,lon=bridge.plant_coordinates(p)
  a=DailyModel(p,i,lat,lon).energies()[day];b=DailyModel({**p,'capacity_dc':28},i,lat,lon).energies()[day]
  self.assertAlmostEqual(b,2*a,places=8)
 def test_daily_energy_conservation_and_zero(self):
  p=self.plant();days={date(2026,8,1):6.2,date(2026,8,2):0};m=DailyModel(p,days,*bridge.plant_coordinates(p))
  self.assertAlmostEqual(m.ghi_daily[0],6.2,places=8);self.assertEqual(m.energies()[date(2026,8,2)],0)
 def test_winter_tilt_and_location_affect_projection(self):
  day=date(2026,12,15);p=self.plant();coords=bridge.plant_coordinates(p)
  tilted=DailyModel(p,{day:3},*coords).energies()[day];horizontal=DailyModel({**p,'tilt':0},{day:3},*coords).energies()[day]
  self.assertGreater(tilted,horizontal)
  other=DailyModel(p,{day:3},25,51).energies()[day];self.assertNotAlmostEqual(tilted,other,places=2)
 def test_gps_validation_and_missing_capacity(self):
  p=self.plant(location_mode='gps',latitude=35.7,longitude=51.4,utm_easting=None,utm_northing=None,utm_zone='');self.assertEqual(bridge.plant_coordinates(p),(35.7,51.4))
  for bad in [0,-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):self.plant(capacity_dc=bad)
  with self.assertRaisesRegex(ValueError,'PLANT_DC_REQUIRED'):bridge.validate_settings({'plant':bridge.EMPTY_PLANT},require_specs=True)
 def test_mixed_panel_metadata_does_not_add_arbitrary_type_gain(self):
  d=date(2026,9,1);p=self.plant();a=DailyModel(p,{d:6},*bridge.plant_coordinates(p)).energies()
  b=DailyModel({**p,'panel_type':'Bifacial'},{d:6},*bridge.plant_coordinates(p)).energies();self.assertEqual(a,b)
 def test_forecast_mode_and_exact_calendar(self):
  p=self.plant(forecast_mode='model_only');i={m:5. for m in bridge.pe.NASA_MONTH_KEYS}
  r=forecast(p,date(2026,8,22),i,{},[],bridge.pe,*bridge.plant_coordinates(p))
  self.assertEqual(len(r['forecast']['days']),31);self.assertEqual(r['forecast']['days'][0]['gregorian_date'],'2026-08-23');self.assertEqual(r['calibration']['reason'],'MODEL_ONLY')
  self.assertTrue(math.isfinite(r['annual']['annual_kwh']));self.assertAlmostEqual(r['forecast']['total_kwh'],sum(x['production_kwh'] for x in r['forecast']['days']),places=3)

 def test_rolling_30_includes_today_with_correct_dates(self):
  p=self.plant(forecast_mode='model_only');i={m:5. for m in bridge.pe.NASA_MONTH_KEYS};today=date(2026,12,31)
  r=forecast(p,today,i,{today:1.0},[],bridge.pe,*bridge.plant_coordinates(p),horizon='rolling_30')['forecast']
  self.assertEqual(len(r['days']),30);self.assertEqual(r['target_start'],'2026-12-31');self.assertEqual(r['target_end'],'2027-01-29');self.assertEqual(r['api_days'],1)
  d=r['days'][0];self.assertEqual(d['jalali_date'],'/'.join(f'{n:02d}' if j else str(n) for j,n in enumerate(bridge.pe.gregorian_to_jalali(2026,12,31))))
