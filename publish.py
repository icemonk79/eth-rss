#!/usr/bin/env python3
"""Usage: publish.py report.md <jutro|vece>
Replaces the entry for the slot in items.json, rebuilds feed.xml (only the latest morning item),
commits and pushes. Refuses to publish if the text contains personal-position wording (feed is PUBLIC).

At publish time, emoji and other pictographic symbols are replaced with small
embedded <img> tags (Twemoji PNGs as data:image URIs) so e-readers such as
PocketBook that cannot fetch remote images may still show the icons.
Chat/message copies are not modified by this script.
"""
import sys,re,html,email.utils,datetime,subprocess,zoneinfo,os,json
import re as _re
FORBIDDEN=[r'(?i)tvoj\w*\s+pozicij', r'(?i)\btvoj\w*\b', r'(?i)prose[čc]n\w*\s+(kupovn\w*\s+)?cen', r'(?i)srednj\w*\s+(kupovn\w*\s+)?cen', r'(?i)break[- ]even', r'(?i)nerealizovan', r'\bKUPUJ\b', r'\bDRŽI\b', r'\bSMANJI\b', r'2[,.]?900\b', r'(?i)pozicij\w*\s+od\b', r'(?i)\bkupio\b', r'(?i)\bkupljen\w*\b']
if len(sys.argv)!=3 or sys.argv[2] not in('jutro','vece'):
    sys.exit('Usage: publish.py <file.md> <jutro|vece>')
mdpath=os.path.abspath(sys.argv[1]); slot=sys.argv[2]
md=open(mdpath,encoding='utf-8').read()
hits=[w for w in FORBIDDEN if _re.search(w,md)]
if hits:
    sys.exit('ODBIJENO: tekst sadrži zabranjene izraze (privatnost, feed je javan): '+', '.join(hits))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emojiimg
emojiimg.setup('icons', 'https://icemonk79.github.io/eth-rss/icons')
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
body=emojiimg.replace_html('\n'.join(out).replace(']]>',']]&gt;'))
now=datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Belgrade'))
dani=['ponedeljak','utorak','sreda','četvrtak','petak','subota','nedelja']
name='jutarnji' if slot=='jutro' else 'večernji'
title=emojiimg.replace_plain(f"ETH/BTC {name} presek – {dani[now.weekday()]}, {now.day}. {now.month}. {now.year}.")
entry=dict(title=title,guid=f"eth-{slot}-{now:%Y-%m-%d-%H%M}",pubDate=email.utils.format_datetime(now),html=body,ts=now.timestamp())
items=json.load(open('items.json',encoding='utf-8')) if os.path.exists('items.json') else {}
items[slot]=entry
items={k:v for k,v in items.items() if k=='jutro'}
lst=sorted(items.values(),key=lambda e:e['ts'],reverse=True)
link='https://icemonk79.github.io/eth-rss/'
def item(e):
    html_body=emojiimg.replace_html(e['html'])
    return '''<item>
<title>'''+html.escape(emojiimg.replace_plain(e['title']))+'''</title>
<link>'''+link+'''</link>
<guid isPermaLink="false">'''+e['guid']+'''</guid>
<pubDate>'''+e['pubDate']+'''</pubDate>
<description><![CDATA['''+html_body+''']]></description>
<content:encoded><![CDATA['''+html_body+''']]></content:encoded>
</item>'''
xml='''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>ETH/BTC izveštaj</title>
<link>'''+link+'''</link>
<description>Jutarnji presek tržišta ETH i BTC</description>
<language>sr</language>
<lastBuildDate>'''+lst[0]['pubDate']+'''</lastBuildDate>
'''+chr(10).join(item(e) for e in lst)+'''
</channel>
</rss>
'''
from xml.dom import minidom as _m; _m.parseString(xml.encode())
# final safety check on the generated feed
bad=[w for w in FORBIDDEN if _re.search(w,xml)]
if bad: sys.exit('ODBIJENO: feed sadrži zabranjene izraze: '+', '.join(bad))
json.dump(items,open('items.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
open('feed.xml','w',encoding='utf-8').write(xml)
g=['git','-c','user.name=icemonk79','-c','user.email=icemonk79@users.noreply.github.com']
subprocess.run(['git','pull','-q','--rebase'],check=False)
subprocess.run(['git','add','feed.xml','items.json','icons','emojiimg.py','publish.py'],check=True)
subprocess.run(g+['commit','-qm',title],check=False)
if os.environ.get('SKIP_PUSH')!='1':
    subprocess.run(['git','push','-q'],check=True)
print('published',title)
