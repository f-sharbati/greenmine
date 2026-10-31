'use client';
import {useEffect,useRef,useState} from 'react';
import type {Map as LeafletMap,Marker} from 'leaflet';
export function LocationMap({latitude,longitude,onSelect,lang}:{latitude:number|null;longitude:number|null;onSelect:(lat:number,lng:number)=>void;lang:'fa'|'en'}){
 const host=useRef<HTMLDivElement>(null),map=useRef<LeafletMap|null>(null),marker=useRef<Marker|null>(null),callback=useRef(onSelect),syncing=useRef(false),emitted=useRef<string|null>(null);
 const [failed,setFailed]=useState(false),[loaded,setLoaded]=useState(false);callback.current=onSelect;
 useEffect(()=>{let disposed=false;let resize:ResizeObserver|undefined;let timeout:ReturnType<typeof setTimeout>|undefined;let received=false;
  import('leaflet').then(L=>{if(disposed||!host.current)return;
   const selected=latitude!==null&&longitude!==null;
   const center:[number,number]=selected?[latitude!,longitude!]:[32.4,53.7];
   const m=L.map(host.current,{scrollWheelZoom:true}).setView(center,selected?13:5);map.current=m;
   L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).on('tileload',()=>{received=true;setLoaded(true);setFailed(false);}).on('tileerror',()=>{if(!received)setFailed(true);}).addTo(m);
   timeout=setTimeout(()=>{if(!received)setFailed(true);},15000);
   const pin=L.divIcon({className:'plant-map-pin',html:'<span></span>',iconSize:[28,28],iconAnchor:[14,14]});
   const mk=L.marker(center,{icon:pin,draggable:false,keyboard:true,title:lang==='fa'?'محل نیروگاه':'Plant location'});marker.current=mk;
   mk.addTo(m);
   // Move the marker with the map, without React renders during each animation frame.
   m.on('move',()=>mk.setLatLng(m.getCenter()));
   m.on('moveend',()=>{if(syncing.current)return;const point=m.getCenter().wrap();const lat=Number(Math.max(-85,Math.min(85,point.lat)).toFixed(6)),lng=Number(point.lng.toFixed(6));emitted.current=`${lat},${lng}`;callback.current(lat,lng);});
   m.on('click',e=>m.panTo(e.latlng,{animate:false}));
   resize=new ResizeObserver(()=>m.invalidateSize());resize.observe(host.current);
  }).catch(()=>setFailed(true));
  return()=>{disposed=true;clearTimeout(timeout);resize?.disconnect();map.current?.remove();map.current=null;marker.current=null;};
 },[]);
 useEffect(()=>{if(map.current&&marker.current&&latitude!==null&&longitude!==null){
  // Do not turn a map-originated update into another pan or reset the user's zoom.
  if(emitted.current===`${latitude},${longitude}`)return;
  syncing.current=true;
  try{map.current.setView([latitude,longitude],Math.max(12,map.current.getZoom()),{animate:false});marker.current.setLatLng(map.current.getCenter());}finally{syncing.current=false;}
 }},[latitude,longitude]);

 return <div className="location-map-wrap"><p>{lang==='fa'?'نقشه را زیر نشانگر جابه‌جا کنید. در رایانه با اسکرول بزرگ‌نمایی کنید.':'Drag the map beneath the pin to select your plant. Scroll to zoom on desktop.'}</p><div ref={host} className="location-map" dir="ltr" aria-label={lang==='fa'?'نقشه انتخاب محل نیروگاه':'Plant location map'}/>{!loaded&&!failed&&<p role="status">{lang==='fa'?'\u062f\u0631 \u062d\u0627\u0644 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0646\u0642\u0634\u0647\u2026':'Loading map tiles…'}</p>}{failed&&<p role="status">{lang==='fa'?'نقشه در دسترس نیست؛ مختصات را وارد کنید یا شهر را جستجو کنید.':'Map tiles unavailable. Enter coordinates or search for a city.'}</p>}</div>;
}
