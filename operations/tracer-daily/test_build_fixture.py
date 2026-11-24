"""TEST FIXTURE ONLY: actual isolated Bun build, no network publication permitted."""
import tempfile,subprocess,json,hashlib,sys,csv
import keyword_input as input_adapter
from pathlib import Path
from unittest.mock import patch
import common,keyword_pages as pages,release
from common import save
from prepare import run

def main():
 root=Path(tempfile.mkdtemp(prefix='golfcut-semrush-TEST-FIXTURE-'));work=root/'website';home=root/'state';report=root/'reports';home.mkdir();report.mkdir()
 protected=common.PROJECT/'website-tracer';base=run(['git','rev-parse','origin/main'],protected)
 run(['git','clone','--shared','--no-checkout',str(protected),str(work)],root);run(['git','checkout','--detach',base],work)
 run(['git','config','user.name','GolfCut TEST FIXTURE'],work);run(['git','config','user.email','test-fixture@example.invalid'],work)
 save(home/'config.json',{'enabled':True,'target':3,'hour':12,'minute':30,'prepare_hour':13,'prepare_minute':0,'timezone':'Asia/Shanghai'})
 source=root/'source';source.mkdir();(source/'run.lock').touch();save(source/'config.json',{'domains':['example.test']})
 words=['golf shot tracer test fixture','golf swing video test fixture','golf bunker recording test fixture'];original=source/'TEST-FIXTURE-original.csv'
 with original.open('w') as f:
  w=csv.writer(f);w.writerow(['Keyword','Keyword Difficulty','Search Volume','URL'])
  for n,word in enumerate(words):w.writerow([word,20,200,'https://example.test/fixture-'+str(n)])
 sha=input_adapter.digest(original)
 with (source/'keywords.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['keyword','status','url','batch_id','source','volume','kd','evidence_url','metric_timestamp','source_sha256'])
  for n,word in enumerate(words):w.writerow([word,'available','','',str(original),200,20,'https://example.test/fixture-'+str(n),'TEST FIXTURE ONLY',sha])
 save(source/'manifest.json',{'app':'golfcut','sport':'golf','sources':[{'path':str(original),'sha256':sha,'rows':3}]})
 save(home/'input-binding.json',{'keywords_csv':str(source/'keywords.csv'),'source_manifest':str(source/'manifest.json')})
 def evidence(url):
  n=int(url.rsplit('-',1)[1]);return {'ok':True,'url':url,'title':'TEST FIXTURE '+words[n],'text':(words[n]+'. This synthetic data only validates local golf rendering and must never be deployed. ')*6,'sha256':'fixture','checked_at':0}
 with patch.object(common,'HOME',home),patch.object(common,'REPORT',report),patch.object(pages,'HOME',home),patch.object(input_adapter,'HOME',home),patch.object(input_adapter,'SOURCE_ROOT',source),patch.object(input_adapter,'fetch_evidence',side_effect=evidence):
  pool=input_adapter.load_candidates('2099-01-01');selected=list(pool.values());assert len(selected)==3
  receipt=pages.build_batch('2099-01-01',selected,work,3,fixture=True)
  assert receipt['validated_count']==3
  blocked=[]
  with patch.object(release,'HOME',home),patch.object(release,'api',side_effect=AssertionError('Network forbidden')),patch.object(release,'cli',side_effect=AssertionError('Network forbidden')):
   for action in [lambda:release.stage('2099-01-01'),lambda:release.check_manifest(receipt)]:
    try:action();raise AssertionError('Fixture was allowed')
    except RuntimeError as e:assert 'FIXTURE' in str(e);blocked.append(str(e))
   ready={**receipt,'state':'ready'};save(home/'2099-01-01-receipt.json',ready)
   try:release.publish('2099-01-01',immediate=True);raise AssertionError('Fixture promoted')
   except RuntimeError as e:assert 'FIXTURE' in str(e);blocked.append(str(e))
  before=run(['git','rev-parse',base+':public/index.html'],work);after=run(['git','rev-parse','HEAD:public/index.html'],work);assert before==after
  # All legacy published guide files remain byte-identical.
  changed=run(['git','diff','--name-only',base,'HEAD'],work).splitlines();assert not any(x.startswith(('api/','server/','public/shot-library/')) or x in ['public/privacy.html','public/index.html'] for x in changed)
 result={'test_fixture':True,'published_count':0,'site_base':base,'fixture_root':str(root),'generated_count':3,'validated_count':3,'bun_build':'passed','protected_content':'unchanged','stage_and_publish_guards':blocked}
 save(common.HOME/'semrush-fixture-build-result.json',result);print(json.dumps(result))
if __name__=='__main__':main()
