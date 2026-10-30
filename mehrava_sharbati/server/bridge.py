"""JSON adapter calling the original prediction and CSV-cleaning algorithms."""
import ast
import io
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone, timedelta

ROOT = Path(os.environ.get('GREENMINE_PYTHON_ROOT', str(Path(__file__).resolve().parents[2] / 'python project')))
CODES = ROOT / 'codes' if (ROOT / 'codes').is_dir() else ROOT.parent
sys.path.insert(0, str(CODES))
import prediction_engine as pe

DEFAULT_PLANT = dict(name='Tehran rooftop', capacity_ac=14, utm_easting=539000,
    utm_northing=3957000, utm_zone='39S', tilt=30, azimuth=180,
    performance_ratio=0.8, panel_type='Monocrystalline', mount_type='Fixed')

def clean_csv(text):
    """Parse daily energy explicitly; retain zeros and reject conflicting readings."""
    import csv
    from decimal import Decimal, InvalidOperation
    lines = text.lstrip('\ufeff').splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().lower().startswith(('date;', 'date,'))), None)
    if start is None:
        raise ValueError('CSV_HEADER')
    delimiter = ';' if ';' in lines[start] else ','
    reader = csv.DictReader(lines[start:], delimiter=delimiter)
    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
    energy_key = next((k for k in ('e[wh]', 'yield', 'kwh', 'energy (kwh)') if k in reader.fieldnames), None)
    if energy_key is None:
        raise ValueError('CSV_HEADER')
    result = {}
    for row in reader:
        raw_date = (row.get('date') or '').strip()
        if raw_date.lower() in ('', 'total', 'summary'):
            continue
        try:
            fmt = '%d/%m/%Y' if energy_key == 'e[wh]' else ('%Y-%m-%d' if '-' in raw_date else '%m/%d/%Y')
            day = datetime.strptime(raw_date, fmt).date().isoformat()
            value = Decimal((row.get(energy_key) or '').strip().replace(',', ''))
            if not value.is_finite() or value < 0:
                raise ValueError('CSV_VALUE')
            kwh = value if energy_key in ('kwh', 'energy (kwh)') else value / 1000
        except (ValueError, InvalidOperation):
            raise ValueError('CSV_VALUE') from None
        if day in result and result[day] != kwh:
            raise ValueError('CSV_CONFLICT')
        result[day] = kwh
    if not result:
        raise ValueError('CSV_EMPTY')
    return [{'date': day, 'kwh': float(value)} for day, value in sorted(result.items())]


def summary(rows):
    total = round(sum(r['kwh'] for r in rows), 3)
    return dict(readings=rows, total_kwh=total, impact=pe.environmental_impact(total))

def validate_settings(data):
    plant = {**DEFAULT_PLANT, **data.get('plant', {})}
    bounds = {'capacity_ac': (0.01, 1000000), 'performance_ratio': (0.01, 1),
        'tilt': (0, 90), 'azimuth': (0, 360), 'utm_easting': (100000, 900000), 'utm_northing': (0, 10000000)}
    for key, (minimum, maximum) in bounds.items():
        value = float(plant[key])
        if not minimum <= value <= maximum:
            raise ValueError('PLANT_INVALID')
        plant[key] = value
    import re
    if not re.fullmatch(r'(?:[1-9]|[1-5][0-9]|60)[C-HJ-NP-X]', str(plant['utm_zone'])):
        raise ValueError('PLANT_INVALID')
    pe._parse_zone(plant['utm_zone'])
    if plant['panel_type'] not in pe.PANEL_FACTORS or plant['mount_type'] not in pe.MOUNT_FACTORS:
        raise ValueError('PLANT_INVALID')
    tariff = float(data.get('tariff', 25000))
    if not 0 <= tariff <= 1000000000:
        raise ValueError('TARIFF_INVALID')
    return plant, tariff

def main(data):
    action = data.get('action', 'overview')
    if action == 'overview':
        rows = {}
        for filename in ['202608.CSV', '202609.CSV']:
            for row in clean_csv((ROOT / filename).read_text(encoding='utf-8-sig')):
                rows.setdefault(row['date'], row)
        return dict(**summary(sorted(rows.values(), key=lambda r: r['date'])), plant=DEFAULT_PLANT,
                    source='202608.CSV + 202609.CSV', sample=True)
    if action == 'import':
        return summary(clean_csv(data['csv']))
    if action != 'forecast':
        raise ValueError('ACTION_INVALID')
    plant, tariff = validate_settings(data)
    today = datetime.now(timezone(timedelta(hours=3, minutes=30))).date()
    lat, lon = pe.utm_to_latlon(plant['utm_easting'], plant['utm_northing'], plant['utm_zone'])
    irradiance = pe.fetch_nasa_irradiance(lat, lon)
    forecast = pe.next_month_forecast(plant, today=today, irradiance=irradiance)
    from calibration import calibrate
    calibration = calibrate(data.get('readings', []), plant, irradiance, today, pe)
    uncalibrated_kwh = forecast['total_kwh']
    if calibration['applied']:
        for row in forecast['days']:
            row['production_kwh'] = round(row['production_kwh'] * calibration['factor'], 3)
        forecast['first_half_kwh'] = sum(r['production_kwh'] for r in forecast['days'] if r['day'] <= 15)
        forecast['second_half_kwh'] = sum(r['production_kwh'] for r in forecast['days'] if r['day'] > 15)
        forecast['total_kwh'] = round(sum(r['production_kwh'] for r in forecast['days']), 3)
    return dict(calibration=calibration, uncalibrated_kwh=uncalibrated_kwh, forecast=forecast, annual=pe.monthly_production(plant, irradiance=irradiance),
        impact=pe.environmental_impact(forecast['total_kwh']), revenue=pe.revenue(forecast['total_kwh'], tariff),
        tariff=tariff, plant=plant)

if __name__ == '__main__':
    try:
        print(json.dumps(main(json.load(sys.stdin)), ensure_ascii=True, allow_nan=False))
    except Exception as exc:
        code = str(exc) if str(exc) in {'CSV_HEADER','CSV_EMPTY','PLANT_INVALID','TARIFF_INVALID','ACTION_INVALID','CSV_VALUE','CSV_CONFLICT'} else 'ENGINE_UNAVAILABLE'
        print(json.dumps({'error': code}))
        sys.exit(1)
