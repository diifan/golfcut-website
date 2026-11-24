"""Public course scorecard facts; never execute embedded source JavaScript."""
import json,re,html,unicodedata
from html.parser import HTMLParser
from urllib.parse import urlparse

def decode(v):
 if not isinstance(v,list) or len(v)!=2 or v[0] not in (0,1):raise ValueError('Unsupported public data encoding')
 kind,value=v
 if isinstance(value,dict):return {k:decode(x) for k,x in value.items()}
 if kind==1:return [decode(x) for x in value]
 return value

class Parser(HTMLParser):
 def __init__(self):super().__init__();self.profile=None
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=='astro-island' and a.get('component-export')=='Course' and self.profile is None:
   self.profile=decode(json.loads(a['props'])['profile'])

def extract(raw,url):
 if not re.fullmatch(r'/golf-courses/club/[a-z0-9-]+/[^/]+/?',urlparse(url).path):return None
 p=Parser();p.feed(raw)
 if not p.profile:return None
 c=p.profile.get('club',{});ident=c.get('id',{}).get('id')
 if ident!=urlparse(url).path.split('/')[3] or c.get('deleted') or not c.get('name') or not c.get('address'):return None
 courses=[]
 for course in c.get('courses',[]):
  if course.get('deleteTimestamp'):continue
  try:
   indices=[i for s in course['holeSetIndexes'] for i in c['holeSets'][s]['holeIndexes']]
   if len(indices)!=course['holeCount'] or len(set(indices))!=len(indices):continue
   tees=[]
   for i,t in enumerate(c['tees']):
    if t.get('gender') not in ('MALE','FEMALE'):continue
    yards=[c['holes'][h]['teeYardages'][i] for h in indices]
    pars=[c['holes'][h]['ladiesPar' if t['gender']=='FEMALE' else 'menPar'] for h in indices]
    if not all(isinstance(y,(int,float)) and 10<=y<=1000 for y in yards):continue
    if not all(isinstance(x,int) and 2<=x<=7 for x in pars):continue
    rating=course.get('tcrs',[])[i];slope=course.get('tsls',[])[i]
    tees.append({'name':t['name'],'category':t['gender'],'yards':sum(yards),'par':sum(pars),'rating':rating if 15<=rating<=100 else None,'slope':slope if 55<=slope<=155 else None})
   if tees:courses.append({'name':course['name'],'holes':len(indices),'tees':tees})
  except (KeyError,IndexError,TypeError):continue
 if not courses:return None
 return {'id':ident,'name':c['name'],'address':c['address'],'courses':courses,'source_url':url}

def tokens(text):return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower())
def aligned(word,profile):
 if not profile or re.search(r'[:?]|\b(?:reviews?|photos?|pictures?|jobs?|weather|prices?|fees?|rates?|booking|tee times?|membership|restaurant|menu|wedding|events?|after|before|near me)\b',word,re.I):return False
 stop={'golf','course','courses','club','country','the','at','and','of','scorecard','scorecards'}
 wanted=set(tokens(word))-stop;named=set(tokens(profile['name']))-stop
 context=set(tokens(profile['name']+' '+profile['address']+' '+' '.join(c['name'] for c in profile['courses'])))
 return bool(wanted and named) and len(wanted&named)>=min(2,len(named)) and wanted<=context

def render(template,row,slug,layout,fixture=False):
 p=row['evidence'].get('course_profile')
 if not aligned(row['keyword'],p):raise ValueError('Course identity mismatch')
 E=html.escape;name=p['name'];date=__import__('datetime').datetime.fromtimestamp(row['evidence']['checked_at'],__import__('datetime').timezone.utc).date().isoformat()
 body='<article class="article-body" data-page-type="course_reference"><h1>'+E(name)+' — course and tee comparison</h1><p>'+E(p['address'])+'</p><p>Compare the listed layouts, tee lengths and scorecard totals before planning a round. These are source-recorded figures checked on '+date+', not live course conditions or booking availability.</p>'
 for c in p['courses']:
  body+='<h2>'+E(c['name'])+' · '+str(c['holes'])+' holes</h2><p>On a small screen, scroll the table sideways to see every column.</p><div tabindex="0" role="region" aria-label="Tee comparison table" style="overflow-x:auto"><table style="width:100%;min-width:540px;border-collapse:collapse"><caption>Listed tee options and calculated scorecard totals</caption><thead><tr>'+''.join('<th scope="col">'+x+'</th>' for x in ['Tee','Rating category','Yards','Par','Course rating','Slope'])+'</tr></thead><tbody>'
  for t in c['tees']:
   values=[t['name'],{'MALE':'Men','FEMALE':'Women'}.get(t['category'],t['category']),t['yards'],t['par'],t['rating'] if t['rating'] is not None else 'Not listed',t['slope'] if t['slope'] is not None else 'Not listed']
   body+='<tr>'+''.join('<td style="padding:8px;border-bottom:1px solid #ddd">'+E(str(v))+'</td>' for v in values)+'</tr>'
  yards=[t['yards'] for t in c['tees']];body+='</tbody></table></div><p>The listed options span '+str(min(yards))+'–'+str(max(yards))+' yards, a difference of '+str(max(yards)-min(yards))+' yards across '+str(c['holes'])+' holes. Yardage and par totals above are summed from the source scorecard. Repeated tee names can have separate rating categories; keep the category with its corresponding figures.</p>'
 body+='<h2>Check the layout before your round</h2><p>Match the layout name and tee color to the current scorecard supplied by the course. Temporary tees, closures and course changes may affect the figures. Confirm access, opening hours and current fees directly with the course.</p><h2>Source</h2><p><a rel="noopener noreferrer" href="'+E(row['source_url'],quote=True)+'">18Birdies course listing and scorecard for '+E(name)+'</a>, checked '+date+'. GolfCut is not affiliated with the listing provider or this course.</p><p><a href="/golf-guides">Browse golf references</a> · <a href="/try-tracer">Edit your own golf footage</a></p></article>'
 return layout(template,'/golf-guides/'+slug(row),name+' — '+p['address']+' | GolfCut',name+' at '+p['address']+'. Compare listed tee yardages, par, rating categories and course layouts using a dated scorecard source.',body).replace('href="/shot-library"','href="/golf-guides"').replace('>Shot library<','>Golf references<').replace('/shot-library.css','/golf-guides.css').replace('/shot-library.js','/golf-guides.js')
