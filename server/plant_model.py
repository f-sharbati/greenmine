"""Aggregate-capacity solar estimate; daily GHI is disaggregated, not measured hourly weather."""
from datetime import date,timedelta
import math
import numpy as np
import pandas as pd
import pvlib

ASSUMPTIONS=[
 'One representative tilt and direction are used for the whole site.',
 'Hourly irradiation shape is estimated from daily totals, not measured hourly weather.',
 'Temperature, shading and soiling are represented only by the aggregate loss factor.',
 'Mixed panel models use total DC nameplate capacity; no per-panel or bifacial rear-gain model.',
 'The site-wide performance factor includes inverter conversion and other losses; no per-inverter model is assumed.'
]
class DailyModel:
 def __init__(self,plant,ghi,lat,lon):
  self.days=sorted(ghi);self.plant=plant
  if any(not math.isfinite(float(v)) or v<0 for v in ghi.values()):raise ValueError('WEATHER_UNAVAILABLE')
  times=pd.DatetimeIndex([pd.Timestamp(d,tz='Asia/Tehran')+pd.Timedelta(hours=h,minutes=30) for d in self.days for h in range(24)])
  loc=pvlib.location.Location(lat,lon,tz='Asia/Tehran',altitude=0)
  pos=loc.get_solarposition(times)
  clear=loc.get_clearsky(times,model='haurwitz')['ghi'].to_numpy().reshape(-1,24)
  sums=clear.sum(axis=1)
  energy=np.array([ghi[d]*1000 for d in self.days])
  if np.any((sums<=0)&(energy>0)):raise ValueError('PLANT_LOCATION_REVIEW')
  hourly=np.divide(clear*energy[:,None],sums[:,None],out=np.zeros_like(clear),where=sums[:,None]>0).reshape(-1)
  self.ghi_daily=(hourly.reshape(-1,24).sum(axis=1)/1000).tolist()
  doy=np.array([d.timetuple().tm_yday for d in times.to_pydatetime()])
  diffuse=pvlib.irradiance.erbs(hourly,pos['zenith'],doy)
  poa=pvlib.irradiance.get_total_irradiance(plant['tilt'],plant['azimuth'],pos['apparent_zenith'],pos['azimuth'],diffuse['dni'],hourly,diffuse['dhi'],dni_extra=pvlib.irradiance.get_extra_radiation(doy),model='haydavies')['poa_global']
  self.pdc=np.maximum(np.nan_to_num(np.asarray(poa)),0)*plant['capacity_dc']*plant['performance_ratio']
  self.poa_daily=(np.maximum(np.nan_to_num(np.asarray(poa)),0).reshape(-1,24).sum(axis=1)/1000).tolist()
 def energies(self,factor=1):
  # Aggregate site output. The performance factor includes all inverter losses.
  return dict(zip(self.days,((self.pdc*factor).reshape(-1,24).sum(axis=1)/1000).tolist()))

def history_factor(reference,readings,irradiance,today,pe,lat,lon,correction=None):
 from calibration import eligible_history
 history,result=eligible_history(readings,today)
 result['model']='frozen_reference_bias_v4'
 if reference.get('forecast_mode')=='model_only':result.update(applied=False,reason='MODEL_ONLY');return 1.,result
 if result['reason']!='ELIGIBLE':return 1.,result
 values=DailyModel(reference,{d:pe.climatology_ghi(irradiance,d) for d in history},lat,lon).energies()
 if correction:values=correction.apply(values)
 expected=sum(values.values());actual=sum(history.values())
 result.update(observed_kwh=round(actual,3),modeled_training_kwh=round(expected,3))
 if actual<=0 or expected<=0:result['reason']='NO_POSITIVE_ENERGY';return 1.,result
 factor=actual/expected
 if not .5<=factor<=1.5:result.update(reason='SETTINGS_OR_DATA_REVIEW',candidate_factor=factor);return 1.,result
 result.update(applied=True,factor=factor,reason='APPLIED')
 return factor,result

def forecast(plant,today,irradiance,daily_api,readings,pe,lat,lon,horizon='next_month',reference_plant=None,reference_irradiance=None):
 from calibration import eligible_history
 from pilot_model import correction_for
 from validation import backtest
 reference=reference_plant or plant
 ref_lat,ref_lon=(reference['latitude'],reference['longitude']) if reference['location_mode']=='gps' else pe.utm_to_latlon(reference['utm_easting'],reference['utm_northing'],reference['utm_zone'])
 reference_irradiance=reference_irradiance or irradiance
 correction=correction_for(plant,reference_irradiance,pe)
 reference={**reference,'forecast_mode':plant.get('forecast_mode','history_calibrated')}
 factor,calibration=history_factor(reference,readings,reference_irradiance,today,pe,ref_lat,ref_lon,correction)
 calibration['reference_plant']={k:reference.get(k) for k in ['capacity_dc','capacity_ac','tilt','azimuth','performance_ratio','location_mode','latitude','longitude','mount_type']}
 calibration['profile']=plant.get('calibration_profile','none')
 def differs(key):
  a,b=plant.get(key),reference.get(key)
  if isinstance(a,(int,float)) and isinstance(b,(int,float)):return not math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-6)
  return a!=b
 calibration['scenario_changed']=any(differs(k) for k in ['capacity_dc','tilt','azimuth','performance_ratio','latitude','longitude','utm_easting','utm_northing','mount_type'])
 jy,jm,_=pe.gregorian_to_jalali(today.year,today.month,today.day);ny,nm=pe.next_jalali_month(jy,jm)
 start=today if horizon=='rolling_30' else date(*pe.jalali_to_gregorian(ny,nm,1))
 days=[start+timedelta(days=i) for i in range(30 if horizon=='rolling_30' else pe.jalali_month_days(ny,nm))]
 ghi={d:daily_api[d] if d in daily_api else pe.climatology_ghi(irradiance,d) for d in days}
 target=DailyModel(plant,ghi,lat,lon);raw=target.energies()
 baseline=correction.apply(raw) if correction else raw
 values={d:v*factor for d,v in baseline.items()}
 rows=[dict(day=i+1,jalali_date='/'.join(f'{n:02d}' if j else str(n) for j,n in enumerate(pe.gregorian_to_jalali(d.year,d.month,d.day))),gregorian_date=d.isoformat(),production_kwh=round(values[d],3),ghi=round(ghi[d],3),source='API forecast' if d in daily_api else 'Climate model') for i,d in enumerate(days)]
 # Exact Jalali year boundaries, independent of the legacy fixed month weights.
 year_start=date(*pe.jalali_to_gregorian(jy,1,1));year_end=date(*pe.jalali_to_gregorian(jy+1,1,1))
 year_days=[year_start+timedelta(days=i) for i in range((year_end-year_start).days)]
 annual_values=DailyModel(plant,{d:pe.climatology_ghi(irradiance,d) for d in year_days},lat,lon).energies()
 if correction:annual_values=correction.apply(annual_values)
 result=dict(horizon=horizon,target_start=days[0].isoformat(),target_end=days[-1].isoformat(),target_year=jy if horizon=='rolling_30' else ny,target_month=jm if horizon=='rolling_30' else nm,days=rows,total_kwh=round(sum(r['production_kwh'] for r in rows),3),first_half_kwh=round(sum(r['production_kwh'] for r in rows[:15]),3),second_half_kwh=round(sum(r['production_kwh'] for r in rows[15:]),3),api_days=sum(d in daily_api for d in days),model_days=sum(d not in daily_api for d in days))
 validation=backtest(reference,readings,reference_irradiance,pe,ref_lat,ref_lon,today,correction)
 if correction:validation['fit_checks']=correction.fit_checks
 annual_total=round(sum(annual_values.values()),3)
 return dict(forecast=result,calibration=calibration,validation=validation,uncalibrated_kwh=round(sum(raw.values()),3),annual={'annual_kwh':annual_total,'recent_bias_annual_kwh':round(annual_total*factor,3),'year':jy,'specific_yield_kwh_kwp':round(annual_total/plant['capacity_dc'],1),'tehran_reference_range':[1700*plant['capacity_dc'],1850*plant['capacity_dc']] if 35<lat<36.5 and 50.5<lon<52.5 else None},model={'id':'aggregate_site_poa_v4','capacity_dc_kw':plant['capacity_dc'],'latitude':lat,'longitude':lon,'assumptions':ASSUMPTIONS+(['Pilot seasonal profile fitted to 2025 annual total and its Azar subset; not independent accuracy evidence.'] if correction else [])})
