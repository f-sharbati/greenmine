import {cookies} from 'next/headers';
import {randomBytes} from 'node:crypto';
import {service,headers,validOrigin,readBody} from '../../../lib/service';
export const runtime='nodejs';
const options={httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax' as const,path:'/'};
const client=(r:Request)=>r.headers.get('x-forwarded-for')?.split(',')[0].trim()||'local';
const httpsRequired=()=>process.env.NODE_ENV==='production'&&(!process.env.APP_ORIGIN||new URL(process.env.APP_ORIGIN).protocol!=='https:');
export async function GET(request:Request){
 const jar=await cookies();
 const action=new URL(request.url).searchParams.get('action');
 if(action==='captcha'||action==='context'){
  if(httpsRequired())return Response.json({error:'HTTPS_REQUIRED'},{status:503,headers});
  const binding=jar.get('greenmine_auth_flow')?.value||randomBytes(32).toString('hex');
  const p=await service({op:action==='captcha'?'captcha':'auth_status',binding,client:client(request)});
  if(p.status===200)jar.set('greenmine_auth_flow',binding,{...options,maxAge:1800});
  return Response.json(p.data,{status:p.status,headers});
 }
 const p=await service({op:'me',token:jar.get('greenmine_session')?.value});
 const status=await service({op:'auth_status'});
 p.data.auth_mode=status.data.auth_mode;
 p.data.auth_email_available=Boolean(status.data.auth_email_available);
 p.data.recovery_available=Boolean(status.data.auth_email_available);
 return Response.json(p.data,{status:p.status,headers});
}
export async function POST(request:Request){
 if(!validOrigin(request))return Response.json({error:'INVALID_ORIGIN'},{status:403,headers});
 if(httpsRequired())return Response.json({error:'HTTPS_REQUIRED'},{status:503,headers});
 let data;try{data=await readBody(request);}catch{return Response.json({error:'INVALID_REQUEST'},{status:400,headers});}
 if(!['login','register','logout','forgot','reset','auth_verify','auth_resend'].includes(data.action))return Response.json({error:'INVALID_REQUEST'},{status:400,headers});
 const jar=await cookies();const binding=jar.get('greenmine_auth_flow')?.value;
 const p=await service({op:data.action,data,binding,token:jar.get('greenmine_session')?.value,client:client(request)});
 if(p.status===200&&typeof p.data.token==='string'){
  jar.set('greenmine_session',p.data.token,{...options,maxAge:14*86400});delete p.data.token;
  jar.set('greenmine_auth_flow','',{...options,maxAge:0});
 }else if(p.status===200&&binding&&['auth_resend','login','register'].includes(data.action))jar.set('greenmine_auth_flow',binding,{...options,maxAge:1800});
 if(data.action==='logout'||data.action==='reset'&&p.status===200)jar.set('greenmine_session','',{...options,maxAge:0});
 return Response.json(p.data,{status:p.status,headers});
}
