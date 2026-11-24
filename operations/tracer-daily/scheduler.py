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
 try:run(['git','rebase','--onto',base,r['base_commit']],work)
 except Exception:
  run(['git','rebase','--abort'],work)
  raise RuntimeError('Concurrent production edit conflicts with SEO batch; preserved both versions, reconciliation required')
 log=run([BUN,'run','build'],work);(HOME/(day+'-build.log')).write_text(log)
 progress(day,state='validated',base_commit=base,commit=run(['git','rev-parse','HEAD'],work),deployment_id=None,deployment_url=None)
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
 for action,day in due(c,clock):
  r=read(HOME/(day+'-receipt.json'),{})
  if r.get('state')=='published':continue
  # Retrying source outages must not hammer upstream every minute.
  attempted=r.get('last_attempt_at')
  if attempted and (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(attempted)).total_seconds()<900:continue
  if action=='publish' and (r.get('input_kind')!='semrush_keywords_v1' or r.get('state') not in ['ready','publishing','verifying','reconcile_required']):
   if not r:progress(day,state='missing_prepared_batch',blockers=['No validated version was prepared; publish tick will not build or publish partial content.'])
   continue
  progress(day,last_attempt_at=now())
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
