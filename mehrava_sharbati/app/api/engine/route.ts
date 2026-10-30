import {cookies} from 'next/headers';
import {service,headers,validOrigin,readBody} from '../../../lib/service';
export const runtime='nodejs';
export const maxDuration=60;
export async function POST(request:Request){
 if(!validOrigin(request))return Response.json({error:'INVALID_ORIGIN'},{status:403,headers});
 let data;try{data=await readBody(request);}catch{return Response.json({error:'INVALID_REQUEST'},{status:400,headers});}
 const token=(await cookies()).get('greenmine_session')?.value;
 const p=await service({op:'engine',token,data});
 return Response.json(p.data,{status:p.status,headers});
}
