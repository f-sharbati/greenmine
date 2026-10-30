"""Explicit empirical bias correction of the existing climate/geometry model."""
from datetime import date, timedelta
import math

def eligible_history(readings, today):
    prior={}
    for row in readings:
        day=date.fromisoformat(row['date']); value=float(row['kwh'])
        if not math.isfinite(value) or value<0: raise ValueError('CSV_VALUE')
        if day>=today or day<today-timedelta(days=120): continue
        if day in prior and prior[day]!=value: raise ValueError('CSV_CONFLICT')
        prior[day]=value
    result={'model':'climate_with_production_bias_v2','applied':False,'factor':1.0,'reason':'INSUFFICIENT_HISTORY','training_days':len(prior)}
    if len(prior)<21:return prior, result
    last=max(prior); first=max(min(prior),last-timedelta(days=89)); prior={d:v for d,v in prior.items() if d>=first}
    result.update(training_start=first.isoformat(),training_end=last.isoformat(),training_days=len(prior),staleness_days=(today-last).days)
    if len(prior)<21:return prior, result
    if (today-last).days>45:result['reason']='STALE_HISTORY';return prior, result
    result['reason']='ELIGIBLE'
    return prior,result

def calibrate(readings, plant, irradiance, today, pe):
    prior,result=eligible_history(readings,today)
    if result['reason']!='ELIGIBLE':return result
    lat,_=pe.utm_to_latlon(plant['utm_easting'],plant['utm_northing'],plant['utm_zone'])
    coefficient=plant['capacity_ac']*plant['performance_ratio']*pe.tilt_azimuth_factor(plant['tilt'],plant['azimuth'],lat)*pe.MOUNT_FACTORS[plant['mount_type']]*pe.PANEL_FACTORS[plant['panel_type']]
    expected=sum(pe.climatology_ghi(irradiance,d)*coefficient for d in prior)
    actual=sum(prior.values())
    if expected<=0 or actual<=0:result['reason']='NO_POSITIVE_ENERGY';return result
    factor=actual/expected
    result.update(observed_kwh=round(actual,3),modeled_training_kwh=round(expected,3),candidate_factor=round(factor,6))
    if not .5<=factor<=1.5:result['reason']='SETTINGS_OR_DATA_REVIEW';return result
    result.update(applied=True,factor=factor,reason='APPLIED')
    return result
