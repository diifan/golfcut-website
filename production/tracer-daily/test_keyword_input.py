import unittest,tempfile,csv,json,hashlib,socket
from pathlib import Path
from unittest.mock import patch,MagicMock
import keyword_input as k
from release import check_manifest
class Tests(unittest.TestCase):
 def setUp(self):
  k._sessions=__import__("threading").local()
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.patches=[patch.object(k,'HOME',self.home),patch.object(k,'SOURCE_ROOT',self.home),patch.object(k,'progress')]
  for p in self.patches:p.start()
  (self.home/'run.lock').touch();(self.home/'config.json').write_text(json.dumps({'domains':['example.test']}))
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def files(self,records):
  source=self.home/'original.csv'
  with source.open('w') as f:
   w=csv.writer(f);w.writerow(['Keyword','Keyword Difficulty','Search Volume','URL']);w.writerows(records)
  sha=k.digest(source);p=self.home/'keywords.csv'
  with p.open('w') as f:
   w=csv.DictWriter(f,fieldnames=['keyword','status','url','batch_id','source','volume','kd','evidence_url','metric_timestamp','source_sha256']);w.writeheader()
   for word,kd,vol,url in records:w.writerow({'keyword':word,'status':'available','source':str(source),'volume':vol,'kd':kd,'evidence_url':url,'metric_timestamp':'TEST FIXTURE','source_sha256':sha})
  (self.home/'manifest.json').write_text(json.dumps({'app':'golfcut','sport':'golf','sources':[{'path':str(source),'sha256':sha,'rows':len(records)}]}));return p
 def evidence(self,url):return {'ok':True,'url':url,'resolved_url':url,'title':'Golf shot tracer camera swing video guide','text':('Golf shot tracer camera swing video recording and ball visibility. '*12),'sha256':'fixture-hash','checked_at':0}
 def test_video_and_fixture_release_blocked(self):
  for r in [{'input_kind':'video'},{'input_kind':'semrush_keywords_v1','test_fixture':True}]:
   with self.assertRaises(RuntimeError):check_manifest(r)
 def test_empty_then_incremental(self):
  self.files([]);self.assertEqual(k.load_candidates('2099-01-01'),{})
  self.files([['golf shot tracer',29,101,'https://example.test/a']])
  with patch.object(k,'fetch_evidence',side_effect=self.evidence):self.assertEqual(len(k.load_candidates('2099-01-01')),1)
  self.assertEqual(json.loads((self.home/'capacity.json').read_text())['eligible_available'],1)
 def test_strict_thresholds(self):
  self.files([['golf shot tracer',29,101,'https://example.test/a'],['golf camera',30,999,'https://example.test/b'],['golf swing',10,100,'https://example.test/c']])
  with patch.object(k,'fetch_evidence',side_effect=self.evidence):self.assertEqual(len(k.load_candidates('2099-01-01')),1)
 def test_forged_row(self):
  p=self.files([['golf shot tracer',20,200,'https://example.test/a']]);s=p.read_text().replace(',200,20,',',999,20,');p.write_text(s)
  with self.assertRaisesRegex(ValueError,'Forged'):k.load_candidates('2099-01-01')
 def test_forged_url(self):
  p=self.files([['golf shot tracer',20,200,'https://example.test/a']]);p.write_text(p.read_text().replace('https://example.test/a','https://example.test/b'))
  with self.assertRaisesRegex(ValueError,'Forged'):k.load_candidates('2099-01-01')
 def test_preserve_reservation_and_dedupe_source(self):
  self.files([['golf shot tracer',20,200,'https://example.test/a'],['golf tracer camera',20,150,'https://example.test/a']])
  with patch.object(k,'fetch_evidence',side_effect=self.evidence):
   pool=k.load_candidates('2099-01-01');self.assertEqual(len(pool),1);i=next(iter(pool));pool[i].update(status='reserved',batch='2099-01-01');(self.home/'semrush-keyword-state.json').write_text(json.dumps(pool));again=k.load_candidates('2099-01-01');self.assertEqual(again[i]['status'],'reserved');self.assertEqual(json.loads((self.home/'capacity.json').read_text())['eligible_available'],0)
 def test_original_alternative_source_can_rescue_keyword(self):
  self.files([['golf shot tracer',20,200,'https://example.test/missing']])
  original=self.home/'second.csv';original.write_text('Keyword,Keyword Difficulty,Search Volume,URL\ngolf shot tracer,19,210,https://example.test/working\n')
  manifest=json.loads((self.home/'manifest.json').read_text());manifest['sources'].append({'path':str(original),'sha256':k.digest(original),'rows':1});(self.home/'manifest.json').write_text(json.dumps(manifest))
  def evidence(url):return {'ok':False,'error':'unavailable'} if url.endswith('missing') else self.evidence(url)
  with patch.object(k,'fetch_evidence',side_effect=evidence):
   pool=k.load_candidates('2099-01-01');self.assertEqual(len(pool),1);row=next(iter(pool.values()));self.assertEqual(row['source_url'],'https://example.test/working');self.assertEqual(row['source_export'],str(original));self.assertEqual(row['kd'],19)

 def test_source_hash_tampering(self):
  self.files([['golf shot tracer',20,200,'https://example.test/a']]);(self.home/'original.csv').write_text('tampered')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):k.load_candidates('2099-01-01')
 def test_concurrent_snapshot_change(self):
  p=self.files([['golf shot tracer',20,200,'https://example.test/a']])
  def changing(url):p.write_text(p.read_text()+'\n');return self.evidence(url)
  with patch.object(k,'fetch_evidence',side_effect=changing):
   with self.assertRaises(k.InputPending):k.load_candidates('2099-01-01')
  self.assertFalse((self.home/'semrush-keyword-state.json').exists())
 def test_equivalent_intent(self):
  self.files([['golf shot tracer',20,200,'https://example.test/a'],['best golf shot tracer',20,150,'https://example.test/b']])
  with patch.object(k,'fetch_evidence',side_effect=self.evidence):self.assertEqual(len(k.load_candidates('2099-01-01')),1)
 def test_unsafe_urls(self):
  for url in ['http://example.test/a','https://127.0.0.1/a','https://example.test.evil.test/a','https://user:pass@example.test/a','https://example.test:8080/a']:
   with self.assertRaises(ValueError):k.allowed_url(url)
 def test_private_dns(self):
  with patch.object(socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
   with self.assertRaises(ValueError):k.allowed_url('https://example.test/a')
 def test_unsafe_redirect(self):
  response=MagicMock();response.__enter__.return_value=response;response.status_code=302;response.headers={'Location':'https://127.0.0.1/private'}
  with patch.object(socket,'getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443))]),patch.object(k.requests,'Session') as session:
   session.return_value.get.return_value=response;r=k.fetch_evidence('https://example.test/a');self.assertFalse(r['ok']);self.assertEqual(session.return_value.get.call_count,2)
 def test_large_script_heavy_html_with_useful_text(self):
  raw=b'<html><title>Golf shot tracer</title><script>'+b'x'*2_200_000+b'</script><p>'+b'Golf shot tracer video recording keeps the ball visible. '*20+b'</p></html>'
  response=MagicMock();response.__enter__.return_value=response;response.status_code=200;response.encoding='utf-8';response.headers={'Content-Type':'text/html'};response.iter_content.side_effect=lambda n:iter([raw])
  with patch.object(socket,'getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443))]),patch.object(k.requests,'Session') as session:
   session.return_value.get.return_value=response;r=k.fetch_evidence('https://example.test/a');self.assertTrue(r['ok']);self.assertLess(len(r['text']),2000)
 def test_non_tracer_topic_and_unknown_preservation(self):
  self.files([['3 iron',20,200,'https://example.test/compare'],['3 hybrid',20,150,'https://example.test/compare'],['unresolved phrase',20,150,'https://example.test/unknown']])
  def evidence(url):return {**self.evidence(url),'text':('Golf comparison of a 3-iron and a 3-hybrid from comparable lies. '*20)}
  with patch.object(k,'fetch_evidence',side_effect=evidence):
   pool=k.load_candidates('2099-01-01');self.assertEqual(len(pool),1)
  queue=json.loads((self.home/'intent-review-queue.json').read_text())['rows']
  self.assertEqual(queue[0]['keyword'],'unresolved phrase');self.assertEqual(queue[0]['routing_state'],'needs_review')
  self.assertFalse(k.relevance('3 iron',self.evidence('https://example.test/unrelated')))
 def test_editorial_renderer_is_not_a_tracer_template(self):
  import keyword_pages as pages
  row={'keyword':'3 iron','keyword_id':'test-key','source_url':'https://example.test/compare','evidence':{'ok':True,'title':'3-iron versus 3-hybrid','text':('Golf club comparison of a 3-iron and a 3-hybrid. '*20)}}
  with patch.object(pages,'layout',side_effect=lambda template,path,title,desc,body:body):html=pages.render('template',row,[])
  self.assertIn('data-page-type="equipment_guide"',html);self.assertIn('Decision checklist',html);self.assertNotIn('shot-notes',html)
 def test_distinct_topic_can_share_source(self):
  self.assertNotEqual(k.page_intent('3 iron','https://example.test/a'),k.page_intent('golf app','https://example.test/a'))
 def test_stream_limit(self):
  response=MagicMock();response.__enter__.return_value=response;response.status_code=200;response.headers={'Content-Type':'text/html'};response.iter_content.side_effect=lambda n:iter([b'x'*1000000]*4)
  with patch.object(socket,'getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443))]),patch.object(k.requests,'Session') as session:
   session.return_value.get.return_value=response;r=k.fetch_evidence('https://example.test/a');self.assertFalse(r['ok']);self.assertIn('byte limit',r['error'])
if __name__=='__main__':unittest.main()
