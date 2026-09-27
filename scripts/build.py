"""Render the entire publication offline; preserve permanent and daily-snapshot URLs."""
import html,json,math,re,os
from pathlib import Path
from datetime import datetime
from core import CATEGORIES,load,parse,ROME
E=html.escape
MONTHS=['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre']
def date_label(value):
 d=parse(value) if 'T' in value else datetime.fromisoformat(value)
 if d.tzinfo:d=d.astimezone(ROME)
 return f'{d.day} {MONTHS[d.month-1]} {d.year}'
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
def shell(title,body,prefix=''):
 return f'<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}</title><link rel="stylesheet" href="{prefix}assets/style.css"></head><body><a class="skip" href="#contenuto">Vai al contenuto</a><div class="wrap">{body}</div></body></html>'
def header(prefix=''):
 return f'<header><a class="masthead" href="{prefix}index.html">notiziepure</a></header>'
def footer(prefix=''):
 return f'<footer class="footer"><a href="{prefix}index.html">Prima pagina</a><a href="{prefix}archivio/index.html">Archivio</a><span>notiziepure</span></footer>'
def story_page(a,icons,prefix='../',snapshot=None):
 note='Edizione di prova del 26 settembre 2026' if a.get('demo') else 'Pubblicato '+date_label(a['published_at'])+' · Aggiornato '+date_label(a['updated_at'])+' alle '+parse(a['updated_at']).astimezone(ROME).strftime('%H:%M')
 if snapshot:note+=' · Copia dell’edizione del '+date_label(snapshot)
 elif a.get('status')=='archived':note+=' · In archivio'
 sources=''.join(f'<li><a href="{E(v["url"],quote=True)}" target="_blank" rel="noopener noreferrer">{E(v["name"])} ↗</a><span>{E(v.get("role","Fonte consultata"))}</span></li>' for v in a['sources'])
 paragraphs=''.join(f'<p>{E(t)}</p>' for t in a['body'])
 body=header(prefix)+f'<nav class="breadcrumb"><a href="{prefix}index.html">← Prima pagina</a> / <a href="{prefix}index.html#{a["category"].lower()}">{E(a["category"])}</a></nav><main class="article-main" id="contenuto"><article><div class="kicker">{icons[a["category"]]}{E(a["category"])}</div><h1>{E(a["title"])}</h1><p class="standfirst">{E(a["summary"])}</p><div class="article-meta">{E(note)}</div><div class="article-body">{paragraphs}</div><section class="sources" id="fonti"><h2>Fonti e approfondimenti</h2><ul>{sources}</ul><p class="source-note">Rielaborazione originale. Le fonti esterne richiedono una connessione. Dichiarazioni e posizioni appartengono ai soggetti cui sono attribuite.</p></section></article></main>'+footer(prefix)
 return shell(a['title']+' | notiziepure',body,prefix)
def card(a,icons,featured=False,hero=False,href=None,image_prefix=''):
 href=href or a['page'];h='h2' if featured else 'h3'
 text=f'<div class="kicker">{icons[a["category"]]}{E(a["category"])}</div><{h}><a href="{href}">{E(a["title"])}</a></{h}><p class="story-text">{E(a["summary"])}</p><div class="meta"><a href="{href}#fonti">{E(" · ".join(s["name"] for s in a["sources"][:2]))} · {len(a["sources"])} fonti</a></div>'
 if hero:text='<div class="lead-copy">'+text+'</div>'+f'<figure class="lead-art"><img src="{image_prefix}assets/apertura-china.png" width="1536" height="1024" alt="Illustrazione in bianco e nero: fascicoli su un tavolo, sedie vuote e una porta aperta"><figcaption>Illustrazione editoriale generata con AI · scena simbolica, non una ricostruzione dei fatti</figcaption></figure>'
 return f'<article class="story" data-category="{a["category"]}" data-id="{a["id"]}">{text}</article>'
def front(items,featured,icons,prefix='',snapshot=False):
 byid={a['id']:a for a in items};lead=[byid[i] for i in featured];rest=[a for a in items if a['id'] not in featured]
 out='<section class="opening" aria-label="Le quattro notizie principali">'+''.join(card(a,icons,True,index==0,image_prefix=prefix) for index,a in enumerate(lead))+'</section><div class="category-sections">'
 for c in CATEGORIES:
  group=[a for a in rest if a['category']==c];nlead=sum(a['category']==c for a in lead)
  count=f'{len(group)} notizie'+(f' · {nlead} in apertura' if nlead else '')
  out+=f'<section class="category-section" id="{c.lower()}" data-section="{c}" aria-labelledby="heading-{c.lower()}"><div class="horizontal-heading"><h2 id="heading-{c.lower()}">{icons[c]}{c}</h2><span>{count}</span></div><div class="section-stories">'+''.join(card(a,icons) for a in group)+'</div></section>'
 return out+'</div>'
def build(root):
 root=Path(root);site=root/'site';state=load(root/'data/state.json');icons=load(root/'templates/icons.json')
 active=[state['articles'][i] for i in state['active']]
 for a in state['articles'].values():
  if a.get('status')!='candidate':write(site/a['page'],story_page(a,icons))
 editions=sorted((root/'data/editions').glob('*.json'),reverse=True)
 daily_links=[]
 for file in editions:
  ed=load(file);day=ed['date'];target=site/'edizioni'/day
  for a in ed['items']:write(target/a['page'],story_page(a,icons,'../../../',day))
  note='Edizione di prova' if ed.get('demo') else 'Edizione chiusa a mezzanotte · Europe/Rome'
  if ed.get('delayed'):note+=' · Archiviazione recuperata alla ripresa del servizio'
  body=header('../../')+f'<nav class="breadcrumb"><a href="../../archivio/index.html">← Archivio</a> / {date_label(day)}</nav><main id="contenuto"><div class="section-top"><span>{E(note)}</span></div>'+front(ed['items'],ed['featured'],icons,'../../',True)+'</main>'+footer('../../')
  write(target/'index.html',shell('Edizione del '+date_label(day)+' | notiziepure',body,'../../'))
  daily_links.append(f'<li><a href="../edizioni/{day}/index.html">{date_label(day)}</a>'+(' · Prova' if ed.get('demo') else '')+'</li>')
 archived=sorted((a for a in state['articles'].values() if a.get('status')=='archived'),key=lambda a:a.get('archived_at') or a['updated_at'],reverse=True)
 retired=''.join(f'<li><a href="../{a["page"]}">{E(a["title"])}</a> · {E(a["category"])}</li>' for a in archived)
 archivebody=header('../')+'<main class="article-main" id="contenuto"><h1>Archivio</h1><p>Una sola edizione al giorno, chiusa a mezzanotte nel fuso italiano. Ogni copia conserva testi e ordine di quel giorno.</p><h2>Edizioni giornaliere</h2><ul>'+(''.join(daily_links) or '<li>La prima edizione sarà salvata alla prossima chiusura.</li>')+'</ul><h2>Notizie uscite dalla prima pagina</h2><p>Gli articoli restano consultabili al loro indirizzo originale.</p><ul>'+(retired or '<li>Nessuna notizia rimossa dalla selezione.</li>')+'</ul></main>'+footer('../')
 write(site/'archivio/index.html',shell('Archivio | notiziepure',archivebody,'../'))
 nav='<button type="button" data-filter="Tutte" aria-pressed="true">Tutte</button>'+''.join(f'<button type="button" data-filter="{c}" aria-pressed="false">{icons[c]}{c}</button>' for c in CATEGORIES)
 label=date_label(state.get('last_selection','2026-09-26')) if state.get('live') else '26 settembre 2026 · Edizione di prova'
 status='Controlli ogni 30 minuti · Archivio alle 00:00' if state.get('live') else 'Aggiornamento ogni 30 minuti predisposto · non ancora attivo'
 checked='Ultimo controllo: '+parse(state['last_check']).astimezone(ROME).strftime('%d/%m/%Y %H:%M') if state.get('last_check') else 'In attesa della pubblicazione'
 body=f'<header><div class="topline"><span>{E(label)}</span><a href="archivio/index.html">Archivio</a></div><a class="masthead" href="index.html">notiziepure</a><div class="editions"><span>{E(status)}</span></div><nav class="filters" aria-label="Filtra per sezione">{nav}</nav></header><main id="contenuto"><div class="section-top"><div class="eyebrow" id="opening-label">In primo piano</div><span id="count" aria-live="polite">{len(active)} notizie · 9 sezioni</span></div><p class="source-note">{E(checked)}</p>'+front(active,state['featured'],icons)
 body+='<section class="archive"><h2>Archivio</h2><p>Ritrova l’edizione di ogni giorno e gli articoli usciti dalla homepage. Testi e indirizzi vengono conservati.</p><a href="archivio/index.html">Sfoglia l’archivio →</a></section><details class="about"><summary>Come funziona notiziepure</summary><p>Quattro aperture scelte per rilevanza tra tutte le sezioni, poi le altre notizie senza doppioni. Da 4 a 6 articoli per Sport, Rosa e Movimenti; da 6 a 10 per le altre sezioni, comprese le aperture.</p><p>Il controllo confronta fonti diverse, aggiorna gli sviluppi dello stesso fatto e ricalcola l’ordine. I testi senza riscontri sufficienti non vengono inseriti. In mancanza di novità attendibili restano le notizie precedenti. Le informazioni hanno la data mostrata nei singoli articoli.</p><p>L’archivio giornaliero viene chiuso alle 00:00, Europe/Rome. Se il servizio parte in ritardo, recupera la chiusura conservando l’ultima versione disponibile prima del nuovo aggiornamento. Questa versione di prova non è ancora collegata ai servizi di aggiornamento.</p></details></main>'+footer()+ '<script src="assets/site.js"></script>'
 if state.get('live'):body=body.replace('Questa versione di prova non è ancora collegata ai servizi di aggiornamento.','Gli orari di esecuzione possono subire ritardi. L’ora dell’ultimo controllo è indicata in homepage.')
 write(site/'index.html',shell('notiziepure',body))
 (site/'.nojekyll').touch()
 if (root/'config/domain.txt').exists():write(site/'CNAME',(root/'config/domain.txt').read_text().strip()+'\n')
 if (site/'notizie.json').exists():(site/'notizie.json').unlink()
if __name__=='__main__':build(Path(__file__).resolve().parents[1])
