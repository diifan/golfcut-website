"""GolfCut Semrush-only preparation entrypoint; legacy video renderer is unreachable."""
import argparse,subprocess,os,fcntl
from common import *
BUN='/var/lib/swi-codex/.bun/bin/bun'
def run(args,cwd):
 env=dict(os.environ);env['PATH']='/var/lib/swi-codex/.bun/bin:'+env.get('PATH','')
 result=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
 if result.returncode:raise RuntimeError(result.stdout[-4000:])
 return result.stdout.strip()
def prepare(day,refresh=True):
 from keyword_pages import prepare_keywords
 return prepare_keywords(day)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--day',required=True);a.add_argument('--no-refresh',action='store_true',help='Compatibility option; source integrity is always rechecked');args=a.parse_args()
 with (HOME/'executor.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:prepare(args.day)
  except Exception as e:progress(args.day,state='failed',blockers=[str(e)[-1800:]]);raise
