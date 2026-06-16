#!/usr/bin/env python3
"""Pull Cloudflare Web Analytics stats for wanna-know-ai.com.

Needs CLOUDFLARE_API_TOKEN (read-only Account Analytics) and
CLOUDFLARE_ACCOUNT_ID in the environment (both are in ~/.zshenv).

IMPORTANT: the GraphQL `siteTag` is NOT the beacon token in the page HTML.
They are different identifiers for the same Web Analytics site. To find the
real siteTag, query rumPageloadEventsAdaptiveGroups with no site filter and
group by `siteTag` (see SITE_TAG below).
"""
import os, sys, json, time, urllib.request, datetime

TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
ACC   = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
SITE_TAG = "2d1d1a8b79d84c39b31e606ea1d2affd"   # Web Analytics site tag (≠ beacon token 219ba416…)

if not TOKEN or not ACC:
    print("Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID in env"); sys.exit(1)

now = datetime.datetime.now(datetime.timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
D1, D7, N = iso(now - datetime.timedelta(hours=24)), iso(now - datetime.timedelta(days=7)), iso(now)


def gql(query, variables, retries=3):
    for i in range(retries):
        body = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            "https://api.cloudflare.com/client/v4/graphql", data=body,
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            r = {"errors": [{"message": str(e)}]}
        if not r.get("errors"):
            return r
        time.sleep(2)
    return r


def grouped(dim, frm):
    """Rows grouped by one dimension, ordered by count desc."""
    q = (f"query($a:String!,$s:String!,$f:Time!,$t:Time!){{viewer{{accounts(filter:{{accountTag:$a}}){{"
         f"g:rumPageloadEventsAdaptiveGroups(filter:{{siteTag:$s,datetime_geq:$f,datetime_leq:$t}},"
         f"limit:20,orderBy:[count_DESC]){{count dimensions{{{dim}}}}}}}}}}}")
    r = gql(q, {"a": ACC, "s": SITE_TAG, "f": frm, "t": N})
    if r.get("errors"):
        print("  (query error:", r["errors"][0]["message"], ")")
        return []
    return r["data"]["viewer"]["accounts"][0]["g"]


def total(frm):
    return sum(x["count"] for x in grouped("requestPath", frm))


def main():
    print("=========== Web Analytics · wanna-know-ai.com ===========")
    print(f"as of {N}")
    print(f"Last 24h : {total(D1)} page views")
    print(f"Last 7d  : {total(D7)} page views")
    for label, dim in [("Top pages", "requestPath"), ("Top referrers", "refererHost"),
                       ("Top countries", "countryName"), ("By device", "deviceType")]:
        print(f"\n{label} (7d):")
        for x in grouped(dim, D7):
            print(f"  {x['count']:>4}  {x['dimensions'][dim] or '(direct/none)'}")
    print("=" * 57)


if __name__ == "__main__":
    main()
