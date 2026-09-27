from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import re
ROOT=Path(__file__).resolve().parents[1]/'site'
class Page(HTMLParser):
 def __init__(self,text):super().__init__();self.ids=set();self.links=[];self.images=0;self.feed_ids=[];self.feed_cats=[];self.feed(text)
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.add(a['id'])
  if t=='img':self.images+=1
  if t=='article' and a.get('class')=='story':self.feed_ids.append(a['data-id']);self.feed_cats.append(a['data-category'])
  for key in ('href','src'):
   if key in a:self.links.append(a[key])
def check(root=ROOT):
 pages={f.resolve():Page(f.read_text()) for f in root.rglob('*.html')}
 for f,p in pages.items():
  for url in p.links:
   u=urlsplit(url)
   if u.scheme:
    assert u.scheme in ('http','https'),(f,url)
    continue
   target=(f.parent/unquote(u.path)).resolve() if u.path else f
   assert target.is_relative_to(root.resolve()) and target.exists(),(f,url)
   if u.fragment:assert target in pages and unquote(u.fragment) in pages[target].ids,(f,url)
 home=pages[(root/'index.html').resolve()]
 assert home.images==1
 assert len(home.feed_ids)==len(set(home.feed_ids))
 print(f'PASS: {len(pages)} pagine, collegamenti e ancore validi, una sola immagine in homepage.')
if __name__=='__main__':check()
