"""Minute tick; all dates, quantities and times come from the controller-owned config."""
import fcntl,datetime,traceback
from zoneinfo import ZoneInfo
from common import *
from prepare import prepare,run,BUN
from release import stage,publish

def due(c,clock):
 today=clock.date().isoformat();jobs=[]
 if not c['enabled']:return jobs
 if (clock.hour,clock.minute)>=(c['hour'],c['minute']):jobs.append(('publish',today))
 if (clock.hour,clock.minute)>=(c['prepare_hour'],c['prepare_minute']):jobs.append(('prepare',(clock.date()+datetime.timedelta(days=1)).isoformat()))
 return jobs

def refresh_ready(day,r):
 work=Path(r['worktree'])
 run(['git','-c','http.proxy=http://127.0.0.1:7890','fetch','origin','main'],work)
 base=run(['git','rev-parse','origin/main'],work)
 progress(day,last_base_check_at=now())
 if base in [r['base_commit'],r['commit']]:return
 # Each day modifies shared generated hubs/sitemap. Rebase routinely conflicts
 # after today's release; rebuild the RESERVED batch on the new main instead.
 from keyword_pages import build_batch
 from release import check_manifest
 check_manifest(r)
 pool=read(HOME/'semrush-keyword-state.json',{})
 rows=[x for x in pool.values() if x.get('batch')==day and x.get('status')=='reserved']
 if len(rows)!=r['target']:raise RuntimeError('Reserved batch no longer matches target')
 refreshed=PROJECT/('website-seo-keywords-'+day.replace('-','')+'-'+base[:10])
 if refreshed.exists():raise RuntimeError('Reconciliation worktree already exists; preserved for inspection')
 run(['git','worktree','add','--detach',str(refreshed),base],work)
 import shutil
 runtime=refreshed/'production/tracer-daily';runtime.mkdir(parents=True,exist_ok=True)
 for source in Path(__file__).resolve().parent.iterdir():
  if source.is_file() and source.suffix in ('.py','.md'):shutil.copy2(source,runtime/source.name)
 build_batch(day,rows,refreshed,r['target'])
 stage(day)

def tick():
 c=config();clock=datetime.datetime.now(ZoneInfo(c['timezone']));state=read(HOME/'state.json',{'runs':[]});state['heartbeat']=now();state['schedule']={k:c[k] for k in ['enabled','target','hour','minute','prepare_hour','prepare_minute','timezone']};save(HOME/'state.json',state)
 # Revalidate prebuilt batches against production between publish ticks.
 if c['enabled'] and (clock.hour,clock.minute)!=(c['hour'],c['minute']):
  for delta in [0,1]:
   day=(clock.date()+datetime.timedelta(days=delta)).isoformat();r=read(HOME/(day+'-receipt.json'),{})
   checked=r.get('last_base_check_at')
   if r.get('state')=='ready' and r.get('input_kind')=='semrush_keywords_v1' and (not checked or (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(checked)).total_seconds()>=900):
    try:refresh_ready(day,r)
    except Exception as e:progress(day,state='rebase_required',blockers=[str(e)[-1500:]])
 jobs=due(c,clock)
 # Catch up today's failed preparation even after the release cutoff.
 # Tomorrow cannot consume inventory or build on an unpublished main.
 if c['enabled']:
  today=clock.date().isoformat();current=read(HOME/(today+'-receipt.json'),{})
  if current.get('state') not in ['ready','published','publishing','verifying','reconcile_required']:
   jobs.insert(0,('prepare',today))
 for action,day in jobs:
  if day>clock.date().isoformat() and read(HOME/(clock.date().isoformat()+'-receipt.json'),{}).get('state')!='published':continue
  r=read(HOME/(day+'-receipt.json'),{})
  if r.get('state')=='published':continue
  # Retrying source outages must not hammer upstream every minute.
  attempted=r.get('last_attempt_at')
  if attempted and r.get('last_attempt_action',action)==action and (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(attempted)).total_seconds()<900:continue
  if action=='publish' and (r.get('input_kind')!='semrush_keywords_v1' or r.get('state') not in ['ready','publishing','verifying','reconcile_required']):
   if not r:progress(day,state='missing_prepared_batch',blockers=['No validated version was prepared; publish tick will not build or publish partial content.'])
   continue
  progress(day,last_attempt_at=now(),last_attempt_action=action)
  try:
   if action=='prepare':
    if r.get('state') not in ['validated','stage_failed','staging','ready']:r=prepare(day)
    else:r=read(HOME/(day+'-receipt.json'))
    if r.get('state') in ['validated','stage_failed','staging']:stage(day)
   else:publish(day)
  except Exception as e:
   r=read(HOME/(day+'-receipt.json'),{})
   state='reconcile_required' if action=='publish' else 'stage_failed' if r.get('state') in ['validated','staging','stage_failed'] else 'failed'
   progress(day,state=state,blockers=[str(e)[-1500:]])
   traceback.print_exc()
if __name__=='__main__':
 with (HOME/'executor.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise SystemExit(0)
  tick()
