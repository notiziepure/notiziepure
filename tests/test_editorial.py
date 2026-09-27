import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import *
from collect import parse_feed,public_url
from editor import validate,API,BudgetStop
from build import build
from run import cycle
NOW=datetime(2026,9,27,10,tzinfo=timezone.utc)
def article(c,n,score=75):
 ident=c+str(n)
 return {'id':ident,'category':c,'event_key':ident,'title':f'Notizia {ident}','summary':'Una sintesi di prova con informazioni verificate.','body':['Approfondimento di prova.'],'sources':[{'name':'Uno','url':'https://example.com/'+ident},{'name':'Due','url':'https://example.org/'+ident}],'relevance':score,'event_time':stamp(NOW),'published_at':stamp(NOW),'updated_at':stamp(NOW),'page':'articoli/'+slug(ident)+'.html','demo':False,'status':'active'}
def populated():
 articles={a['id']:a for c in CATEGORIES for a in [article(c,n) for n in range(RANGES[c][0]) ]}
 return {'articles':articles,'active':list(articles),'featured':list(articles)[:4],'live':True,'open_day':'2026-09-27'}
class EditorialTests(unittest.TestCase):
 def test_ranges_and_four_global_leads(self):
  state=populated()
  for c in CATEGORIES:
   for n in range(20,32):
    a=article(c,n,90 if c=='Sport' else 80);state['articles'][a['id']]=a
  self.assertTrue(select(state,NOW))
  for c,(lo,hi) in RANGES.items():self.assertEqual(sum(state['articles'][i]['category']==c for i in state['active']),hi)
  self.assertEqual(len(state['featured']),4);self.assertTrue(all(state['articles'][i]['category']=='Sport' for i in state['featured']))
 def test_update_keeps_url_and_first_date(self):
  s=populated();old=copy.deepcopy(s['articles']['Mondo0']);story={**old,'existing_id':'Mondo0','title':'Titolo aggiornato','body':['Un nuovo sviluppo documentato.']}
  ident=apply_story(s,story,NOW);self.assertEqual(ident,'Mondo0');self.assertEqual(s['articles'][ident]['page'],old['page']);self.assertEqual(s['articles'][ident]['published_at'],old['published_at'])
 def test_duplicate_event_merges_without_explicit_id(self):
  s=populated();old=s['articles']['Italia0'];ident=apply_story(s,{**old,'existing_id':None,'title':'Altro titolo per lo stesso fatto'},NOW)
  self.assertEqual(ident,'Italia0')
 def test_removal_archives_and_keeps_original_page(self):
  s=populated();old=s['articles']['Sport0'];url=old['page'];old['relevance']=1
  for n in range(10,18):
   a=article('Sport',n,99);s['articles'][a['id']]=a
  select(s,NOW);self.assertNotIn('Sport0',s['active']);self.assertEqual(old['status'],'archived');self.assertEqual(old['page'],url)
 def test_shortage_keeps_whole_previous_edition(self):
  s=populated();previous=list(s['active']);s['articles']['Sport0']['withdrawn']=True
  self.assertFalse(select(s,NOW));self.assertEqual(s['active'],previous);self.assertEqual(s['shortages'],{'Sport':1})
 def test_day_boundary_is_rome_not_utc(self):
  s=populated();s['open_day']='2026-09-26';s['last_selection']='2026-09-26T21:30:00+00:00'
  self.assertIsNone(close_day(s,datetime(2026,9,26,21,59,tzinfo=timezone.utc)))
  edition=close_day(s,datetime(2026,9,26,22,0,tzinfo=timezone.utc));self.assertEqual(edition['date'],'2026-09-26')
  s['articles']['Mondo0']['title']='Modificato';self.assertNotEqual(edition['items'][0]['title'],'Modificato')
  self.assertIsNone(close_day(s,datetime(2026,9,26,22,30,tzinfo=timezone.utc)))
 def test_dst_winter_boundary_and_downtime(self):
  s=populated();s['open_day']='2026-10-25'
  self.assertIsNone(close_day(s,datetime(2026,10,25,22,30,tzinfo=timezone.utc)))
  ed=close_day(s,datetime(2026,10,25,23,0,tzinfo=timezone.utc));self.assertEqual(ed['date'],'2026-10-25')
  s['open_day']='2026-09-20';ed=close_day(s,NOW);self.assertEqual(ed['date'],'2026-09-20');self.assertTrue(ed['delayed']);self.assertEqual(s['open_day'],'2026-09-27')
 def test_low_relevance_does_not_fill_to_maximum(self):
  s=populated();a=article('Sport',20,10);s['articles'][a['id']]=a;select(s,NOW)
  self.assertEqual(sum(s['articles'][i]['category']=='Sport' for i in s['active']),4)
 def test_rss_atom_and_xxe(self):
  rss='<rss><channel><item><title>Prova</title><link>https://example.com/a</link><pubDate>Sun, 27 Sep 2026 10:00:00 GMT</pubDate><description>Testo</description></item></channel></rss>'
  self.assertEqual(parse_feed(rss,'https://example.com/')[0]['title'],'Prova')
  atom='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title><link href="/a"/><updated>2026-09-27T10:00:00Z</updated><summary>Testo</summary></entry></feed>'
  self.assertEqual(parse_feed(atom,'https://example.com/')[0]['url'],'https://example.com/a')
  with self.assertRaises(ValueError):parse_feed('<!DOCTYPE rss>'+rss,'https://example.com/')
 def test_private_urls_rejected(self):
  with self.assertRaises(ValueError):public_url('file:///etc/passwd')
  with self.assertRaises(ValueError):public_url('http://127.0.0.1/test')
 def test_budget_zero_never_calls_api(self):
  with tempfile.TemporaryDirectory() as d:
   settings={'model':'configured-model','ai_enabled':True,'monthly_budget_usd':0,'input_usd_per_million_tokens':1,'output_usd_per_million_tokens':1,'max_calls_per_run':10,'max_output_tokens':100}
   with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only-not-real'}),patch('urllib.request.urlopen') as request:
    with self.assertRaises(BudgetStop):API(settings,Path(d)/'usage.json',NOW).ask('test',{}, {})
    request.assert_not_called()
 def test_budget_reserved_before_failed_request(self):
  with tempfile.TemporaryDirectory() as d:
   settings={'model':'configured-model','ai_enabled':True,'monthly_budget_usd':1,'input_usd_per_million_tokens':1,'output_usd_per_million_tokens':1,'max_calls_per_run':10,'max_output_tokens':100}
   with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only-not-real','NOTIZIEPURE_PERSIST_BUDGET':'0'}),patch('urllib.request.urlopen',side_effect=TimeoutError):
    with self.assertRaises(TimeoutError):API(settings,Path(d)/'usage.json',NOW).ask('test',{}, {})
   self.assertGreater(load(Path(d)/'usage.json')['2026-09']['reserved_usd'],0)
 def test_evidence_and_distinct_publishers(self):
  text='Il consiglio ha approvato oggi il nuovo progetto dopo il voto finale.'
  docs=[{'id':str(i),'text':text,'publisher':str(i),'name':str(i),'url':'https://example.com/'+str(i),'published_at':stamp(NOW)} for i in (1,2)]
  story={'category':'Italia','title':'Un progetto approvato','summary':' '.join(['Sintesi']*25),'body':[' '.join(['Contenuto']*65)]*3,'source_ids':['1','2'],'event_time':stamp(NOW),'relevance':70,'confidence':.95,'evidence':[{'source_id':str(i),'quote':'Il consiglio ha approvato oggi'} for i in (1,2)]}
  self.assertEqual(len(validate(story,docs,{'minimum_confidence':.9,'lookback_hours':72},NOW,'Italia')['sources']),2)
  story['evidence'][0]['quote']='Questa informazione non esiste nel documento'
  with self.assertRaises(ValueError):validate(story,docs,{'minimum_confidence':.9,'lookback_hours':72},NOW,'Italia')
  docs[1]['publisher']='1'
  with self.assertRaises(ValueError):validate(story,docs,{'minimum_confidence':.9,'lookback_hours':72},NOW,'Italia')
 def test_disabled_cycle_has_no_network(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as d:
   import shutil
   dest=Path(d);shutil.copytree(root/'config',dest/'config');shutil.copytree(root/'data',dest/'data');shutil.copytree(root/'templates',dest/'templates');shutil.copytree(root/'site/assets',dest/'site/assets')
   with patch('run.collect') as network,patch('editor.API.ask') as api:
    cycle(dest,NOW);network.assert_not_called();api.assert_not_called()
   self.assertTrue((dest/'site/archivio/index.html').exists())
 def test_day_snapshot_texts_immutable_after_update(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as d:
   import shutil
   dest=Path(d);shutil.copytree(root/'templates',dest/'templates');shutil.copytree(root/'site/assets',dest/'site/assets')
   s=populated();s['open_day']='2026-09-26';s['last_selection']=stamp(NOW)
   edition=close_day(s,NOW);atomic(dest/'data/editions/2026-09-26.json',edition)
   s['articles']['Mondo0']['title']='Nuovo titolo permanente';atomic(dest/'data/state.json',s);build(dest)
   self.assertIn('Nuovo titolo permanente',(dest/'site'/s['articles']['Mondo0']['page']).read_text())
   self.assertNotIn('Nuovo titolo permanente',(dest/'site/edizioni/2026-09-26'/s['articles']['Mondo0']['page']).read_text())
if __name__=='__main__':unittest.main()
