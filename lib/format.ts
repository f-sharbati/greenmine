export type Language='fa'|'en';
const numberCache=new Map<string,Intl.NumberFormat>();
export function formatNumber(value:number,lang:Language,digits=1,grouping=true){
 const key=`${lang}:${digits}:${grouping}`;
 let formatter=numberCache.get(key);
 if(!formatter){formatter=new Intl.NumberFormat(lang==='fa'?'fa-IR':'en-US',{maximumFractionDigits:digits,useGrouping:grouping});numberCache.set(key,formatter);}
 return formatter.formatToParts(value).map(part=>lang==='fa'&&part.type==='group'?'،':lang==='fa'&&part.type==='decimal'?'.':part.value).join('');
}
export function formatDate(value:string|number,lang:Language){
 const date=typeof value==='number'?new Date(value):new Date(value+'T12:00:00Z');
 if(Number.isNaN(date.getTime()))return '—';
 return new Intl.DateTimeFormat(lang==='fa'?'fa-IR':'en-GB',{calendar:lang==='fa'?'persian':'gregory',year:'numeric',month:'long',day:'numeric',timeZone:'Asia/Tehran'}).format(date);
}
