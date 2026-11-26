"""Read only explicit publisher dates; never infer a recurring release day."""
from datetime import date,datetime
from html import unescape
import re
from urllib.parse import urlsplit
MONTHS={name:i+1 for i,name in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'])}
def text(s):return ' '.join(unescape(re.sub('<[^>]+>',' ',s)).split())
def boc_events(page,source):
    rows=[]
    for table in re.findall(r'<table\b[^>]*>(.*?)</table>',page,re.I|re.S):
        caption=re.search(r'<caption\b[^>]*>(.*?)</caption>',table,re.I|re.S)
        year=re.fullmatch(r'Schedule for (\d{4})',text(caption[1])) if caption else None
        if not year:continue
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.I|re.S):
            cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)
            if len(cells)!=2 or 'interest rate announcement' not in text(cells[1]).lower():continue
            m=re.fullmatch(r'([A-Za-z]+)\s+(\d{1,2})',text(cells[0]))
            if not m or m[1] not in MONTHS:raise ValueError('Unrecognized Bank of Canada calendar date')
            d=date(int(year[1]),MONTHS[m[1]],int(m[2])).isoformat()
            rows.append({'date':d,'title':'Interest rate announcement','reference':'Scheduled policy decision; no outcome implied','url':source,'provider':'Bank of Canada'})
    if not rows or len({r['date'] for r in rows})!=len(rows):raise ValueError('Empty or duplicate Bank of Canada dates')
    return rows
def statcan_events(raw,matches,source):
    out=[]
    for r in raw:
        title=r.get('title','')
        if not any(title.startswith(m) for m in matches if m):continue
        d=date.fromisoformat(r['date'][:10]).isoformat()
        url=r.get('url') or source
        if url.startswith('/daily-quotidien/'):url='https://www150.statcan.gc.ca/n1'+url
        elif url.startswith('//'):url='https:'+url
        if urlsplit(url).hostname not in ['www150.statcan.gc.ca','www.statcan.gc.ca']:raise ValueError('Unexpected calendar host')
        out.append({'date':d,'title':title,'reference':r.get('description',''),'url':url,'provider':'Statistics Canada'})
    if not out:raise ValueError('Empty Statistics Canada release calendar')
    return out
