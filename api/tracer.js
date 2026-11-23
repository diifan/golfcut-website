import {createHmac} from 'node:crypto';
export default async function handler(req,res){
 res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','application/json');
 const fail=(s,e)=>{res.statusCode=s;res.end(JSON.stringify({error:e}));};
 if(req.method!=='POST')return fail(405,'method_not_allowed');
 if(req.headers.origin!==`https://${req.headers.host}`)return fail(403,'origin_not_allowed');
 let b=req.body;try{if(typeof b==='string')b=JSON.parse(b);if(!b||Array.isArray(b)||Buffer.byteLength(JSON.stringify(b))>16384)throw Error();}catch{return fail(400,'invalid_request');}
 if(!['create','complete','status','process','download','cancel'].includes(b.action))return fail(400,'invalid_action');
 const secret=process.env.WEB_TRACER_SECRET;if(!secret)return fail(503,'not_configured');
 if(b.action==='create'){const ip=req.headers['x-vercel-forwarded-for'];if(typeof ip!=='string'||ip.includes(','))return fail(503,'trusted_ingress_required');b.data={...b.data,rate_key:createHmac('sha256',secret).update(ip).digest('hex')};}
 try{const r=await fetch('https://xdjdgqlqdabugwgnsugl.supabase.co/functions/v1/golfcut-web-tracer', {method:'POST',headers:{'Content-Type':'application/json','x-hc-web':secret},body:JSON.stringify({...b,environment:'production'}),signal:AbortSignal.timeout(15000),redirect:'error'});const body=await r.json();res.statusCode=r.status;res.end(JSON.stringify(body));}catch{return fail(503,'bridge_unavailable');}
}
