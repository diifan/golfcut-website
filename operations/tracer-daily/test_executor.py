import unittest,datetime,sys
from scheduler import due
from source_cache import classify,normalize
from content_engine import facts,slug
class Tests(unittest.TestCase):
 def setUp(self):self.c={'enabled':True,'target':2000,'hour':12,'minute':30,'prepare_hour':13,'prepare_minute':0,'timezone':'Asia/Shanghai'}
 def t(self,h,m):return datetime.datetime(2026,11,24,h,m)
 def test_publish_boundary(self):
  self.assertEqual(due(self.c,self.t(12,29)),[])
  self.assertEqual(due(self.c,self.t(12,30)),[('publish','2026-11-24')])
 def test_prepare_next_day(self):self.assertIn(('prepare','2026-11-25'),due(self.c,self.t(13,0)))
 def test_config_changes(self):
  self.c.update(hour=14,minute=5,prepare_hour=15)
  self.assertEqual(due(self.c,self.t(12,30)),[])
  self.assertIn(('publish','2026-11-24'),due(self.c,self.t(14,5)))
 def test_disabled(self):
  self.c['enabled']=False;self.assertEqual(due(self.c,self.t(23,0)),[])
 def test_year_rollover(self):self.assertIn(('prepare','2027-01-01'),due(self.c,datetime.datetime(2026,12,31,13,0)))
 def test_scope(self):
  self.assertIsNone(classify({'title':'Player interview after winning'}))
  self.assertIsNone(classify({'title':'Player sinks a 20-foot putt'}))
  self.assertEqual(classify({'title':'Player hits approach on No. 5'}),'approach')
 def test_normalization(self):self.assertEqual(normalize(' Golf  SHOT '),normalize('golf shot'))
if __name__=='__main__':unittest.main()
