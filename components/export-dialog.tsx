'use client';
import {formatNumber,formatDate} from '../lib/format';
import type {Validation} from './forecast-validation';
import {useState} from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {Download,FileText,X} from 'lucide-react';
type Row={date:string;kwh:number;source?:string};
const escape=(s:string)=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function ExportDialog({open,onOpenChange,lang,onCsv,plantName,forecast,rows,validation}:{open:boolean;onOpenChange:(v:boolean)=>void;lang:'fa'|'en';onCsv:()=>void;plantName:string;forecast:boolean;rows:Row[];validation?:Validation}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');const t=(en:string,fa:string)=>lang==='fa'?fa:en;
 async function pdf(){
  setBusy(true);setError('');
  try{
   const formatter={format:(n:number)=>formatNumber(n,lang,3)};
   const title=t(forecast?'Production forecast':'Production report',forecast?'گزارش پیش‌بینی تولید':'گزارش تولید');
   const score=validation?.latest;
   const validationSummary=score?`<h2>${t('Retrospective error test','آزمون خطای گذشته‌نگر')}</h2><p>${escape(formatDate(score.start,lang))} - ${escape(formatDate(score.end,lang))}<br>${t('Actual / predicted','واقعی / پیش‌بینی')}: ${formatter.format(score.actual_kwh)} / ${formatter.format(score.predicted_kwh)} kWh<br>${t('Monthly absolute error','خطای مطلق ماهانه')}: ${score.absolute_error_pct==null?'?':formatter.format(score.absolute_error_pct)}%<br>${t('Historical test, not guaranteed future accuracy.','آزمون تاریخی؛ دقت آینده تضمین نمی‌شود.')}</p>`:'';
   const dateLabel=t('Date','تاریخ'),energy=t('Energy (kWh)','انرژی (کیلووات‌ساعت)'),source=t('Source','منبع');
   const html=`<!doctype html><html lang="${lang}" dir="${lang==='fa'?'rtl':'ltr'}"><head><meta charset="utf-8"><title>GreenMine — ${title}</title><style>@font-face{font-family:Anjoman;src:url('${location.origin}/fonts/Anjoman.woff')}@page{size:A4;margin:16mm}body{font:14px ${lang==='fa'?'Anjoman,':''}Arial,sans-serif;color:#172b43;margin:0}h1{font-size:25px}p{line-height:1.8}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px;text-align:start;border-bottom:1px solid #cbd5e1}th{background:#e8edf5}thead{display:table-header-group}tr{break-inside:avoid}.number{direction:ltr;unicode-bidi:isolate}footer{margin-top:20px;font-size:11px}</style></head><body><h1>GreenMine · ${title}</h1><p>${escape(plantName)}<br>${escape(t('Total energy','جمع انرژی'))}: <b>${formatter.format(rows.reduce((n,r)=>n+r.kwh,0))} kWh</b></p>${forecast?`<p>${t('Forecast estimates; not guaranteed production.','مقادیر پیش‌بینی تخمینی هستند و تضمین تولید نیستند.')}</p>`:''}${validationSummary}<table><thead><tr><th>${dateLabel}</th><th>${energy}</th>${forecast?`<th>${source}</th>`:''}</tr></thead><tbody>${rows.map(r=>`<tr><td class="number">${escape(formatDate(r.date,lang))}</td><td class="number">${formatter.format(r.kwh)}</td>${forecast?`<td>${escape(r.source||'')}</td>`:''}</tr>`).join('')}</tbody></table><footer>${t('Exported rows match the selected period or forecast.','ردیف‌ها مطابق بازه یا پیش‌بینی انتخاب‌شده هستند.')}</footer></body></html>`;
   if(navigator.userAgent.includes('GreenMineAndroid/')){
    const result=window.prompt('greenmine:print',JSON.stringify({html}));
    if(result!=='opened')throw Error('Native PDF printing requires the updated Android app.');
   }else{
    const frame=document.createElement('iframe');frame.className='print-report-frame';frame.title=title;
    document.body.append(frame);
    const loaded=new Promise<void>((resolve,reject)=>{frame.onload=()=>resolve();frame.onerror=()=>reject(Error('load'));});
    frame.srcdoc=html;await loaded;
    await frame.contentDocument?.fonts.ready;
    const win=frame.contentWindow;if(!win)throw Error('print');
    let timer:ReturnType<typeof setTimeout>;const remove=()=>{clearTimeout(timer);frame.remove();};
    win.addEventListener('afterprint',remove,{once:true});timer=setTimeout(remove,120000);
    win.focus();win.print();
   }
   onOpenChange(false);
  }catch{setError(t('Could not open PDF export. On Android, install the updated app.','خروجی PDF باز نشد. در اندروید نسخه جدید برنامه را نصب کنید.'));}finally{setBusy(false);}
 }
 return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="dialog-overlay"/><Dialog.Content className="dialog-content export-dialog" dir={lang==='fa'?'rtl':'ltr'}><Dialog.Title>{t('Export report','خروجی گزارش')}</Dialog.Title><Dialog.Description>{t('Choose CSV for data, or PDF for a readable report. Select Save as PDF in the print dialog.','برای داده‌ها CSV و برای گزارش خوانا PDF را انتخاب کنید. در پنجره چاپ، گزینه ذخیره به‌صورت PDF را بزنید.')}</Dialog.Description><Dialog.Close className="dialog-close icon-button" aria-label={t('Close','بستن')}><X size={20}/></Dialog.Close><div className="export-options"><button className="button outline" disabled={busy||!rows.length} onClick={()=>{onCsv();onOpenChange(false);}}><Download size={18}/>CSV</button><button className="button dark" disabled={busy||!rows.length} onClick={pdf}><FileText size={18}/>PDF</button></div>{!rows.length&&<p>{t('No readings to export.','داده‌ای برای خروجی موجود نیست.')}</p>}{error&&<p role="alert">{error}</p>}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
