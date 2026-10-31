import {formatDate,formatNumber} from './format';
export type ReportSection='overview'|'forecast'|'impact'|'readings';
export type ReportRow={date:string;kwh:number;source?:string;complete?:boolean;source_count?:number;expected_sources?:number};
export type Report={title:string;headers:string[];rows:(string|number)[][];filename:string;note:string};
export function buildReport(section:ReportSection,rows:ReportRow[],lang:'fa'|'en',tariff:number):Report{
 const t=(en:string,fa:string)=>lang==='fa'?fa:en;
 const titles={overview:t('Production overview','نمای کلی تولید'),forecast:t('Production forecast','پیش‌بینی تولید'),impact:t('Carbon impact','اثر کربن'),readings:t('Recorded readings','داده‌های ثبت‌شده')};
 const headers=[t('Date','تاریخ'),t('Energy (kWh)','انرژی (kWh)')];
 if(section!=='readings')headers.push(t('Avoided CO2 (kg)','کاهش انتشار CO₂ (کیلوگرم)'));
 if(section==='impact')headers.push(t('Tree-years','معادل درخت‌سال'),t('Electric driving (km)','پیمایش برقی (کیلومتر)'),t('Household-months','برق خانوار (ماه)'),t('Demo carbon units (VCT)','واحد کربن آزمایشی (VCT)'));
 if(section==='forecast')headers.push(t('Estimated revenue (IRR)','درآمد تخمینی (ریال)'),t('Source','منبع'));
 if(section==='readings')headers.push(t('Completeness','کامل بودن داده'),t('Available sources','منابع موجود'),t('Expected sources','منابع مورد انتظار'));
 const data=rows.map(r=>{const kg=r.kwh*.66;const row:(string|number)[]=[formatDate(r.date,lang),r.kwh];
  if(section!=='readings')row.push(kg);
  if(section==='impact')row.push(kg/21,r.kwh/.18,r.kwh/300,kg/10);
  if(section==='forecast')row.push(r.kwh*tariff,r.source||'');
  if(section==='readings')row.push(r.complete===false?t('Partial','ناقص'):t('Complete','کامل'),r.source_count??'',r.expected_sources??'');
  return row;
 });
 return {title:titles[section],headers,rows:data,filename:`greenmine-${section}`,note:section==='forecast'?t('Forecast estimates, not recorded production. Revenue uses the forecast tariff.','برآورد پیش‌بینی؛ نه تولید ثبت‌شده. درآمد بر اساس تعرفه همین پیش‌بینی است.'):section==='readings'?t('Imported daily readings for the selected period.','داده‌های روزانه واردشده در بازه انتخاب‌شده.'):t('Avoided emissions: 0.66 kg CO2/kWh. Carbon units are illustrative, not tradable credits.','کاهش انتشار: ۰.۶۶ کیلوگرم CO₂ به‌ازای هر کیلووات‌ساعت. واحدهای کربن آزمایشی و غیرقابل معامله‌اند.')};
}
export function reportCsv(report:Report){
 const cell=(v:string|number)=>{let s=typeof v==='number'?String(Math.round(v*1000)/1000):v;if(typeof v==='string'&&/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};
 return '\ufeff'+[report.headers,...report.rows].map(row=>row.map(cell).join(',')).join('\r\n');
}
export function reportCell(value:string|number,lang:'fa'|'en'){return typeof value==='number'?formatNumber(value,lang,3):value;}
