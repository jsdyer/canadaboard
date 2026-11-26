"""Capture national indicators directly from official public sources."""
import argparse,json,math,re,time
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError
from calendars import boc_events,statcan_events
ROOT=Path(__file__).resolve().parents[1]
WDS='https://www150.statcan.gc.ca/t1/wds/rest/'
UA='CoolCode Canada Board (+https://coolcode.ca/canadaboard/)'
def request(url,payload=None,text=False):
    req=Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'User-Agent':UA,'Accept':'text/html' if text else 'application/json','Content-Type':'application/json'})
    for attempt in range(3):
        try:
            with urlopen(req,timeout=60) as r:raw=r.read(12_000_001)
            if len(raw)>12_000_000:raise ValueError('Source response too large')
            return raw.decode() if text else json.loads(raw)
        except (URLError,TimeoutError,OSError):
            if attempt==2:raise
            time.sleep(2**attempt)
def validate_config(c):
    if not 24<=c['periods']<=240 or not c['series']:raise ValueError('Invalid collection periods')
    ids=[s['id'] for s in c['series']]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch('[a-z][a-z0-9-]*',x) for x in ids):raise ValueError('Invalid series IDs')
    for s in c['series']:
        if s['provider'] not in ('statcan','valet') or s['transform'] not in ('level','yoy','reciprocal'):raise ValueError('Unknown source/transform')
def normalize_statcan(raw,meta,specs):
    defs={x['object']['vectorId']:x['object'] for x in meta if x.get('status')=='SUCCESS'}
    expected={s['vector']:s for s in specs};out={}
    for response in raw:
        o=response.get('object',{});v=o.get('vectorId')
        if v not in expected or response.get('status')!='SUCCESS' or o.get('responseStatusCode')!=0:raise ValueError('Unexpected vector response')
        s=expected[v];m=defs.get(v,{})
        if m.get('productId')!=s['table'] or m.get('memberUomCode')!=s['source_unit'] or m.get('scalarFactorCode')!=s['scalar'] or m.get('frequencyCode')!=6:raise ValueError('Vector metadata changed')
        points=[]
        for p in o['vectorDataPoint']:
            d=date.fromisoformat(p['refPer']).isoformat()[:7]
            if p.get('frequencyCode')!=6 or p.get('scalarFactorCode')!=s['scalar']:raise ValueError('Observation dimensions changed')
            value=p.get('value');valid=value is not None and p.get('statusCode',0)==0 and p.get('securityLevelCode',0)==0
            if valid:
                value=float(value)*10**s['scalar']
                if not math.isfinite(value):raise ValueError('Non-finite observation')
            else:value=None
            points.append({'date':d,'value':value,'release_time':p.get('releaseTime'),'status':p.get('statusCode',0)})
        if not points or len({p['date'] for p in points})!=len(points):raise ValueError('Missing or duplicate periods')
        out[s['id']]={'metadata':m,'points':sorted(points,key=lambda p:p['date'])}
    if set(out)!={s['id'] for s in specs}:raise ValueError('Missing required vector')
    return out
def transform(points,kind):
    lookup={p['date']:p['value'] for p in points};out=[]
    for p in points:
        q=dict(p);v=p['value']
        if kind=='reciprocal':q['value']=1/v if v is not None and v>0 else None
        elif kind=='yoy':
            prior=lookup.get(str(int(p['date'][:4])-1)+p['date'][4:]);q['index_value']=v;q['value']=round((v/prior-1)*100,1) if v is not None and prior and prior>0 else None
        out.append(q)
    return out
def collect():
    c=json.loads((ROOT/'config/series.json').read_text());validate_config(c);checked=datetime.now(timezone.utc).isoformat(timespec='seconds');sc=[s for s in c['series'] if s['provider']=='statcan'];bc=[s for s in c['series'] if s['provider']=='valet'];tracks={};sources=[]
    if sc:
        meta=request(WDS+'getSeriesInfoFromVector',[{'vectorId':s['vector']} for s in sc]);raw=request(WDS+'getDataFromVectorsAndLatestNPeriods',[{'vectorId':s['vector'],'latestN':c['periods']} for s in sc]);tracks.update(normalize_statcan(raw,meta,sc));sources.append(WDS+'getDataFromVectorsAndLatestNPeriods')
    if bc:
        url='https://www.bankofcanada.ca/valet/observations/'+','.join(s['series'] for s in bc)+'/json?start_date='+c['valet_start'];raw=request(url);sources.append(url)
        for s in bc:
            m=raw['seriesDetail'][s['series']]
            if m['metadata']['unit']!=s['source_unit']:raise ValueError('Valet unit changed: '+s['series'])
            points=[]
            for p in raw['observations']:
                d=date.fromisoformat(p['d']).isoformat();v=p.get(s['series'],{}).get('v');v=None if v in (None,'') else float(v)
                if v is not None and not math.isfinite(v):raise ValueError('Non-finite Valet observation')
                points.append({'date':d,'value':v})
            tracks[s['id']]={'metadata':m,'points':points}
    series=[]
    for s in c['series']:
        item={**s,**tracks[s['id']]};item['source_url']='https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid='+str(s['table'])+'01' if s['provider']=='statcan' else 'https://www.bankofcanada.ca/valet/series/'+s['series']
        item['points']=transform(item['points'],s['transform'])
        usable=[p for p in item['points'] if p['value'] is not None]
        if len(usable)<12:raise ValueError('Too few observations for '+s['id'])
        if date.fromisoformat(usable[-1]['date']+'-01' if len(usable[-1]['date'])==7 else usable[-1]['date'])>datetime.now(timezone.utc).date():raise ValueError('Future observation')
        series.append(item)
    events=statcan_events(request(c['calendar_url']),[s['calendar_match'] for s in sc],c['calendar_url'])+boc_events(request(c['boc_calendar_url'],text=True),c['boc_calendar_url'])
    since=str(int(checked[:4])-1)+'-01-01';events=sorted([e for e in events if e['date']>=since],key=lambda x:(x['date'],x['title']))
    out={'schema':'coolcode.canadaboard.v1','checked_at':checked,'series':series,'calendar':{'checked_at':checked,'events':events,'sources':[c['calendar_url'],c['boc_calendar_url']]},'sources':sources}
    dest=ROOT/'web/data';dest.mkdir(exist_ok=True);old=dest/'snapshot.json'
    if old.exists():
        prev=json.loads(old.read_text());before={s['id']:max(p['date'] for p in s['points'] if p['value'] is not None) for s in prev['series']}
        for s in series:
            if s['id'] in before and max(p['date'] for p in s['points'] if p['value'] is not None)<before[s['id']]:raise ValueError('Observation coverage regressed')
    tmp=dest/'snapshot.json.tmp';tmp.write_text(json.dumps(out,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n');tmp.replace(old)
    print('Captured '+str(len(series))+' official indicators and '+str(len(events))+' calendar entries')
if __name__=='__main__':collect()
