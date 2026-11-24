"""Small attributed context excerpts; reject navigation, prices and unstructured tables."""
import re
STOP={'tennis','golf','with','what','best','that','your','the','and','for','how','you','are','can','does','from','this'}
def context_excerpt(keyword,text):
 tokens=set(re.findall(r'[a-z]{3,}',keyword.lower()))-STOP
 if not tokens:raise ValueError('No specific context terms')
 ranked=[]
 for sentence in re.split(r'(?<=[.!?])\s+',text):
  words=sentence.split()
  if not 8<=len(words)<=100:continue
  if re.search(r'\$|\||\.com\s+beta|\b(?:add to cart|best seller|sign in|log in|cookie policy|accept cookies|free shipping|privacy policy)\b',sentence,re.I):continue
  found=[i for i,w in enumerate(words) if set(re.findall(r'[a-z]{3,}',w.lower()))&tokens]
  if not found:continue
  start=max(0,min(found[0]-6,len(words)-24));quote=' '.join(words[start:start+24])
  if any(t in quote.lower() for t in tokens):ranked.append((len(found),-len(words),quote))
 if not ranked:raise ValueError('No meaningful source-specific prose excerpt')
 return max(ranked)[2]
