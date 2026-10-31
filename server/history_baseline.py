"""Transparent production-history benchmark; no weather/seasonality accuracy claim."""
from datetime import date, timedelta
from decimal import Decimal

def predict(readings, target_start, target_days, window_days=31):
    target_start = date.fromisoformat(target_start)
    if not 1 <= target_days <= 366 or window_days < 1:
        raise ValueError('Invalid forecast window')
    by_date = {}
    for row in readings:
        day = date.fromisoformat(row['date'])
        if day >= target_start:
            continue  # Prevent target-period leakage.
        energy = Decimal(str(row['kwh']))
        if not energy.is_finite() or energy < 0:
            raise ValueError('Invalid historical energy')
        if day in by_date and by_date[day] != energy:
            raise ValueError('Conflicting historical readings')
        by_date[day] = energy
    if not by_date:
        raise ValueError('No prior readings')
    last = max(by_date)
    start = last - timedelta(days=window_days - 1)
    values = [v for d, v in by_date.items() if start <= d <= last]
    if len(values) < window_days:
        raise ValueError('Incomplete training window')
    return {'model':'historical_daily_mean_v1', 'total_kwh':float(sum(values) / len(values) * target_days),
            'training_start':start.isoformat(), 'training_end':last.isoformat(),
            'training_days':len(values), 'target_start':target_start.isoformat(),
            'target_days':target_days, 'staleness_days':(target_start-last).days-1}
