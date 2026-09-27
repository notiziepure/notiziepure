"""Public RSS/Atom discovery and bounded, robots-aware article retrieval."""
import html, ipaddress, re, socket, urllib.request, urllib.parse, urllib.robotparser, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from core import digest,parse,stamp
MAX_BYTES=2_000_000
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  public_url(newurl)
  return super().redirect_request(req,fp,code,msg,headers,newurl)
def public_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:raise ValueError('URL non pubblico')
 if p.port not in (None,80,443):raise ValueError('Porta non consentita')
 for record in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80)):
  if not ipaddress.ip_address(record[4][0]).is_global:raise ValueError('Indirizzo privato escluso')
 return url
class Reader:
 def __init__(self,agent):self.agent=agent;self.robots={};self.opener=urllib.request.build_opener(SafeRedirect())
 def raw(self,url):
  public_url(url)
  req=urllib.request.Request(url,headers={'User-Agent':self.agent,'Accept':'application/rss+xml, application/atom+xml, text/html, application/xml;q=0.9'})
  with self.opener.open(req,timeout=18) as response:
   body=response.read(MAX_BYTES+1)
   if len(body)>MAX_BYTES:raise ValueError('Documento troppo grande')
   charset=response.headers.get_content_charset() or 'utf-8'
   return body.decode(charset,errors='replace'),response.geturl()
 def get(self,url):
  p=urllib.parse.urlsplit(url);origin=f'{p.scheme}://{p.netloc}'
  if origin not in self.robots:
   robot=urllib.robotparser.RobotFileParser()
   try:content,_=self.raw(origin+'/robots.txt');robot.parse(content.splitlines())
   except urllib.error.HTTPError as ex:
    if ex.code==404:robot.parse([])
    else:raise
   self.robots[origin]=robot
  if not self.robots[origin].can_fetch(self.agent,url):raise ValueError('Accesso escluso da robots.txt')
  return self.raw(url)
class HTML(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.feeds=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style','nav','footer','header'):self.skip+=1
  if tag=='link' and a.get('type') in ('application/rss+xml','application/atom+xml'):self.feeds.append(a.get('href',''))
 def handle_endtag(self,tag):
  if tag in ('script','style','nav','footer','header'):self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def plain(text):
 p=HTML();p.feed(text);return ' '.join(' '.join(p.parts).split())
def parse_feed(text,base):
 # Do not expand entities or accept DTDs from external feeds.
 if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ValueError('DTD non consentito')
 root=ET.fromstring(text);out=[]
 for item in root.iter():
  if item.tag.split('}')[-1] not in ('item','entry'):continue
  fields={};links=[]
  for child in item:
   key=child.tag.split('}')[-1];value=''.join(child.itertext()).strip()
   fields[key]=value
   if key=='link' and child.get('rel','alternate')=='alternate':links.append(child.get('href') or value)
  url=urllib.parse.urljoin(base,next((v for v in links if v),''))
  date=fields.get('updated') or fields.get('published') or fields.get('pubDate')
  try:dt=parse(date)
  except (ValueError,AttributeError,TypeError):
   try:dt=parsedate_to_datetime(date)
   except (ValueError,TypeError):continue
  if not dt.tzinfo:dt=dt.replace(tzinfo=timezone.utc)
  out.append({'title':plain(fields.get('title','')),'url':url,'published_at':stamp(dt),'text':plain(fields.get('encoded') or fields.get('content') or fields.get('description') or fields.get('summary',''))})
 return out

def collect(sources,settings,now):
 reader=Reader(settings['user_agent']);docs={};errors=[]
 for source in sources:
  if not source.get('enabled'):continue
  try:
   feed=source.get('feed')
   if not feed:
    raw,home=reader.get(source['home']);p=HTML();p.feed(raw)
    if not p.feeds:raise ValueError('Nessun feed RSS dichiarato')
    feed=urllib.parse.urljoin(home,p.feeds[0])
   raw,feed_url=reader.get(feed);entries=parse_feed(raw,feed_url)
   recent=[x for x in entries if -1<=(now-parse(x['published_at'])).total_seconds()/3600<=settings['lookback_hours']]
   recent.sort(key=lambda x:x['published_at'],reverse=True)
   for item in recent[:settings['max_articles_per_source']]:
    try:
     host=urllib.parse.urlsplit(item['url']).hostname or ''
     if not any(host==h or host.endswith('.'+h) for h in source['article_hosts']):continue
     # A short feed is a discovery pointer, not sufficient evidence for a long article.
     text=item['text']
     if len(text.split())<180:
      article,final=reader.get(item['url']);finalhost=urllib.parse.urlsplit(final).hostname or ''
      if not any(finalhost==h or finalhost.endswith('.'+h) for h in source['article_hosts']):continue
      # Extract article/main regions rather than navigation and subscription notices.
      match=re.search(r'<(?:article|main)\b[^>]*>(.*?)</(?:article|main)>',article,re.S|re.I)
      if not match:continue
      text=plain(match[1])
     if len(text.split())<180:continue
     text=' '.join(text.split()[:1400]);ident=digest(item['url'])[:20]
     docs[ident]={**item,'id':ident,'text':text,'publisher':source['publisher'],'name':source['name'],'categories':source['categories'],'primary':source.get('primary',False),'checked_at':stamp(now)}
    except Exception as ex:errors.append({'source':source['name'],'stage':'article','error':type(ex).__name__})
  except Exception as ex:errors.append({'source':source['name'],'stage':'feed','error':type(ex).__name__})
 return list(docs.values()),errors
