'use client';
import {useEffect,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {UserRound,LogOut} from 'lucide-react';
import {AuthForm} from './auth-form';
import {MailSettings} from './mail-settings';
type User={id:number;email:string;mail_admin?:boolean};
export function AuthGate({lang,children}:{lang:'fa'|'en';children:ReactNode}){
 const t=(en:string,fa:string)=>lang==='fa'?fa:en;
 const [slots,setSlots]=useState<{account:HTMLElement;profile:HTMLElement}|null>(null);
 useEffect(()=>{const account=document.getElementById('account-menu-slot'),profile=document.getElementById('profile-menu-slot');if(account&&profile)setSlots({account,profile});},[]);
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(''),[mailAvailable,setMailAvailable]=useState(false);
 useEffect(()=>{const expired=()=>setUser(null);window.addEventListener('greenmine-session-expired',expired);return()=>window.removeEventListener('greenmine-session-expired',expired);},[]);
 useEffect(()=>{let active=true;fetch('/api/auth',{cache:'no-store'}).then(async r=>{const p=await r.json();if(active){setMailAvailable(Boolean(p.auth_email_available));if(r.ok)setUser(p.user);else if(r.status!==401)setError('SERVICE_UNAVAILABLE');}}).catch(()=>{if(active)setError('SERVICE_UNAVAILABLE');}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);
 async function logout(){setBusy(true);try{const r=await fetch('/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'logout'})});if(r.ok||r.status===401){setUser(null);window.dispatchEvent(new Event('greenmine-menu-close'));}else setError('SERVICE_UNAVAILABLE');}catch{setError('SERVICE_UNAVAILABLE');}finally{setBusy(false);}}
 if(loading)return <main className="workspace"><p role="status">{t('Loading your account…','در حال دریافت حساب شما…')}</p></main>;
 if(user)return <>{slots&&<>{createPortal(<section className="account-menu" aria-label={t('Your account','حساب شما')}><div className="account-identity"><UserRound size={20}/><span dir="ltr">{user.email}</span></div>{user.mail_admin&&<MailSettings lang={lang}/>}<button className="button outline account-logout" disabled={busy} onClick={logout}><LogOut size={17}/>{t('Sign out','خروج')}</button>{error&&<p role="alert">{t('Could not sign out. Please retry.','خروج انجام نشد؛ دوباره تلاش کنید.')}</p>}</section>,slots.account)}{createPortal(<button className="icon-button profile-button" aria-label={t('Profile and account settings','پروفایل و تنظیمات حساب')} aria-controls="site-menu" onClick={()=>window.dispatchEvent(new Event('greenmine-menu-open'))}><UserRound size={20}/></button>,slots.profile)}</>}<div key={user.id}>{children}</div></>;
 return <AuthForm lang={lang} mailAvailable={mailAvailable} onUser={setUser}/>;
}
