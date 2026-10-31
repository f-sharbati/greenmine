"""Explicit, opt-in Tehran pilot fit. Never a universal solar coefficient."""
from datetime import date, timedelta
from functools import lru_cache
import json
import math
from pathlib import Path

PROFILE = 'tehran_kaco_11_4'

@lru_cache(maxsize=1)
def evidence():
    return json.loads((Path(__file__).parent/'reference_data'/'tehran_pilot.json').read_text(encoding='utf-8'))

def winter_basis(day):
    # Local winter adjustment, supported only within 60 days of Azar's centre.
    # One winter month does not justify imposing a sinusoid across summer.
    phase=(day-date(day.year,1,1)).days/((date(day.year+1,1,1)-date(day.year,1,1)).days)
    distance=((phase-340/365+.5)%1-.5)*365
    return .5*(1+math.cos(math.pi*distance/60)) if abs(distance)<60 else 0.

class PilotCorrection:
    def __init__(self, irradiance, pe):
        from plant_model import DailyModel
        data=evidence(); plant=data['plant']; year=data['annual']['year']
        start=date(year,1,1); end=date(year+1,1,1)
        days=[start+timedelta(days=i) for i in range((end-start).days)]
        values=DailyModel(plant,{d:pe.climatology_ghi(irradiance,d) for d in days},plant['latitude'],plant['longitude']).energies()
        winter={date.fromisoformat(r['date']) for r in data['azar']}
        # Two measured aggregates, two coefficients. These are fitting data,
        # not two independent validation successes (Azar is inside the year).
        ay=sum(values.values()); by=sum(v*winter_basis(d) for d,v in values.items())
        aw=sum(v for d,v in values.items() if d in winter)
        bw=sum(v*winter_basis(d) for d,v in values.items() if d in winter)
        measured_year=data['annual']['kwh']; measured_winter=sum(r['kwh'] for r in data['azar'])
        det=ay*bw-aw*by
        if abs(det)<1e-9:raise ValueError('PLANT_REFERENCE_REVIEW')
        self.a=(measured_year*bw-measured_winter*by)/det
        self.b=(ay*measured_winter-aw*measured_year)/det
        if not .25<=self.a-abs(self.b)<=self.a+abs(self.b)<=2:raise ValueError('PLANT_REFERENCE_REVIEW')
        self.fit_checks=[dict(period='2025',start='2025-01-01',end='2025-12-31',actual_kwh=measured_year,raw_kwh=round(ay,3),fitted_kwh=round(sum(v*self.factor(d) for d,v in values.items()),3),role='calibration'),dict(period='Azar 1404',start='2025-11-22',end='2025-12-21',actual_kwh=round(measured_winter,3),raw_kwh=round(aw,3),fitted_kwh=round(sum(v*self.factor(d) for d,v in values.items() if d in winter),3),role='calibration_subset')]

    def factor(self, day):return self.a+self.b*winter_basis(day)
    def apply(self, values):return {d:v*self.factor(d) for d,v in values.items()}

def correction_for(plant, irradiance, pe):
    return PilotCorrection(irradiance,pe) if plant.get('calibration_profile')==PROFILE else None
