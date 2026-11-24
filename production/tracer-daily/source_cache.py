"""Read-only public PGA TOUR video catalog; no Semrush calls or paid API use."""
import re,json,time,hashlib,concurrent.futures,requests,unicodedata
from common import *
PROXIES=['http://127.0.0.1:7890','http://192.168.0.110:10808']
def get_session():
 for proxy in PROXIES:
  s=requests.Session();s.proxies={'http':proxy,'https':proxy};s.headers['User-Agent']='GolfCut-source-index/1.0 (+https://golfcut.goswie.com)'
  try:
   r=s.get('https://www.pgatour.com/robots.txt',timeout=10);r.raise_for_status();return s
  except requests.RequestException:pass
 raise RuntimeError('Both verified proxy routes are unavailable')
def classify(v):
 t=v['title'].lower()
 if re.search(r'interview|highlights|round recap|best shots|putt|sinks|winning|wins |discussion',t):return None
 for kind,pat in [('bunker',r'bunker|sand '),('chip',r'chips? |chip-in|pitch shot'),('approach',r'approach|iron |sticks |second shot|third shot'),('tee',r'tee shot|drive |drives |driving|aces |ace on|hole-in-one')]:
  if re.search(pat,t):return kind
 return None
def normalize(t):return ' '.join(unicodedata.normalize('NFKC',t).casefold().split())
def collect(day,max_pages=160):
 session=get_session();html=session.get('https://www.pgatour.com/watch',timeout=35);html.raise_for_status()
 scripts=re.findall(r'<script[^>]*src="([^"]+)',html.text);app=next(x for x in scripts if '/_app-' in x)
 js=session.get(app,timeout=35);js.raise_for_status()
 # Browser-public client identifier, used only for the same read-only catalog operation.
 key=re.search(r'"apiKey":"([^"]+)","queryEndpoint":"https://orchestrator.pgatour.com/graphql"',js.text)
 if not key:raise RuntimeError('Public catalog client schema changed')
 query='query Videos($limit:Int,$offset:Int){videos(tourCode:R,category:"competition",limit:$limit,offset:$offset){id title description shareUrl duration year roundNumber holeNumber shotNumber playerVideos{firstName lastName} franchise}}'
 pool=read(HOME/'keywords.json',{});seen={normalize(v['keyword']) for v in pool.values()};cache=HOME/'source-cache';cache.mkdir(exist_ok=True)
 fetched=0;failed=[];collected=0;target=config()['target'];available=lambda:sum(v['status']=='available' for v in pool.values())
 def fetch(offset):
  p=cache/f'catalog-{offset}.json'
  if p.exists() and time.time()-p.stat().st_mtime<21600:return offset,read(p),None
  for attempt in range(3):
   try:
    r=session.post('https://orchestrator.pgatour.com/graphql',headers={'x-api-key':key[1],'x-pgat-platform':'web'},json={'query':query,'variables':{'limit':100,'offset':offset}},timeout=35);r.raise_for_status();d=r.json()
    if d.get('errors'):raise ValueError('Catalog returned GraphQL errors')
    videos=d['data']['videos'];save(p,videos);return offset,videos,None
   except Exception as e:
    if attempt==2:return offset,[],type(e).__name__
    time.sleep(attempt+1)
 previous=read(HOME/'source-manifest.json',{})
 cursor=previous.get('archive_offset',previous.get('cached_pages',0)*100)
 offsets=list(dict.fromkeys(list(range(0,1200,100))+[x['offset'] for x in previous.get('failed_pages',[])]+list(range(max(1200,cursor),max(1200,cursor)+(max_pages-12)*100,100))))
 last_archive=cursor
 for start in range(0,len(offsets),4):
  with concurrent.futures.ThreadPoolExecutor(4) as ex:results=list(ex.map(fetch,offsets[start:start+4]))
  for offset,rows,error in results:
   fetched+=1;collected+=len(rows)
   if offset>=1200 and rows and not error:last_archive=max(last_archive,offset+100)
   if error:failed.append({'offset':offset,'error':error})
   for v in rows:
    kind=classify(v);name=normalize(v.get('title',''))
    if not kind or not v.get('shareUrl','').startswith('https://www.pgatour.com/video/') or not v.get('playerVideos') or not v.get('description') or len(name)<20:continue
    if v['id'] in pool or name in seen:continue
    seen.add(name);pool[v['id']]={'keyword':v['title'],'status':'available','source_url':v['shareUrl'],'source_kind':'public_video_catalog','kind':kind,'evidence':v,'fetched_at':now(),'evidence_sha256':hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()}
  save(HOME/'keywords.json',pool)
  progress(day,state='collecting',collected_count=collected,candidate_count=available(),source_fetch_incomplete_count=len(failed),keyword_sources=[{'url':'https://www.pgatour.com/watch','type':'public_video_catalog','cached_pages':fetched,'failures':failed}],note='Fresh GolfCut pool: public golf video metadata. No paid keyword queries; no legacy pool dependency.')
  if available()>=target+200:break
  if all(not rows and not error for _,rows,error in results):break
 save(HOME/'source-manifest.json',{'checked_at':now(),'source':'https://www.pgatour.com/watch','candidate_count':available(),'collected_count':collected,'failed_pages':failed,'cached_pages':fetched,'archive_offset':last_archive})
 return pool
if __name__=='__main__':
 import sys
 collect(sys.argv[1])
