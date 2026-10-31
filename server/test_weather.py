import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import bridge, weather
class WeatherTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'GREENMINE_DATA_DIR':self.tmp.name});self.env.start();self.values={m:5.0 for m in bridge.pe.NASA_MONTH_KEYS}
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def test_cache_reuses_only_matching_location(self):
  with patch.object(bridge.pe,'fetch_nasa_irradiance',return_value=self.values) as fetch:
   first,meta=weather.nasa(bridge.pe,35,51);second,other=weather.nasa(bridge.pe,35,51)
   self.assertEqual(first,second);self.assertEqual(meta['source'],'live');self.assertEqual(other['source'],'cache');self.assertEqual(fetch.call_count,1)
   weather.nasa(bridge.pe,36,51);self.assertEqual(fetch.call_count,2)
   self.assertEqual(fetch.call_args.kwargs['timeout'],(3,8))
 def test_failure_without_cache_is_explicit(self):
  with patch.object(bridge.pe,'fetch_nasa_irradiance',side_effect=TimeoutError):
   with self.assertRaisesRegex(ValueError,'WEATHER_UNAVAILABLE'):weather.nasa(bridge.pe,35,51)
 def test_old_cache_fallback_discloses_age(self):
  with patch.object(bridge.pe,'fetch_nasa_irradiance',return_value=self.values):weather.nasa(bridge.pe,35,51)
  path=next((Path(self.tmp.name)/'climate').glob('*.json'));payload=json.loads(path.read_text());payload['fetched_at']-=31*86400;path.write_text(json.dumps(payload))
  with patch.object(bridge.pe,'fetch_nasa_irradiance',side_effect=TimeoutError):
   _,meta=weather.nasa(bridge.pe,35,51);self.assertTrue(meta['stale']);self.assertEqual(meta['source'],'cache')
   payload['fetched_at']-=366*86400;path.write_text(json.dumps(payload))
   with self.assertRaisesRegex(ValueError,'WEATHER_UNAVAILABLE'):weather.nasa(bridge.pe,35,51)
 def test_nonfinite_provider_values_are_rejected(self):
  with patch.object(bridge.pe,'fetch_nasa_irradiance',return_value={m:float('nan') for m in bridge.pe.NASA_MONTH_KEYS}):
   with self.assertRaisesRegex(ValueError,'WEATHER_UNAVAILABLE'):weather.nasa(bridge.pe,35,51)

class ForecastTransportTests(unittest.TestCase):
 def test_forecast_days_request_and_date_filter(self):
  import weather
  from datetime import date
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GREENMINE_DATA_DIR':tmp}):
   response=SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'daily':{'time':['2026-10-31','2026-11-01','2026-11-02'],'shortwave_radiation_sum':[3.6,7.2,None]}})
   with patch('requests.get',return_value=response) as get:
    result,meta=weather.daily_forecast(bridge.pe,35,51,date(2026,10,31),date(2026,11,1))
    self.assertEqual(result,{date(2026,10,31):1,date(2026,11,1):2});self.assertEqual(meta['source'],'live')
    params=get.call_args.kwargs['params'];self.assertEqual(params['forecast_days'],16);self.assertNotIn('end_date',params);self.assertNotIn('start_date',params)
   with patch('requests.get',side_effect=AssertionError('cache should prevent request')):
    cached,meta=weather.daily_forecast(bridge.pe,35,51,date(2026,10,31),date(2026,11,1));self.assertEqual(cached,result);self.assertEqual(meta['source'],'cache')
 def test_outside_horizon_does_not_request_weather(self):
  import weather
  from datetime import date
  with patch('requests.get') as get:
   result,meta=weather.daily_forecast(bridge.pe,35,51,date(2026,11,22),date(2026,11,15));self.assertEqual(result,{});self.assertEqual(meta['source'],'outside_horizon');get.assert_not_called()
