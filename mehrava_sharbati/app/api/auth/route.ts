import {cookies} from 'next/headers';
import {service,headers,validOrigin,readBody} from '../../../lib/service';
export const runtime='nodejs';
export async function GET(){const token=(await cookies()).get('greenmine_session')?.value;const p=await service({op:'me',token});const recovery=await service({op:'recovery_status'});p.data.recovery_available=Boolean(recovery.data.recovery_available);return Response.json(p.data,{status:p.status,headers});}
export async function POST(request:Request){
 if(!validOrigin(request))return Response.json({error:'INVALID_ORIGIN'},{status:403,headers});
 let data;try{data=await readBody(request);}catch{return Response.json({error:'INVALID_REQUEST'},{status:400,headers});}
 if(!['login','register','logout','forgot','reset'].includes(data.action))return Response.json({error:'INVALID_REQUEST'},{status:400,headers});
 const jar=await cookies();const p=await service({op:data.action,data,token:jar.get('greenmine_session')?.value,client:request.headers.get('x-forwarded-for')?.split(',')[0].trim()||'local'});
 if(p.status===200&&typeof p.data.token==='string'){
  jar.set('greenmine_session',p.data.token,{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax',path:'/',maxAge:14*86400});delete p.data.token;
 }
 if(data.action==='logout'||data.action==='reset'&&p.status===200)jar.set('greenmine_session','',{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax',path:'/',maxAge:0});
 return Response.json(p.data,{status:p.status,headers});
}
