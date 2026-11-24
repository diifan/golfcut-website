import os
import argparse,subprocess,re,hashlib,xml.etree.ElementTree as ET,fcntl,collections
from common import *
from keyword_input import load_candidates, InputPending
from content_engine import *
BUN='/var/lib/swi-codex/.bun/bin/bun'
def run(args,cwd):
 env=dict(os.environ);env['PATH']='/var/lib/swi-codex/.bun/bin:'+env.get('PATH','')
 result=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
 if result.returncode:raise RuntimeError(result.stdout[-4000:])
 return result.stdout.strip()
def prepare(day,refresh=True):
 from keyword_pages import prepare_keywords
 return prepare_keywords(day)

def _legacy_video_prepare_DISABLED(day,refresh=True):
 c=config();target=c['target'];r=read(HOME/(day+'-receipt.json'),{})
 if r.get('state') in ['ready','published']:return r
 pool=load_candidates(day)
 reserved=[v for v in pool.values() if v.get('batch')==day and v['status']=='reserved']
 selected=reserved or [v for v in pool.values() if v['status']=='available'][:target]
 if len(selected)<target:
  return progress(day,state='insufficient_candidates',candidate_count=len(selected),candidate_shortfall=target-len(selected),blockers=['Not enough distinct, evidenced golf shot candidates in current collection.'],note='Collection remains append-only; no synthetic keyword expansion.')
 work=PROJECT/('website-seo-daily-'+day.replace('-',''));protected=PROJECT/'website-tracer'
 run(['git','-c','http.proxy=http://127.0.0.1:7890','fetch','origin','main'],protected)
 base=run(['git','rev-parse','origin/main'],protected)
 if not work.exists():run(['git','worktree','add','--detach',str(work),base],protected)
 if run(['git','rev-parse','HEAD'],work)!=base:raise RuntimeError('Worktree base differs from current main; preserve work and reconcile before publishing')
 # A second run regenerates only this executor's own files.
 for v in selected:v.update(status='reserved',batch=day)
 save(HOME/'semrush-keyword-state.json',pool)
 template=(work/'public/golf-shot-tracer/index.html').read_text();library=work/'public/shot-library';library.mkdir(exist_ok=True)
 manifest=work/'content/shot-library'/day/'pages.json';pages=[]
 for i,v in enumerate(selected):
  s=slug(v);p=library/s/'index.html';p.parent.mkdir(exist_ok=True)
  peers=[x for x in selected[max(0,i-2):i+4] if x['evidence']['id']!=v['evidence']['id']][:3]
  p.write_text(render(template,v,peers));pages.append({'keyword':v['keyword'],'slug':s,'source_url':v['source_url'],'source_sha256':v['evidence_sha256'],'video_id':v['evidence']['id'],'kind':v['kind'],'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  if (i+1)%50==0:progress(day,state='generating',generated_count=i+1,pages_path=str(manifest),worktree=str(work),base_commit=base,candidate_count=len(selected),blockers=[])
 save(manifest,pages)
 # All previous batches remain present and linked.
 allpages=[]
 for m in sorted((work/'content/shot-library').glob('*/pages.json')):allpages.extend(read(m))
 if len({p['video_id'] for p in allpages})!=len(allpages):raise RuntimeError('Duplicate source video across batches')
 if len({p['slug'] for p in allpages})!=len(allpages):raise RuntimeError('Duplicate canonical slug')
 (work/'public/shot-library.css').write_text(CSS);(work/'public/shot-library.js').write_text(JS)
 chunk=100;groups=[allpages[i:i+chunk] for i in range(0,len(allpages),chunk)];newurls=[]
 for i,group in enumerate(groups):
  path='/shot-library' if i==0 else '/shot-library/browse-'+str(i+1);p=work/'public'/path.lstrip('/')/'index.html';p.parent.mkdir(exist_ok=True)
  body='<section class="sub-hero"><h1>Golf shot video references'+('' if i==0 else ' — page '+str(i+1))+'</h1><p>Explore real golf moments and plan how to film your own shot. Each reference links to its publisher and includes a recording checklist and a browser-only worksheet.</p></section><article class="article-body"><label>Filter this page<input class="library-search" data-library-search type="search" placeholder="Player or shot"></label><ul class="library-links">'+''.join('<li><a href="/shot-library/'+x['slug']+'">'+E(x['keyword'])+'</a></li>' for x in group)+'</ul><nav aria-label="Library pages">'+' · '.join('<a href="'+('/shot-library' if j==0 else '/shot-library/browse-'+str(j+1))+'">'+str(j+1)+'</a>' for j in range(len(groups)))+'</nav><p><a href="/try-tracer">Try a tracer on your own video</a></p></article>'
  p.write_text(layout(template,path,'Golf shot reference library'+('' if i==0 else ' — page '+str(i+1))+' | GolfCut','Browse golf video references, source details and recording worksheets. Library page '+str(i+1)+'.',body));newurls.append(ORIGIN+path)
 # One relevant discovery link; leave the home page, APIs and privacy untouched.
 link='<p><a href="/shot-library">Explore golf shot references and filming worksheets</a></p>'
 existing=work/'public/golf-shot-tracer/index.html'
 if 'href="/shot-library"' not in existing.read_text():existing.write_text(existing.read_text().replace('</article>',link+'</article>'))
 sitemap=work/'public/sitemap.xml';text=sitemap.read_text();urls=set(re.findall(r'<loc>(.*?)</loc>',text))
 for u in newurls+[ORIGIN+'/shot-library/'+p['slug'] for p in allpages]:
  if u not in urls:text=text.replace('</urlset>','<url><loc>'+u+'</loc></url>\n</urlset>');urls.add(u)
 sitemap.write_text(text)
 progress(day,state='validating',generated_count=len(pages),pages_path=str(manifest),worktree=str(work),base_commit=base)
 build=run([BUN,'run','build'],work);(HOME/(day+'-build.log')).write_text(build)
 changed=run(['git','diff','--name-only'],work).splitlines()
 if any(x not in ['public/sitemap.xml','public/golf-shot-tracer/index.html','public/shot-library/index.html'] and not re.fullmatch(r'public/shot-library/browse-\d+/index.html',x) for x in changed):raise RuntimeError('Unexpected change to existing production file')
 run(['git','add','public/shot-library','public/shot-library.css','public/shot-library.js','public/sitemap.xml','public/golf-shot-tracer/index.html','content/shot-library'],work)
 run(['git','commit','-m','Add '+str(target)+' sourced golf shot reference pages ('+day+')'],work)
 commit=run(['git','rev-parse','HEAD'],work)
 return progress(day,state='validated',validated_count=len(pages),generated_count=len(pages),commit=commit,pages_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),blockers=[],checks={'bun_build':'passed','unique_video_ids':len(allpages),'batch_sitemap_urls':len(pages),'protected_files_unchanged':True})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--day',required=True);a.add_argument('--no-refresh',action='store_true');args=a.parse_args()
 with (HOME/'executor.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:prepare(args.day,not args.no_refresh)
  except InputPending as e:progress(args.day,state='waiting_keyword_pool',blockers=[str(e)])
  except Exception as e:progress(args.day,state='failed',blockers=[str(e)[-1800:]]);raise
