import unittest
from history_baseline import predict
import bridge
class HistoricalBaselineTests(unittest.TestCase):
    def test_september_is_held_out(self):
        rows=bridge.main({'action':'overview'})['readings']
        result=predict(rows,'2026-09-01',30)
        self.assertAlmostEqual(result['total_kwh'],1986.5235483870968)
        poisoned=[{**r,'kwh':999999} if r['date']>='2026-09-01' else r for r in rows]
        self.assertEqual(result,predict(poisoned,'2026-09-01',30))
    def test_missing_days_are_not_zero_energy(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            predict([{'date':'2026-08-31','kwh':0}],'2026-09-01',30)
