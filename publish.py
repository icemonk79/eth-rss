#!/usr/bin/env python3
"""Usage: publish.py report.md <jutro|vece>
Replaces the entry for the slot in items.json, rebuilds feed.xml (max 2 items: latest morning + latest evening),
commits and pushes. Refuses to publish if the text contains personal-position wording (feed is PUBLIC)."""
import sys,re,html,email.utils,datetime,subprocess,zoneinfo,os,json
FORBIDDEN=['Tvoja pozicija','pozicij','prosečn','srednj','break-even','nerealizovan','tvoj','KUPUJ','DRŽI','SMANJI','2,900','2.900','2900']
if len(sys.argv)!=3 or sys.argv[2] not in('jutro','vece'):
    sys.exit('Usage: publish.py <file.md> <jutro|vece>')
mdpath=os.path.abspath(sys.argv[1]); slot=sys.argv[2]
md=open(mdpath,encoding='utf-8').read()
low=md.casefold()
hits=[w for w in FORBIDDEN if w.casefold() in low]
if hits:
    sys.exit('ODBIJENO: tekst sadrži zabranjene izraze (privatnost, feed je javan): '+', '.join(hits))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def inline(s):
    s=html.escape(s,quote=False)
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s
out=[];inl=False
for l in md.split('\n'):
    l=l.rstrip()
    if re.match(r'#{1,6} ',l):
        if inl: out.append('</ul>');inl=False
        out.append('<h2>'+inline(l.lstrip('#').strip())+'</h2>')
    elif re.match(r'[-*] ',l):
        if not inl: out.append('<ul>');inl=True
        out.append('<li>'+inline(l[2:])+'</li>')
    elif l.strip():
        if inl: out.append('</ul>');inl=False
        out.append('<p>'+inline(l)+'</p>')
if inl: out.append('</ul>')
body='\n'.join(out).replace(']]>',']]&gt;')
now=datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Belgrade'))
dani=['ponedeljak','utorak','sreda','četvrtak','petak','subota','nedelja']
name='jutarnji' if slot=='jutro' else 'večernji'
title=f"ETH/BTC {name} presek – {dani[now.weekday()]}, {now.day}. {now.month}. {now.year}."
entry=dict(title=title,guid=f"eth-{slot}-{now:%Y-%m-%d-%H%M}",pubDate=email.utils.format_datetime(now),html=body,ts=now.timestamp())
items=json.load(open('items.json',encoding='utf-8')) if os.path.exists('items.json') else {}
items[slot]=entry
items={k:v for k,v in items.items() if k in('jutro','vece')}
lst=sorted(items.values(),key=lambda e:e['ts'],reverse=True)
link='https://icemonk79.github.io/eth-rss/'
def item(e):
    return f'''<item>
<title>{html.escape(e['title'])}</title>
<link>{link}</link>
<guid isPermaLink="false">{e['guid']}</guid>
<pubDate>{e['pubDate']}</pubDate>
<description><![CDATA[{e['html']}]]></description>
<content:encoded><![CDATA[{e['html']}]]></content:encoded>
</item>'''
xml=f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>ETH/BTC izveštaj</title>
<link>{link}</link>
<description>Jutarnji i večernji presek tržišta ETH i BTC</description>
<language>sr</language>
<lastBuildDate>{lst[0]['pubDate']}</lastBuildDate>
{chr(10).join(item(e) for e in lst)}
</channel>
</rss>
'''
from xml.dom import minidom as _m; _m.parseString(xml.encode())
# final safety check on the generated feed
fl=xml.casefold()
bad=[w for w in FORBIDDEN if w.casefold() in fl]
if bad: sys.exit('ODBIJENO: feed sadrži zabranjene izraze: '+', '.join(bad))
json.dump(items,open('items.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
open('feed.xml','w',encoding='utf-8').write(xml)
g=['git','-c','user.name=icemonk79','-c','user.email=icemonk79@users.noreply.github.com']
subprocess.run(['git','pull','-q','--rebase'],check=False)
subprocess.run(['git','add','feed.xml','items.json'],check=True)
subprocess.run(g+['commit','-qm',title],check=False)
subprocess.run(['git','push','-q'],check=True)
print('published',title)
