"""Orchestration test: every external Git/Vercel/HTTP operation is mocked."""
import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import release as r,common
class Response:
 def __init__(self,data):self.content=data;self.text=data.decode()
 def raise_for_status(self):pass
class Tests(unittest.TestCase):
 def test_stage_promote_verify_finalize_with_mock_transports(self):
  with tempfile.TemporaryDirectory(prefix='TEST-FIXTURE-release-') as temp:
   home=Path(temp);report=home/'reports';report.mkdir();work=home/'site';work.mkdir();day='2099-01-01'
   cfg={'enabled':True,'target':1,'hour':12,'minute':30,'prepare_hour':13,'prepare_minute':0,'timezone':'Asia/Shanghai'};common.save(home/'config.json',cfg)
   data=b'TEST FIXTURE: mocked HTTP only';row={'keyword_id':'fixture','slug':'fixture','file_sha256':hashlib.sha256(data).hexdigest()};receipt={'day':day,'state':'validated','input_kind':'semrush_keywords_v1','target':1,'validated_count':1,'generated_count':1,'published_count':0,'worktree':str(work),'base_commit':'base','commit':'commit','checks':{}}
   common.save(home/(day+'-receipt.json'),receipt);common.save(home/'semrush-keyword-state.json',{'fixture':{'status':'reserved'}})
   deployment={'id':'dpl_TEST_FIXTURE','url':'golfcut-website-fixture.vercel.app','readyState':'READY','target':'production','projectId':r.PID,'meta':{'swieCommit':'commit'}}
   def api(path,work):
    if '/v6/deployments' in path:return {'deployments':[]}
    if '/v4/aliases/' in path:return {'deploymentId':'dpl_TEST_FIXTURE'}
    return deployment
   def run(args,work):
    if 'rev-parse' in args:return 'base'
    if 'ls-remote' in args:return 'commit\trefs/heads/main'
    return ''
   def get(url,**kwargs):return Response(('<urlset><url><loc>'+r.ORIGIN+'/golf-guides/fixture</loc></url></urlset>').encode() if url.endswith('sitemap.xml') else data)
   with patch.object(common,'HOME',home),patch.object(common,'REPORT',report),patch.object(r,'HOME',home),patch.object(r,'check_manifest',return_value=[row]),patch.object(r,'api',side_effect=api),patch.object(r,'cli',return_value='https://golfcut-website-fixture.vercel.app') as cli,patch.object(r,'run',side_effect=run),patch.object(r.requests,'Session') as session:
    session.return_value.get.side_effect=get
    self.assertEqual(r.stage(day)['state'],'ready');result=r.publish(day,immediate=True);self.assertEqual(result['state'],'published');self.assertEqual(result['checks']['live_html_hash_count'],1);self.assertEqual(result['checks']['live_sitemap_batch_count'],1)
    before=cli.call_count;r.publish(day,immediate=True);self.assertEqual(cli.call_count,before)
    self.assertEqual(json.loads((home/'semrush-keyword-state.json').read_text())['fixture']['status'],'published')
if __name__=='__main__':unittest.main()
