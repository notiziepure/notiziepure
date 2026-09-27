"""Scheduled transaction: midnight snapshot, discovery, editorial checks, ranking, rendering."""
import argparse,copy,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
from core import *
from collect import collect
from editor import API,BudgetStop,prepare
from build import build
ROOT=Path(__file__).resolve().parents[1]
def cycle(root,now,mode='update'):
 settings=load(root/'config/settings.json');state=load(root/'data/state.json')
 edition=close_day(state,now)
 if edition:
  target=root/'data/editions'/f'{edition["date"]}.json'
  if not target.exists():atomic(target,edition)
 atomic(root/'data/state.json',state)
 if mode=='archive':build(root);return
 if not settings['live_enabled']:
  build(root);print('PREPARATO: automazione disattivata; nessuna richiesta di rete o API.');return
 report={'started_at':stamp(now),'errors':[],'rejected':[],'accepted':0}
 try:
  docs,report['errors']=collect(load(root/'config/sources.json'),settings,now)
  report['documents']=len(docs)
  state['last_check']=stamp(now)
  if not docs:report['status']='Nessun documento utilizzabile; edizione conservata'
  api=API(settings,root/'data/usage.json',now)
  cursor=state.get('cursor',0);order=CATEGORIES[cursor:]+CATEGORIES[:cursor]
  for c in order:
   subset=[d for d in docs if c in d['categories']][:settings['max_documents_per_category']]
   if len({d['publisher'] for d in subset})<2:continue
   signature=digest([{k:d[k] for k in ('id','text','published_at')} for d in subset])
   if state.setdefault('processed',{}).get(c)==signature:continue
   # Persist rotation even when a paid request fails or the budget is exhausted.
   state['cursor']=(CATEGORIES.index(c)+1)%len(CATEGORIES);atomic(root/'data/state.json',state)
   try:
    stories,rejected=prepare(c,subset,state,api,settings,now);report['rejected']+=rejected
    for story in stories:
     try:apply_story(state,story,now);report['accepted']+=1
     except ValueError as ex:report['rejected'].append({'title':story['title'],'reason':str(ex)})
    state['processed'][c]=signature
    atomic(root/'data/state.json',state)
   except BudgetStop as ex:report['status']=str(ex);break
   except Exception as ex:report['errors'].append({'category':c,'error':type(ex).__name__})
  if select(state,now,settings['extra_story_threshold']):
   state['open_day']=now.astimezone(ROME).date().isoformat()
  report['shortages']=state.get('shortages',{})
  report['stale_active']=[i for i in state['active'] if not state['articles'][i].get('demo') and (now-parse(state['articles'][i]['event_time'])).total_seconds()>settings['lookback_hours']*3600]
 except Exception as ex:report['errors'].append({'stage':'cycle','error':type(ex).__name__})
 finally:
  atomic(root/'data/state.json',state);atomic(root/'data/report.json',report);build(root)
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['update','archive','build'],default='update');args=p.parse_args()
 if args.mode=='build':build(ROOT)
 else:cycle(ROOT,datetime.now(timezone.utc),args.mode)
