from pathlib import Path
import json,os,tempfile,datetime
ROOT=Path(__file__).resolve().parent
HOME=Path('/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily-golfcut')
REPORT=Path('/data/swi-algo/Swi-IP-Config/swie-app-mac/reports/seo-expansion-20261124')
PROJECT=Path('/data/swi-algo/Swi-App-Factory/GolfCut')
ORIGIN='https://golfcut.goswie.com'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p,default=None):return json.loads(p.read_text()) if p.exists() else default
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent)
 with os.fdopen(fd,'w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(name,p)
def config():
 c=read(HOME/'config.json');assert isinstance(c['target'],int) and c['target']>0
 for x,upper in [('hour',24),('minute',60),('prepare_hour',24),('prepare_minute',60)]:assert 0<=c[x]<upper
 return c
def progress(day,**updates):
 p=HOME/(day+'-receipt.json');r=read(p,{})
 r={'app':'golfcut','state':'collecting','day':day,'target':config()['target'],'generated_count':0,'validated_count':0,'published_count':0,'keyword_pool':str(HOME/'keywords.json'),'keyword_sources':[],'pages_path':None,'commit':None,'deployment_url':None,'schedule':{'config':str(HOME/'config.json')},'blockers':[],**r,**updates,'last_progress_at':now()}
 save(p,r);save(REPORT/'golfcut-receipt.json',r)
 s=read(HOME/'state.json',{'runs':[]});s['heartbeat']=now();s['runs']=[x for x in s.get('runs',[]) if x['day']!=day]+[{k:r[k] for k in ['day','target','state','generated_count','published_count']}];save(HOME/'state.json',s)
 text=f"# GolfCut SEO progress\n\nUpdated: {now()}\nState: {r['state']}\nTarget: {r['target']}\nCollected: {r.get('collected_count',0)}; candidates: {r.get('candidate_count',0)}\nGenerated: {r['generated_count']}; validated: {r['validated_count']}; published: {r['published_count']}\n\n{r.get('note','')}\n\nBlockers: {json.dumps(r['blockers'],ensure_ascii=False)}\n"
 tmp=REPORT/'golfcut-progress.md.tmp';tmp.write_text(text);tmp.replace(REPORT/'golfcut-progress.md');return r
