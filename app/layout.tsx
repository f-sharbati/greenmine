import type { Metadata, Viewport } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'GreenMine | Solar intelligence', description: 'Solar production insights, Persian-calendar forecasting and transparent carbon accounting.' };
export const viewport: Viewport = {themeColor:'#e2e9f2'};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="fa" dir="rtl" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:`try{var t=localStorage.getItem('greenmine-theme');document.documentElement.dataset.theme=t||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}catch(e){}`}}/></head><body>{children}</body></html>;
}
