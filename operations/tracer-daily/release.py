"""Stage validated production deployment, promote only ready immutable batch, verify and fast-forward Git."""
import subprocess,os,json,re,time,hashlib,concurrent.futures,requests
from zoneinfo import ZoneInfo
from common import *
from prepare import run
VC='/var/lib/swi-codex/agent-relay/bin/vercel';PID='prj_mMHI2xwzfbZyFZBhTRrLg0DsraCR';TEAM='team_eGIdbsMLrcfsmcds8FCKJZ5t';SCOPE='diifans-projects'
def cli(args,work):return run([VC]+args+['--scope',SCOPE],work)
def api(path,work):
 text=cli(['api',path],work);start=text.find('{');return json.loads(text[start:])
def check_manifest(r):
 p=Path(r['pages_path'])
 if hashlib.sha256(p.read_bytes()).hexdigest()!=r['pages_sha256']:raise RuntimeError('Batch manifest changed')
 rows=read(p)
 if len(rows)!=r['target'] or r['validated_count']!=r['target']:raise RuntimeError('Batch not fully validated')
 work=Path(r['worktree'])
 for row in rows:
  f=work/'public/shot-library'/row['slug']/'index.html'
  if hashlib.sha256(f.read_bytes()).hexdigest()!=row['file_sha256']:raise RuntimeError('Validated page changed')
 return rows

def stage(day):
 r=read(HOME/(day+'-receipt.json'));work=Path(r['worktree']);check_manifest(r)
 if r['state'] in ['ready','published']:return r
 if r['state'] not in ['validated','staging','stage_failed']:raise RuntimeError('Batch must pass build before staging')
 save(work/'.vercel/project.json',{'projectId':PID,'orgId':TEAM,'projectName':'golfcut-website'})
 # Reconcile uncertain uploads before retrying; never create a deployment storm.
 listings=api('/v6/deployments?projectId='+PID+'&limit=100',work)
 matches=[d for d in listings.get('deployments',[]) if d.get('meta',{}).get('swieBatch')=='golfcut-'+day and d.get('meta',{}).get('swieCommit')==r['commit'] and d.get('state') not in ['ERROR','CANCELED']]
 if matches:did=matches[0]['uid']
 else:
  progress(day,state='staging',blockers=[])
  result=cli(['deploy','--prod','--skip-domain','--archive=tgz','--yes','--meta','swieBatch=golfcut-'+day,'--meta','swieCommit='+r['commit']],work)
  urls=re.findall(r'https://golfcut-website-[a-zA-Z0-9-]+\.vercel\.app',result)
  if not urls:raise RuntimeError('Deployment response had no URL; next retry will reconcile metadata')
  did=urls[-1].split('://')[1]
 d=api('/v13/deployments/'+did,work)
 if d.get('projectId')!=PID or d.get('target')!='production' or d.get('meta',{}).get('swieCommit')!=r['commit']:raise RuntimeError('Deployment project/environment/commit mismatch')
 if d.get('readyState')!='READY':raise RuntimeError('Deployment not READY: '+str(d.get('readyState')))
 return progress(day,state='ready',deployment_id=d['id'],deployment_url='https://'+d['url'],blockers=[])

def publish(day,immediate=False):
 r=read(HOME/(day+'-receipt.json'));c=config();clock=datetime.datetime.now(ZoneInfo(c['timezone']))
 if not c['enabled']:return r
 if r.get('state')=='published':return r
 if not immediate and (clock.date().isoformat()!=day or (clock.hour,clock.minute)<(c['hour'],c['minute'])):return r
 if r['target']!=c['target']:raise RuntimeError('Configured target changed after preparation; rebuild required')
 if r['state'] not in ['ready','publishing','verifying','reconcile_required']:raise RuntimeError('Only a ready prebuilt version can publish')
 rows=check_manifest(r);work=Path(r['worktree'])
 run(['git','-c','http.proxy=http://127.0.0.1:7890','fetch','origin','main'],work)
 base=run(['git','rev-parse','origin/main'],work)
 if base not in [r['base_commit'],r['commit']]:raise RuntimeError('Production main advanced; preserve latest production and rebuild batch')
 d=api('/v13/deployments/'+r['deployment_id'],work)
 if d.get('readyState')!='READY' or d.get('projectId')!=PID or d.get('meta',{}).get('swieCommit')!=r['commit']:raise RuntimeError('Prepared deployment identity mismatch')
 progress(day,state='publishing',blockers=[])
 cli(['promote',r['deployment_id'],'--yes','--timeout','3m'],work)
 alias=api('/v4/aliases/golfcut.goswie.com',work)
 if alias.get('deploymentId')!=r['deployment_id']:raise RuntimeError('Production alias does not point to prepared deployment')
 progress(day,state='verifying')
 session=requests.Session();session.proxies={'https':'http://127.0.0.1:7890'}
 sm=session.get(ORIGIN+'/sitemap.xml',timeout=40);sm.raise_for_status();urls=set(re.findall(r'<loc>(.*?)</loc>',sm.text));expected={ORIGIN+'/shot-library/'+x['slug'] for x in rows}
 if not expected.issubset(urls):raise RuntimeError('Live sitemap missing batch URLs')
 def verify(row):
  url=ORIGIN+'/shot-library/'+row['slug']
  for attempt in range(3):
   try:
    res=session.get(url,timeout=30);res.raise_for_status()
    if hashlib.sha256(res.content).hexdigest()!=row['file_sha256']:raise ValueError('Live HTML differs from validated version')
    return None
   except Exception as e:
    if attempt==2:return {'url':url,'error':type(e).__name__}
    time.sleep(attempt+1)
 errors=[];verified=0
 with concurrent.futures.ThreadPoolExecutor(8) as ex:
  for error in ex.map(verify,rows):
   if error:errors.append(error)
   else:verified+=1
   if (verified+len(errors))%50==0:progress(day,state='verifying',live_verified_count=verified,live_verification_errors=errors)
 if errors:raise RuntimeError('Live HTML verification failed for '+str(len(errors))+' pages')
 # Git reconciliation uses fast-forward only; no change to the inference worktree.
 if base!=r['commit']:run(['git','-c','http.proxy=http://127.0.0.1:7890','push','origin',r['commit']+':refs/heads/main'],work)
 remote=run(['git','-c','http.proxy=http://127.0.0.1:7890','ls-remote','origin','refs/heads/main'],work).split()[0]
 if remote!=r['commit']:raise RuntimeError('Git remote commit verification failed')
 pool=read(HOME/'keywords.json',{})
 for row in rows:pool[row['video_id']].update(status='published',published_at=now(),url=ORIGIN+'/shot-library/'+row['slug'])
 save(HOME/'keywords.json',pool)
 return progress(day,state='published',published_count=len(rows),live_verified_count=verified,blockers=[],checks={**r.get('checks',{}),'live_sitemap_batch_count':len(expected&urls),'live_html_hash_count':verified,'vercel_project':PID,'alias_deployment_id':r['deployment_id'],'github_main':remote},public_examples=list(sorted(expected))[:3])
if __name__=='__main__':
 import argparse,fcntl
 a=argparse.ArgumentParser();a.add_argument('action',choices=['stage','publish']);a.add_argument('--day',required=True);a.add_argument('--immediate',action='store_true');args=a.parse_args()
 with (HOME/'executor.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:stage(args.day) if args.action=='stage' else publish(args.day,args.immediate)
  except Exception as e:
   r=read(HOME/(args.day+'-receipt.json'));progress(args.day,state='stage_failed' if args.action=='stage' else 'reconcile_required',blockers=[str(e)[-1500:]]);raise
