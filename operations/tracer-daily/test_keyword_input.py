import unittest,tempfile,csv,json,hashlib
from pathlib import Path
from unittest.mock import patch
import keyword_input as k
from release import check_manifest
class Tests(unittest.TestCase):
 def test_video_release_blocked(self):
  with self.assertRaisesRegex(RuntimeError,'disabled for video'):check_manifest({'input_kind':'video'})
 def test_missing_binding_waits(self):
  with tempfile.TemporaryDirectory() as d,patch.object(k,'HOME',Path(d)):
   with self.assertRaises(k.InputPending):k.load_candidates('2026-11-25')
 def test_strict_thresholds_dedup_preservation(self):
  with tempfile.TemporaryDirectory() as d,patch.object(k,'HOME',Path(d)),patch.object(k,'progress'):
   home=Path(d);p=home/'keywords.csv'
   rows=[['golf shot tracer','29','101','https://example.test/golf'],[' golf   SHOT tracer ','20','1000','https://example.test/golf'],['golf swing video','30','1000','https://example.test/golf'],['golf filming','10','100','https://example.test/golf'],['golf camera','10','200','https://example.test/missing']]
   with p.open('w') as f:
    w=csv.writer(f);w.writerow(['keyword','kd','volume','source_url']);w.writerows(rows)
   sha=hashlib.sha256(p.read_bytes()).hexdigest();m=home/'manifest.json'
   m.write_text(json.dumps({'keywords_sha256':sha,'sources':[{'provider':'semrush','local_path':str(p),'sha256':sha}],'evidence':{'golf shot tracer':{'url':'https://example.test/golf','title':'Golf shot tracer','text':'Golf shot tracer recording and ball visibility. '*10,'sport':'golf','tracer_relevance':'Golf recording'}}}))
   (home/'input-binding.json').write_text(json.dumps({'keywords_csv':str(p),'source_manifest':str(m)}))
   pool=k.load_candidates('2026-11-25');self.assertEqual(len(pool),1);identifier=next(iter(pool));pool[identifier]['status']='published';(home/'semrush-keyword-state.json').write_text(json.dumps(pool))
   self.assertEqual(k.load_candidates('2026-11-25')[identifier]['status'],'published')
   receipt=json.loads((home/'input-import-receipt.json').read_text());self.assertEqual(receipt['counts']['metric_rejected'],2);self.assertEqual(receipt['counts']['evidence_pending'],1)
if __name__=='__main__':unittest.main()
