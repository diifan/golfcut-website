import unittest,datetime,sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
import scheduler as schedule
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
 def test_overnight_failure_prepares_before_cutoff_only(self):
  for hour,minute,expected in [(9,0,True),(12,30,False)]:
   class Clock(datetime.datetime):
    @classmethod
    def now(cls,tz=None):return cls(2026,11,25,hour,minute,tzinfo=tz)
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);(root/'2026-11-25-receipt.json').write_text(json.dumps({'state':'insufficient_keywords'}))
    with patch.object(schedule,'HOME',root),patch.object(schedule,'config',return_value=self.c),patch.object(schedule.datetime,'datetime',Clock),patch.object(schedule,'progress'),patch.object(schedule,'prepare',return_value={'state':'insufficient_keywords'}) as prepare,patch.object(schedule,'stage') as stage,patch.object(schedule,'publish') as publish:
     schedule.tick()
     if expected:prepare.assert_called_once_with('2026-11-25')
     else:prepare.assert_not_called()
     stage.assert_not_called();publish.assert_not_called()
 def test_scope(self):
  self.assertIsNone(classify({'title':'Player interview after winning'}))
  self.assertIsNone(classify({'title':'Player sinks a 20-foot putt'}))
  self.assertEqual(classify({'title':'Player hits approach on No. 5'}),'approach')
 def test_normalization(self):self.assertEqual(normalize(' Golf  SHOT '),normalize('golf shot'))
if __name__=='__main__':unittest.main()
