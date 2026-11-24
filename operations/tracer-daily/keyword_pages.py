"""Real keyword -> source-specific recording guide -> existing Bun build -> immutable batch."""
import re,hashlib,html,fcntl
from common import *
from keyword_input import load_candidates,InputPending,key
from content_engine import layout,CSS,JS

def slug(row):return re.sub(r'[^a-z0-9]+','-',row['keyword'].lower()).strip('-')[:110]+'-'+row['keyword_id'][:10]
def plan(word):
 w=word.lower()
 if re.search('recruit|highlight|reel',w):return ('Recruiting and highlight footage',['Keep a complete swing in each selected clip so the viewer can see setup, contact and finish.','Use an orderly sequence of clearly labelled shots; retain the original recordings alongside the edited reel.','Review whether a tracer helps the viewer follow the ball. It should not hide the swing or imply a result the recording does not show.'])
 if re.search('chip|pitch|bunker|sand',w):return ('Short-game recording',['Frame both the starting ball and the near landing area when possible, without placing the camera in the playing area.','Keep the camera steady through contact. Sand, grass and the club can temporarily hide the ball.','Separate visible flight from bounce and roll when reviewing an overlay. Do not extend a trajectory through an obstruction.'])
 if re.search('draw|fade|slice|hook',w):return ('Reviewing visible ball flight',['Record from a steady position behind the ball with room above the target line.','Distinguish the launch direction from any later curvature you can actually see in the same camera view.','A phone-video overlay does not diagnose the swing or measure a shot. Use the source guidance for technique context and keep the original footage for review.'])
 if re.search('slow|swing|analysis',w):return ('Swing-video review',['Keep the complete swing in frame, including the club at the top and the balanced finish.','Use a stable camera position for a comparison; changing the viewing angle can change how the same movement appears.','Retain an unedited clip. A ball-flight tracer and a swing analysis answer different questions; inspect the original movement separately.'])
 if re.search('camera|film|record|tripod',w):return ('Camera setup',['Position the camera safely outside the swing area before the shot begins.','Include the ball, player and enough space for the expected launch; avoid panning or zooming during contact.','Review a short test recording at full size before a longer session. Check ball visibility, exposure and framing rather than assuming the phone captured it.'])
 return ('Tracer editing workflow',['Choose an original, continuous golf shot in which the ball is visible around impact.','Keep an unedited copy and identify the exact hit moment before applying an overlay.','Review where the ball stops being observable. Do not treat an inferred continuation or an edited camera cut as measured flight.'])

def render(template,row,related,fixture=False):
 from html import escape as E
 word=row['keyword'];topic,steps=plan(word);ev=row['evidence'];path='/golf-guides/'+slug(row);title=word[0].upper()+word[1:]+' — video guide | GolfCut';desc='A golf video recording and tracer checklist for '+word+'. Includes a relevant source, practical capture steps and review limits.'
 # One short attributed excerpt; never republish the source article or infer athlete facts.
 sentences=re.split(r'(?<=[.!?])\s+',ev['text']);terms=set(re.findall(r'[a-z]{4,}',word.lower()))
 sentence=max(sentences,key=lambda s:sum(t in s.lower() for t in terms));excerpt=' '.join(sentence.split()[:20])
 body='<section class="sub-hero"><p class="eyebrow">GOLF VIDEO GUIDE'+(' · TEST FIXTURE — NOT FOR PUBLICATION' if fixture else '')+'</p><h1>'+E(word[0].upper()+word[1:])+'</h1><p>Use this recording checklist to make useful golf footage for '+E(word)+'. The linked source provides topic context; the steps below focus on capturing and reviewing your own video.</p></section><article class="article-body"><h2>Source context for this topic</h2><p><a href="'+E(row['source_url'],quote=True)+'" rel="noopener noreferrer">'+E(ev['title'])+'</a></p><blockquote>'+E(excerpt)+'…</blockquote><p>This short excerpt identifies the relevant source context. Read the original for its complete explanation. GolfCut does not claim affiliation with the publisher or independently measured results from its material.</p><h2>'+E(topic)+'</h2><ol>'+''.join('<li>'+E(step)+'</li>' for step in steps)+'</ol>'
 body+='<h2>Plan what your own clip must show</h2><p>Before recording, decide which part of '+E(word)+' you want to review. Keep the observable event in one camera view. If the ball disappears or the clip changes angle, note that limit instead of filling the gap with an assumed flight.</p><form class="shot-notes" data-shot="'+row['keyword_id']+'"><label>Impact time (seconds)<input name="impact" type="number" min="0" step="0.01"></label><label>Last visible ball (seconds)<input name="visible" type="number" min="0" step="0.01"></label><label>Camera view<select name="camera"><option value="unknown">Not checked</option><option value="steady">One steady view</option><option value="moving">Moving camera</option><option value="cut">Camera cut</option></select></label><label>Recording notes<textarea name="notes" rows="4"></textarea></label><button class="btn" type="submit">Check recording plan</button><output aria-live="polite"></output><button type="button" data-download-notes>Download notes</button></form><p>Your worksheet runs in this browser. It does not upload the entries or analyse video.</p>'
 body+='<h2>Use the GolfCut online trial</h2><ol><li>Use your own footage or footage you have permission to edit.</li><li>Trim a single shot to 30 seconds or less.</li><li>Mark the impact moment and starting ball position in the trial.</li><li>Review the output for detection errors before sharing. The overlay is not a distance measurement or proof of the landing point.</li></ol><p><a class="btn" href="/try-tracer">Try your golf clip</a> <a href="/golf-shot-tracer">Golf shot tracer overview</a></p><h2>Related recording guides</h2><ul>'+''.join('<li><a href="/golf-guides/'+slug(x)+'">'+E(x['keyword'])+'</a></li>' for x in related)+'</ul><p><a href="/golf-guides">Browse golf video guides</a></p></article>'
 return layout(template,path,title,desc,body).replace('href="/shot-library"','href="/golf-guides"').replace('>Shot library<','>Golf video guides<').replace('/shot-library.css','/golf-guides.css').replace('/shot-library.js','/golf-guides.js')

def build_batch(day,selected,work,target,fixture=False):
 from prepare import run,BUN
 if len(selected)!=target or not selected:raise ValueError('No partial or empty batches')
 if any(v.get('input_kind')!='semrush_keywords_v1' or not 0<=v['kd']<30 or not v['volume']>100 or not v['evidence'].get('ok') for v in selected):raise ValueError('Unqualified input')
 if len({key(v['keyword']) for v in selected})!=target or len({v['source_url'] for v in selected})!=target:raise ValueError('Duplicate keyword/source intent')
 base=run(['git','rev-parse','HEAD'],work);template=(work/'public/golf-shot-tracer/index.html').read_text();folder=work/'public/golf-guides';folder.mkdir(exist_ok=True);manifest=work/'content/golf-guides'/day/'pages.json';pages=[]
 for i,row in enumerate(selected):
  path=folder/slug(row)/'index.html';path.parent.mkdir(exist_ok=True);peers=[x for x in selected[max(0,i-2):i+4] if x['keyword_id']!=row['keyword_id']][:3];path.write_text(render(template,row,peers,fixture))
  pages.append({'keyword_id':row['keyword_id'],'keyword':row['keyword'],'slug':slug(row),'kd':row['kd'],'volume':row['volume'],'source_url':row['source_url'],'source_export':row['source_export'],'source_export_sha256':row['source_export_sha256'],'evidence_sha256':row['evidence_sha256'],'test_fixture':fixture,'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
  if (i+1)%50==0:progress(day,state='generating',generated_count=i+1,test_fixture=fixture,pages_path=str(manifest),worktree=str(work),base_commit=base,input_kind='semrush_keywords_v1')
 save(manifest,pages);allpages=[]
 for m in sorted((work/'content/golf-guides').glob('*/pages.json')):allpages.extend(read(m))
 if len({p['keyword_id'] for p in allpages})!=len(allpages) or len({p['source_url'] for p in allpages})!=len(allpages):raise ValueError('Duplicate published intent')
 (work/'public/golf-guides.css').write_text(CSS);(work/'public/golf-guides.js').write_text(JS)
 chunks=[allpages[i:i+100] for i in range(0,len(allpages),100)];urls=[]
 for i,chunk in enumerate(chunks):
  route='/golf-guides'+('' if i==0 else '/browse-'+str(i+1));p=work/'public'/route.lstrip('/')/'index.html';p.parent.mkdir(exist_ok=True)
  body='<section class="sub-hero"><h1>Golf video guides'+('' if i==0 else ' — page '+str(i+1))+'</h1><p>Source-linked recording checklists and tracer workflows for your own golf footage.</p></section><article class="article-body"><ul>'+''.join('<li><a href="/golf-guides/'+x['slug']+'">'+html.escape(x['keyword'])+'</a></li>' for x in chunk)+'</ul><nav aria-label="Guide pages">'+' · '.join('<a href="/golf-guides'+('' if j==0 else '/browse-'+str(j+1))+'">'+str(j+1)+'</a>' for j in range(len(chunks)))+'</nav></article>'
  p.write_text(layout(template,route,'Golf video guides — page '+str(i+1)+' | GolfCut','Explore source-linked golf video recording guides, page '+str(i+1)+'.',body).replace('href="/shot-library"','href="/golf-guides"'));urls.append(ORIGIN+route)
 tracer=work/'public/golf-shot-tracer/index.html'
 if 'href="/golf-guides"' not in tracer.read_text():tracer.write_text(tracer.read_text().replace('</article>','<p><a href="/golf-guides">Golf recording guides</a></p></article>'))
 sm=work/'public/sitemap.xml';text=sm.read_text();existing=set(re.findall(r'<loc>(.*?)</loc>',text))
 for url in urls+[ORIGIN+'/golf-guides/'+x['slug'] for x in allpages]:
  if url not in existing:text=text.replace('</urlset>','<url><loc>'+url+'</loc></url>\n</urlset>');existing.add(url)
 sm.write_text(text)
 log=run([BUN,'run','build'],work);(HOME/(day+'-build.log')).write_text(log)
 changed=run(['git','diff','--name-only'],work).splitlines()
 if any(x not in ['public/sitemap.xml','public/golf-shot-tracer/index.html','public/golf-guides/index.html'] and not re.fullmatch(r'public/golf-guides/browse-\d+/index.html',x) for x in changed):raise ValueError('Unexpected modification to existing site')
 run(['git','add','public/golf-guides','public/golf-guides.css','public/golf-guides.js','public/sitemap.xml','public/golf-shot-tracer/index.html','content/golf-guides'],work)
 run(['git','commit','-m',('TEST FIXTURE NOT FOR PUBLICATION: ' if fixture else '')+'Add sourced golf keyword guides '+day],work);commit=run(['git','rev-parse','HEAD'],work)
 return progress(day,state='validated',target=target,input_kind='semrush_keywords_v1',test_fixture=fixture,generated_count=target,validated_count=target,published_count=0,page_prefix='/golf-guides',pages_path=str(manifest),pages_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),worktree=str(work),base_commit=base,commit=commit,blockers=[],checks={'bun_build':'passed','batch_sitemap_urls':target,'unique_source_intents':target,'protected_files_unchanged':True})

def prepare_keywords(day):
 from prepare import run
 old=read(HOME/(day+'-receipt.json'),{})
 try:pool=load_candidates(day)
 except InputPending as e:return progress(day,state='insufficient_keywords',input_kind='semrush_keywords_v1',generated_count=0,validated_count=0,published_count=0,blockers=[str(e)])
 if old.get('input_kind')=='semrush_keywords_v1' and old.get('state') in ['validated','ready','published']:return old
 target=config()['target'];reserved=[v for v in pool.values() if v.get('batch')==day and v['status']=='reserved'];selected=reserved or sorted([v for v in pool.values() if v['status']=='available'],key=lambda x:-x['volume'])[:target]
 if len(selected)<target:
  quota=read(PROJECT/'production/keyword-expansion/latest-check.json',{})
  return progress(day,state='insufficient_keywords',input_kind='semrush_keywords_v1',candidate_count=len(selected),candidate_shortfall=target-len(selected),generated_count=0,validated_count=0,published_count=0,source_state='source_quota_blocked' if '-32107' in json.dumps(quota) or 'limit' in json.dumps(quota).lower() else 'insufficient_keywords',blockers=['Insufficient verified Semrush keywords; empty/partial batches never build or publish.'])
 protected=PROJECT/'website-tracer';run(['git','-c','http.proxy=http://127.0.0.1:7890','fetch','origin','main'],protected);base=run(['git','rev-parse','origin/main'],protected);work=PROJECT/('website-seo-keywords-'+day.replace('-',''))
 if not work.exists():run(['git','worktree','add','--detach',str(work),base],protected)
 if run(['git','rev-parse','HEAD'],work)!=base:raise RuntimeError('Existing keyword worktree needs reconciliation; preserved without overwrite')
 with (HOME/'keyword-pool.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  full=read(HOME/'semrush-keyword-state.json',{})
  for row in selected:
   current=full[row['keyword_id']]
   if current['status']!='available' and current.get('batch')!=day:raise RuntimeError('Concurrent keyword reservation')
   row.update(status='reserved',batch=day);full[row['keyword_id']]=row
  save(HOME/'semrush-keyword-state.json',full)
 return build_batch(day,selected,work,target)
