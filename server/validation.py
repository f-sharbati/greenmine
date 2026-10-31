"""Chronological hindcast scoring. Target readings never enter the training fit."""
import calendar
from datetime import date, timedelta
import math

def metrics(actual, predicted):
    if set(actual)!=set(predicted) or not actual:raise ValueError('CSV_VALIDATION_RANGE')
    errors=[predicted[d]-actual[d] for d in sorted(actual)]
    total=sum(actual.values()); estimate=sum(predicted.values())
    positive=[d for d in actual if actual[d]>0]
    return dict(actual_kwh=round(total,3),predicted_kwh=round(estimate,3),difference_kwh=round(estimate-total,3),
        bias_pct=round((estimate-total)/total*100,3) if total else None,
        absolute_error_pct=round(abs(estimate-total)/total*100,3) if total else None,
        mae_kwh=round(sum(abs(e) for e in errors)/len(errors),3),
        rmse_kwh=round(math.sqrt(sum(e*e for e in errors)/len(errors)),3),
        wape_pct=round(sum(abs(e) for e in errors)/total*100,3) if total else None,
        mape_pct=round(sum(abs(predicted[d]-actual[d])/actual[d]*100 for d in positive)/len(positive),3) if positive else None,
        days=len(errors),zero_actual_days=len(actual)-len(positive))

def backtest(plant, readings, irradiance, pe, lat, lon, today, correction=None):
    from plant_model import DailyModel, history_factor
    observed={}
    for r in readings:
        d=date.fromisoformat(r['date']); value=float(r['kwh'])
        if not math.isfinite(value) or value<0:raise ValueError('CSV_VALUE')
        if r.get('complete') is False or d>=today:continue
        if d in observed and observed[d]!=value:raise ValueError('CSV_CONFLICT')
        observed[d]=value
    periods=[]
    windows=[('gregorian',date(y,m,1),calendar.monthrange(y,m)[1]) for y,m in sorted({(d.year,d.month) for d in observed})]
    for y,m in sorted({pe.gregorian_to_jalali(d.year,d.month,d.day)[:2] for d in observed}):
        windows.append(('persian',date(*pe.jalali_to_gregorian(y,m,1)),pe.jalali_month_days(y,m)))
    for calendar_name,start,length in windows:
        days=[start+timedelta(days=i) for i in range(length)]
        if not all(d in observed for d in days):continue
        prior=[dict(date=d.isoformat(),kwh=v) for d,v in observed.items() if d<start]
        # A calibration profile fitted to 2025 cannot be scored as a forecast in 2025.
        if correction and start<date(2026,1,1):continue
        raw=DailyModel(plant,{d:pe.climatology_ghi(irradiance,d) for d in days},lat,lon).energies()
        base=correction.apply(raw) if correction else raw
        factor,fit=history_factor(plant,prior,irradiance,start,pe,lat,lon,correction)
        predicted={d:v*factor for d,v in base.items()}
        actual={d:observed[d] for d in days}
        period=dict(calendar=calendar_name,start=start.isoformat(),end=days[-1].isoformat(),**metrics(actual,predicted),training_days=fit['training_days'],training_start=fit.get('training_start'),training_end=fit.get('training_end'),factor=factor,calibration_applied=fit['applied'],raw=metrics(actual,raw),baseline=metrics(actual,base),daily=[dict(date=d.isoformat(),actual_kwh=actual[d],predicted_kwh=round(predicted[d],3)) for d in days])
        # Simple persistence is a transparent competing baseline.
        if len(prior)>=21:
            selected=sorted(prior,key=lambda r:r['date'])[-31:]
            avg=sum(r['kwh'] for r in selected)/len(selected)
            period['daily_mean_baseline']=metrics(actual,{d:avg for d in days})
        periods.append(period)
    periods.sort(key=lambda p:(p['end'],p['start']))
    return dict(method='chronological_monthly_climatology_v1',scope='measured_reference_configuration',weather='long_term_climatology_not_archived_forecasts',periods=periods,latest=periods[-1] if periods else None,reason=None if periods else 'COMPLETE_MONTH_REQUIRED')
