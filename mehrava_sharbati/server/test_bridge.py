import hashlib
import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import bridge

class BridgeTests(unittest.TestCase):
    def test_original_python_files_unchanged(self):
        entries = json.loads((Path(__file__).parent / 'original-hashes.json').read_text(encoding='utf-8-sig'))
        for entry in entries:
            target = bridge.CODES / Path(entry['Path']).name
            if target.name == 'test_smtp.py':
                # This diagnostic was deliberately sanitized; algorithm files stay unchanged.
                self.assertIn("os.environ['SMTP_PASSWORD']",target.read_text())
                self.assertNotIn('APP_PW',target.read_text())
                continue
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest().upper(), entry['Hash'])

    def test_sample_readings_and_impact(self):
        result = bridge.main({'action':'overview'})
        self.assertEqual(len(result['readings']),61)
        self.assertAlmostEqual(result['total_kwh'],3930.115)
        self.assertEqual(result['impact'],bridge.pe.environmental_impact(result['total_kwh']))
        self.assertEqual(len({r['date'] for r in result['readings']}),61)

    def test_original_cleaner_deduplication_and_wh_conversion(self):
        result = bridge.clean_csv('date,yield\n2026-08-01,68000\n2026-08-01,68000\n2026-08-02,72000\nTotal,140000\n')
        self.assertEqual(result,[{'date':'2026-08-01','kwh':68.0},{'date':'2026-08-02','kwh':72.0}])

    def test_kaco_header_and_day_first_dates(self):
        result = bridge.clean_csv('Inverter type;Serial number\nKACO;test\nDate;E[Wh]\n03/09/2026;64000\n04/09/2026;63000\n')
        self.assertEqual(result[0],{'date':'2026-09-03','kwh':64.0})

    def test_zero_days_and_valid_spikes_are_retained(self):
        rows = bridge.clean_csv('date,yield\n2026-08-01,0\n2026-08-02,100\n2026-08-03,1000')
        self.assertEqual([r['kwh'] for r in rows], [0, .1, 1])

    def test_conflicting_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, 'CSV_CONFLICT'):
            bridge.clean_csv('date,yield\n2026-08-01,100\n2026-08-01,200')

    def test_nonfinite_and_negative_values_rejected(self):
        for value in ('NaN', 'Infinity', '-1'):
            with self.assertRaisesRegex(ValueError, 'CSV_VALUE'):
                bridge.clean_csv('date,yield\n2026-08-01,' + value)

    def test_explicit_kwh_report_can_be_reimported(self):
        self.assertEqual(bridge.clean_csv('date,kwh\n2026-08-01,68.095'),
                         [{'date':'2026-08-01','kwh':68.095}])

    def test_invalid_csv(self):
        with self.assertRaises(ValueError):
            bridge.clean_csv('not,a,reading\n1,2,3')

    def test_forecast_uses_original_outputs(self):
        irradiance={month:5.0 for month in bridge.pe.NASA_MONTH_KEYS}
        with patch('weather.nasa',return_value=(irradiance,{'source':'test','fetched_at':0,'stale':False})), patch('weather.daily_forecast',return_value=({}, {'source':'test'})):
            result=bridge.main({'action':'forecast','plant':bridge.DEFAULT_PLANT,'tariff':25000})
        f=result['forecast']
        self.assertAlmostEqual(f['total_kwh'],sum(row['production_kwh'] for row in f['days']))
        self.assertEqual(f['api_days'],0)
        self.assertEqual(f['model_days'],len(f['days']))
        self.assertEqual(result['impact'],bridge.pe.environmental_impact(f['total_kwh']))
        self.assertEqual(result['revenue'],bridge.pe.revenue(f['total_kwh'],25000))
        self.assertEqual(result['annual'],bridge.pe.monthly_production(bridge.DEFAULT_PLANT,irradiance))

    def test_validation_precedes_network_request(self):
        with patch.object(bridge.pe,'fetch_nasa_irradiance') as fetch:
            with self.assertRaises(ValueError):
                bridge.main({'action':'forecast','plant':{'performance_ratio':2}})
            fetch.assert_not_called()

    def test_jalali_year_rollover_preserved(self):
        self.assertEqual(bridge.pe.next_jalali_month(1405,12),(1406,1))
        day=date(2026,10,30)
        self.assertEqual(bridge.pe.jalali_to_gregorian(*bridge.pe.gregorian_to_jalali(day.year,day.month,day.day)),(2026,10,30))

if __name__=='__main__':
    unittest.main()
