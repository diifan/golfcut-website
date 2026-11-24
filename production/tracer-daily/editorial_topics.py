"""Non-tracer answers; source-backed topic clusters, not keyword-variant pages."""
import re
TOPICS={
 'long_club_comparison':dict(kind='equipment_guide',title='3-iron versus 3-hybrid: make a comparison from your own shots',
  query=r'\b3[ -]?(?:iron|hybrid)\b|\bthree (?:iron|hybrid)\b',evidence=r'3.iron.*3.hybrid|3.hybrid.*3.iron',
  answer='Compare a 3-iron and a 3-hybrid by the job you need the club to do. Record the lie, intended target and outcome of several shots with each club. A club number alone is not enough to establish which option will work better for your game.',
  sections=[('Keep the comparison fair','Use comparable lies and targets. Note poor contact instead of deleting every miss: the spread of outcomes is part of the decision. If you have measured distances, keep carry and total distance separate.'),('Record the decision, not just the longest shot','Write down the shot you need most often, the trouble you want to avoid and which club gives you a usable result more consistently. Ask a qualified fitter or coach to interpret technical measurements; this guide does not prescribe a universal club choice.')],
  checklist=['Name the shot you need from this slot in the bag.','Test both clubs from comparable lies.','Record misses alongside successful shots.','Compare measured outcomes without treating video effects as distance data.']),
 'golf_app_selection':dict(kind='tool_guide',title='Choose a golf app by the task you need',
  query=r'^golf (?:training app|app for beginners|software|apps?)$',evidence=r'golf',
  answer='Begin with the task: course navigation, round statistics, structured practice or editing your own golf footage. Those tasks require different information and interfaces. Decide which one matters first, then check the app’s current product documentation rather than assuming every golf app offers the same features.',
  sections=[('Check the workflow before committing','List the phone or wearable you intend to use, whether the app needs extra hardware, and which data you must enter yourself. Verify availability, hardware support and pricing on the provider’s current site.'),('Keep tracking and editing separate','A recorded round, measured shot statistics and a visible ball-trail effect are different outputs. GolfCut’s online tool edits a short clip using a manually marked hit moment and ball position; it does not replace GPS navigation or measured club-distance data.')],
  checklist=['Choose one primary task.','Check device and hardware requirements.','Verify current plan details with the provider.','Try the complete task with your own data or footage.'])}
def topic(word):
 return next((key for key,spec in TOPICS.items() if re.search(spec['query'],word.casefold())),None)
def supported(word,evidence):
 key=topic(word)
 if not key:return False
 text=evidence.get('title','')+' '+evidence.get('text','')
 return bool(evidence.get('ok') and len(text)>200 and re.search(TOPICS[key]['evidence'],text,re.I|re.S))
