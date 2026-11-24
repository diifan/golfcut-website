"""Semrush handoff gate. Video renderer is intentionally unreachable.
Source-specific rendering is bound to the actual incoming evidence, never to video-title substitutions.
"""
from common import *
from keyword_input import load_candidates,InputPending

def prepare_keywords(day):
 try:pool=load_candidates(day)
 except InputPending as e:
  return progress(day,state='waiting_keyword_pool',input_kind='semrush_keywords_v1',generated_count=0,validated_count=0,published_count=0,blockers=[str(e)],note='Controller owns keyword-expansion. Executor accepts immutable CSV/export/evidence manifests; legacy video batches cannot publish.')
 candidates=[v for v in pool.values() if v['status']=='available'];target=config()['target']
 if len(candidates)<target:
  return progress(day,state='insufficient_keyword_candidates',candidate_count=len(candidates),candidate_shortfall=target-len(candidates),blockers=['Fewer than target unique golf-relevant keywords meet KD<30, volume>100 and source evidence checks.'])
 # Preserve all imported rows. The production writer must be adapted against the
 # actual controller evidence schema before its first Semrush batch, then tested.
 return progress(day,state='keyword_input_validated',candidate_count=len(candidates),blockers=['Semrush input validated. Source-specific page writer integration is pending the first real controller evidence handoff; no video renderer fallback.'])
