"""Persistent editorial state. No network or credentials required."""
from __future__ import annotations
import copy, hashlib, json, re, unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
CATEGORIES=['Mondo','Italia','Politica','Cronaca','Tecnologia','Movimenti','Nera','Rosa','Sport']
RANGES={c:((4,6) if c in ('Sport','Rosa','Movimenti') else (6,10)) for c in CATEGORIES}
ROME=ZoneInfo('Europe/Rome')
def stamp(now): return now.astimezone(timezone.utc).isoformat()
def parse(value): return datetime.fromisoformat(value.replace('Z','+00:00'))
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def atomic(path, data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def load(path): return json.loads(Path(path).read_text())
def normalize(text): return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKD',text).lower()))
def slug(text): return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()).strip('-')[:90]
def match_existing(articles, story):
 explicit=story.get('existing_id')
 if explicit:
  if explicit not in articles: raise ValueError('ID di aggiornamento inesistente')
  return explicit
 urls={s['url'] for s in story.get('sources',[])}
 for ident,a in articles.items():
  if a.get('demo'): continue
  if a.get('event_key')==story['event_key']: return ident
  # Exact headline is an additional deterministic guard; loose semantic merging is left to the editor.
  if normalize(a['title'])==normalize(story['title']): return ident
  if urls & {s['url'] for s in a['sources']}: return ident
 return None

def apply_story(state, story, now):
 """An update never changes id, URL or first-publication time."""
 articles=state['articles']; ident=match_existing(articles,story)
 old=articles.get(ident) if ident else None
 if old and old['category']!=story['category']: raise ValueError('Cambio sezione richiede revisione manuale')
 if not ident: ident='n-'+digest(story['event_key'])[:16]
 if ident in articles and not old: raise ValueError('Collisione ID')
 content={k:copy.deepcopy(story[k]) for k in ('category','event_key','title','summary','body','sources','relevance','event_time')}
 fingerprint=digest({k:content[k] for k in ('title','summary','body','sources')})
 if old and old.get('fingerprint')==fingerprint: return ident
 article={**content,'id':ident,'page':old['page'] if old else 'articoli/'+ident+'-'+slug(story['title'])+'.html','published_at':old['published_at'] if old else stamp(now),'updated_at':stamp(now),'fingerprint':fingerprint,'demo':False,'status':'candidate','revision':(old.get('revision',1)+1) if old else 1}
 if old:
  article['status']=old.get('status','candidate');article['archived_at']=old.get('archived_at')
  # A content update does not reset the age of the underlying event.
 articles[ident]=article
 return ident

def rank_score(a,now):
 age=max(0,(now-parse(a['event_time'])).total_seconds()/3600)
 return float(a['relevance'])-min(30,age/8)

def select(state,now,threshold=55):
 """Fill minima from verified material, add only relevant extras; never invent quota fillers."""
 pool=[a for a in state['articles'].values() if not a.get('demo') and not a.get('withdrawn')]
 desired=[]; shortages={}
 for c in CATEGORIES:
  lo,hi=RANGES[c];group=sorted((a for a in pool if a['category']==c),key=lambda a:(-rank_score(a,now),a['id']))
  if len(group)<lo:shortages[c]=lo-len(group)
  chosen=group[:lo]+[a for a in group[lo:] if rank_score(a,now)>=threshold][:hi-lo]
  desired.extend(chosen)
 # Initial launch is atomic: do not mix old demo stories with today's edition.
 if shortages:
  state['shortages']=shortages
  return False
 ordered=sorted(desired,key=lambda a:(-rank_score(a,now),a['id']))
 active=[a['id'] for a in ordered]; previously=set(state.get('active',[]))
 for ident,a in state['articles'].items():
  if ident in active:a['status']='active';a.pop('archived_at',None)
  elif ident in previously or a.get('status')=='active':a['status']='archived';a['archived_at']=stamp(now)
 state.update(active=active,featured=active[:4],shortages={},live=True,last_selection=stamp(now))
 return True

def close_day(state,now):
 """Close the last observed local day once; never fabricate editions for downtime."""
 today=now.astimezone(ROME).date().isoformat();previous=state.get('open_day')
 if not state.get('live'):return None
 if previous and previous<today:
  edition={'date':previous,'closed_at':stamp(now),'last_selection':state.get('last_selection'),'delayed':now.astimezone(ROME).date().isoformat()!=(datetime.fromisoformat(previous).date()+timedelta(days=1)).isoformat() or now.astimezone(ROME).hour>0 or now.astimezone(ROME).minute>5,'featured':list(state['featured']),'items':[copy.deepcopy(state['articles'][i]) for i in state['active']]}
  state['open_day']=today
  return edition
 state['open_day']=today
 return None
