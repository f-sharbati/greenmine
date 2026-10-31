'use client';
import NextLink from 'next/link';
import type {ComponentProps} from 'react';

// The packaged Android UI uses full documents so it cannot mix RSC responses
// from an older deployed Next.js build with its bundled client assets.
export default function SiteLink(props:ComponentProps<typeof NextLink>){
 return <NextLink {...props} prefetch={false} onNavigate={e=>{
  props.onNavigate?.(e);
  if(navigator.userAgent.includes('GreenMineAndroid/')){
   e.preventDefault();const href=typeof props.href==='string'?props.href:props.href.pathname||'/';
   window.location.assign(href);
  }
 }}/>;
}
