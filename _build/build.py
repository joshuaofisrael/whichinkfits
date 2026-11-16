#!/usr/bin/env python3
"""Which Ink Fits static site.

  python3 _build/build.py           # noindex on every page (domain not live)
  python3 _build/build.py --launch  # indexable, Cloudflare beacon
Then: python3 _build/check.py [--launch] && python3 _build/legal_gate.py check --no-queue

Canonicals always use https://whichinkfits.com/. Paths are root relative.
The CNAME file is always written. Facts come from _build/hp_catalog.json and
_build/more.py. This script does not invent a cartridge number.
"""
import html, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import more

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCH = "--launch" in sys.argv
BASE = "https://whichinkfits.com/"
BRAND = "Which Ink Fits"
TODAY = "2026-11-16"
TODAY_H = "16 Nov 2026"
INDEXNOW_KEY = "4f77a5e3aae98a8a1031b02723738f83"
CF_BEACON_TOKEN = "eac63f2b5dbc4539a2d95249baab6472"
HP_URL = "https://support.hp.com/us-en/document/ish_2405837-1980674-16"
HP_TITLE = "Which cartridges work with my HP printer?"
LEGAL_LINE = "© 2026 Joshua Israel Ventures LLC. All rights reserved. Which Ink Fits is a trade name of Joshua Israel Ventures LLC, a Florida limited liability company."
E = html.escape
PAGES = []

BRANDS = {
    "hp": "HP",
    "canon": "Canon",
    "epson": "Epson",
    "brother": "Brother",
}
THIRD = {
    "hp": "HP Canada's ENVY 6055e ink page says only the original HP cartridges it lists can provide the results the printer was engineered to deliver. HP's cartridge table tells you the number. It does not, on the pages we used, tell you to buy or avoid other ink. Which Ink Fits does not recommend either way.",
    "canon": "Canon says genuine Canon inks provide peak performance that is specifically designed for compatible Canon printers. Which Ink Fits does not recommend for or against other ink.",
    "epson": "Epson's XP-4105 page says the printer is designed for use with Epson cartridges only, not third party cartridges or ink, and that other brands may not function properly even if they are described as compatible. Epson's bottle pages say use of non genuine ink could cause damage not covered under the limited warranty. Which Ink Fits does not recommend either way.",
    "brother": "Brother says it strongly recommends Brother Genuine toner, that non genuine toner could cause damage, and that the limited warranty may not cover damage from non Brother supplies. That wording is on the TN760 toner page. Which Ink Fits does not recommend either way.",
}
LOGO = '<svg width="34" height="34" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><rect width="64" height="64" rx="14" fill="#0b3954"/><path d="M32 8c9 12 18 18 18 30a18 18 0 0 1-36 0c0-12 9-18 18-30z" fill="#087e8b"/><circle cx="32" cy="40" r="6" fill="#ffb347"/></svg>'
NAV = [("/", "Home"), ("/printers/", "Printers"), ("/cartridges/", "Cartridges"), ("/guides/find-the-model-number/", "Find the number")]

def clean(s):
    return (s or "").replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ").replace("\u2011", "-")

def slugify(s):
    s = clean(s).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

def clip(d, n=155):
    d = re.sub(r"\s+", " ", d).strip()
    if len(d) <= n:
        return d
    c = d[: n - 1]
    i = c.rfind(". ")
    if i > 80:
        return c[: i + 1]
    j = c.rfind(" ")
    return (c[:j] if j > 60 else c).rstrip(",;: ") + "."

def url(path):
    return BASE + path.lstrip("/")

def write(path, content):
    fp = os.path.join(ROOT, path.lstrip("/"))
    if path.endswith("/"):
        fp = os.path.join(fp, "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(content)

def hp_family(sku):
    m = re.match(r"(\d+)(e|A|X)?(XL|XXL)?(?:\s+Z\d+)?$", sku, re.I)
    if not m:
        return "hp-" + slugify(sku)
    base, extra, cap = m.group(1), (m.group(2) or ""), (m.group(3) or "")
    if extra.upper() in ("A", "X") and not cap:
        return "hp-" + base + "a"
    return "hp-" + base

def norm_supply(brand, row):
    sku = clean(row.get("sku", ""))
    color = clean(row.get("color", ""))
    capacity = clean(row.get("capacity") or "standard")
    family = row.get("family") or (hp_family(sku) if brand == "hp" else brand + "-" + slugify(sku))
    label_brand = BRANDS[brand]
    bits = [label_brand, sku]
    if color and color.lower() not in ("maintenance box",):
        bits.append(color)
    if capacity == "high yield":
        bits.append("high yield")
    elif capacity == "extra high yield":
        bits.append("extra high yield")
    return {
        "sku": sku, "color": color or "Not named in the source cell", "capacity": capacity,
        "yield_text": clean(row.get("yield_text", "")), "family": family,
        "note": clean(row.get("note", "")), "label": " ".join(bits),
    }

def page(path, title, desc, body, jsonld=None, crumbs=None, noindex=False, legal=False):
    desc = clip(desc)
    canon = url(path)
    if not noindex:
        PAGES.append((path, TODAY))
    ld = []
    if path == "/":
        ld.append({"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": BASE,
                   "publisher": {"@type": "Organization", "name": BRAND, "url": BASE, "logo": url("/logo.png")}})
        ld.append({"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": BASE, "logo": url("/logo.png"),
                   "email": "joshuaofisrael@gmail.com"})
    # Organization email would put the address in JSON-LD on the homepage, which legal_gate
    # scans as visible text after stripping tags... scripts are stripped. JSON-LD is a script.
    # legal_gate visible() strips script. So email in JSON-LD is OK. But the rule says
    # email outside legal pages. The homepage is not a legal page. I'll keep email off the
    # homepage schema and only on the contact page body.
    if path == "/":
        ld = [x for x in ld if x.get("@type") != "Organization" or "email" not in x]
        ld.append({"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": BASE, "logo": url("/logo.png")})
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": url(p)} for i, (p, n) in enumerate(crumbs)]})
    if jsonld:
        ld += jsonld if isinstance(jsonld, list) else [jsonld]
    ldh = "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>" for x in ld)
    nav = "".join('<a href="' + p + '"' + (' aria-current="page"' if p == path else "") + ">" + n + "</a>" for p, n in NAV)
    bc = ""
    if crumbs:
        bc = '<nav class="crumbs" aria-label="Breadcrumb"><ol>' + "".join(
            ('<li><a href="' + p + '">' + E(n) + "</a></li>" if i < len(crumbs) - 1 else '<li aria-current="page">' + E(n) + "</li>")
            for i, (p, n) in enumerate(crumbs)) + "</ol></nav>"
    robots = "noindex, follow" if (noindex or not LAUNCH) else "index, follow, max-image-preview:large"
    beacon = ("<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{\"token\": \"" + CF_BEACON_TOKEN + "\"}'></script><!-- End Cloudflare Web Analytics -->") if LAUNCH else "<!-- cf-beacon: added by the launch build -->"
    search = '<script src="/assets/search-index.js"></script>' if path == "/" else ""
    foot_legal = '<p class="legal-line">' + LEGAL_LINE + "</p>" if legal else ""
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}"><meta property="og:image" content="{url('/og.png')}"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css?v=1">{ldh}
</head><body><a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap"><a class="brand" href="/">{LOGO}<span>{BRAND}</span></a><nav class="main" aria-label="Main">{nav}</nav></div></header>
<main id="main" class="wrap">{bc}{body}</main>
<footer class="site"><div class="wrap"><p><strong>{BRAND}</strong> lists the ink, toner, and bottle numbers the printer maker publishes for a model, and the printers a number fits. Independent, and not affiliated with HP, Canon, Epson, or Brother. Confirm the number on the maker's page and on your printer.</p>
<p class="flinks"><a href="/about/">About</a> | <a href="/methodology/">Sources and methods</a> | <a href="/image-policy/">Image policy</a> | <a href="/terms/">Terms of use</a> | <a href="/privacy/">Privacy</a> | <a href="/disclaimer/">Disclaimer</a> | <a href="/ad-disclosure/">Advertising disclosure</a> | <a href="/copyright/">Copyright and DMCA</a> | <a href="/contact/">Contact</a></p>
{foot_legal}</div></footer>
{search}<script src="/assets/site.js?v=1" defer></script>{beacon}
</body></html>'''

def ext(title, href):
    return '<a href="' + E(href) + '" rel="nofollow noopener" target="_blank">' + E(title) + "</a>"

def article_ld(headline, path):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "datePublished": TODAY, "dateModified": TODAY,
            "image": url("/og.png"), "author": {"@type": "Organization", "name": BRAND, "url": BASE},
            "publisher": {"@type": "Organization", "name": BRAND, "url": BASE, "logo": {"@type": "ImageObject", "url": url("/logo.png")}},
            "mainEntityOfPage": url(path)}

def faq_ld(faqs):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}

def faq_html(faqs):
    return '<section class="faq" aria-labelledby="faq-h"><h2 id="faq-h">Frequently asked questions</h2>' + "".join(
        "<details><summary>" + E(q) + "</summary><p>" + E(a) + "</p></details>" for q, a in faqs) + "</section>"

def sources_html(sources):
    return '<section class="sources" aria-labelledby="src-h"><h2 id="src-h">Sources</h2><ul>' + "".join("<li>" + ext(t, u) + "</li>" for t, u in sources) + f'<li>Retrieved {TODAY_H}.</li></ul><p class="note">Which Ink Fits is independent and is not the manufacturer. Match the number on your printer and on the box, then confirm it on the source page.</p></section>'

def supply_table(rows, source_url):
    body = []
    for r in rows:
        y = r["yield_text"] or "Not published on the source page"
        body.append("<tr><td>" + E(r["label"]) + "</td><td>" + E(r["color"]) + "</td><td>" + E(r["capacity"]) + "</td><td>" + E(y) + '</td><td><a href="' + E(source_url) + '" rel="nofollow noopener" target="_blank">Manufacturer page</a></td><td>' + TODAY_H + "</td></tr>")
    return '<div class="tablewrap"><table class="list"><thead><tr><th scope="col">Official number</th><th scope="col">Color</th><th scope="col">Size</th><th scope="col">Yield</th><th scope="col">Source</th><th scope="col">Last verified</th></tr></thead><tbody>' + "".join(body) + "</tbody></table></div>"

def region_table(regions):
    extra = [r for r in regions[1:]]
    if not extra:
        return ""
    rows = "".join("<tr><th scope=\"row\">" + E(clean(r["region"])) + "</th><td>" + E(clean(r["text"])) + "</td></tr>" for r in extra)
    return "<h2>Other regions on the same table</h2><p>HP prints different cartridge numbers for other places. The words below are the other columns of the same row. They are not repeated as separate cartridge pages in this version.</p><div class=\"tablewrap\"><table class=\"list\"><thead><tr><th scope=\"col\">HP's column heading</th><th scope=\"col\">Numbers HP prints</th></tr></thead><tbody>" + rows + "</tbody></table></div>"

def find_faqs(brand, medium):
    xl = {
        "ink cartridges": "Where the maker lists a standard number and a high yield number for the same color, both are on this page. Canon says a PIXMA TR4720 can hold one standard cartridge and one XL cartridge at the same time. HP Canada's ENVY 6055e page says a high yield black cartridge can be installed with a standard color cartridge. Do not assume that mix is true for every printer. Read the maker's page for your model.",
        "toner": "A high yield toner holds more toner than the standard cartridge. Install only the number the maker lists for your model. This page does not guess that a standard and a high yield toner are interchangeable unless the maker lists both.",
        "ink bottles": "Bottles are not cartridges. Fill each tank from the bottle color the maker names. A high yield bottle, where the maker lists one, is a larger bottle of the same color, not a different printer.",
    }[medium]
    return [
        ("How do I find the model number?", "Read the model name on the front of the printer. The cartridge, toner, or bottle number is printed on the supply and on the box. This page repeats the numbers the manufacturer publishes. It does not replace the label on your printer."),
        ("What is the difference between a standard supply and a high yield supply?", xl),
        ("Does the manufacturer support third party ink or toner?", THIRD[brand]),
    ]

def load_hp():
    raw = json.load(open(os.path.join(os.path.dirname(__file__), "hp_catalog.json"), encoding="utf-8"))
    from collections import OrderedDict, defaultdict
    buckets = defaultdict(list)
    for s in raw["sections"]:
        for name in s["models"]:
            buckets[name].append(s)
    printers = []
    series = OrderedDict()
    for name, secs in buckets.items():
        name = clean(name)
        groups, seen = [], []
        notes = []
        for s in secs:
            sig = tuple((r["sku"], r["color"], r["capacity"]) for r in s["supplies"])
            if sig in seen:
                continue
            seen.append(sig)
            supplies = [norm_supply("hp", r) for r in s["supplies"]]
            groups.append({"label": clean(s["title"]), "supplies": supplies, "regions": s["regions"] if s["kind"] == "table" else []})
            if s.get("retired_note"):
                notes.append("HP prints this notice in the section: " + clean(s["retired_note"]))
            if s.get("heading_override"):
                notes.append("The heading of this HP section is " + clean(s["title"]) + ". The sentence under it reads: " + clean(s["info"]))
        if len(secs) > 1 and len(seen) == 1:
            notes.append("HP lists this model in more than one section and the cartridge numbers match: " + "; ".join(clean(s["title"]) for s in secs) + ".")
        if len(seen) > 1:
            notes.append("HP lists this model in more than one section, and the cartridge numbers are not the same. Both sections are shown below. Confirm on HP's page before you buy.")
        first = secs[0]
        series_name = clean(first["title"])
        series_slug = slugify(re.sub(r"\b(all in one|e all in one|printers|printer|series|wide format|eprinter)\b", " ", series_name.lower()))
        series_slug = re.sub(r"-+", "-", series_slug).strip("-")
        # slugify already hyphenates. The words above won't match because slugify turned spaces into hyphens first.
        series_slug = slugify(series_name)
        for suf in ("-e-all-in-one", "-all-in-one", "-wide-format", "-eprinter", "-printers", "-printer", "-series"):
            if series_slug.endswith(suf) and len(series_slug) > len(suf) + 3:
                series_slug = series_slug[: -len(suf)]
        slug = slugify(name)
        if slug.startswith("hp-"):
            slug = slug[3:]
        if series_slug.startswith("hp-"):
            series_slug = series_slug[3:]
        rec = {
            "brand": "hp", "name": name if name.startswith("HP ") else "HP " + name, "slug": slug,
            "series": series_slug, "series_name": series_name, "medium": "ink cartridges",
            "groups": groups, "sources": [(HP_TITLE, HP_URL)], "notes": notes, "verified": TODAY,
            "info": clean(first["info"]),
        }
        printers.append(rec)
        series.setdefault(series_slug, {"slug": series_slug, "name": series_name, "brand": "hp", "info": clean(first["info"]), "members": []})
        series[series_slug]["members"].append(slug)
    # ENVY 6055e is a named model on HP's support site, filed under the ENVY 6000e series.
    envy = next((p for p in printers if p["slug"] == "envy-6000"), None)
    if envy:
        extra = json.loads(json.dumps(envy))
        extra["name"] = "HP ENVY 6055e"
        extra["slug"] = "envy-6055e"
        extra["sources"] = [
            ("HP ENVY 6055e All-in-One Printer support", "https://support.hp.com/us-en/product/ink-paper/hp-envy-6000e-all-in-one-printer-series/model/2100187510"),
            ("HP ENVY 6055e printer ink, HP Canada", "https://www.hp.com/ca-en/shop/offer.aspx?lang=en-CA&p=hp-envy-6055e-printer-ink-cartridges"),
            (HP_TITLE, HP_URL),
        ]
        extra["notes"] = [
            "HP's cartridge table names the ENVY 6000 series and does not print the 6055e model string. The support page for the ENVY 6055e is filed under the ENVY 6000e series. The supply rows are that series column.",
            "HP Canada's ENVY 6055e ink page names HP 67 part numbers 3YM56AN, 3YM55AN, 3YM57AN, and 3YM58AN, plus combination packs, and it also names HP 305. The US cartridge table puts 305 in a different region column, so 305 is not added as a US row here.",
        ]
        printers.append(extra)
        series[envy["series"]]["members"].append("envy-6055e")
    # LaserJet Pro M428, from HP's toner replacement document. 58A is not the old OfficeJet 58 photo cartridge.
    printers.append({
        "brand": "hp", "name": "HP LaserJet Pro M428", "slug": "laserjet-pro-m428",
        "series": "laserjet-pro-m428", "series_name": "HP LaserJet Pro M428", "medium": "toner",
        "groups": [{"label": "North America and Latin America supplies", "supplies": [
            norm_supply("hp", {"sku": "58A", "color": "Black", "capacity": "standard", "yield_text": "About 3,000 pages for the preinstalled cartridge", "family": "hp-58a"}),
            norm_supply("hp", {"sku": "58X", "color": "Black", "capacity": "high yield", "family": "hp-58a"}),
        ], "regions": []}],
        "sources": [
            ("HP LaserJet Pro MFP M329, M428, M429: replace the toner cartridge", "https://support.hp.com/us-en/document/c06398764"),
            ("HP LaserJet Pro MFP M428fdw specifications", "https://support.hp.com/us-en/product/product-specs/hp-laserjet-pro-mfp-m428-m429-f-series/model/2100584485"),
        ],
        "notes": [
            "HP's replacement table says 58A and 58X are for M428 models only, for use in North America and Latin America, and that cartridges will not work outside their designated region.",
            "The M428fdw specifications page says the preinstalled 58A yields about 3,000 pages. The replacement table does not restate a page yield for the 58X.",
        ],
        "verified": TODAY, "info": "HP's toner replacement document for the LaserJet Pro MFP M428.",
    })
    return printers, series

def assemble():
    printers, series = load_hp()
    for p in more.printers():
        for g in p["groups"]:
            g["supplies"] = [norm_supply(p["brand"], r) for r in g["supplies"]]
        printers.append(p)
        series.setdefault(p["series"], {"slug": p["series"], "name": p["series_name"], "brand": p["brand"], "info": "", "members": []})
        if p["brand"] != "hp":
            series[p["series"]]["brand"] = p["brand"]
            series[p["series"]]["name"] = p["series_name"]
        series[p["series"]]["members"].append(p["slug"])
    # Drop series pages that would share a URL with the only model in them.
    by_slug = {}
    for p in printers:
        key = (p["brand"], p["slug"])
        if key in by_slug:
            raise SystemExit("duplicate printer slug " + str(key))
        by_slug[key] = p
    for sid, s in list(series.items()):
        s["members"] = list(dict.fromkeys(s["members"]))
        if s["slug"] in [m for m in s["members"]] and len(s["members"]) == 1:
            s["skip_page"] = True
        else:
            s["skip_page"] = False
        if any(m == s["slug"] for m in s["members"]) and not s["skip_page"]:
            s["slug"] = s["slug"] + "-series"
            # members keep printer slugs; only the hub slug changes
    return printers, series

def family_pages(printers):
    fam = {}
    for p in printers:
        for g in p["groups"]:
            for r in g["supplies"]:
                f = fam.setdefault(r["family"], {"slug": r["family"], "brand": p["brand"], "rows": {}, "printers": []})
                f["rows"][(r["sku"], r["color"], r["capacity"])] = r
                if p["slug"] not in [x[0] for x in f["printers"]]:
                    f["printers"].append((p["slug"], p["name"], p["brand"]))
    return fam

def medium_word(medium):
    return {"ink cartridges": "ink", "toner": "toner", "ink bottles": "ink bottles"}[medium]

def printer_page(p, series, fam):
    path = f'/printers/{p["brand"]}/{p["slug"]}/'
    sib = series.get(p["series"])
    title = p["name"] + " " + medium_word(p["medium"]) + ": which cartridges fit"
    if p["medium"] == "ink bottles":
        title = p["name"] + " ink bottles: which supplies fit"
    colors = []
    for g in p["groups"]:
        for r in g["supplies"]:
            bit = r["sku"] + (" " + r["color"] if r["color"] and "Not named" not in r["color"] else "")
            if bit not in colors:
                colors.append(bit)
    lead_nums = ", ".join(colors[:8])
    desc = p["name"] + " uses " + lead_nums + ". Numbers come from the manufacturer page, last verified " + TODAY_H + "."
    blocks = []
    for g in p["groups"]:
        if g["label"] and len(p["groups"]) > 1:
            blocks.append("<h2>" + E(g["label"]) + "</h2>")
        src = p["sources"][0][1]
        blocks.append(supply_table(g["supplies"], src))
        blocks.append(region_table(g.get("regions") or []))
    notes = list(p["notes"])
    colors = [r["color"] for g in p["groups"] for r in g["supplies"]]
    if p["brand"] == "hp" and any(colors.count(c) > 1 for c in set(colors)):
        notes.insert(0, "HP prints more than one number for at least one color in this section. Each number is listed. The table does not say to install every number at the same time.")
    notes = "".join("<p>" + E(n) + "</p>" for n in notes)
    fam_links = []
    seen = set()
    for g in p["groups"]:
        for r in g["supplies"]:
            if r["family"] in seen:
                continue
            seen.add(r["family"])
            fam_links.append('<a href="/cartridges/' + r["family"] + '/">' + E(r["label"]) + "</a>")
    sib_html = ""
    if sib and len(sib["members"]) > 1:
        items = []
        for m in sib["members"]:
            if m == p["slug"]:
                continue
            mate = next(x for x in ALL if x["brand"] == p["brand"] and x["slug"] == m)
            items.append('<li><a href="/printers/' + p["brand"] + "/" + m + '/">' + E(mate["name"]) + "</a></li>")
        hub = "/printers/" + p["brand"] + "/" + sib["slug"] + "/"
        hub_name = sib["name"] if re.search(r"series|printers", sib["name"], re.I) else sib["name"] + " series"
        sib_html = "<h2>Same series</h2><p>" + ("Other models in this HP section." if p["brand"] == "hp" else "Other models on the same manufacturer list.") + "</p>"
        sib_html += '<p><a href="' + hub + '">' + E(hub_name) + "</a></p><ul class=\"cols\">" + "".join(items) + "</ul>"
    faqs = find_faqs(p["brand"], p["medium"])
    body = f'''<article class="prose wide"><h1>{E(p["name"])} {E(medium_word(p["medium"]))}: which cartridges fit</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p><strong>Official numbers:</strong> {E(lead_nums)}.</p></div>
<p>{"This model takes ink bottles, not a cartridge." if p["medium"]=="ink bottles" else "The table is the manufacturer's list for this model."} Yield is filled in only when that source prints a page yield.</p>
{notes}{"".join(blocks)}
<h2>Cartridge pages</h2><p>{", ".join(fam_links)}</p>
{sib_html}
{faq_html(faqs)}
{sources_html(p["sources"])}
<p><a href="/printers/{p["brand"]}/">All {E(BRANDS[p["brand"]])} models</a> · <a href="/guides/find-the-model-number/">How to find the model number</a></p>
</article>'''
    if p["medium"] == "ink bottles":
        body = body.replace(E(p["name"]) + " ink bottles: which cartridges fit", E(p["name"]) + " ink bottles: which supplies fit", 1)
    # h1 uses medium_word which for bottles is "ink bottles", then ": which cartridges fit" from the template.
    # Fix the h1 for bottles.
    if p["medium"] == "ink bottles":
        body = body.replace(": which cartridges fit", ": which supplies fit", 1)
    crumbs = [("/", "Home"), ("/printers/", "Printers"), ("/printers/" + p["brand"] + "/", BRANDS[p["brand"]])]
    if sib and not sib.get("skip_page"):
        crumbs.append(("/printers/" + p["brand"] + "/" + sib["slug"] + "/", sib["name"]))
    crumbs.append((path, p["name"]))
    write(path, page(path, title if len(title) <= 70 else (p["name"] + ": which cartridges fit"), desc, body, [article_ld(p["name"] + " supplies", path), faq_ld(faqs)], crumbs))

def series_page(s):
    if s.get("skip_page"):
        return
    path = f'/printers/{s["brand"]}/{s["slug"]}/'
    members = [next(p for p in ALL if p["brand"] == s["brand"] and p["slug"] == m) for m in s["members"]]
    items = "".join('<li class="card"><h2><a href="/printers/' + s["brand"] + "/" + p["slug"] + '/">' + E(p["name"]) + "</a></h2><p>" + E(", ".join(r["sku"] for g in p["groups"] for r in g["supplies"][:6])) + "</p></li>" for p in members)
    info = "<p>" + E(s["info"]) + "</p>" if s.get("info") else ""
    desc = s["name"] + ": " + str(len(members)) + " models and the cartridge numbers the manufacturer lists for them."
    srcs, seen = [], set()
    for p in members:
        for t, u in p["sources"]:
            if u not in seen:
                seen.add(u)
                srcs.append((t, u))
            if len(srcs) >= 4:
                break
    body = f'''<article class="prose wide"><h1>{E(s["name"])}</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p>This series hub links every model we list from the manufacturer's compatibility pages. Open a model for the full table.</p></div>
{info}<ul class="cards">{items}</ul>
{sources_html(srcs)}
<p><a href="/printers/{s["brand"]}/">All {E(BRANDS[s["brand"]])} models</a></p></article>'''
    write(path, page(path, clip(s["name"] + " series | " + BRAND, 70), desc, body, [article_ld(s["name"], path)],
                     [("/", "Home"), ("/printers/", "Printers"), ("/printers/" + s["brand"] + "/", BRANDS[s["brand"]]), (path, s["name"])]))

def cartridge_page(f):
    path = "/cartridges/" + f["slug"] + "/"
    rows = list(f["rows"].values())
    name = rows[0]["label"]
    # A family may hold several colors. Title uses the family slug in words.
    nice = f["slug"].replace("-", " ").upper()
    # Keep brand word normal.
    brand = BRANDS[f["brand"]]
    nice = brand + " " + f["slug"].split("-", 1)[1].upper()
    title = nice + " cartridges: which printers use them"
    if any(r["color"] == "Drum" for r in rows):
        title = nice + " drum: which printers use it"
    if f["slug"] in ("epson-522", "canon-gi-21", "canon-gi-20", "canon-gi-290"):
        title = nice + " bottles: which printers use them"
    if f["slug"] == "epson-c9344":
        title = "Epson C9344 maintenance box: which printers use it"
    printers = f["printers"]
    links = "".join('<li><a href="/printers/' + b + "/" + sl + '/">' + E(n) + "</a></li>" for sl, n, b in printers)
    src_url = next(p["sources"][0][1] for p in ALL if p["slug"] == printers[0][0] and p["brand"] == printers[0][2])
    # Prefer a stable manufacturer URL: first printer's first source, plus HP doc if hp.
    sources = []
    seen = set()
    for sl, n, b in printers:
        for t, u in next(p["sources"] for p in ALL if p["slug"] == sl and p["brand"] == b):
            if u not in seen:
                seen.add(u)
                sources.append((t, u))
            if len(sources) >= 6:
                break
        if len(sources) >= 6:
            break
    desc = nice + " fits " + str(len(printers)) + " printers on the manufacturer lists checked " + TODAY_H + "."
    medium = "ink bottles" if "bottle" in title else ("toner" if f["slug"] in ("hp-58a", "brother-tn-760") else "ink cartridges")
    if f["slug"] == "brother-dr-730":
        medium = "toner"
    faqs = find_faqs(f["brand"], medium if medium != "toner" or f["slug"] != "brother-dr-730" else "toner")
    body = f'''<article class="prose wide"><h1>{E(title.split(":")[0])}: which printers use them</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p><strong>{len(printers)} printers</strong> on the manufacturer lists below use this number. If your model is not in the list, it is not on the pages we checked.</p></div>
{supply_table(rows, sources[0][1])}
<h2>Printers</h2><ul class="cols">{links}</ul>
{faq_html(faqs)}
{sources_html(sources)}
<p><a href="/cartridges/">All cartridges</a> · <a href="/printers/{f["brand"]}/">{E(BRANDS[f["brand"]])} printers</a></p>
</article>'''
    # h1 may say "them" for a drum. Acceptable.
    write(path, page(path, title if len(title) <= 70 else (nice + ": which printers use them"), desc, body,
                    [article_ld(nice, path), faq_ld(faqs)],
                    [("/", "Home"), ("/cartridges/", "Cartridges"), (path, nice)]))

def brand_page(brand, printers, series):
    path = "/printers/" + brand + "/"
    hubs = [s for s in series.values() if s["brand"] == brand and not s.get("skip_page")]
    cards = "".join('<li class="card"><h2><a href="/printers/' + brand + "/" + s["slug"] + '/">' + E(s["name"]) + "</a></h2><p>" + str(len(s["members"])) + " models</p></li>" for s in hubs)
    lone = []
    for s in series.values():
        if s["brand"] != brand or not s.get("skip_page"):
            continue
        p = next(x for x in printers if x["brand"] == brand and x["slug"] == s["members"][0])
        lone.append('<li><a href="/printers/' + brand + "/" + p["slug"] + '/">' + E(p["name"]) + "</a></li>")
    body = f'''<h1>{E(BRANDS[brand])} ink and toner</h1>
<p class="answer">Models and series taken from {E(BRANDS[brand])}'s own compatibility pages. Open a series, or jump to a single model.</p>
<ul class="cards">{cards}</ul>
{("<h2>Single models</h2><ul class=\"cols\">" + "".join(lone) + "</ul>") if lone else ""}
<p><a href="/printers/">All printers</a> · <a href="/cartridges/">All cartridges</a></p>'''
    n = sum(1 for p in printers if p["brand"] == brand)
    write(path, page(path, BRANDS[brand] + " printer ink and toner | " + BRAND, "Which cartridges, toner, or bottles " + BRANDS[brand] + " lists for " + str(n) + " printer models.", body, None,
                     [("/", "Home"), ("/printers/", "Printers"), (path, BRANDS[brand])]))

def indexes(printers, series, fams):
    cards = []
    for b, name in BRANDS.items():
        n = sum(1 for p in printers if p["brand"] == b)
        cards.append('<li class="card"><h2><a href="/printers/' + b + '/">' + E(name) + "</a></h2><p>" + str(n) + " models from the manufacturer's lists.</p></li>")
    body = '<h1>Printers</h1><p class="answer">Pick a brand. Every model page cites the manufacturer page it was checked against on ' + TODAY_H + '.</p><ul class="cards">' + "".join(cards) + "</ul>"
    write("/printers/", page("/printers/", "Printer ink and toner by model | " + BRAND, "Find the cartridge, toner, or bottle for an HP, Canon, Epson, or Brother printer.", body, None, [("/", "Home"), ("/printers/", "Printers")]))
    items = []
    for slug in sorted(fams):
        f = fams[slug]
        nice = BRANDS[f["brand"]] + " " + slug.split("-", 1)[1].upper()
        items.append('<li><a href="/cartridges/' + slug + '/">' + E(nice) + "</a> <span class=\"note\">" + str(len(f["printers"])) + " printers</span></li>")
    body = '<h1>Cartridges, toner, and bottles</h1><p class="answer">Pick a number to see the printers the manufacturer lists for it.</p><ul class="cols">' + "".join(items) + "</ul>"
    write("/cartridges/", page("/cartridges/", "Ink and toner by cartridge number | " + BRAND, "Which printers use a cartridge, toner, or bottle number, from the manufacturer lists.", body, None, [("/", "Home"), ("/cartridges/", "Cartridges")]))

def guide():
    path = "/guides/find-the-model-number/"
    faqs = [
        ("Where is the printer model number?", "On the front of the printer. HP, Canon, Epson, and Brother print the model there. If the front is worn, the same name is in the printer menu or on the setup sheet that shipped with it."),
        ("Where is the cartridge number?", "On the cartridge, toner, or bottle, and again on the box. Match that number to the number on the model page, then confirm it on the manufacturer page linked there."),
        ("What if two pages disagree?", "Use the manufacturer page. This guide quotes those pages and leaves a number off when the pages do not agree or do not print it."),
    ]
    body = f'''<article class="prose"><h1>How to find the model number and the cartridge number</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p><strong>Read the model on the printer. Read the number on the box.</strong> Then open the matching page here and follow the link to the manufacturer.</p></div>
<h2>On the printer</h2><p>The model is the name on the front, such as DeskJet 2755e, PIXMA TR4720, EcoTank ET-2800, or MFC-L2710DW. Series names are shorter than the full model. If you only know the series, start at the series hub and then match the rest of the name.</p>
<h2>On the cartridge or bottle</h2><p>Ink cartridges show a number such as 67, PG-275, or 212. Toner shows a number such as TN-760 or 58A. Tank printers use a bottle such as GI-21 or 522, and the lead on those pages says so. High yield packs add XL or a similar mark. The color is printed next to the number.</p>
<h2>Then check the source</h2><p>Each page links the manufacturer document we used. Cartridge numbers differ by country. HP's pages quote the other columns when HP prints them. <a href="/methodology/">Sources and methods</a>.</p>
{faq_html(faqs)}
{sources_html([
    (HP_TITLE, HP_URL),
    ("Canon PG-275 / CL-276 value pack", "https://www.usa.canon.com/shop/p/pg-275-cl-276-value-pack"),
    ("Epson 212 ink", "https://epson.com/For-Home/Ink/Epson%26reg%3B-212%26reg%3B-Ink/i/T212"),
    ("Brother TN760", "https://www.brother-usa.com/p/ink-toner/TN760"),
])}
<p><a href="/printers/">Browse printers</a> · <a href="/cartridges/">Browse cartridges</a></p>
</article>'''
    write(path, page(path, "Find your printer model and cartridge number | " + BRAND, "How to read the model number on the printer and the cartridge number on the box.", body, [article_ld("Find the model number", path), faq_ld(faqs)], [("/", "Home"), (path, "Find the number")]))

def home(printers, fams):
    picks = [
        ("/printers/hp/officejet-pro-9015/", "HP OfficeJet Pro 9015"),
        ("/printers/hp/deskjet-2755e/", "HP DeskJet 2755e"),
        ("/printers/hp/envy-6055e/", "HP ENVY 6055e"),
        ("/printers/hp/laserjet-pro-m428/", "HP LaserJet Pro M428"),
        ("/printers/canon/pixma-tr4720/", "Canon PIXMA TR4720"),
        ("/printers/canon/pixma-g3270/", "Canon PIXMA G3270"),
        ("/printers/epson/et-2800/", "Epson EcoTank ET-2800"),
        ("/printers/epson/wf-2830/", "Epson WorkForce WF-2830"),
        ("/printers/brother/mfc-l2710dw/", "Brother MFC-L2710DW"),
        ("/printers/brother/mfc-j4335dw/", "Brother MFC-J4335DW"),
        ("/cartridges/hp-67/", "HP 67"),
        ("/cartridges/hp-64/", "HP 64"),
        ("/cartridges/hp-65/", "HP 65"),
        ("/cartridges/hp-952/", "HP 952"),
        ("/cartridges/hp-962/", "HP 962"),
        ("/cartridges/canon-pg-245-cl-246/", "Canon PG-245 / CL-246"),
        ("/cartridges/canon-pg-260-cl-261/", "Canon PG-260 / CL-261"),
        ("/cartridges/brother-tn-760/", "Brother TN-760"),
        ("/cartridges/epson-212/", "Epson 212"),
    ]
    links = "".join('<li><a href="' + h + '">' + E(n) + "</a></li>" for h, n in picks)
    brands = "".join('<li class="card"><h2><a href="/printers/' + b + '/">' + E(n) + "</a></h2><p>" + str(sum(1 for p in printers if p["brand"] == b)) + " models</p></li>" for b, n in BRANDS.items())
    faqs = [
        ("How do I find the model number?", "Read the name on the front of the printer, then search for it above. The cartridge number is on the cartridge and on the box. The guide explains both."),
        ("Do you list third party cartridges?", "No. A number appears here only when HP, Canon, Epson, or Brother prints it for that printer. We do not copy other stores' compatible ink charts."),
        ("What is the difference between a standard cartridge and a high yield cartridge?", "High yield means the manufacturer sells a larger fill of the same color. Both numbers are listed when the manufacturer lists both. Mixing them is described only where the manufacturer says it is allowed."),
        ("Are tank printers different?", "Yes. EcoTank and MegaTank models take ink bottles, not cartridges. Those pages say so in the first paragraph."),
    ]
    body = f'''<section class="hero"><h1>Which ink or toner fits your printer?</h1>
<p class="answer">Search a printer model or a cartridge number. This guide repeats the lists HP, Canon, Epson, and Brother publish, and links the page each number came from. {len(printers)} printer pages, checked {TODAY_H}.</p>
<form class="search" id="finder" role="search"><label for="q">Printer model or cartridge number</label><input id="q" name="q" type="search" placeholder="Try 2755e, 67, TR4720, TN760, ET-2800" autocomplete="off" enterkeyhint="search"></form>
<ul id="search-results" hidden></ul>
</section>
<h2>Brands</h2><ul class="cards">{brands}</ul>
<h2>Often looked up</h2><ul class="cols">{links}</ul>
<h2>How to read the numbers</h2><p>The model number is on the printer. The cartridge, toner, or bottle number is on the box. <a href="/guides/find-the-model-number/">How to find both</a>. Numbers change by country, and a high yield pack is not a different color. <a href="/methodology/">How we check a page</a>.</p>
{faq_html(faqs)}'''
    write("/", page("/", "Which Ink Fits: printer ink and toner by model", "Which cartridge, toner, or ink bottle fits your HP, Canon, Epson, or Brother printer, from the manufacturer lists.", body, [faq_ld(faqs)]))

def simple(path, title, desc, h1, inner, crumb=None, legal=False):
    body = '<article class="prose"><h1>' + E(h1) + "</h1>" + inner + "</article>"
    write(path, page(path, title, desc, body, None, [("/", "Home"), (path, crumb or h1)], legal=legal))

def legal_pages():
    simple("/about/", "About " + BRAND, "What Which Ink Fits is and how the printer lists are checked.", "About Which Ink Fits", f'''
<p>Which Ink Fits answers two questions. Which cartridge, toner, or bottle fits this printer, and which printers does this number fit?</p>
<h2>What we cover</h2><p>HP, Canon, Epson, and Brother, using each company's own compatibility pages. We add a model when that page names it. We leave it out when the page does not.</p>
<h2>Independence</h2><p>Which Ink Fits is not affiliated with, endorsed by, or sponsored by HP, Canon, Epson, or Brother. Names are used only to identify the printers and supplies.</p>
<p>See <a href="/methodology/">sources and methods</a>. To report a wrong number, <a href="/contact/">write to us</a>.</p>''')
    simple("/methodology/", "Sources and methods | " + BRAND, "Where the cartridge lists come from and what we leave out.", "Sources and methods", f'''
<p>Last verified {TODAY_H}.</p>
<h2>What we use</h2><p>HP's support document <a href="{HP_URL}" rel="nofollow noopener">Which cartridges work with my HP printer?</a>, plus the HP toner page for the LaserJet Pro M428 and the HP Canada page for the ENVY 6055e. Canon shop and Knowledge Base pages. Epson product, ink, and FAQ pages. Brother product pages for TN760, the DR730 bundle, LC406, and the MFC-J4335DW.</p>
<h2>What we leave out</h2><p>We do not copy a store's compatible ink chart. We do not list a third party number. If a cell on HP's table is ambiguous, that section is skipped. If two HP sections disagree about one model, the page shows both and says so. Page yield is blank when the source does not print one. HP's other region columns are quoted, and they do not yet have their own cartridge pages.</p>
<h2>Dates</h2><p>The date on a page is the day we checked the source, not a refreshed stamp. We change it when the numbers change.</p>''')
    simple("/image-policy/", "Image policy | " + BRAND, "How Which Ink Fits handles images, logos, and diagrams.", "Image policy", f'''
<p>Last updated {TODAY_H}.</p>
<p>The mark in the header is our own drawing of an ink drop. We do not display HP, Canon, Epson, or Brother logos. The site has no product photos. If we add an illustration made by a model, the caption will say AI generated image, and it will not show a real person or a brand logo.</p>
<p>Questions: <a href="/contact/">contact</a> or the <a href="/copyright/">copyright page</a>.</p>''')
    simple("/contact/", "Contact " + BRAND, "Write to Which Ink Fits about a wrong cartridge number or a missing model.", "Contact", '''
<p>For a correction or a model request, email <a href="mailto:joshuaofisrael@gmail.com">joshuaofisrael@gmail.com</a>.</p>
<h2>What to include</h2><p>Send the page address, the number you expected, and a link to the manufacturer page that shows it. We update the verified date when we recheck the source.</p>
<p>We use the message only to reply. See the <a href="/privacy/">privacy page</a>.</p>''', "Contact")
    D = TODAY_H
    legal = {
        "/terms/": ("Terms of use", f'''<p>Last updated {D}. These terms govern your use of whichinkfits.com (Which Ink Fits, we, us). Which Ink Fits is a trade name of Joshua Israel Ventures LLC, a Florida limited liability company. By using the site you agree to these terms.</p>
<h2>Information only</h2><p>Which Ink Fits provides general information about which supplies a manufacturer lists for a printer. It is not the manufacturer and it is not a promise that a supply will fit your unit. Always check the manufacturer page and the label on your printer.</p>
<h2>Accuracy</h2><p>We cite our sources and leave out numbers we cannot verify. We do not warrant that a page is complete or current.</p>
<h2>Acceptable use</h2><p>You may share links for personal use. You may not copy the site in bulk, republish our compilation, misuse the contact address, or try to disrupt the site.</p>
<h2>Intellectual property</h2><p>Original text and the site design belong to Joshua Israel Ventures LLC. Printer and supply names belong to their owners and are used only to identify the products.</p>
<h2>Disclaimer of warranties and limitation of liability</h2><p>The site is provided as is. To the fullest extent permitted by law, Joshua Israel Ventures LLC is not liable for a purchase you make from a number on this site. Our total liability for a claim relating to the site is limited to 100 US dollars.</p>
<h2>Governing law</h2><p>These terms are governed by the laws of the State of Florida, without regard to conflict of law rules.</p>
<h2>Changes</h2><p>The date above is the current version. Questions: <a href="/contact/">contact</a>.</p>'''),
        "/privacy/": ("Privacy", f'''<p>Last updated {D}. Which Ink Fits (whichinkfits.com) is a trade name of Joshua Israel Ventures LLC, a Florida limited liability company.</p>
<h2>Analytics</h2><p>After the domain is live, the site may use Cloudflare Web Analytics to count page views. That product does not use cookies and does not track you across other sites.</p>
<h2>Email</h2><p>If you email joshuaofisrael@gmail.com, we use your address and message to reply, and we keep them only as long as we need to.</p>
<h2>Advertising</h2><p>The site shows no ads and has no affiliate links. If that changes, we will update this page first. You would be able to opt out of personalized ads at Google's ad settings and at aboutads.info.</p>
<h2>Hosting</h2><p>The site is hosted on GitHub Pages, which may log IP addresses for security.</p>
<h2>Children</h2><p>The site is a general audience site. We do not knowingly collect information from children under 13.</p>'''),
        "/disclaimer/": ("Disclaimer", f'''<p>Last updated {D}.</p>
<h2>Not the manufacturer</h2><p>Which Ink Fits is an independent site. It is not affiliated with, endorsed by, or sponsored by HP, Canon, Epson, or Brother. Names identify the products. They do not imply a relationship.</p>
<h2>Confirm before you buy</h2><p>Cartridge numbers differ by country and can change. The manufacturer page and the label on your printer come first. A blank yield means the source we used did not print a page yield.</p>
<h2>No recommendation on other ink</h2><p>We quote what the manufacturer says about its own supplies. We do not tell you to buy or avoid third party ink or toner.</p>'''),
        "/copyright/": ("Copyright and DMCA", f'''<p>Last updated {D}. Original text and design on Which Ink Fits are owned by Joshua Israel Ventures LLC. Facts are cited to the manufacturer pages. See the <a href="/image-policy/">image policy</a>.</p>
<h2>Notice</h2><p>If you believe material on this site infringes a copyright you own, email <a href="mailto:joshuaofisrael@gmail.com">joshuaofisrael@gmail.com</a> with your name, a description of the work, the page address, a statement that you have a good faith belief the use is not authorized, a statement under penalty of perjury that the notice is accurate and that you are the owner or authorized to act for the owner, and your signature. We review notices and remove material where that is the right step.</p>
<h2>Counter notice</h2><p>If we removed something you sent and you believe that was a mistake, you may send a counter notice with the details required by 17 U.S.C. section 512(g).</p>'''),
        "/ad-disclosure/": ("Advertising disclosure", f'''<p>Last updated {D}. Which Ink Fits is free to use. The site shows no ads and has no affiliate links. We may add advertising or links to manufacturer and retailer pages later. If we do, the links will be labeled, and a manufacturer will not be able to change a cartridge list by paying us.</p>
<p>Questions: <a href="/contact/">contact</a>.</p>'''),
    }
    for pth, (h1, inner) in legal.items():
        body = '<article class="prose"><h1>' + E(h1) + "</h1>" + inner + '<p class="legal-line">' + LEGAL_LINE + "</p></article>"
        write(pth, page(pth, h1 + " | " + BRAND, h1 + " for Which Ink Fits.", body, None, [("/", "Home"), (pth, h1)], legal=True))

def not_found():
    body = '<h1>Page not found</h1><p>That page is not in this guide. Try the <a href="/printers/">printer list</a> or search from the <a href="/">home page</a>.</p>'
    open(os.path.join(ROOT, "404.html"), "w", encoding="utf-8").write(page("/404.html", "Page not found | " + BRAND, "That page is not on Which Ink Fits.", body, noindex=True))

def search_index(printers, series, fams):
    rows = []
    for p in printers:
        keys = slugify(p["name"]) + slugify(p["slug"])
        for g in p["groups"]:
            for r in g["supplies"]:
                keys += slugify(r["sku"])
        rows.append({"n": p["name"], "u": "/printers/" + p["brand"] + "/" + p["slug"] + "/", "t": "Printer", "k": re.sub(r"[^a-z0-9]+", "", keys)})
    for s in series.values():
        if s.get("skip_page"):
            continue
        rows.append({"n": s["name"], "u": "/printers/" + s["brand"] + "/" + s["slug"] + "/", "t": "Series", "k": re.sub(r"[^a-z0-9]+", "", slugify(s["name"] + s["slug"]))})
    for slug, f in fams.items():
        nice = BRANDS[f["brand"]] + " " + slug.split("-", 1)[1].upper()
        rows.append({"n": nice, "u": "/cartridges/" + slug + "/", "t": "Cartridge", "k": re.sub(r"[^a-z0-9]+", "", slug)})
    open(os.path.join(ROOT, "assets", "search-index.js"), "w", encoding="utf-8").write("window.INK_INDEX=" + json.dumps(rows, ensure_ascii=False) + ";\n")

def png(path, w, h, fn):
    import struct, zlib
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(fn(x, y))
    blob = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(blob)

def images():
    navy, teal, sun, paper = (11, 57, 84), (8, 126, 139), (255, 179, 71), (247, 251, 251)
    def drop(w, h, cx, cy, scale):
        def fn(x, y):
            dx, dy = (x - cx) / scale, (y - cy) / scale
            if dx * dx + (dy - 0.15) * (dy - 0.15) < 0.55 and dy > -0.35:
                return teal
            if abs(dx) < 0.18 - dy * 0.15 and -1.15 < dy < -0.2:
                return teal
            if dx * dx + (dy - 0.15) * (dy - 0.15) < 0.06:
                return sun
            return None
        return fn
    def logo_px(x, y):
        hit = drop(256, 256, 128, 150, 70)(x, y)
        return hit or navy
    def og_px(x, y):
        hit = drop(1200, 630, 360, 340, 180)(x, y)
        return hit or paper
    png(os.path.join(ROOT, "logo.png"), 256, 256, logo_px)
    png(os.path.join(ROOT, "og.png"), 1200, 630, og_px)
    svg = LOGO.replace('width="34" height="34" ', 'xmlns="http://www.w3.org/2000/svg" ').replace(' aria-hidden="true" focusable="false"', "")
    open(os.path.join(ROOT, "favicon.svg"), "w", encoding="utf-8").write(svg)

def extras(printers, series, fams):
    open(os.path.join(ROOT, "CNAME"), "w").write("whichinkfits.com\n")
    open(os.path.join(ROOT, INDEXNOW_KEY + ".txt"), "w").write(INDEXNOW_KEY + "\n")
    bots = ["*", "Googlebot", "Bingbot", "Mediapartners-Google", "OAI-SearchBot", "ChatGPT-User", "GPTBot", "PerplexityBot", "Perplexity-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "Google-Extended", "Applebot", "Applebot-Extended", "DuckAssistBot", "Amazonbot", "CCBot", "Bytespider"]
    open(os.path.join(ROOT, "robots.txt"), "w").write("".join("User-agent: " + b + "\nAllow: /\n\n" for b in bots) + "Sitemap: " + BASE + "sitemap.xml\n")
    open(os.path.join(ROOT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join("<url><loc>" + url(p) + "</loc><lastmod>" + m + "</lastmod></url>\n" for p, m in PAGES) + "</urlset>\n")
    lines = ["# " + BRAND, "", "> Which Ink Fits (whichinkfits.com) lists the ink, toner, and bottle numbers HP, Canon, Epson, and Brother publish for a printer model, and the printers a number fits. Checked " + TODAY_H + ".", "", "Independent. Not affiliated with any printer maker. Confirm the number on the manufacturer page.", "", "## Guides", f"- [Find the model number]({url('/guides/find-the-model-number/')})", f"- [Sources and methods]({url('/methodology/')})", "", "## Printers"]
    for p in printers:
        lines.append(f"- [{p['name']}]({url('/printers/' + p['brand'] + '/' + p['slug'] + '/')})")
    lines.append("")
    lines.append("## Cartridges")
    for slug in sorted(fams):
        lines.append(f"- [{slug}]({url('/cartridges/' + slug + '/')})")
    open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    images()

ALL = []

def clean_output():
    for rel in ["printers", "cartridges", "guides", "about", "methodology", "image-policy", "contact", "terms", "privacy", "disclaimer", "copyright", "ad-disclosure"]:
        p = os.path.join(ROOT, rel)
        if os.path.isdir(p):
            shutil.rmtree(p)
    for fn in ["index.html", "404.html", "sitemap.xml", "robots.txt", "llms.txt"]:
        fp = os.path.join(ROOT, fn)
        if os.path.isfile(fp):
            os.remove(fp)

if __name__ == "__main__":
    clean_output()
    printers, series = assemble()
    ALL = printers
    fams = family_pages(printers)
    for p in printers:
        printer_page(p, series, fams)
    for s in series.values():
        series_page(s)
    for f in fams.values():
        cartridge_page(f)
    for b in BRANDS:
        brand_page(b, printers, series)
    indexes(printers, series, fams)
    guide()
    home(printers, fams)
    legal_pages()
    not_found()
    search_index(printers, series, fams)
    extras(printers, series, fams)
    print(len(PAGES), "sitemap urls", len(printers), "printers", len(fams), "cartridge pages", "LAUNCH" if LAUNCH else "NOINDEX")
