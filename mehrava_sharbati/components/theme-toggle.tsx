'use client';
import {useEffect,useRef,useState,type MouseEvent} from 'react';
import {flushSync} from 'react-dom';
import {motion,useReducedMotion} from 'motion/react';
import {Moon,Sun} from 'lucide-react';

type Theme='light'|'dark';
export function ThemeToggle({lang}:{lang:'fa'|'en'}){
 const [theme,setTheme]=useState<Theme>('light');
 const [busy,setBusy]=useState(false);const locked=useRef(false);const reduced=useReducedMotion();
 useEffect(()=>{const saved=localStorage.getItem('greenmine-theme');const next:Theme=saved==='dark'||(!saved&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';setTheme(next);document.documentElement.dataset.theme=next;},[]);
 async function toggle(event:MouseEvent<HTMLButtonElement>){
   if(locked.current)return;locked.current=true;setBusy(true);
   const next:Theme=theme==='dark'?'light':'dark';
   const rect=event.currentTarget.getBoundingClientRect();const x=rect.left+rect.width/2,y=rect.top+rect.height/2;
   const radius=Math.hypot(Math.max(x,innerWidth-x),Math.max(y,innerHeight-y));
   const apply=()=>{flushSync(()=>setTheme(next));document.documentElement.dataset.theme=next;localStorage.setItem('greenmine-theme',next);document.querySelector('meta[name="theme-color"]')?.setAttribute('content',next==='dark'?'#101c2b':'#e2e9f2');};
   try{
     if(!reduced&&document.startViewTransition){
       const transition=document.startViewTransition(apply);
       await transition.ready;
       await document.documentElement.animate({clipPath:[`circle(0px at ${x}px ${y}px)`,`circle(${radius}px at ${x}px ${y}px)`]},{duration:1500,easing:'cubic-bezier(.4,0,.2,1)',pseudoElement:'::view-transition-new(root)',fill:'both'}).finished;
       await transition.finished;
     }else if(!reduced){
       // Older WebViews: expand a matching color veil, apply the palette, then reveal.
       const veil=document.createElement('div');veil.className='theme-veil';veil.setAttribute('aria-hidden','true');veil.style.background=next==='dark'?'#101c2b':'#e2e9f2';document.body.append(veil);
       try{await veil.animate({clipPath:[`circle(0px at ${x}px ${y}px)`,`circle(${radius}px at ${x}px ${y}px)`]},{duration:1100,easing:'cubic-bezier(.4,0,.2,1)',fill:'forwards'}).finished;apply();await veil.animate({opacity:[1,0]},{duration:350,fill:'forwards'}).finished;}finally{veil.remove();}
     }else apply();
   }catch{apply();}finally{locked.current=false;setBusy(false);}
 }
 const label=lang==='fa'?(theme==='dark'?'تغییر به حالت روشن':'تغییر به حالت تیره'):(theme==='dark'?'Switch to light theme':'Switch to dark theme');
 return <motion.button className="theme-toggle icon-button" onClick={toggle} disabled={busy} aria-label={label} title={label} aria-pressed={theme==='dark'} whileTap={{scale:.88}}><motion.span animate={{rotate:theme==='dark'?180:0}} transition={{duration:reduced?0:.5}}>{theme==='dark'?<Sun size={19}/>:<Moon size={19}/>}</motion.span></motion.button>;
}
