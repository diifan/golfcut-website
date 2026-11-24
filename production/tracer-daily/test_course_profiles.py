import unittest,json,html
from course_profiles import extract,aligned

def enc(v):
 if isinstance(v,dict):return [0,{k:enc(x) for k,x in v.items()}]
 if isinstance(v,list):return [1,[enc(x) for x in v]]
 return [0,v]
class CourseTests(unittest.TestCase):
 def fixture(self):
  c={'id':{'id':'abc-123'},'name':'Example Hills Golf Club','address':'12 Main Road, Example City','tees':[{'name':'Blue','gender':'MALE'},{'name':'Blue','gender':'FEMALE'}],'holes':[{'teeYardages':[300,300],'menPar':4,'ladiesPar':4} for _ in range(9)],'holeSets':[{'holeIndexes':list(range(9))}],'courses':[{'name':'Main','holeSetIndexes':[0],'holeCount':9,'tcrs':[35,37],'tsls':[110,120]}]}
  return c
 def parse(self,c):
  raw='<astro-island component-export="Course" props="'+html.escape(json.dumps({'profile':enc({'club':c})}),quote=True)+'"></astro-island>'
  return extract(raw,'https://18birdies.com/golf-courses/club/abc-123/example-hills')
 def test_scorecard_totals_categories_and_identity(self):
  p=self.parse(self.fixture());self.assertEqual(p['courses'][0]['tees'][0]['yards'],2700);self.assertEqual(p['courses'][0]['tees'][0]['par'],36)
  self.assertEqual(p['courses'][0]['tees'][1]['slope'],120);self.assertTrue(aligned('example hills golf course',p));self.assertFalse(aligned('other hills golf course',p));self.assertFalse(aligned('example hills tee times',p));self.assertFalse(aligned('example hills after:2026-08-16',p))
 def test_bad_indices_and_wrong_club_not_accepted(self):
  c=self.fixture();c['courses'][0]['holeCount']=18;self.assertIsNone(self.parse(c))
  c=self.fixture();c['id']['id']='wrong';self.assertIsNone(self.parse(c))
 def test_missing_measurements_never_invented(self):
  c=self.fixture();c['courses'][0]['tcrs']=[0,0];p=self.parse(c);self.assertIsNone(p['courses'][0]['tees'][0]['rating'])
  c['holes'][0]['teeYardages']=[0,0];self.assertIsNone(self.parse(c))
if __name__=='__main__':unittest.main()
