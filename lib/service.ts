import {spawn} from 'node:child_process';
import path from 'node:path';
export function service(input: unknown): Promise<{status:number;data:Record<string,unknown>}> {
 return new Promise(resolve=>{
  let output='';let ended=false;
  const child=spawn(/* turbopackIgnore: true */ process.env.PYTHON_EXECUTABLE||(process.platform==='win32'?'python':'python3'),[path.join(process.cwd(),'server/service.py')],{windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'},stdio:['pipe','pipe','pipe']});
  const finish=(status:number,data:Record<string,unknown>)=>{if(!ended){ended=true;clearTimeout(timer);resolve({status,data});}};
  const timer=setTimeout(()=>{child.kill();finish(504,{error:'ENGINE_TIMEOUT'});},55000);
  child.stdout.on('data',chunk=>{output+=chunk.toString();if(output.length>4_000_000){child.kill();finish(503,{error:'RESPONSE_TOO_LARGE'});}});
  child.stderr.on('data',()=>{}); child.stdin.on('error',()=>{});
  child.on('error',()=>finish(503,{error:'SERVICE_UNAVAILABLE'}));
  child.on('close',()=>{try{const p=JSON.parse(output);finish(p.status,p.data);}catch{finish(503,{error:'SERVICE_UNAVAILABLE'});}});
  child.stdin.end(JSON.stringify(input));
 });
}
export const headers={'Cache-Control':'no-store'};
export function validOrigin(request:Request){
 const expected=process.env.APP_ORIGIN||new URL(request.url).origin;
 return request.headers.get('origin')===expected;
}
export async function readBody(request:Request){
 if(Number(request.headers.get('content-length')||0)>2_000_000)throw Error();
 const raw=await request.text();if(Buffer.byteLength(raw)>2_000_000)throw Error();
 const body=JSON.parse(raw);if(!body||typeof body!=='object'||Array.isArray(body))throw Error();return body;
}
