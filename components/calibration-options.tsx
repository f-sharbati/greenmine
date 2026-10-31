'use client';
import type {Plant} from '../lib/plant';
export function CalibrationOptions({rebase,onRebase,lang}:{plant:Plant;onChange:(p:Plant)=>void;rebase:boolean;onRebase:(v:boolean)=>void;lang:'fa'|'en'}){
 const t=(en:string,fa:string)=>lang==='fa'?fa:en;
 return <section className="calibration-options"><h3>{t('Measured configuration','مشخصات اندازه‌گیری‌شده')}</h3>
 <p>{t('Physical model + your production history','مدل فیزیکی و سوابق تولید شما')}</p>
 <label className="plant-history-option"><input type="checkbox" checked={rebase} onChange={e=>onRebase(e.target.checked)}/>{t('These are the settings that produced my imported readings','این مشخصات مربوط به نیروگاهی است که سوابق واردشده را تولید کرده است')}</label>
 <p className="fine-print">{t('Keep the measured configuration fixed when exploring changes, so changing capacity or orientation remains visible.','هنگام بررسی تغییرات، مشخصات مرجع اندازه‌گیری‌شده را ثابت نگه دارید تا اثر تغییر ظرفیت یا جهت قابل مشاهده باشد.')}</p></section>;
}
