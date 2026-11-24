"""Read-only handoff from controller-owned production/keyword-expansion.
Binding paths live beside (not inside) the controller-owned source tree.
"""
import csv,hashlib,re,unicodedata
from urllib.parse import urlparse
from common import *
class InputPending(RuntimeError):pass
def key(t):return ' '.join(unicodedata.normalize('NFKC',t).casefold().split())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def metric(row,names):
 for name in names:
  if row.get(name) not in [None,'']:
   s=str(row[name]).strip().replace(',','').rstrip('%')
   try:return float(s)
   except ValueError:raise ValueError('Invalid numeric '+name)
 raise ValueError('Missing metric '+names[0])
def load_candidates(day):
 binding=read(HOME/'input-binding.json',{})
 if not binding.get('keywords_csv') or not binding.get('source_manifest'):raise InputPending('Awaiting controller keywords.csv and evidence/source manifest paths; video-title inputs are disabled.')
 csvpath=Path(binding['keywords_csv']);mp=Path(binding['source_manifest'])
 if not csvpath.is_file() or not mp.is_file():raise InputPending('Configured CSV/manifest is not yet present')
 manifest=read(mp);csvsha=digest(csvpath)
 if manifest.get('keywords_sha256')!=csvsha:raise ValueError('Keyword CSV SHA256 does not match source manifest')
 sources=manifest.get('sources',[])
 if not sources:raise ValueError('Original Semrush export provenance is missing')
 for src in sources:
  if src.get('provider','').casefold()!='semrush':raise ValueError('Keyword metrics must come from Semrush')
  if not src.get('local_path') or digest(src['local_path'])!=src.get('sha256'):raise ValueError('Original source export missing or hash mismatch')
 evidence=manifest.get('evidence',{})
 if isinstance(evidence,list):evidence={key(x['keyword']):x for x in evidence}
 else:evidence={key(k):v for k,v in evidence.items()}
 # Optional separate evidence file, also hash-bound.
 if manifest.get('evidence_file'):
  ep=Path(manifest['evidence_file'])
  if digest(ep)!=manifest.get('evidence_sha256'):raise ValueError('Evidence file hash mismatch')
  ev=read(ep);evidence={key(x['keyword']):x for x in ev} if isinstance(ev,list) else {key(k):v for k,v in ev.items()}
 statepath=HOME/'semrush-keyword-state.json';pool=read(statepath,{})
 seen={key(v['keyword']) for v in pool.values()};counts={'raw':0,'metric_rejected':0,'duplicate':0,'evidence_pending':0,'unrelated':0,'added':0};pending=[]
 # Keep historical video identities excluded from new candidate inventory without altering their states.
 historical={key(v['keyword']) for v in read(HOME/'keywords.json',{}).values()}
 with csvpath.open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
   counts['raw']+=1;word=(row.get('keyword') or row.get('Keyword') or '').strip();norm=key(word)
   if not norm:continue
   try:kd=metric(row,['kd','keyword_difficulty','Keyword Difficulty']);volume=metric(row,['volume','search_volume','Search Volume'])
   except ValueError:counts['metric_rejected']+=1;continue
   if not (0<=kd<30 and volume>100):counts['metric_rejected']+=1;continue
   if norm in seen or norm in historical:counts['duplicate']+=1;continue
   url=row.get('source_url') or row.get('url') or row.get('URL');ev=evidence.get(norm)
   if not url or urlparse(url).scheme!='https' or not ev or ev.get('url')!=url or not ev.get('title') or len(ev.get('text',''))<200:
    counts['evidence_pending']+=1;pending.append({'keyword':word,'url':url,'reason':'missing corresponding fetched source evidence'});continue
   if ev.get('sport')!='golf' or not ev.get('tracer_relevance'):
    counts['unrelated']+=1;continue
   # Exact source/topic alignment is required; broad golf relevance alone is insufficient.
   terms={x for x in re.findall(r'[a-z0-9]+',norm) if len(x)>2 and x not in {'the','and','for','with','best'}}
   source_text=key(ev['title']+' '+ev['text'])
   if terms and sum(t in source_text for t in terms)/len(terms)<0.6:
    counts['unrelated']+=1;continue
   identity=hashlib.sha256(norm.encode()).hexdigest()[:24]
   pool[identity]={'keyword':word,'keyword_id':identity,'status':'available','input_kind':'semrush_keywords_v1','kd':kd,'volume':volume,'source_url':url,'source_manifest':str(mp),'source_csv_sha256':csvsha,'evidence':ev,'evidence_sha256':hashlib.sha256(json.dumps(ev,sort_keys=True).encode()).hexdigest(),'added_at':now()};seen.add(norm);counts['added']+=1
 if digest(csvpath)!=csvsha:raise ValueError('Input CSV changed during import; retry with stable export')
 save(statepath,pool);save(HOME/'input-import-receipt.json',{'at':now(),'keywords_csv':str(csvpath),'keywords_sha256':csvsha,'source_manifest':str(mp),'counts':counts,'pending_evidence':pending})
 progress(day,input_kind='semrush_keywords_v1',keyword_pool=str(csvpath),keyword_state=str(statepath),keyword_sources=sources,candidate_count=sum(v['status']=='available' for v in pool.values()),source_fetch_incomplete_count=counts['evidence_pending'],keyword_filter_counts=counts)
 return pool
