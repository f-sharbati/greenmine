'use client';
import {useEffect,useRef,useState,type MouseEvent} from 'react';
import {flushSync} from 'react-dom';
import {motion,useReducedMotion} from 'motion/react';
import {Moon,Sun} from 'lucide-react';
type Theme='light'|'dark';
const colors={dark:'#101c2b',light:'#e2e9f2'};
export function ThemeToggle({lang}:{lang:'fa'|'en'}){
 const [theme,setTheme]=useState<Theme>('light'),[busy,setBusy]=useState(false);
 const locked=useRef(false),mounted=useRef(true),cleanup=useRef<(()=>void)|null>(null);
 const reduced=useReducedMotion();
 useEffect(()=>{mounted.current=true;let saved:string|null=null;try{saved=localStorage.getItem('greenmine-theme');}catch{}const next:Theme=saved==='dark'||(!saved&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';setTheme(next);document.documentElement.dataset.theme=next;return()=>{mounted.current=false;cleanup.current?.();};},[]);
 async function toggle(event:MouseEvent<HTMLButtonElement>){
  if(locked.current)return;locked.current=true;setBusy(true);
  const next:Theme=theme==='dark'?'light':'dark';
  const rect=event.currentTarget.getBoundingClientRect(),x=rect.left+rect.width/2,y=rect.top+rect.height/2;
  const radius=Math.ceil(Math.hypot(Math.max(x,innerWidth-x),Math.max(y,innerHeight-y)))+2;
  let applied=false,transition:ViewTransition|undefined,mask:Animation|undefined;
  const paused:Animation[]=[];
  const apply=()=>{if(applied||!mounted.current)return;applied=true;flushSync(()=>setTheme(next));document.documentElement.dataset.theme=next;document.querySelector('meta[name="theme-color"]')?.setAttribute('content',colors[next]);};
  const interrupt=()=>{mask?.cancel();transition?.skipTransition();};
  cleanup.current=interrupt;
  try{
   if(reduced||!document.startViewTransition){apply();return;}
   // Avoid competing CSS/WAAPI motion while capturing and revealing the two themes.
   for(const animation of document.getAnimations()){if(animation.playState==='running'){animation.pause();paused.push(animation);}}
   document.documentElement.classList.add('theme-switching');
   window.addEventListener('resize',interrupt,{once:true});document.addEventListener('visibilitychange',interrupt,{once:true});
   transition=document.startViewTransition(apply);
   // Observe both promises, including interrupted/hidden-tab captures.
   const done=transition.finished.catch(()=>{});
   await transition.ready;
   mask=document.documentElement.animate({clipPath:[`circle(0px at ${x}px ${y}px)`,`circle(${radius}px at ${x}px ${y}px)`]},{duration:1500,easing:'cubic-bezier(.4,0,.2,1)',pseudoElement:'::view-transition-new(root)',fill:'forwards'});
   await mask.finished;await done;
  }catch{apply();}
  finally{
   interrupt();cleanup.current=null;
   window.removeEventListener('resize',interrupt);document.removeEventListener('visibilitychange',interrupt);
   document.documentElement.classList.remove('theme-switching');
   for(const animation of paused){if(animation.playState==='paused')animation.play();}
   if(applied){try{localStorage.setItem('greenmine-theme',next);}catch{}}
   locked.current=false;if(mounted.current)setBusy(false);
  }
 }
 const label=lang==='fa'?(theme==='dark'?'تغییر به حالت روشن':'تغییر به حالت تیره'):(theme==='dark'?'Switch to light theme':'Switch to dark theme');
 return <motion.button className="theme-toggle icon-button" onClick={toggle} disabled={busy} aria-label={label} aria-pressed={theme==='dark'} whileTap={{scale:.92}}>{theme==='dark'?<Sun size={19}/>:<Moon size={19}/>}</motion.button>;
}
