#!/usr/bin/env python3
import os, sys, json, urllib.request, datetime

token = os.environ.get('CLOUDFLARE_API_TOKEN')
acc   = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
site  = "219ba416e0434050bc864e8ab09692be"   # Web Analytics beacon token (site id)
if not token or not acc:
    print("Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID in env"); sys.exit(1)

now = datetime.datetime.now(datetime.timezone.utc)
iso = lambda dt: dt.strftime('%Y-%m-%dT%H:%M:%SZ')
d1, d7, n = iso(now-datetime.timedelta(hours=24)), iso(now-datetime.timedelta(days=7)), iso(now)

q = """
query($acc:String!,$site:String!,$d1:Time!,$d7:Time!,$now:Time!){
 viewer{ accounts(filter:{accountTag:$acc}){
  last24: rumPageloadEventsAdaptiveGroups(filter:{siteTag:$site,datetime_geq:$d1,datetime_leq:$now},limit:1){ count sum{visits} }
  last7d: rumPageloadEventsAdaptiveGroups(filter:{siteTag:$site,datetime_geq:$d7,datetime_leq:$now},limit:1){ count sum{visits} }
  pages: rumPageloadEventsAdaptiveGroups(filter:{siteTag:$site,datetime_geq:$d7,datetime_leq:$now},limit:10,orderBy:[count_DESC]){ count sum{visits} dimensions{ requestPath } }
  referrers: rumPageloadEventsAdaptiveGroups(filter:{siteTag:$site,datetime_geq:$d7,datetime_leq:$now},limit:10,orderBy:[count_DESC]){ count dimensions{ refererHost } }
  countries: rumPageloadEventsAdaptiveGroups(filter:{siteTag:$site,datetime_geq:$d7,datetime_leq:$now},limit:10,orderBy:[count_DESC]){ count dimensions{ countryName } }
 }}}
"""
body = json.dumps({"query":q,"variables":{"acc":acc,"site":site,"d1":d1,"d7":d7,"now":n}}).encode()
req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", data=body,
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"})
try:
    resp = json.load(urllib.request.urlopen(req, timeout=30))
except Exception as e:
    print("HTTP error:", e); sys.exit(1)
if resp.get("errors"):
    print("GraphQL errors:", json.dumps(resp["errors"], indent=2))
data = ((resp.get("data") or {}).get("viewer") or {}).get("accounts") or []
if not data:
    print("No account data. Raw:", json.dumps(resp)[:400]); sys.exit(0)
a = data[0]
tot = lambda x: (x[0]['count'], x[0]['sum']['visits']) if x else (0,0)
pv24,v24 = tot(a['last24']); pv7,v7 = tot(a['last7d'])
print("=========== Web Analytics · wanna-know-ai.com ===========")
print(f"as of {n}")
print(f"Last 24h : {pv24} page views, {v24} visits")
print(f"Last 7d  : {pv7} page views, {v7} visits")
print("\nTop pages (7d):")
for r in a['pages']: print(f"  {r['count']:>4} views {r['sum']['visits']:>3} visits  {r['dimensions']['requestPath']}")
print("\nTop referrers (7d):")
for r in a['referrers']: print(f"  {r['count']:>4}  {r['dimensions']['refererHost'] or '(direct/none)'}")
print("\nTop countries (7d):")
for r in a['countries']: print(f"  {r['count']:>4}  {r['dimensions']['countryName']}")
print("="*57)
