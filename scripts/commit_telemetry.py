import os, json, urllib.request, random, argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
from xml.sax.saxutils import escape

COLORS=['#152638','#16535e','#187e83','#19c9b9','#ff8744']
QUERY='''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){totalCommitContributions commitContributionsByRepository(maxRepositories:100){repository{isPrivate} contributions(first:32){pageInfo{hasNextPage} nodes{occurredAt commitCount}}}}}}'''
def get_counts(login,start,end):
    token=os.environ['GH_TOKEN']; counts=defaultdict(int); cursor=start
    while cursor<=end:
        stop=min(cursor+timedelta(days=27),end)
        payload={'query':QUERY,'variables':{'login':login,'from':str(cursor)+'T00:00:00Z','to':str(stop)+'T23:59:59Z'}}
        req=urllib.request.Request('https://api.github.com/graphql',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'commit-telemetry'})
        with urllib.request.urlopen(req,timeout=40) as res: data=json.load(res)
        if data.get('errors'): raise RuntimeError(str(data['errors']))
        collection=data['data']['user']['contributionsCollection']; repos=collection['commitContributionsByRepository']
        if len(repos)>=100: raise RuntimeError('Repository limit reached; refusing incomplete calendar')
        for repo in repos:
            if repo['repository']['isPrivate']: continue
            if repo['contributions']['pageInfo']['hasNextPage']: raise RuntimeError('Unexpected pagination')
            for node in repo['contributions']['nodes']:
                day=date.fromisoformat(node['occurredAt'][:10])
                if cursor<=day<=stop: counts[day]+=node['commitCount']
        cursor=stop+timedelta(days=1)
    return counts

def demo_counts(start,end):
    rng=random.Random(42042); counts={}; day=start
    while day<=end:
        counts[day]=rng.choice([0,0,0,1,2,3,4,6,8,12]) if day.weekday()<5 else rng.choice([0,0,0,1,2,4]); day+=timedelta(days=1)
    return counts

def level(n): return 0 if not n else 1 if n<=2 else 2 if n<=5 else 3 if n<=9 else 4

def render(counts,start,end,login,demo):
    first=start-timedelta(days=start.weekday()); total=sum(counts.values()); active=sum(n>0 for n in counts.values()); peak=max(counts.values(),default=0)
    title='DEMO DATA / NOT REAL COMMITS' if demo else 'LIVE / PUBLIC COMMIT CONTRIBUTIONS'
    a=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 296" width="960" height="296" role="img">',f'<title>{escape(title)} — {escape(login)}</title>', '<rect width="960" height="296" rx="15" fill="#080e19"/>','<rect x="12" y="12" width="936" height="272" rx="10" fill="none" stroke="#284755"/>','<path d="M28 27H104" stroke="#ff8744" stroke-width="3"/>','<g font-family="monospace" fill="#dff6fa">',f'<text x="28" y="53" font-size="23" font-weight="bold">COMMIT TELEMETRY // {escape(login)}</text>',f'<text x="28" y="74" font-size="12" fill="#19e5d0">{title}  |  {start} — {end}</text>']
    for i,(label,value) in enumerate([('COMMITS',total),('ACTIVE DAYS',active),('PEAK / DAY',peak)]):
        x=28+i*305; a.extend([f'<rect x="{x}" y="88" width="288" height="44" rx="6" fill="#101d2c" stroke="#284755"/>',f'<text x="{x+12}" y="104" font-size="10" fill="#82adb9">{label}</text>',f'<text x="{x+12}" y="124" font-size="20" fill="#e8faff">{value}</text>'])
    for i,s in enumerate(['M','T','W','T','F','S','S']): a.append(f'<text x="30" y="{165+i*15}" font-size="10" fill="#82adb9">{s}</text>')
    day=start; prevmonth=None
    while day<=end:
        col,row=divmod((day-first).days,7); x=52+col*16; y=154+row*15; n=counts.get(day,0)
        if day.month!=prevmonth:
            a.append(f'<text x="{x}" y="146" font-size="9" fill="#82adb9">{day.strftime("%b")}</text>'); prevmonth=day.month
        a.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" fill="{COLORS[level(n)]}"><title>{day}: {n} commits</title></rect>'); day+=timedelta(days=1)
    a.extend(['<rect x="49" y="151" width="20" height="107" rx="3" fill="#19e5d0" fill-opacity=".10" stroke="#19e5d0" stroke-opacity=".7"><animate attributeName="x" values="49;881;49" dur="12s" repeatCount="indefinite"/></rect>','<path d="M52 263H900" stroke="#284755"/>','<text x="52" y="278" font-size="10" fill="#82adb9">LOW</text>'])
    for i,c in enumerate(COLORS): a.append(f'<rect x="{82+i*16}" y="268" width="12" height="10" rx="2" fill="{c}"/>')
    a.append('<text x="166" y="278" font-size="10" fill="#82adb9">HIGH</text><text x="900" y="278" font-size="10" text-anchor="end" fill="#19e5d0">SIGNAL / SCANNING</text></g></svg>')
    return '\n'.join(a)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--demo',action='store_true'); parser.add_argument('--login',default='PilSenior'); parser.add_argument('--output',default='assets/commit-telemetry.svg'); args=parser.parse_args()
    end=datetime.now(timezone.utc).date(); start=end-timedelta(days=364)
    counts=demo_counts(start,end) if args.demo else get_counts(args.login,start,end)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(render(counts,start,end,args.login,args.demo),encoding='utf-8')
if __name__=='__main__': main()
