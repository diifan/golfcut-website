export default async function handler(req,res){
 res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','application/json');
 const fail=(status,error)=>{res.statusCode=status;res.end(JSON.stringify({error}));};
 if(req.method!=='POST')return fail(405,'method_not_allowed');
 const key=req.headers['x-hc-worker'];if(typeof key!=='string'||!/^[A-Za-z0-9_-]{40,100}$/.test(key))return fail(401,'unauthorized');
 let b=req.body;try{if(typeof b==='string')b=JSON.parse(b);if(!b||Array.isArray(b)||Buffer.byteLength(JSON.stringify(b))>65536)throw Error();}catch{return fail(400,'invalid_request');}
 if(!['poll','heartbeat','finish','artifact','cleanup'].includes(b.action))return fail(400,'invalid_action');
 try{const r=await fetch('https://xdjdgqlqdabugwgnsugl.supabase.co/functions/v1/golfcut-web-tracer',{method:'POST',headers:{'Content-Type':'application/json','x-hc-worker':key},body:JSON.stringify({...b,environment:'production'}),signal:AbortSignal.timeout(15000),redirect:'error'});res.statusCode=r.status;res.end(JSON.stringify(await r.json()));}catch{return fail(503,'bridge_unavailable');}
}
