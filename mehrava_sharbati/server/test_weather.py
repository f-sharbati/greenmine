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
