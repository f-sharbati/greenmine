'use client';
import {useEffect,useRef,useState,type RefObject} from 'react';
import {animate,motion,useInView,useMotionValue,useReducedMotion,useTransform} from 'motion/react';
import {RotateCw} from 'lucide-react';
import {AnimatedCard} from './animated-card';

export function AnimatedNumber({value,lang,digits=1}:{value:number;lang:'fa'|'en';digits?:number}){
 const reduced=useReducedMotion();const ref=useRef<HTMLSpanElement>(null);const visible=useInView(ref,{once:true});
 const progress=useMotionValue(0);
 const format=(n:number)=>new Intl.NumberFormat(lang==='fa'?'fa-IR':'en-US',{maximumFractionDigits:digits}).format(n);
 const display=useTransform(progress,latest=>format(latest));
 useEffect(()=>{if(!visible)return;if(reduced){progress.set(value);return;}const controls=animate(progress,value,{duration:1.3,ease:[.22,1,.36,1]});return()=>controls.stop();},[value,progress,reduced,visible]);
 return <span ref={ref} aria-label={format(value)}><motion.span aria-hidden="true">{display}</motion.span></span>;
}

function useCircularMotion(target:number,replay:number,ref:RefObject<HTMLDivElement|null>){
 const angle=useMotionValue(0);const visible=useInView(ref,{once:true,amount:.25});const reduced=useReducedMotion();const lastReplay=useRef(-1);
 useEffect(()=>{if(!visible)return;if(lastReplay.current!==replay){angle.set(0);lastReplay.current=replay;}if(reduced){angle.set(target);return;}const control=animate(angle,target,{duration:1.9,ease:[.22,1,.36,1],delay:.2});return()=>control.stop();},[target,replay,angle,visible,reduced]);
 return angle;
}

export function PerformanceGauge({ratio,lang}:{ratio:number;lang:'fa'|'en'}){
 const ref=useRef<HTMLDivElement>(null);const [replay,setReplay]=useState(0);const percentage=Math.max(0,Math.min(100,ratio*100));
 const angle=useCircularMotion(percentage*1.8,replay,ref);
 const cx=useTransform(angle,a=>130-Math.cos(a*Math.PI/180)*100);
 const cy=useTransform(angle,a=>130-Math.sin(a*Math.PI/180)*100);
 const arc=useTransform(angle,a=>a/180);
 const readout=useTransform(angle,a=>new Intl.NumberFormat(lang==='fa'?'fa-IR':'en-US',{maximumFractionDigits:0}).format(a/1.8));
 return <AnimatedCard className="gauge-card metric-card"><div className="card-top"><span>{lang==='fa'?'ضریب عملکرد':'Performance ratio'}</span><button className="replay-button" onClick={()=>setReplay(n=>n+1)} aria-label={lang==='fa'?'پخش دوباره نشانگر عملکرد':'Replay performance gauge'}><RotateCw size={17}/></button></div><div className="dial" ref={ref} dir="ltr"><svg viewBox="0 0 260 160" aria-hidden="true"><path className="dial-track" d="M30 130 A100 100 0 0 1 230 130"/>{Array.from({length:25},(_,i)=>{const a=Math.PI+i/24*Math.PI;return <line key={i} x1={130+Math.cos(a)*108} y1={130+Math.sin(a)*108} x2={130+Math.cos(a)*(i%4===0?116:112)} y2={130+Math.sin(a)*(i%4===0?116:112)} className="dial-tick"/>;})}<motion.path className="dial-value" d="M30 130 A100 100 0 0 1 230 130" style={{pathLength:arc}}/><motion.circle className="gauge-marker" r="4" fill="currentColor" cx={cx} cy={cy}/></svg><div className="dial-number" aria-label={`${percentage}%`}><motion.span aria-hidden>{readout}</motion.span><small>%</small></div><span className="dial-min">0</span><span className="dial-max">100</span></div><p>{lang==='fa'?'ضریب ورودی مدل پیش‌بینی؛ نه اندازه‌گیری زنده':'Forecast model input, not a live measurement'}</p><span className="instrument-caption">{lang==='fa'?'تنظیمات نیروگاه':'Plant configuration'}</span></AnimatedCard>;
}

export function AzimuthCompass({azimuth,tilt,lang}:{azimuth:number;tilt:number;lang:'fa'|'en'}){
 const ref=useRef<HTMLDivElement>(null);const [replay,setReplay]=useState(0);const angle=useCircularMotion(azimuth,replay,ref);
 const cx=useTransform(angle,a=>120+Math.sin(a*Math.PI/180)*84);
 const cy=useTransform(angle,a=>120-Math.cos(a*Math.PI/180)*84);
 const x1=useTransform(angle,a=>120+Math.sin(a*Math.PI/180)*72);
 const y1=useTransform(angle,a=>120-Math.cos(a*Math.PI/180)*72);
 const x2=useTransform(angle,a=>120+Math.sin(a*Math.PI/180)*89);
 const y2=useTransform(angle,a=>120-Math.cos(a*Math.PI/180)*89);
 const readout=useTransform(angle,a=>new Intl.NumberFormat(lang==='fa'?'fa-IR':'en-US',{maximumFractionDigits:0}).format(a));
 return <AnimatedCard className="compass-card metric-card"><div className="card-top"><span>{lang==='fa'?'جهت و شیب پنل':'Panel orientation'}</span><button className="replay-button" onClick={()=>setReplay(n=>n+1)} aria-label={lang==='fa'?'پخش دوباره نشانگر جهت':'Replay orientation gauge'}><RotateCw size={17}/></button></div><div className="compass" ref={ref} dir="ltr"><svg viewBox="0 0 240 240" aria-hidden="true"><circle className="compass-track" cx="120" cy="120" r="84" fill="none" strokeWidth=".7"/>{Array.from({length:36},(_,i)=>{const a=i*10*Math.PI/180;return <line key={i} x1={120+Math.sin(a)*92} y1={120-Math.cos(a)*92} x2={120+Math.sin(a)*(i%9===0?101:95)} y2={120-Math.cos(a)*(i%9===0?101:95)} className="compass-tick" strokeWidth={i%9===0?1.3:.7}/>;})}<motion.line className="compass-needle" strokeWidth="2" x1={x1} y1={y1} x2={x2} y2={y2}/><motion.circle className="compass-marker" r="3.5" cx={cx} cy={cy}/></svg><span className="north">{lang==='fa'?'ش':'N'}</span><span className="south">{lang==='fa'?'ج':'S'}</span><span className="east">{lang==='fa'?'ش‌ق':'E'}</span><span className="west">{lang==='fa'?'غ':'W'}</span><div className="compass-number" aria-label={`${azimuth}°`}><motion.span aria-hidden>{readout}</motion.span><small>°</small><span>{lang==='fa'?'آزیموت':'Azimuth'}</span></div></div><div className="compass-footer"><span>{lang==='fa'?'شیب پنل':'Panel tilt'}</span><strong><AnimatedNumber value={tilt} lang={lang}/>°</strong></div></AnimatedCard>;
}
