"""Read-only controller CSV, independently fetched evidence and isolated consumption state."""
import threading
import csv,hashlib,re,unicodedata,time,concurrent.futures,requests,fcntl,io,socket,ipaddress
from urllib.parse import urljoin
from urllib.parse import urlparse
from html.parser import HTMLParser
from common import *
from intent_router import route
from editorial_topics import topic,supported
_sessions=threading.local()
class InputPending(RuntimeError):pass
MAX_SOURCE_BYTES=3_000_000  # Measured Shot Tracer Wix HTML: 2,312,880 bytes; still bounded.
SOURCE_ROOT=PROJECT/'production/keyword-expansion'
def key(t):return ' '.join(unicodedata.normalize('NFKC',t).casefold().split())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def intent_key(word):
 tokens=re.findall(r'[a-z0-9]+',key(word));stop={'best','the','a','an','how','to','for','with','your','and','of','in','golf'}
 return ' '.join(sorted(t[:-1] if t.endswith('s') and len(t)>4 else t for t in tokens if t not in stop))
def venue_key(ev):
 profile=ev.get('course_profile')
 return key(profile['name']+' | '+profile['address']) if profile else None

def page_intent(word,url):
 return ('editorial:'+topic(word)) if topic(word) else source_intent(url)

def source_intent(url):
 u=urlparse(url);return u.hostname.lower().removeprefix('www.')+u.path.rstrip('/')
def metric(row,names):
 for name in names:
  if row.get(name) not in [None,'']:
   try:return float(str(row[name]).strip().replace(',','').rstrip('%'))
   except ValueError:raise ValueError('Invalid numeric '+name)
 raise ValueError('Missing metric '+names[0])
class TextParser(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.title=False;self.titles=[];self.parts=[]
 def handle_starttag(self,t,a):
  if t in ['script','style','nav','footer','header']:self.skip+=1
  if t=='title':self.title=True
 def handle_endtag(self,t):
  if t in ['script','style','nav','footer','header']:self.skip=max(0,self.skip-1)
  if t=='title':self.title=False
 def handle_data(self,d):
  if self.title:self.titles.append(d)
  if not self.skip and d.strip():self.parts.append(d.strip())
def allowed_url(url):
 cfg=read(SOURCE_ROOT/'config.json',{});domains={x.lower().removeprefix('www.') for x in cfg.get('domains',[])}
 u=urlparse(url);host=(u.hostname or '').lower()
 if u.scheme!='https' or u.username or u.password or u.port not in [None,443] or not host.isascii() or host.removeprefix('www.') not in domains:raise ValueError('Unregistered or unsafe HTTPS source URL')
 addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
 if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Source DNS resolves to a non-public address')
 return url

def fetch_evidence(url):
 result={'url':url,'checked_at':time.time(),'ok':False}
 try:allowed_url(url)
 except Exception as e:return {**result,'error':str(e)}
 p=HOME/'keyword-evidence'/(hashlib.sha256(url.encode()).hexdigest()+'.json');old=read(p,{})
 if old and ('/golf-courses/club/' not in url or 'course_profile' in old) and time.time()-old.get('checked_at',0)<(86400*7 if old.get('ok') else 1800):
  if old.get('resolved_url'):allowed_url(old['resolved_url'])
  return old
 for proxy in ['http://127.0.0.1:7890','http://192.168.0.110:10808']:
  try:
   session=getattr(_sessions,'session',None)
   if session is None:session=requests.Session();session.trust_env=False;_sessions.session=session
   current=url
   for hop in range(6):
    allowed_url(current)
    with session.get(current,timeout=(8,20),stream=True,allow_redirects=False,proxies={'https':proxy},headers={'User-Agent':'GolfCut-reference-check/1.0 (+https://golfcut.goswie.com)'}) as r:
     if r.status_code in [301,302,303,307,308]:
      current=urljoin(current,r.headers.get('Location',''));allowed_url(current);continue
     r.raise_for_status()
     if 'html' not in r.headers.get('Content-Type',''):raise ValueError('Source is not HTML')
     if int(r.headers.get('Content-Length','0'))>MAX_SOURCE_BYTES:raise ValueError('Source exceeds byte limit')
     chunks=[];size=0
     for chunk in r.iter_content(32768):
      size+=len(chunk)
      if size>MAX_SOURCE_BYTES:raise ValueError('Source exceeds streamed byte limit')
      chunks.append(chunk)
     raw=b''.join(chunks);text=raw.decode(r.encoding or 'utf-8',errors='replace');break
   else:raise ValueError('Source redirect limit exceeded')
   parser=TextParser();parser.feed(text);title=' '.join(parser.titles);body=' '.join(parser.parts)
   if len(body)<200 or not title:raise ValueError('Insufficient source text')
   result.update(ok=True,title=title,text=body[:80000],resolved_url=current,sha256=hashlib.sha256(raw).hexdigest())
   if '/golf-courses/club/' in url:
    from course_profiles import extract
    result['course_profile']=extract(text,url)
   break
  except Exception as e:result['error']=str(e)[:250]
 save(p,result);return result

def keyword_intent(word):
 norm=key(word)
 if topic(word):return True
 # Reject unrelated purchase/navigation/person searches instead of attaching a tracer paragraph.
 if re.search(r'\b(net worth|wife|girlfriend|salary|tuition|admission|application fee|scholarship amount|jobs|tickets|leaderboard|live scores)\b',norm):return False
 if re.search(r'\b(?:apple watch|smartwatch|sensors?|rangefinders?|gps|arccos|devices?)\b',norm) and not re.search(r'\b(?:video|filming|recording|tracer)\b',norm):return False
 if not re.search(r'tracer|track.*ball|ball.*track|swing|shot|filming|film |record|camera|video|highlights|reel|pitch|chipping|bunker|draw|fade',norm):return False
 return True

def relevance(word,ev):
 if ev.get('course_profile'):
  from course_profiles import aligned
  return aligned(word,ev['course_profile'])
 if topic(word):return supported(word,ev)
 norm=key(word);text=key(ev.get('title','')+' '+ev.get('text',''))
 if not keyword_intent(word) or not re.search(r'\bgolf\b|\bgolfer',text):return False
 from evidence_text import context_excerpt
 try:context_excerpt(word,ev.get('text',''))
 except ValueError:return False
 terms={x for x in re.findall(r'[a-z0-9]+',norm) if len(x)>2 and x not in {'the','and','for','with','best','how','can','you','your','golf'}}
 return bool(terms) and sum(t in text for t in terms)/len(terms)>=0.6

def load_candidates(day):
 HOME.mkdir(parents=True,exist_ok=True)
 with (HOME/'keyword-pool.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  return _load_candidates(day)
def _load_candidates(day):
 binding=read(HOME/'input-binding.json',{})
 csvpath=Path(binding.get('keywords_csv',SOURCE_ROOT/'keywords.csv'));mp=Path(binding.get('source_manifest',SOURCE_ROOT/'manifest.json'))
 if not csvpath.is_file() or not mp.is_file():raise InputPending('Controller CSV/manifest is not yet present')
 lockpath=csvpath.parent/'run.lock'
 with lockpath.open('rb') as source_lock:
  fcntl.flock(source_lock,fcntl.LOCK_SH)
  csvraw=csvpath.read_bytes();mraw=mp.read_bytes();csvsha=hashlib.sha256(csvraw).hexdigest();msha=hashlib.sha256(mraw).hexdigest();manifest=json.loads(mraw)
  rows=list(csv.DictReader(io.StringIO(csvraw.decode('utf-8-sig'))))
  source_bytes={str(Path(src['path'])):Path(src['path']).read_bytes() for src in manifest.get('sources',[])}
 if manifest.get('app') not in [None,'golfcut'] or manifest.get('sport') not in [None,'golf']:raise ValueError('Wrong app/sport manifest')
 # Manifest and each export are read afresh each round. No pinned first-import hash.
 sources={str(Path(s['path'])):s for s in manifest.get('sources',[])}
 original_rows={};alternatives={}
 for path,source in sources.items():
  raw=source_bytes[path]
  if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Original export hash mismatch: '+path)
  index=set()
  for original in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
   word=original.get('Keyword') or original.get('keyword') or ''
   try:kd=metric(original,['Keyword Difficulty','kd']);volume=metric(original,['Search Volume','volume'])
   except ValueError:continue
   url=original.get('URL') or original.get('evidence_url') or original.get('url') or ''
   index.add((key(word),kd,volume,url.strip()))
   if word and 0<=kd<30 and volume>100:
    alternatives.setdefault(key(word),[]).append({'keyword':word,'kd':kd,'volume':volume,'evidence_url':url.strip(),'source':path,'source_sha256':source['sha256'],'metric_timestamp':original.get('Timestamp','')})
  original_rows[path]=index
 pool=read(HOME/'semrush-keyword-state.json',{});seen={key(v['keyword']) for v in pool.values()};occupied_urls={page_intent(v['keyword'],v['source_url']) for v in pool.values() if v.get('status') in ['published','reserved']};occupied_intents={intent_key(v['keyword']) for v in pool.values() if v.get('status') in ['published','reserved']}
 controller_count=len(rows);expanded=[]
 for row in rows:
  expanded.append(row)
  if row.get('status','').lower() in ('published','reserved','used') or row.get('batch_id'):continue
  existing_urls={row.get('evidence_url')}
  for option in alternatives.get(key(row.get('keyword','')),[]):
   if option['evidence_url'] in existing_urls:continue
   existing_urls.add(option['evidence_url']);expanded.append({**row,**option})
 rows=expanded
 counts={'source_alternatives':len(rows)-controller_count,'raw':controller_count,'metric_rejected':0,'duplicate':0,'evidence_pending':0,'unrelated':0,'intent_rejected':0,'evidence_rejected':0,'added':0,'controller_occupied':0,'needs_template':0,'needs_review':0,'freshness_required':0,'specialist_review':0};pending=[];candidates=[];review_queue=[]
 for row in rows:
  word=row.get('keyword','').strip();norm=key(word)
  try:kd=metric(row,['kd']);volume=metric(row,['volume'])
  except ValueError:counts['metric_rejected']+=1;continue
  if not word or not (0<=kd<30 and volume>100):counts['metric_rejected']+=1;continue
  if row.get('status','').lower() in ['published','reserved','used'] or row.get('batch_id'):counts['controller_occupied']+=1;continue
  source=row.get('source','');declared=sources.get(str(Path(source)))
  if not declared or row.get('source_sha256')!=declared.get('sha256'):raise ValueError('Row source provenance mismatch: '+word)
  url=row.get('evidence_url','').strip()
  if (norm,kd,volume,url) not in original_rows[str(Path(source))]:raise ValueError('Forged or unmatched keyword/metrics/evidence URL row: '+word)
  if urlparse(url).scheme not in ['https','http'] or not urlparse(url).hostname:counts['evidence_pending']+=1;continue
  if norm in seen:
   # Metrics/source may be refreshed, but workflow status is never overwritten.
   existing=next(v for v in pool.values() if key(v['keyword'])==norm)
   if existing['status'] in ['published','reserved']:counts['duplicate']+=1;continue
  if page_intent(word,url) in occupied_urls or intent_key(word) in occupied_intents:counts['duplicate']+=1;continue
  if not keyword_intent(word) and not (urlparse(url).hostname=='18birdies.com' and re.fullmatch(r'/golf-courses/club/[^/]+/[^/]+/?',urlparse(url).path)):
   decision=route(word,url,'golf');state=decision['routing_state'];state='needs_template' if state=='content_candidate' else state;decision['routing_state']=state
   if state=='out_of_scope':counts['unrelated']+=1;counts['intent_rejected']+=1
   else:
    counts[state]+=1;review_queue.append({**row,**decision})
   continue
  candidates.append((row,kd,volume,url,norm))
 unique_urls=list(dict.fromkeys(x[3] for x in candidates));evidence={};fetch_urls=[];new_requests=0
 for url in unique_urls:
  cached=read(HOME/'keyword-evidence'/(hashlib.sha256(url.encode()).hexdigest()+'.json'),{})
  fresh=cached and time.time()-cached.get('checked_at',0)<(86400*7 if cached.get('ok') else 1800)
  if fresh or new_requests<500:
   fetch_urls.append(url);new_requests+=int(not fresh)
  else:evidence[url]={'ok':False,'error':'Pending bounded source harvest; resumes next tick'}
 with concurrent.futures.ThreadPoolExecutor(8) as ex:
  for i,(url,ev) in enumerate(zip(fetch_urls,ex.map(fetch_evidence,fetch_urls)),1):
   evidence[url]=ev
   if i%100==0:progress(day,state='fetching_keyword_evidence',source_fetch_completed=i,source_fetch_target=len(fetch_urls))
 # One source intent per page; do not create keyword variants of the same source.
 accepted_urls=set(occupied_urls);accepted_norms=set();accepted_intents=set(occupied_intents)
 accepted_venues={venue_key(v.get('evidence',{})) for v in pool.values() if v.get('status') in ('reserved','published')};accepted_venues.discard(None)
 for row,kd,volume,url,norm in sorted(candidates,key=lambda x:-x[2]):
  ev=evidence[url]
  if not ev.get('ok'):counts['evidence_pending']+=1;pending.append({'keyword':row['keyword'],'url':url,'error':ev.get('error')});continue
  if not relevance(row['keyword'],ev):counts['unrelated']+=1;counts['evidence_rejected']+=1;continue
  venue=venue_key(ev)
  if (venue and venue in accepted_venues) or norm in accepted_norms or page_intent(row['keyword'],url) in accepted_urls or intent_key(row['keyword']) in accepted_intents:counts['duplicate']+=1;continue
  if venue:accepted_venues.add(venue)
  accepted_norms.add(norm);accepted_urls.add(page_intent(row['keyword'],url));accepted_intents.add(intent_key(row['keyword']));identity=hashlib.sha256(norm.encode()).hexdigest()[:24];old=pool.get(identity,{})
  pool[identity]={**old,'keyword':row['keyword'],'keyword_id':identity,'status':old['status'] if old.get('status') in ('reserved','published') else 'available','input_kind':'semrush_keywords_v1','kd':kd,'volume':volume,'metric_timestamp':row.get('metric_timestamp'),'source_url':url,'source_export':row['source'],'source_export_sha256':row['source_sha256'],'source_manifest':str(mp),'source_csv_sha256':csvsha,'evidence':ev,'evidence_sha256':ev['sha256'],'added_at':old.get('added_at',now()),'active_import':csvsha}
  counts['added']+=int(not old)
 with lockpath.open('rb') as source_lock:
  fcntl.flock(source_lock,fcntl.LOCK_SH)
  if digest(csvpath)!=csvsha or digest(mp)!=msha or any(digest(path)!=sources[path]['sha256'] for path in sources):raise InputPending('Controller files changed during import; retry next round')
 # Keep stored availability consistent with the fresh policy, preserving occupied rows.
 for v in pool.values():
  if v['status']=='available' and key(v['keyword']) not in accepted_norms:v['status']='excluded'
 # Available rows not present/qualified in this fresh snapshot cannot satisfy capacity.
 available={i:v for i,v in pool.items() if v['status']=='available' and v.get('active_import')==csvsha and key(v['keyword']) in accepted_norms}
 save(HOME/'intent-review-queue.json',{'at':now(),'keywords_sha256':csvsha,'rows':review_queue})
 save(HOME/'semrush-keyword-state.json',pool)
 save(HOME/'input-import-receipt.json',{'at':now(),'keywords_csv':str(csvpath),'keywords_sha256':csvsha,'manifest_sha256':msha,'counts':counts,'pending_evidence':pending,'eligible_available':len(available)})
 capacity=csvpath.parent/'capacity.json';save(capacity,{'checked_at':time.time(),'eligible_available':len(available)},mode=0o640)
 progress(day,input_kind='semrush_keywords_v1',keyword_pool=str(csvpath),keyword_state=str(HOME/'semrush-keyword-state.json'),keyword_sources=list(sources.values()),candidate_count=len(available),source_fetch_incomplete_count=counts['evidence_pending'],keyword_filter_counts=counts)
 # Keep reservations available to the batch restart, without offering stale available rows.
 return {**{i:v for i,v in pool.items() if v['status'] in ['reserved','published']},**available}
