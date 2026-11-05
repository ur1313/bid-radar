#!/usr/bin/env python3
"""Bid Radar: static SEO site of open federal contract opportunities small businesses can bid on.
Source: SAM.gov public daily Contract Opportunities CSV (no API key)."""
import csv, datetime, html, os, re, json
from collections import Counter, defaultdict

CSV_PATH = os.environ.get("SAM_CSV", "/tmp/sam-opps.csv")
CSV_URL = "https://sam.gov/api/prod/fileextractservices/v1/api/download/Contract%20Opportunities/datagov/ContractOpportunitiesFullCSV.csv?privacy=Public"
PRO_URL = os.environ.get("PRO_URL", "#pro")
BASE = "https://ur1313.github.io/bid-radar/"
BIDABLE = {
    "Solicitation",
    "Combined Synopsis/Solicitation",
    "Sources Sought",
    "Presolicitation",
    "Special Notice",
}
SB_CODES = {"SBA", "SBP", "SDVOSBC", "SDVOSBS", "WOSB", "EDWOSB", "HZC", "HZS", "8A", "8AN", "VSA"}
# Friendly short labels for set-aside pages
SA_PAGES = {
    "SBA": "Small Business Set-Aside",
    "SDVOSBC": "SDVOSB Set-Aside",
    "8A": "8(a) Set-Aside",
    "HZC": "HUBZone Set-Aside",
    "WOSB": "WOSB Set-Aside",
    "EDWOSB": "EDWOSB Set-Aside",
}

# Common NAICS labels (subset; unknown codes still get a page if popular)
NAICS_LABEL = {
    "541511": "Custom Computer Programming",
    "541512": "Computer Systems Design",
    "541519": "Other Computer Related Services",
    "541611": "Administrative Management Consulting",
    "541330": "Engineering Services",
    "541690": "Other Scientific/Technical Consulting",
    "236220": "Commercial Building Construction",
    "238210": "Electrical Contractors",
    "238220": "Plumbing/HVAC Contractors",
    "561210": "Facilities Support Services",
    "561720": "Janitorial Services",
    "484110": "General Freight Trucking Local",
    "493110": "General Warehousing",
    "334111": "Electronic Computer Manufacturing",
    "339112": "Surgical/Medical Instrument Mfg",
    "423450": "Medical Equipment Merchant Wholesalers",
    "621111": "Offices of Physicians",
    "622110": "General Medical/Surgical Hospitals",
    "541620": "Environmental Consulting",
    "562910": "Remediation Services",
    "237310": "Highway/Street/Bridge Construction",
    "237990": "Other Heavy Construction",
    "238910": "Site Preparation Contractors",
    "811310": "Commercial Machinery Repair",
    "541380": "Testing Laboratories",
    "518210": "Data Processing/Hosting",
    "541715": "R&D Physical Engineering Life Sciences",
    "541990": "All Other Professional Services",
    "561320": "Temporary Help Services",
    "811111": "General Automotive Repair",
}

today = datetime.date.today()

def parse_deadline(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(s[:19] if len(s) >= 19 and fmt.startswith("%Y-%m-%d %H") else s[:10], fmt[:8] if fmt == "%Y-%m-%d" else fmt).date()
            except Exception:
                continue
    return None

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"

def download_if_needed():
    if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 1_000_000:
        return
    import urllib.request
    print("Downloading SAM CSV...")
    urllib.request.urlretrieve(CSV_URL, CSV_PATH)

download_if_needed()

opps = []
naics_count = Counter()
state_count = Counter()
sa_count = Counter()

with open(CSV_PATH, "r", encoding="cp1252", newline="") as f:
    for row in csv.DictReader(f):
        if row.get("Active") != "Yes":
            continue
        if row.get("Type") not in BIDABLE:
            continue
        deadline = parse_deadline(row.get("ResponseDeadLine") or "")
        if not deadline or deadline < today:
            continue
        code = (row.get("SetASideCode") or "").strip()
        naics = (row.get("NaicsCode") or "").strip()
        state = (row.get("PopState") or row.get("State") or "").strip().upper()
        o = {
            "id": row.get("NoticeId") or "",
            "title": (row.get("Title") or "").strip(),
            "sol": (row.get("Sol#") or "").strip(),
            "agency": (row.get("Department/Ind.Agency") or "").strip(),
            "office": (row.get("Office") or "").strip(),
            "type": row.get("Type") or "",
            "sa_code": code,
            "sa": (row.get("SetASide") or "").strip(),
            "deadline": deadline,
            "deadline_raw": row.get("ResponseDeadLine") or "",
            "naics": naics,
            "state": state,
            "link": row.get("Link") or "",
            "sb": code in SB_CODES,
        }
        opps.append(o)
        if naics:
            naics_count[naics] += 1
        if state and len(state) == 2:
            state_count[state] += 1
        if code in SA_PAGES:
            sa_count[code] += 1

opps.sort(key=lambda o: o["deadline"])
top_naics = [c for c, _ in naics_count.most_common(40)]
top_states = [s for s, _ in state_count.most_common(25)]

CSS = """body{font-family:system-ui,sans-serif;max-width:1000px;margin:auto;padding:16px;color:#1a2332;line-height:1.45}
h1{color:#0a3d62;font-size:1.6rem}h2{font-size:1.15rem;color:#0a3d62}a{color:#0a3d62}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid #e2e8f0;padding:7px 6px;text-align:left;vertical-align:top}
th{background:#f1f5f9}.cta{background:#0a3d62;color:#fff;padding:16px;border-radius:8px;margin:16px 0}
.cta a{color:#fff;font-weight:700}.soon{color:#b00020;font-weight:700}
.badge{display:inline-block;background:#e0f2fe;color:#0a3d62;padding:1px 6px;border-radius:4px;font-size:11px;margin-right:4px}
.sb{background:#dcfce7;color:#166534}nav{margin:12px 0;line-height:1.9}nav a{margin-right:10px;font-size:13px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.stat{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;min-width:120px}
.stat b{display:block;font-size:1.4rem;color:#0a3d62}"""

def days_left(d):
    return (d - today).days

def row_html(o):
    d = days_left(o["deadline"])
    dl = f'<span class="soon">{o["deadline"].isoformat()} ({d}d)</span>' if d <= 14 else o["deadline"].isoformat()
    badges = ""
    if o["sb"]:
        badges += '<span class="badge sb">Small biz set-aside</span>'
    if o["sa_code"] in SA_PAGES:
        badges += f'<span class="badge">{html.escape(SA_PAGES[o["sa_code"]])}</span>'
    title = html.escape(o["title"][:140] + ("…" if len(o["title"]) > 140 else ""))
    link = html.escape(o["link"] or "#")
    agency = html.escape((o["agency"] or "")[:60])
    naics = html.escape(o["naics"] or "—")
    state = html.escape(o["state"] or "—")
    return (
        f'<tr><td><a href="{link}" rel="nofollow" target="_blank">{title}</a><br>'
        f'<small>{html.escape(o["sol"])} · {html.escape(o["type"])}</small><br>{badges}</td>'
        f"<td>{agency}</td><td>{naics}</td><td>{state}</td><td>{dl}</td></tr>"
    )

def page(title, desc, items, fname, extra=""):
    items = sorted(items, key=lambda o: o["deadline"])
    # Cap huge pages for HTML size; full data still in opportunities.json
    shown = items[:800]
    note = ""
    if len(items) > 800:
        note = f"<p><em>Showing 800 of {len(items)} (soonest deadlines first). Full dump in opportunities.json.</em></p>"
    naics_nav = " ".join(
        f'<a href="naics-{c}.html">{c}</a>' for c in top_naics[:20]
    )
    sa_nav = " ".join(
        f'<a href="setaside-{slug(SA_PAGES[c])}.html">{html.escape(SA_PAGES[c])}</a>' for c in SA_PAGES if sa_count.get(c)
    )
    state_nav = " ".join(f'<a href="state-{s.lower()}.html">{s}</a>' for s in top_states[:15])
    cta = (
        f'<div class="cta" id="pro"><b>Bid Radar Pro — $49/month:</b> weekday morning email of new SAM.gov '
        f"solicitations matching your NAICS codes, set-aside status, and states — plus 7-day and 48-hour "
        f'deadline alerts. <a href="{PRO_URL}">Start Pro</a></div>'
    )
    out = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{BASE}{fname}">
<style>{CSS}</style></head><body>
<h1>{html.escape(title)}</h1>
<p>{html.escape(desc)} Updated {today:%B %d, %Y} from the SAM.gov public Contract Opportunities extract. {len(items)} matching open bids.</p>
{extra}{cta}{note}
<nav><a href="index.html">Home</a> <a href="closing-soon.html">Closing in 30 days</a>
<a href="small-business.html">Small business set-asides</a> <a href="sources-sought.html">Sources Sought</a></nav>
<nav><b>Set-aside:</b> {sa_nav}</nav>
<nav><b>Top NAICS:</b> {naics_nav}</nav>
<nav><b>States:</b> {state_nav}</nav>
<table><thead><tr><th>Opportunity</th><th>Agency</th><th>NAICS</th><th>State</th><th>Deadline</th></tr></thead>
<tbody>{"".join(row_html(o) for o in shown)}</tbody></table>
{cta}
<p><small>Data: SAM.gov public Contract Opportunities extract. Not affiliated with GSA or the U.S. government.
Always confirm eligibility, set-aside status, and attachments on the official notice before bidding.
Do not use contracting-officer emails for bulk marketing.</small></p>
</body></html>"""
    os.makedirs("site", exist_ok=True)
    open(f"site/{fname}", "w", encoding="utf-8").write(out)

closing = [o for o in opps if 0 <= days_left(o["deadline"]) <= 30]
closing14 = [o for o in opps if 0 <= days_left(o["deadline"]) <= 14]
sb = [o for o in opps if o["sb"]]
sources = [o for o in opps if o["type"] == "Sources Sought"]

stats = f"""<div class="stats">
<div class="stat"><b>{len(opps):,}</b>open with deadline</div>
<div class="stat"><b>{len(closing14):,}</b>due in 14 days</div>
<div class="stat"><b>{len(sb):,}</b>small-biz set-aside</div>
<div class="stat"><b>{len(sources):,}</b>sources sought</div>
</div>"""

page(
    f"Federal Contract Bids Open Now ({today:%B %Y})",
    "Free daily list of open SAM.gov solicitations small businesses can bid on, sorted by response deadline.",
    closing14,
    "index.html",
    extra=stats + "<p>Home shows bids due in the next 14 days. Browse Small business set-asides, Sources Sought, NAICS, and state pages for the full pipeline.</p>",
)
page(
    f"Federal Bids Closing in 30 Days ({today:%B %Y})",
    "Open SAM.gov contract opportunities with response deadlines in the next 30 days.",
    closing,
    "closing-soon.html",
)
page(
    f"Small Business Set-Aside Federal Contracts ({today:%B %Y})",
    "Open SAM.gov opportunities reserved for small businesses, SDVOSB, 8(a), HUBZone, and WOSB.",
    sb,
    "small-business.html",
)
page(
    f"Federal Sources Sought Notices ({today:%B %Y})",
    "Open Sources Sought notices on SAM.gov — early signals before a full solicitation drops.",
    sources,
    "sources-sought.html",
)

for code, label in SA_PAGES.items():
    items = [o for o in opps if o["sa_code"] == code]
    if not items:
        continue
    page(
        f"{label} Federal Contracts ({today:%B %Y})",
        f"Open SAM.gov opportunities with {label} status.",
        items,
        f"setaside-{slug(label)}.html",
    )

for c in top_naics:
    label = NAICS_LABEL.get(c, f"NAICS {c}")
    items = [o for o in opps if o["naics"] == c]
    page(
        f"{label} Federal Contracts — NAICS {c} ({today:%B %Y})",
        f"Open SAM.gov bids under NAICS {c} ({label}).",
        items,
        f"naics-{c}.html",
    )

for s in top_states:
    items = [o for o in opps if o["state"] == s]
    page(
        f"Federal Contracts in {s} ({today:%B %Y})",
        f"Open SAM.gov opportunities with place of performance or office in {s}.",
        items,
        f"state-{s.lower()}.html",
    )

urls = (
    ["index.html", "closing-soon.html", "small-business.html", "sources-sought.html"]
    + [f"setaside-{slug(SA_PAGES[c])}.html" for c in SA_PAGES if sa_count.get(c)]
    + [f"naics-{c}.html" for c in top_naics]
    + [f"state-{s.lower()}.html" for s in top_states]
)
open("site/sitemap.xml", "w").write(
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    + "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    + "</urlset>"
)
open("site/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n")

# Slim JSON for digests / future Pro
slim = [
    {
        "id": o["id"],
        "title": o["title"],
        "sol": o["sol"],
        "agency": o["agency"],
        "type": o["type"],
        "sa_code": o["sa_code"],
        "deadline": o["deadline"].isoformat(),
        "naics": o["naics"],
        "state": o["state"],
        "link": o["link"],
        "sb": o["sb"],
    }
    for o in opps
]
json.dump(slim, open("site/opportunities.json", "w"), separators=(",", ":"))
print(
    f"{len(opps)} open bids; {len(closing)} closing 30d; {len(sb)} SB set-aside; "
    f"{len(top_naics)} NAICS pages; {len(top_states)} state pages; {len(urls)} URLs"
)
