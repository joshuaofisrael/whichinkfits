#!/usr/bin/env python3
"""Which Ink Fits static site.

  python3 _build/build.py           # noindex on every page (domain not live)
  python3 _build/build.py --launch  # indexable, Cloudflare beacon, GA4 after consent
Then: python3 _build/check.py [--launch] && python3 _build/legal_gate.py check --no-queue

Set GA4_ID before --launch. check.py --launch fails while GA4_ID is empty.
Canonicals always use https://whichinkfits.com/. Paths are root relative.
The CNAME file is always written. Facts come from _build/hp_catalog.json and
_build/more.py. This script does not invent a cartridge number.
See LAUNCH-NOTES.md for the launch-day commands.
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
# Publish date for pages added after launch (the 18 Nov 2026 priority-moves run).
# These pages reuse facts verified on TODAY above; PUBLISHED is only the date the
# page itself went into the sitemap, so lastmod is not backdated or invented.
PUBLISHED = "2026-11-18"
PUBLISHED_H = "18 Nov 2026"
# Material content changes from the 19 Nov 2026 SEO batch.
PUBLISHED_TODAY = "2026-11-19"
PUBLISHED_TODAY_H = "19 Nov 2026"
# Rechecks from the 20 Nov 2026 SEO batch. datePublished stays the day the
# page first went up. dateModified and sitemap lastmod use this date only
# where the words on that page changed.
CHECKED_1120 = "2026-11-20"
CHECKED_1120_H = "20 Nov 2026"
# Rechecks and the new yield guide from the 21 Nov 2026 SEO batch.
# datePublished on older pages stays the day that page first went up.
CHECKED_1121 = "2026-11-21"
CHECKED_1121_H = "21 Nov 2026"
# Assigned bank photo (images-needed carryover). The file is not in the repo
# until it exists on disk. Pages that reference it should not be merged before then.
BANK_PHOTO = "/assets/photos/ink-cartridges-printer.png"
INDEXNOW_KEY = "4f77a5e3aae98a8a1031b02723738f83"
CF_BEACON_TOKEN = "eac63f2b5dbc4539a2d95249baab6472"
# Measurement id from the GA4 property. Empty until the owner sets G-XXXXXXXXXX.
# python3 _build/check.py --launch fails while this is empty.
GA4_ID = "G-HQK26SX9HN"
# AdSense publisher id. Head script + meta only; no ad units yet.
ADSENSE_CLIENT = "ca-pub-5681559774142917"
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
USED_TITLES = set()
FAMS = {}

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

def fit_title(options):
    cleaned = []
    for o in options:
        o = re.sub(r"\s+", " ", o).strip()
        if o and o not in cleaned:
            cleaned.append(o)
    for o in cleaned:
        if len(o) <= 59:
            return o
    raise SystemExit("no title under 60 chars: " + " | ".join(cleaned))

def squeeze_name(name):
    s = name
    for w in ("e-All-in-One", "All-in-One", "Wide Format", "ePrinter", "Printers"):
        s = re.sub(r"(?:\s*[-,]\s*|\s+)" + re.escape(w) + r"\b", " ", s, flags=re.I)
    s = s.replace(" - ", " ")
    s = re.sub(r"\s+", " ", s).strip(" -")
    return s

def printer_title(p):
    name = p["name"]
    short = squeeze_name(name)
    if p["medium"] == "ink bottles":
        options = [name + " bottles: which fit", "Which bottles fit " + name, "Which bottles fit " + short]
    elif p["medium"] == "toner":
        options = [name + " toner: which fits", "Which toner fits " + name, "Which toner fits " + short]
    else:
        options = [name + " ink: which cartridges fit", "Which ink fits " + name, "Which ink fits " + short]
    return fit_title(options)

def series_title(name):
    short = squeeze_name(name)
    return fit_title([name + ": which model", short + ": which model", "Which model: " + short])

def analytics_markup():
    if not LAUNCH:
        return "", ""
    src = "https://www.googletagmanager.com/gtag/js?id=" + GA4_ID
    head = (
        "<script>\n"
        "window.dataLayer = window.dataLayer || [];\n"
        "function gtag(){dataLayer.push(arguments);}\n"
        "gtag('consent', 'default', {\n"
        "  'ad_storage': 'denied',\n"
        "  'ad_user_data': 'denied',\n"
        "  'ad_personalization': 'denied',\n"
        "  'analytics_storage': 'denied',\n"
        "  'functionality_storage': 'denied',\n"
        "  'personalization_storage': 'denied',\n"
        "  'security_storage': 'granted',\n"
        "  'wait_for_update': 500\n"
        "});\n"
        "(function () {\n"
        "  var id = " + json.dumps(GA4_ID) + ";\n"
        "  if (!id) return;\n"
        "  try {\n"
        "    if (localStorage.getItem('wif-consent') === 'granted') {\n"
        "      gtag('consent', 'update', {'analytics_storage': 'granted'});\n"
        "      var s = document.createElement('script');\n"
        "      s.async = true;\n"
        "      s.src = 'https://www.googletagmanager.com/gtag/js?id=' + id;\n"
        "      document.head.appendChild(s);\n"
        "      gtag('js', new Date());\n"
        "      gtag('config', id);\n"
        "      window.__wifGaLoaded = true;\n"
        "    }\n"
        "  } catch (e) {}\n"
        "})();\n"
        "</script>\n"
        '<script id="ga4-loader" type="text/plain" data-ga4-src="' + E(src) + '"></script>'
    )
    body = (
        '<div id="consent-banner" class="consent" role="region" aria-label="Cookie consent" hidden>'
        '<p>Google Analytics 4 stays off until you accept. Cloudflare Web Analytics does not use cookies. <a href="/privacy/">Privacy</a></p>'
        '<p class="consent-actions"><button type="button" id="consent-accept">Accept</button> '
        '<button type="button" id="consent-reject">Reject</button></p></div>\n'
        '<script src="/assets/consent.js?v=1"></script>'
    )
    return head, body

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

# AdSense low-value-content fix (20 Nov 2026): paths listed in _build/thin-noindex.txt
# get noindex,follow and stay out of the sitemap until they have real unique substance.
_THIN_NOINDEX = set()
try:
    import os as _os
    with open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "thin-noindex.txt"), encoding="utf-8") as _fh:
        _THIN_NOINDEX = {l.strip().strip("/") for l in _fh if l.strip() and not l.startswith("#")}
except FileNotFoundError:
    pass


def _is_thin(path):
    return str(path).strip("/") in _THIN_NOINDEX


def page(path, title, desc, body, jsonld=None, crumbs=None, noindex=False, legal=False, lastmod=None):
    if _is_thin(path):
        noindex = True
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > 59:
        raise SystemExit("title over 59 chars (" + str(len(title)) + "): " + title)
    if title in USED_TITLES:
        raise SystemExit("duplicate title: " + title)
    USED_TITLES.add(title)
    desc = clip(desc)
    canon = url(path)
    if not noindex:
        PAGES.append((path, lastmod or TODAY))
    ld = []
    if path == "/":
        ld.append({"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": BASE,
                   "publisher": {"@type": "Organization", "name": BRAND, "url": BASE, "logo": url("/logo.png")}})
        # Email stays on the contact page. The homepage schema does not repeat it.
        ld.append({"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": BASE, "logo": url("/logo.png")})
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": url(p)} for i, (p, n) in enumerate(crumbs)]})
    if jsonld:
        ld += jsonld if isinstance(jsonld, list) else [jsonld]
    if not noindex and path != "/" and not any(isinstance(x, dict) and x.get("@type") == "Article" for x in ld):
        ld.append(article_ld(title, path, lastmod))
    og_type = "article" if any(isinstance(x, dict) and x.get("@type") == "Article" for x in ld) else "website"
    ldh = "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>" for x in ld)
    nav = "".join('<a href="' + p + '"' + (' aria-current="page"' if p == path else "") + ">" + n + "</a>" for p, n in NAV)
    bc = ""
    if crumbs:
        bc = '<nav class="crumbs" aria-label="Breadcrumb"><ol>' + "".join(
            ('<li><a href="' + p + '">' + E(n) + "</a></li>" if i < len(crumbs) - 1 else '<li aria-current="page">' + E(n) + "</li>")
            for i, (p, n) in enumerate(crumbs)) + "</ol></nav>"
    robots = "noindex, follow" if (noindex or not LAUNCH) else "index, follow, max-image-preview:large"
    beacon = ("<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{\"token\": \"" + CF_BEACON_TOKEN + "\"}'></script><!-- End Cloudflare Web Analytics -->") if LAUNCH else "<!-- cf-beacon: added by the launch build -->"
    ga4_head, ga4_body = analytics_markup()
    adsense_head = ""
    if LAUNCH and ADSENSE_CLIENT:
        adsense_head = (
            '<meta name="google-adsense-account" content="' + E(ADSENSE_CLIENT) + '">\n'
            '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
            + E(ADSENSE_CLIENT) + '" crossorigin="anonymous"></script>'
        )
    search = '<script src="/assets/search-index.js"></script>' if path == "/" else ""
    foot_legal = '<p class="legal-line">' + LEGAL_LINE + "</p>" if legal else ""
    foot_links = [
        ("/about/", "About"), ("/methodology/", "Sources and methods"), ("/image-policy/", "Image policy"),
        ("/terms/", "Terms of use"), ("/privacy/", "Privacy"), ("/disclaimer/", "Disclaimer"),
        ("/ad-disclosure/", "Advertising disclosure"), ("/copyright/", "Copyright and DMCA"), ("/contact/", "Contact"),
    ]
    foot = " | ".join('<a href="' + h + '">' + n + "</a>" for h, n in foot_links)
    if LAUNCH:
        foot += ' | <a href="#cookie-settings" id="cookie-settings">Cookie settings</a>'
    mark = '<a class="mark" href="/image-policy/"><img src="/logo.png" width="34" height="34" alt="Image policy"></a>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}"><meta property="og:image" content="{url('/og.png')}"><meta property="og:image:alt" content="{BRAND}"><meta property="og:locale" content="en_US"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{url('/og.png')}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css?v=3">{ldh}
{adsense_head}
{ga4_head}
</head><body><a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap"><div class="brandwrap">{mark}<a class="brand" href="/"><span>{BRAND}</span></a></div><nav class="main" aria-label="Main">{nav}</nav></div></header>
<main id="main" class="wrap">{bc}{body}</main>
<footer class="site"><div class="wrap"><p><strong>{BRAND}</strong> lists the ink, toner, and bottle numbers the printer maker publishes for a model, and the printers a number fits. Independent, and not affiliated with HP, Canon, Epson, or Brother. Confirm the number on the maker's page and on your printer.</p>
<p class="flinks">{foot}</p>
{foot_legal}</div></footer>
{search}<script src="/assets/site.js?v=1" defer></script>{beacon}
{ga4_body}
</body></html>'''

def ext(title, href):
    return '<a href="' + E(href) + '" rel="nofollow noopener" target="_blank">' + E(title) + "</a>"

def article_ld(headline, path, published=None, modified=None):
    d = published or TODAY
    m = modified or d
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "datePublished": d, "dateModified": m,
            "image": url("/og.png"), "author": {"@type": "Organization", "name": BRAND, "url": BASE},
            "publisher": {"@type": "Organization", "name": BRAND, "url": BASE, "logo": {"@type": "ImageObject", "url": url("/logo.png")}},
            "mainEntityOfPage": url(path)}

def faq_ld(faqs):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}

def faq_html(faqs):
    return '<section class="faq" aria-labelledby="faq-h"><h2 id="faq-h">Frequently asked questions</h2>' + "".join(
        "<details><summary>" + E(q) + "</summary><p>" + E(a) + "</p></details>" for q, a in faqs) + "</section>"

def sources_html(sources, retrieved=None):
    when = retrieved or TODAY_H
    return '<section class="sources" aria-labelledby="src-h"><h2 id="src-h">Sources</h2><ul>' + "".join("<li>" + ext(t, u) + "</li>" for t, u in sources) + f'<li>Retrieved {when}.</li></ul><p class="note">Which Ink Fits is independent and is not the manufacturer. Match the number on your printer and on the box, then confirm it on the source page.</p></section>'

def compare_box_html(title, lines):
    """Lookup/compare box for series and cartridge pages (engagement rule c)."""
    items = "".join("<li>" + line + "</li>" for line in lines)
    return (
        '<aside class="compare" aria-label="' + E(title) + '">'
        "<h2>" + E(title) + "</h2><ul>" + items + "</ul></aside>"
    )

def photo_figure():
    """One news-style thumbnail. The file is the assigned bank photo. The link is the image policy."""
    return (
        '<figure class="figure"><a href="/image-policy/">'
        '<img src="' + BANK_PHOTO + '" width="1200" height="675" alt="AI-generated image"></a>'
        '<figcaption>AI-generated image. <a href="/image-policy/">Image policy</a>.</figcaption></figure>'
    )

def with_thumbs(items):
    out = []
    for it in items:
        if len(it) > 3:
            out.append(it)
        else:
            out.append((it[0], it[1], it[2], BANK_PHOTO))
    return out

def next_reads_html(items, heading="Related reading", hid="nr-h"):
    """3-4 closely related next-read links. Thumb optional until a bank photo exists."""
    cards = []
    for it in items:
        href, label, blurb = it[0], it[1], it[2]
        thumb = it[3] if len(it) > 3 else None
        media = ""
        if thumb:
            media = (
                '<a class="nr-thumb" href="/image-policy/">'
                '<img src="' + E(thumb) + '" width="320" height="180" alt="AI-generated image" loading="lazy"></a>'
            )
        cards.append(
            '<li>' + media + '<div class="nr-copy"><a href="' + E(href) + '">' + E(label) + "</a>"
            "<p>" + E(blurb) + "</p></div></li>"
        )
    return (
        '<section class="nextreads" aria-labelledby="' + E(hid) + '"><h2 id="' + E(hid) + '">' + E(heading) + "</h2>"
        '<ul class="nr-list">' + "".join(cards) + "</ul></section>"
    )

def supply_table(rows, source_url, verified=None):
    when = verified or TODAY_H
    body = []
    for r in rows:
        y = r["yield_text"] or "Not published on the source page"
        body.append("<tr><td>" + E(r["label"]) + "</td><td>" + E(r["color"]) + "</td><td>" + E(r["capacity"]) + "</td><td>" + E(y) + '</td><td><a href="' + E(source_url) + '" rel="nofollow noopener" target="_blank">Manufacturer page</a></td><td>' + when + "</td></tr>")
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
        series.setdefault(series_slug, {
            "slug": series_slug, "name": series_name, "brand": "hp",
            "info": clean(first["info"]), "members": [],
            "regions": first["regions"] if first.get("kind") == "table" else [],
            "supplies": [norm_supply("hp", r) for r in first.get("supplies", [])],
        })
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

def pick_faq(p, lead_nums):
    faqs = []
    if lead_nums:
        if p["medium"] == "ink bottles":
            q = "Which ink bottles fit the " + p["name"] + "?"
            a = "The manufacturer lists " + lead_nums + ". These are bottles for the tanks, not cartridges. Confirm the number on the bottle and on the manufacturer page linked below."
        elif p["medium"] == "toner":
            q = "Which toner fits the " + p["name"] + "?"
            a = "The manufacturer lists " + lead_nums + ". Confirm the number on the toner and on the manufacturer page linked below."
        else:
            q = "Which cartridges fit the " + p["name"] + "?"
            a = "The manufacturer lists " + lead_nums + ". Confirm the number on the cartridge and on the manufacturer page linked below."
        faqs.append((q, a))
    faqs.extend(find_faqs(p["brand"], p["medium"]))
    return faqs

def printer_page(p, series, fam):
    path = f'/printers/{p["brand"]}/{p["slug"]}/'
    sib = series.get(p["series"])
    title = printer_title(p)
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
    faqs = pick_faq(p, lead_nums)
    extra_links = []
    if p["medium"] != "ink cartridges":
        extra_links.append('<a href="/guides/ink-toner-or-bottle/">Ink cartridge, toner, or bottle?</a>')
    if p["slug"] == "deskjet-1000" and p["brand"] == "hp":
        extra_links.append('<a href="/guides/hp-cartridge-numbers-by-region/">Why the number changes by country</a>')
    extra_nav = "".join(" · " + l for l in extra_links)
    pub = PUBLISHED if extra_links else None
    body = f'''<article class="prose wide"><h1>{E(p["name"])} {E(medium_word(p["medium"]))}: which cartridges fit</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p><strong>Official numbers:</strong> {E(lead_nums)}.</p></div>
<p>{"This model takes ink bottles, not a cartridge." if p["medium"]=="ink bottles" else "The table is the manufacturer's list for this model."} Yield is filled in only when that source prints a page yield.</p>
{notes}{"".join(blocks)}
<h2>Cartridge pages</h2><p>{", ".join(fam_links)}</p>
{sib_html}
{faq_html(faqs)}
{sources_html(p["sources"])}
<p><a href="/printers/{p["brand"]}/">All {E(BRANDS[p["brand"]])} models</a> · <a href="/guides/find-the-model-number/">How to find the model number</a>{extra_nav}</p>
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
    write(path, page(path, title, desc, body, [article_ld(p["name"] + " supplies", path, pub), faq_ld(faqs)], crumbs, lastmod=pub))

def series_enrichment(s, members, nums):
    """Series-specific facts for thin hubs. Returns (extra_html, faqs_extra, compare_lines, next_reads, pub)."""
    slug = s["slug"]
    brand = s["brand"]
    if brand == "hp" and slug == "deskjet-1200":
        regions = s.get("regions") or []
        region_rows = "".join(
            "<tr><th scope=\"row\">" + E(clean(r["region"])) + "</th><td>" + E(clean(r["text"])) + "</td></tr>"
            for r in regions
        )
        region_block = ""
        if region_rows:
            region_block = (
                "<h2>What HP prints by region for this series</h2>"
                "<p>HP's cartridge document puts the DeskJet 1200 Series in a region table. "
                "North America and Asia Pacific (excluding India, China, Japan, and Indonesia) list "
                "<a href=\"/cartridges/hp-67/\">HP 67 Black</a> and HP 67 Tri-color. "
                "Other columns print different numbers for the same printers.</p>"
                '<div class="tablewrap"><table class="list"><thead><tr><th scope="col">HP\'s column heading</th>'
                '<th scope="col">Numbers HP prints</th></tr></thead><tbody>' + region_rows + "</tbody></table></div>"
                "<p>Those other region numbers are quoted here from HP's table. They do not yet have their own cartridge pages on this site. "
                '<a href="/guides/hp-cartridge-numbers-by-region/">Why HP cartridge numbers differ outside the US</a>.</p>'
            )
        extra = (
            "<h2>What is distinct about this series</h2>"
            "<p>The DeskJet 1200 Series hub covers three named models: "
            '<a href="/printers/hp/deskjet-1210/">DeskJet 1210</a>, '
            '<a href="/printers/hp/deskjet-1212/">DeskJet 1212</a>, and '
            '<a href="/printers/hp/deskjet-1255/">DeskJet 1255</a>. '
            "On HP's US column checked " + TODAY_H + ", every one of those models lists only cartridge family 67 "
            "(black and tri-color). There is no photo cartridge and no second black number on that column.</p>"
            "<p>That is different from older DeskJet All-in-One hubs such as the "
            '<a href="/printers/hp/deskjet-f4100/">DeskJet F4100 All-in-One</a>, where HP lists several black, '
            "tri-color, and photo numbers on the same section.</p>"
            + region_block
        )
        faqs_extra = [
            ("Is HP 67 the only US number for the DeskJet 1200 Series?",
             "On HP's North America and Asia Pacific column for this series, yes: HP 67 Black and HP 67 Tri-color. Other region columns on the same table print 123, 305, or 805 instead."),
            ("Does this series list a high yield 67XL on HP's table?",
             "The DeskJet 1200 Series section we extracted lists 67 Black and 67 Tri-color for the US column. Open a model page and the HP 67 cartridge page for the full family, including any high yield rows HP prints elsewhere."),
        ]
        compare = [
            'Open a model: <a href="/printers/hp/deskjet-1210/">DeskJet 1210</a>, <a href="/printers/hp/deskjet-1212/">1212</a>, or <a href="/printers/hp/deskjet-1255/">1255</a>.',
            'Check the cartridge: <a href="/cartridges/hp-67/">HP 67 printers</a>.',
            'Compare another DeskJet hub: <a href="/printers/hp/deskjet-f4100/">DeskJet F4100 All-in-One</a>.',
            'Region confusion? <a href="/guides/hp-cartridge-numbers-by-region/">HP numbers by country</a>.',
        ]
        reads = [
            ("/cartridges/hp-67/", "HP 67: which printers it fits", "Every printer HP lists for cartridge family 67."),
            ("/guides/hp-cartridge-numbers-by-region/", "Why HP numbers differ by country", "How HP's region columns change the part number."),
            ("/printers/hp/deskjet-f4100/", "DeskJet F4100 All-in-One hub", "An older DeskJet series with several black and color numbers."),
            ("/guides/find-the-model-number/", "Find the model number", "Where to read the name on the printer and the box."),
        ]
        return extra, faqs_extra, compare, reads, PUBLISHED_TODAY
    if brand == "hp" and slug == "deskjet-f4100":
        extra = (
            "<h2>What is distinct about this series</h2>"
            "<p>The DeskJet F4100 All-in-One hub covers ten named models (F4135 through F4194). "
            "HP's section for this family is a bullet list, not a region table. On the list checked " + TODAY_H + ", "
            "every model shows the same five numbers: "
            '<a href="/cartridges/hp-21/">21</a> and <a href="/cartridges/hp-54/">54</a> Black, '
            '<a href="/cartridges/hp-57/">57</a> and <a href="/cartridges/hp-22/">22</a> Tri-color, and '
            '<a href="/cartridges/hp-58/">58</a> Photo.</p>'
            "<p>Two black numbers and two tri-color numbers on one printer section means HP prints more than one "
            "official option per color. The model page table lists each row. It does not tell you to install every "
            "number at once. Confirm the number on the cartridge you have, then on HP's page.</p>"
            "<p>This is not the DeskJet 1200 Series. That newer hub uses family "
            '<a href="/cartridges/hp-67/">67</a> on its US column and has a multi-region table. '
            "F4100 keeps the older 21 / 54 / 57 / 22 / 58 set and has no region columns in the extract we use.</p>"
            "<h2>How to match your F41xx label</h2>"
            "<p>Read the full model on the front of the printer (for example F4180 or F4194), then open that model card below. "
            "The series name F4100 alone is the hub. The supply table lives on the model page.</p>"
        )
        faqs_extra = [
            ("Why are there two black numbers and two tri-color numbers?",
             "HP's DeskJet F4100 All-in-One section lists 21 and 54 for black, and 57 and 22 for tri-color, plus 58 photo. Each number is an official HP row. Match the number on your cartridge; do not assume every row installs together."),
            ("Is this the same ink as the DeskJet 1200 Series?",
             "No. The DeskJet 1200 Series US column lists HP 67. The F4100 section lists 21, 54, 57, 22, and 58. Open the hub that matches the name on your printer."),
        ]
        compare = [
            'Pick the exact F41xx model in the cards below, or start at <a href="/printers/hp/deskjet-f4180/">DeskJet F4180</a>.',
            'Check a number: <a href="/cartridges/hp-21/">HP 21</a>, <a href="/cartridges/hp-54/">54</a>, <a href="/cartridges/hp-22/">22</a>, <a href="/cartridges/hp-57/">57</a>, or <a href="/cartridges/hp-58/">58</a>.',
            'Compare a newer DeskJet hub: <a href="/printers/hp/deskjet-1200/">DeskJet 1200 Series</a> (HP 67).',
            'Not sure it is ink? <a href="/guides/ink-toner-or-bottle/">Ink, toner, or bottle?</a>.',
        ]
        reads = [
            ("/cartridges/hp-21/", "HP 21: which printers it fits", "Printers HP lists for cartridge 21."),
            ("/cartridges/hp-54/", "HP 54: which printers it fits", "The other black number on this F4100 section."),
            ("/printers/hp/deskjet-1200/", "DeskJet 1200 Series hub", "A later DeskJet series on HP 67, with region columns."),
            ("/guides/ink-toner-or-bottle/", "Ink cartridge, toner, or bottle?", "How to tell which supply type you have."),
        ]
        return extra, faqs_extra, compare, reads, PUBLISHED_TODAY
    if brand == "hp" and slug == "deskjet-2700":
        extra = (
            photo_figure()
            + "<h2>Standard and high yield on this series</h2>"
            "<p>HP's compatibility document puts twelve DeskJet models in this one section, from the "
            '<a href="/printers/hp/deskjet-2710/">2710</a> through the '
            '<a href="/printers/hp/deskjet-2755e/">2755e</a>. On the North America column, every model lists the same four rows: '
            '<a href="/cartridges/hp-67/">67 and 67XL</a> black, and 67 and 67XL tri-color. '
            "The model pages repeat that table. They do not each have a different yield, so the page counts live here and in the "
            '<a href="/guides/xl-vs-standard-cartridges/">XL and standard yield guide</a>, not copied onto every model.</p>'
            "<p>HP's own cartridge specifications, opened " + CHECKED_1121_H + ", print the approximate yields. "
            "67 black (3YM56AN) is about 120 pages and 67XL black (3YM57AN) is about 240. "
            "67 tri-color (3YM55AN) is about 100 pages and 67XL tri-color (3YM58AN) is about 200. "
            "Each footnote says the test printer was the HP ENVY 6000 All-in-One series, not a DeskJet 2700, and that the average uses ISO/IEC 24711 or HP's own method, printing continuously. "
            "Actual yield varies with what is on the page. The compatibility document still does not print these counts.</p>"
            "<h2>The other columns are different numbers</h2>"
            "<p>The same HP row prints 305 and 305XL for Europe, the Middle East, and Africa, and 805 and 805XL for China, India, and Indonesia. "
            "Those are not nicknames for 67. A cartridge bought for a US DeskJet 2755e is the 67 family. "
            '<a href="/guides/hp-cartridge-numbers-by-region/">Why HP numbers differ by country</a>.</p>'
        )
        faqs_extra = [
            ("What page yield does HP print for the ink on the DeskJet 2700 series?",
             "HP's cartridge specifications, checked 21 Nov 2026, say about 120 pages for 67 black, about 240 for 67XL black, about 100 for 67 tri-color, and about 200 for 67XL tri-color. The footnotes say the test printer was the ENVY 6000 series, not this DeskJet, and that the figure is an approximate average."),
            ("Do the twelve models use different cartridges?",
             "Not on HP's North America column for this section. 2710, 2720, 2721, 2722, 2723, 2724, 2732, 2742e, 2752, 2752e, 2755, and 2755e all list 67 and 67XL black and tri-color. Open the model only to match the name on the printer."),
        ]
        compare = [
            'Open the number: <a href="/cartridges/hp-67/">HP 67 and 67XL</a>.',
            'Read the four-brand comparison: <a href="/guides/xl-vs-standard-cartridges/">XL vs standard page yields</a>.',
            'Match the name on the front, for example <a href="/printers/hp/deskjet-2755e/">DeskJet 2755e</a>.',
            'A different DeskJet family: <a href="/printers/hp/deskjet-1200/">DeskJet 1200 Series</a>, which lists 67 and not 67XL on the US column we extracted.',
        ]
        reads = with_thumbs([
            ("/guides/xl-vs-standard-cartridges/", "XL vs standard page yields", "HP 67, Epson 212, Brother LC406, and Canon PG-243, from the maker pages."),
            ("/cartridges/hp-67/", "HP 67: which printers it fits", "Every printer on the US column for family 67."),
            ("/guides/hp-cartridge-numbers-by-region/", "Why HP numbers differ by country", "305 and 805 are other columns, not other names for 67."),
            ("/printers/hp/deskjet-1200/", "DeskJet 1200 Series", "A later DeskJet hub whose US column lists 67 without a 67XL row in our extract."),
        ])
        return extra, faqs_extra, compare, reads, CHECKED_1121
    return "", [], [], [], None

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
    fam_seen, fam_items = [], []
    nums = []
    for p in members:
        for g in p["groups"]:
            for r in g["supplies"]:
                if r["sku"] not in nums:
                    nums.append(r["sku"])
                if r["family"] in fam_seen:
                    continue
                fam_seen.append(r["family"])
                fam_items.append('<li><a href="/cartridges/' + r["family"] + '/">' + E(r["label"]) + "</a></li>")
    cart_html = ""
    if fam_items:
        cart_html = "<h2>Numbers in this series</h2><p>Open a number to see every printer the manufacturer lists for it.</p><ul class=\"cols\">" + "".join(fam_items) + "</ul>"
    sigs = {tuple(sorted((r["sku"], r["color"], r["capacity"]) for g in p["groups"] for r in g["supplies"])) for p in members}
    shown = ", ".join(nums[:12])
    if len(sigs) == 1:
        share = "On the manufacturer lists checked " + TODAY_H + ", every model linked here shows the same numbers: " + shown + "."
        if len(nums) > 12:
            share += " The model pages list the rest."
    else:
        share = "The models linked here do not all show the same numbers on the manufacturer lists checked " + TODAY_H + ". Open the model that matches the name on your printer."
    faqs = [
        ("Which model should I open?", "Match the name on the front of the printer to one of the " + str(len(members)) + " models below. The model page has the supply table."),
        ("Do these models use the same numbers?", share),
    ]
    extra_html, faqs_extra, compare_lines, reads, enrich_pub = series_enrichment(s, members, nums)
    faqs.extend(faqs_extra)
    compare = compare_box_html("Check another model or number", compare_lines) if compare_lines else ""
    mid_reads = next_reads_html(reads[:2], "Keep reading", "nr-mid") if reads else ""
    end_reads = next_reads_html(reads, "Related reading", "nr-end") if reads else ""
    extra_links = []
    if s["brand"] == "hp" and s["slug"] in ("deskjet-1110-series", "deskjet-1200"):
        extra_links.append('<a href="/guides/hp-cartridge-numbers-by-region/">Why the number changes by country</a>')
    if enrich_pub:
        extra_links.append('<a href="/guides/ink-toner-or-bottle/">Ink cartridge, toner, or bottle?</a>')
    extra_nav = "".join(" · " + l for l in extra_links)
    pub = enrich_pub or (PUBLISHED if extra_links else None)
    # The 2700 hub has been on the site since launch. The 21 Nov text is a revision, not a new page.
    published_ld = TODAY if (s["brand"] == "hp" and s["slug"] == "deskjet-2700" and enrich_pub) else pub
    modified_ld = CHECKED_1121 if (s["brand"] == "hp" and s["slug"] == "deskjet-2700" and enrich_pub) else None
    if s["brand"] == "hp" and s["slug"] == "deskjet-2700" and enrich_pub:
        verified = CHECKED_1121_H
    else:
        verified = PUBLISHED_TODAY_H if enrich_pub else TODAY_H
    body = f'''<article class="prose wide"><h1>{E(s["name"])}</h1>
<p class="sub">By {BRAND} · Last verified {verified}</p>
<div class="answer"><p>This series hub links every model we list from the manufacturer's compatibility pages. Open a model for the full table.</p></div>
{info}<ul class="cards">{items}</ul>
{extra_html}
{cart_html}
{compare}
{mid_reads}
{faq_html(faqs)}
{sources_html(srcs)}
{end_reads}
<p><a href="/printers/{s["brand"]}/">All {E(BRANDS[s["brand"]])} models</a> · <a href="/guides/find-the-model-number/">How to find the model number</a>{extra_nav}</p></article>'''
    write(path, page(path, series_title(s["name"]), desc, body, [article_ld(s["name"], path, published_ld, modified=modified_ld), faq_ld(faqs)],
                     [("/", "Home"), ("/printers/", "Printers"), ("/printers/" + s["brand"] + "/", BRANDS[s["brand"]]), (path, s["name"])], lastmod=modified_ld or pub))

def _with_yield(rows, yields):
    out = []
    for r in rows:
        if r["sku"] in yields:
            r = dict(r)
            r["yield_text"] = yields[r["sku"]]
        out.append(r)
    return out

def lookup_refresh(slug, printer_count):
    """Page-specific facts rechecked 20 Nov 2026. None for every other cartridge."""
    if slug == "brother-lc406":
        yields = {
            "LC406BK": "3,000 pages, approximate (ISO/IEC 24711)",
            "LC406XLBK": "6,000 pages, approximate (ISO/IEC 24711)",
            "LC406C": "1,500 pages, approximate (ISO/IEC 24711)",
            "LC406XLC": "5,000 pages, approximate (ISO/IEC 24711)",
            "LC406M": "1,500 pages, approximate (ISO/IEC 24711)",
            "LC406XLM": "5,000 pages, approximate (ISO/IEC 24711)",
            "LC406Y": "1,500 pages, approximate (ISO/IEC 24711)",
            "LC406XLY": "5,000 pages, approximate (ISO/IEC 24711)",
        }
        reads = [
            ("/printers/brother/mfc-j4335dw/", "Brother MFC-J4335DW", "The page whose replacement footnote prints the LC406 yields, and whose in-box claim is 150 pages a month."),
            ("/printers/brother/mfc-j4345dw-xl/", "Brother MFC-J4345DW XL", "Same replacement yields. Brother's in-box claim on this model is 300 pages a month for two years."),
            ("/printers/brother/mfc-j5855dw/", "Brother MFC-J5855DW", "Named on Brother's help article for a 300-page, one-year in-box calculation."),
            ("/cartridges/brother-tn-760/", "Brother TN-760", "A toner number, not this ink. Different supply, different ISO method."),
        ]
        prose = f'''<h2>Replacement yields, rechecked {CHECKED_1120_H}</h2>
<p>The numbers in the table are the replacement-cartridge yields, not a promise of a year of printing. On the <a href="/printers/brother/mfc-j4335dw/">MFC-J4335DW</a> page, Brother's feature line says choose standard yield for up to 3,000 black pages and 1,500 color pages, or high yield for up to 6,000 black and 5,000 color. The disclaimer under that page is stricter about the wording: all of those yields are approximate and are calculated to ISO/IEC 24711, and it states LC406BK at 3,000 pages, each LC406 cyan, magenta, and yellow cartridge at 1,500, LC406XLBK at 6,000, and each LC406XL color cartridge at 5,000.</p>
<p>The <a href="/printers/brother/mfc-j4345dw-xl/">MFC-J4345DW XL</a> disclaimer prints the same yields and puts "approx." in front of each count. Brother's help answer on the one-year in-box calculation lists each SKU on its own line and says "up to" those same page counts, still approximate, still ISO/IEC 24711. Checked {CHECKED_1120_H}, those three pages still agree on the replacement numbers. They do not agree on what "a year of ink" means.</p>
<h2>A year of ink is a different sum</h2>
<p>The MFC-J4335DW disclaimer for "Up to 1-year of ink in-box" uses about 150 pages a month, at 60 percent black and 40 percent color, ISO/IEC 24711, from the four cartridges in the box. The same product page was marked Discontinued when we opened it on {CHECKED_1120_H}. The replacement footnote was still there.</p>
<p>The MFC-J4345DW XL page says the box holds up to 2 years of ink, based on about 300 pages a month at the same 60/40 split. A second footnote on that page says the in-box total is about 7,200 pages, against about 1,800 pages for the MFC-J4335DW, which is the "5,400 more pages" line. That comparison is about cartridges shipped in the box. It is not a second set of LC406 replacement yields.</p>
<p>Brother's help article opens with a one-year claim based on about 300 pages a month, not 150. Further down it names the <a href="/printers/brother/mfc-j5855dw/">MFC-J5855DW</a>, <a href="/printers/brother/mfc-j6555dw/">MFC-J6555DW</a>, and <a href="/printers/brother/mfc-j6955dw/">MFC-J6955DW</a> for that 300-page version, and it says the first install uses extra ink to fill the delivery tubes, once. Those three models are on the printer list below. The J4335DW page still prints 150 pages a month for its own one-year line. Read the footnote on the model you own before you treat "one year" as 3,000 pages.</p>
<p>The printer list itself is the one from Brother's MFC-J4335DW page, the LC406 4-pack page, and the LC406 cyan page, checked {TODAY_H}. This recheck did not add or drop a model. <a href="/guides/ink-toner-or-bottle/">Ink, toner, or bottle</a> if you are not sure this is the supply in the printer.</p>
{compare_box_html("Check another Brother number", [
    '<a href="/printers/brother/mfc-j4335dw/">MFC-J4335DW</a>: about 150 pages a month in the one-year in-box footnote.',
    '<a href="/printers/brother/mfc-j4345dw-xl/">MFC-J4345DW XL</a>: about 300 pages a month, and about 7,200 in-box pages against about 1,800.',
    '<a href="/printers/brother/mfc-j5855dw/">MFC-J5855DW</a>: named on the help article\'s 300-page one-year line.',
    'Different supply: <a href="/cartridges/brother-tn-760/">TN-760 toner</a>, not LC406 ink.',
])}
{next_reads_html(reads, "Keep reading")}'''
        faqs = [
            ("Which printers use Brother LC406?", str(printer_count) + " printers are linked on this page, from Brother's MFC-J4335DW, LC406 4-pack, and LC406 cyan pages checked " + TODAY_H + ". The yield recheck on " + CHECKED_1120_H + " did not change that list."),
            ("What page yield does Brother print for a replacement LC406?", "On the MFC-J4335DW disclaimer checked " + CHECKED_1120_H + ", the yields are approximate and calculated to ISO/IEC 24711: LC406BK 3,000 pages, LC406 cyan, magenta, and yellow 1,500 each, LC406XLBK 6,000, and LC406XL cyan, magenta, and yellow 5,000 each. The feature line on that page says \"up to\" those counts. The help article says \"up to\" as well."),
            ("Is one year of ink the same as 3,000 pages?", "No. The 3,000 figure is the approximate ISO yield Brother prints for a replacement LC406BK cartridge. The one-year in-box line is a separate calculation. The J4335DW page uses about 150 pages a month for that line. The J4345DW XL page uses about 300 pages a month for a two-year in-box line. The help article's 300-page one-year line names the J5855DW, J6555DW, and J6955DW."),
            ("How do I find the model number?", "Read the model name on the front of the printer. The cartridge number is printed on the supply and on the box. This page repeats the numbers Brother publishes. It does not replace the label on your printer."),
        ]
        return {
            "desc": "Brother LC406 black is about 3,000 pages, and the XL black is about 6,000. Yields rechecked 20 Nov 2026.",
            "sub": "By " + BRAND + " · Yields rechecked " + CHECKED_1120_H,
            "answer": "<strong>" + str(printer_count) + " printers</strong> on Brother's lists use LC406. Replacement yields rechecked " + CHECKED_1120_H + ": about 3,000 black pages for LC406BK, about 6,000 for LC406XLBK, 1,500 for each standard color, and 5,000 for each XL color. Those are approximate ISO/IEC 24711 figures, not the \"year of ink\" line.",
            "yields": yields,
            "table_url": "https://www.brother-usa.com/p/inkjet-printers/MFCJ4335DW",
            "prose": prose,
            "faqs": faqs,
            "extra_sources": [
                ("Brother MFC-J4345DW XL", "https://www.brother-usa.com/p/inkjet-printers/MFCJ4345DWXL"),
                ("Brother: Up to 1 Year of Ink in-box calculation", "https://help.brother-usa.com/app/answers/detail/a_id/182755/~/up-to-1-year-of-ink-in-box-calculation"),
            ],
            "reads": reads,
        }
    if slug == "hp-932":
        reads = [
            ("/cartridges/hp-933/", "HP 933: which printers use it", "The color number from the same OfficeJet section. HP's list does print a 933XL row."),
            ("/printers/hp/officejet-6700-premium/", "HP OfficeJet 6700 Premium", "The printer HP names as the test unit for the 932 and 932XL yield footnotes."),
            ("/printers/hp/officejet-7510/", "HP OfficeJet 7510", "On the compatibility list for 932, and also named on HP's 932XL shop page."),
            ("/guides/find-the-model-number/", "Find the model number", "Where to read the name on the printer and the number on the cartridge."),
        ]
        prose = f'''<h2>What HP prints for a page yield</h2>
<p>HP's compatibility document, the source for the printer list, does not print a page yield for 932. The yield comes from HP's own cartridge specification. HP's South Africa product page for the HP 932 Black Original Ink Cartridge, part CN057AE, lists a black and white yield of about 400 pages. The footnote says the test printer was the HP Officejet 6700 Premium e-All-in-One, and that the figure is an approximate average based on ISO/IEC 24711 or HP testing methodology and continuous printing. Actual yield, HP says, varies considerably with the content of the pages. The same specification lists an 8.5 ml fill, pigment-based ink, a 12 picoliter drop, and 1,088 nozzles. Checked {CHECKED_1120_H}.</p>
<h2>932XL is on a different HP page</h2>
<p>HP's US shop page for the 932XL High Yield Black cartridge, product CN053AN, lists about 1,000 pages. Its footnote names the same Officejet 6700 Premium test printer and the same ISO/IEC 24711 wording, and it points to <a href="https://www.hp.com/go/learnaboutsupplies" rel="nofollow noopener" target="_blank">hp.com/go/learnaboutsupplies</a> for the method. The compatible printers named on that shop page, when we read it on {CHECKED_1120_H}, include the Officejet 6600 e-All-in-One, the OfficeJet 7110 Wide Format, the <a href="/printers/hp/officejet-7510/">OfficeJet 7510</a>, and the <a href="/printers/hp/officejet-7612/">OfficeJet 7612</a>.</p>
<p>That shop list is not the six-model list in the table above. The compatibility document we extracted on {TODAY_H} has no 932XL row in any section. The OfficeJet 6700 section of that same document does list both <a href="/cartridges/hp-933/">933 and 933XL</a> for cyan, magenta, and yellow, and only 932 (not 932XL) for black. So HP published an XL color number in the compatibility section, and published the 932XL black yield on the cartridge's own shop page instead. This page does not add 932XL to the fit list. Match the number on the cartridge you have, then confirm it on HP's page for your model.</p>
{compare_box_html("Check another HP number", [
    'Color from the same section, with an XL row on the compatibility list: <a href="/cartridges/hp-933/">HP 933</a>.',
    'The yield test printer: <a href="/printers/hp/officejet-6700-premium/">OfficeJet 6700 Premium</a>.',
    'Named on both the compatibility list and the 932XL shop page: <a href="/printers/hp/officejet-7510/">OfficeJet 7510</a>.',
    'Read the name on the printer first: <a href="/guides/find-the-model-number/">model and cartridge numbers</a>.',
])}
{next_reads_html(reads, "Keep reading")}'''
        faqs = [
            ("Which printers use HP 932?", str(printer_count) + " printers are linked on this page, from HP's compatibility document checked " + TODAY_H + ". That document lists 932 Black. It does not list 932XL."),
            ("What page yield does HP print for 932?", "HP's specification for the 932 Black cartridge CN057AE, checked " + CHECKED_1120_H + ", says about 400 pages. The footnote says the test printer was the Officejet 6700 Premium e-All-in-One, and that the average is based on ISO/IEC 24711 or HP testing methodology and continuous printing. HP says actual yield varies with page content."),
            ("Does 932XL fit the same printers?", "Not according to the compatibility document this site uses. That extract has no 932XL row. HP's US shop page for CN053AN rates 932XL at about 1,000 pages and names its own compatible-printer list, which overlaps some of these OfficeJets and is not identical. Confirm the number on your cartridge against HP's page for your model."),
            ("How do I find the model number?", "Read the model name on the front of the printer. The cartridge number is printed on the supply and on the box. This page repeats the numbers HP publishes. It does not replace the label on your printer."),
        ]
        return {
            "checked": CHECKED_1120,
            "checked_h": CHECKED_1120_H,
            "desc": "HP 932 black is about 400 pages on HP's spec. The compatibility list names six printers and does not name 932XL.",
            "sub": "By " + BRAND + " · Compatibility list " + TODAY_H + " · Yield pages " + CHECKED_1120_H,
            "answer": "<strong>" + str(printer_count) + " printers</strong> on HP's compatibility list use 932 Black. HP's specification for CN057AE rates that cartridge at about 400 pages. The compatibility list does not name 932XL.",
            "yields": {"932": "~400 pages (ISO/IEC 24711, tested in Officejet 6700 Premium)"},
            "table_url": "https://www.hp.com/za-en/products/ink-toner/product-details/product-specifications/5094899",
            "prose": prose,
            "faqs": faqs,
            "extra_sources": [
                ("HP 932 Black Original Ink Cartridge CN057AE (HP South Africa specification)", "https://www.hp.com/za-en/products/ink-toner/product-details/product-specifications/5094899"),
                ("HP 932XL High Yield Black Original Ink Cartridge CN053AN (HP US shop)", "https://www.hp.com/us-en/shop/pdp/-p-cn053an-140--1"),
                ("HP: learn about supplies", "https://www.hp.com/go/learnaboutsupplies"),
            ],
            "reads": reads,
        }
    if slug == "canon-pg-243-cl-244":
        ts302 = "https://www.usa.canon.com/support/p/pixma-ts302a-wireless-inkjet-home-printer"
        measure = "https://www.usa.canon.com/printers/inkjet-page-yields/page-measure"
        reads = with_thumbs([
            ("/guides/xl-vs-standard-cartridges/", "XL vs standard page yields", "How HP, Epson, Brother, and Canon print a standard yield next to a larger one."),
            ("/cartridges/canon-pg-245-cl-246/", "Canon PG-245 and CL-246", "The larger numbers on the same Canon spec, including an XL."),
            ("/printers/canon/pixma-mg2420/", "Canon PIXMA MG2420", "One of the five MG models on the 16 Nov list."),
            ("/printers/canon/pixma-mg2520/", "Canon PIXMA MG2520", "Named on the MG article. The value pack we checked does not list it."),
        ])
        prose = f'''<h2>What Canon printed for a page count</h2>
<p>On {CHECKED_1121_H} the PIXMA TS302a support page printed a page yield row for these cartridges: PG-243 black 100 pages and CL-244 color 100 pages. The same row prints the fill: PG-243 black 5.6 ml and CL-244 color 6.2 ml. It does not print an XL of either number. It does print a larger pair on the next line, <a href="/cartridges/canon-pg-245-cl-246/">PG-245 and CL-246</a>, at 180 black and 180 color pages for the standard size and 300 and 300 for the XL.</p>
<p>That 100 is a page count for the cartridge number. The TS302a cell does not say ISO. Canon's separate page, <a href="{E(measure)}" rel="nofollow noopener" target="_blank">How Page Yields Are Measured</a>, says the mixed text and graphics document is declared to ISO/IEC 24711, from continuous printing on plain paper. This page does not paste the word ISO onto the 100, because the TS302a cell itself does not.</p>
<h2>There is no PG-243XL on that spec</h2>
<p>A reader looking for an XL of PG-243 will not find one in this row. The step up Canon prints is a different number. PG-245 standard is 180 pages against PG-243's 100, and PG-245XL is 300. Those are not a high yield fill of PG-243. The five MG printers below are the models whose older Canon article listed PG-243 beside PG-245. Other PIXMA models on our <a href="/cartridges/canon-pg-245-cl-246/">PG-245 page</a> are listed for PG-245 only.</p>
<p>The same TS302a row prints PG-245 standard at 8.9 ml. The MG series article we saved on {TODAY_H} printed 8.0 ml for PG-245, and 5.6 ml and 6.2 ml for PG-243 and CL-244. The 5.6 and 6.2 still match. The 8.0 and the 8.9 do not. That Knowledge Base article did not load on {CHECKED_1121_H} (the page returned an error), so this recheck does not overwrite the PG-245 volume on the other page. It only records the disagreement.</p>
<h2>The printer list is still the 16 Nov list</h2>
<p>Five printers are linked below, from the PG-245 value pack and the MG series article, both checked {TODAY_H}: MG2420, MG2920, MG2924, MG2520, and MG2922. The value pack names the first three. The article names all five. This recheck did not add or drop one of those five, because the article would not open.</p>
<p>The TS302a support page is a different fact. It is the page that prints the 100 page yield, and it names PG-243 and CL-244 as inks for the TS302a. There is no TS302a model page here yet. Do not read the five links as a complete list of every Canon printer that can hold this cartridge.</p>
<p>Cost per page is the price you pay divided by that 100. Canon's TS302a spec does not print a shelf price, so this page does not invent one. The same arithmetic, for HP, Epson, and Brother as well as this Canon pair, is in the <a href="/guides/xl-vs-standard-cartridges/">yield guide</a>.</p>
{compare_box_html("Check another Canon number", [
    'The larger number on the same spec: <a href="/cartridges/canon-pg-245-cl-246/">PG-245 and CL-246</a>, including XL.',
    'A model the value pack and the article both name: <a href="/printers/canon/pixma-mg2420/">PIXMA MG2420</a>.',
    'A model the article names and the value pack does not: <a href="/printers/canon/pixma-mg2520/">PIXMA MG2520</a>.',
    'All four makers, standard against XL: <a href="/guides/xl-vs-standard-cartridges/">page yields compared</a>.',
])}
{next_reads_html(reads, "Keep reading", "nr-mid")}'''
        faqs = [
            ("Which printers use Canon PG-243 and CL-244?", str(printer_count) + " PIXMA MG models are linked on this page, from Canon's value pack and MG series article checked " + TODAY_H + ". The TS302a support page also names these cartridges. TS302a is not one of the five. The Knowledge Base article did not load on " + CHECKED_1121_H + ", so those five names were not re-confirmed that day."),
            ("What page yield does Canon print?", "The PIXMA TS302a support page, opened " + CHECKED_1121_H + ", prints 100 black pages for PG-243 and 100 color pages for CL-244, and fill volumes of 5.6 ml and 6.2 ml. The cell does not say ISO. Canon's measurement page says the mixed-document method follows ISO/IEC 24711."),
            ("Is there an XL of PG-243?", "Not on the TS302a spec. That page prints PG-245 and CL-246 as separate numbers, at 180 pages standard and 300 pages XL for black and for color. It does not print a PG-243XL or a CL-244XL."),
            ("How do I find the model number?", "Read the model name on the front of the printer. The cartridge number is printed on the supply and on the box. This page repeats the numbers Canon publishes. It does not replace the label on your printer."),
        ]
        return {
            "checked": CHECKED_1121,
            "checked_h": CHECKED_1121_H,
            "desc": "PG-243 black and CL-244 color are 100 pages each on Canon's TS302a spec. No XL of this number.",
            "sub": "By " + BRAND + " · Printer list " + TODAY_H + " · Yield page " + CHECKED_1121_H,
            "answer": "<strong>" + str(printer_count) + " PIXMA MG printers</strong> are on the list below. Canon's TS302a spec, opened " + CHECKED_1121_H + ", prints 100 black pages for PG-243 and 100 color pages for CL-244. It does not print an XL of either number.",
            "yields": {
                "PG-243": "100 pages (black), PIXMA TS302a spec",
                "CL-244": "100 pages (color), PIXMA TS302a spec",
            },
            "table_url": ts302,
            "prose": prose,
            "faqs": faqs,
            "extra_sources": [
                ("Canon Support for PIXMA TS302a", ts302),
                ("How Page Yields Are Measured, Canon U.S.A.", measure),
            ],
            "reads": reads,
        }
    return None

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
    faqs = [("Which printers use " + nice + "?", str(len(printers)) + " printers on the manufacturer lists checked " + TODAY_H + " are linked on this page. If your model is not listed, it was not on those pages.")]
    faqs.extend(find_faqs(f["brand"], medium if medium != "toner" or f["slug"] != "brother-dr-730" else "toner"))
    extra_links = []
    if medium != "ink cartridges":
        extra_links.append('<a href="/guides/ink-toner-or-bottle/">Ink cartridge, toner, or bottle?</a>')
    extra_nav = "".join(" · " + l for l in extra_links)
    pub = PUBLISHED if extra_links else None
    modified = None
    sub = "By " + BRAND + " · Last verified " + TODAY_H
    answer = "<strong>" + str(len(printers)) + " printers</strong> on the manufacturer lists below use this number. If your model is not in the list, it is not on the pages we checked."
    table_rows, table_url, table_when = rows, sources[0][1], None
    prose, end_reads, sources_when = "", "", None
    refresh = lookup_refresh(f["slug"], len(printers))
    if refresh:
        checked = refresh.get("checked", CHECKED_1120)
        checked_h = refresh.get("checked_h", CHECKED_1120_H)
        desc = refresh["desc"]
        sub = refresh["sub"]
        answer = refresh["answer"]
        table_rows = _with_yield(rows, refresh["yields"])
        table_url = refresh["table_url"]
        table_when = checked_h
        prose = "\n" + refresh["prose"]
        faqs = refresh["faqs"]
        seen_u = {u for _t, u in sources}
        for t, u in refresh["extra_sources"]:
            if u not in seen_u:
                sources.append((t, u))
                seen_u.add(u)
        sources_when = checked_h
        end_reads = "\n" + next_reads_html(refresh["reads"], "Related reading", "nr-h-end")
        pub = TODAY
        modified = checked
    body = f'''<article class="prose wide"><h1>{E(title.split(":")[0])}: which printers use them</h1>
<p class="sub">{sub}</p>
<div class="answer"><p>{answer}</p></div>
{supply_table(table_rows, table_url, table_when)}
<h2>Printers</h2><ul class="cols">{links}</ul>
{related_cartridge_html(f)}{prose}
{faq_html(faqs)}
{sources_html(sources, sources_when)}{end_reads}
<p><a href="/cartridges/">All cartridges</a> · <a href="/printers/{f["brand"]}/">{E(BRANDS[f["brand"]])} printers</a> · <a href="/guides/find-the-model-number/">How to find the model number</a>{extra_nav}</p>
</article>'''
    # h1 may say "them" for a drum. Acceptable.
    title = fit_title([title, "Which printers use " + nice, nice + ": which printers"])
    write(path, page(path, title, desc, body,
                    [article_ld(nice, path, pub, modified=modified), faq_ld(faqs)],
                    [("/", "Home"), ("/cartridges/", "Cartridges"), (path, nice)], lastmod=modified or pub))

def related_cartridge_html(f):
    mine = {(sl, b) for sl, _n, b in f["printers"]}
    scored = []
    for slug, other in FAMS.items():
        if slug == f["slug"] or other["brand"] != f["brand"]:
            continue
        n = sum(1 for sl, _n, b in other["printers"] if (sl, b) in mine)
        if n:
            nice = BRANDS[other["brand"]] + " " + slug.split("-", 1)[1].upper()
            scored.append((-n, nice, slug))
    scored.sort()
    if not scored:
        return ""
    items = ['<li><a href="/cartridges/' + slug + '/">' + E(nice) + "</a></li>" for _n, nice, slug in scored[:12]]
    more = "<p>Open a printer page above for every number on that model.</p>" if len(scored) > 12 else ""
    return "<h2>Other numbers on these printers</h2><p>These numbers are also on the manufacturer list for at least one printer linked above.</p><ul class=\"cols\">" + "".join(items) + "</ul>" + more

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
    n = sum(1 for p in printers if p["brand"] == brand)
    faqs = [
        ("Which " + BRANDS[brand] + " model should I open?", "Match the name on the front of the printer to one of the " + str(n) + " models. A series hub lists the models taken from that section of the manufacturer pages."),
        ("Which cartridge number should I use?", "Open the model page and read the table. The numbers are the ones " + BRANDS[brand] + " prints, last checked " + TODAY_H + ". We do not copy a store's compatible ink chart."),
    ]
    extra_links = []
    if brand == "hp":
        extra_links.append('<a href="/guides/hp-cartridge-numbers-by-region/">Why the number changes by country</a>')
    extra_nav = "".join(" · " + l for l in extra_links)
    pub = PUBLISHED if extra_links else None
    body = f'''<h1>{E(BRANDS[brand])} ink and toner</h1>
<p class="answer">Models and series taken from {E(BRANDS[brand])}'s own compatibility pages. Open a series, or jump to a single model.</p>
<ul class="cards">{cards}</ul>
{("<h2>Single models</h2><ul class=\"cols\">" + "".join(lone) + "</ul>") if lone else ""}
<p><a href="/printers/">All printers</a> · <a href="/cartridges/">All cartridges</a> · <a href="/guides/find-the-model-number/">How to find the model number</a>{extra_nav}</p>
{faq_html(faqs)}'''
    write(path, page(path, BRANDS[brand] + " printer ink and toner | " + BRAND, "Which cartridges, toner, or bottles " + BRANDS[brand] + " lists for " + str(n) + " printer models.", body, [faq_ld(faqs)],
                     [("/", "Home"), ("/printers/", "Printers"), (path, BRANDS[brand])], lastmod=pub))

def indexes(printers, series, fams):
    cards = []
    for b, name in BRANDS.items():
        n = sum(1 for p in printers if p["brand"] == b)
        cards.append('<li class="card"><h2><a href="/printers/' + b + '/">' + E(name) + "</a></h2><p>" + str(n) + " models from the manufacturer's lists.</p></li>")
    printer_faqs = [
        ("Which brand should I pick?", "Pick the brand printed on the printer. This page links HP, Canon, Epson, and Brother. The count under a brand is the number of models taken from that manufacturer's pages."),
        ("Which page should I open if I only know the cartridge number?", "Open the cartridge list and choose the number printed on the supply or the box."),
    ]
    body = '<h1>Printers</h1><p class="answer">Pick a brand. Every model page cites the manufacturer page it was checked against on ' + TODAY_H + '.</p><ul class="cards">' + "".join(cards) + '</ul><p><a href="/cartridges/">Cartridges</a> · <a href="/guides/">Guides</a> · <a href="/guides/find-the-model-number/">How to find the model number</a> · <a href="/guides/ink-toner-or-bottle/">Ink cartridge, toner, or bottle?</a> · <a href="/guides/xl-vs-standard-cartridges/">XL and standard page yields</a> · <a href="/guides/hp-cartridge-numbers-by-region/">Why the cartridge number changes by country</a></p>' + faq_html(printer_faqs)
    write("/printers/", page("/printers/", "Printer ink and toner by model | " + BRAND, "Find the cartridge, toner, or bottle for an HP, Canon, Epson, or Brother printer.", body, [faq_ld(printer_faqs)], [("/", "Home"), ("/printers/", "Printers")], lastmod=CHECKED_1121))
    items = []
    for slug in sorted(fams):
        f = fams[slug]
        nice = BRANDS[f["brand"]] + " " + slug.split("-", 1)[1].upper()
        items.append('<li><a href="/cartridges/' + slug + '/">' + E(nice) + "</a> <span class=\"note\">" + str(len(f["printers"])) + " printers</span></li>")
    cart_faqs = [
        ("Which cartridge page should I open?", "Open the number printed on the cartridge, toner, or bottle. The page lists the printers the manufacturer names for that number."),
        ("What if my printer is not listed on that page?", "It was not on the manufacturer pages checked " + TODAY_H + ". Open the printer by model, then confirm the number on the manufacturer page linked there."),
    ]
    body = '<h1>Cartridges, toner, and bottles</h1><p class="answer">Pick a number to see the printers the manufacturer lists for it.</p><ul class="cols">' + "".join(items) + '</ul><p><a href="/printers/">Printers</a> · <a href="/guides/">Guides</a> · <a href="/guides/find-the-model-number/">How to find the model number</a> · <a href="/guides/xl-vs-standard-cartridges/">XL and standard page yields</a> · <a href="/guides/ink-toner-or-bottle/">Ink cartridge, toner, or bottle?</a></p>' + faq_html(cart_faqs)
    write("/cartridges/", page("/cartridges/", "Ink and toner by cartridge number | " + BRAND, "Which printers use a cartridge, toner, or bottle number, from the manufacturer lists.", body, [faq_ld(cart_faqs)], [("/", "Home"), ("/cartridges/", "Cartridges")], lastmod=CHECKED_1121))

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
<h2>On the cartridge or bottle</h2><p>Ink cartridges show a number such as 67, PG-275, or 212. Toner shows a number such as TN-760 or 58A. Tank printers use a bottle such as GI-21 or 522, and the lead on those pages says so. High yield packs add XL or a similar mark. The color is printed next to the number. Published page counts, and why a higher count is not automatically a lower cost per page, are in the <a href="/guides/xl-vs-standard-cartridges/">XL and standard yield guide</a>.</p>
<h2>Then check the source</h2><p>Each page links the manufacturer document we used. Cartridge numbers differ by country. HP's pages quote the other columns when HP prints them. <a href="/methodology/">Sources and methods</a>.</p>
{compare_box_html("Check another path", [
    'Have a printer name? Open it from <a href="/printers/">Printers</a>.',
    'Have a cartridge number? Open it from <a href="/cartridges/">Cartridges</a>.',
    'Not sure it is a cartridge? <a href="/guides/ink-toner-or-bottle/">Ink, toner, or bottle?</a>.',
])}
{next_reads_html([
    ("/guides/ink-toner-or-bottle/", "Ink cartridge, toner, or bottle?", "How to tell which supply type your printer takes."),
    ("/guides/hp-cartridge-numbers-by-region/", "Why HP numbers differ by country", "When HP prints a different part number abroad."),
    ("/cartridges/hp-67/", "HP 67: which printers it fits", "A common DeskJet cartridge family."),
    ("/printers/", "Browse printers", "Start from the brand list when you know the model."),
], "Keep reading")}
{faq_html(faqs)}
{sources_html([
    (HP_TITLE, HP_URL),
    ("Canon PG-275 / CL-276 value pack", "https://www.usa.canon.com/shop/p/pg-275-cl-276-value-pack"),
    ("Epson 212 ink", "https://epson.com/For-Home/Ink/Epson%26reg%3B-212%26reg%3B-Ink/i/T212"),
    ("Brother TN760", "https://www.brother-usa.com/p/ink-toner/TN760"),
])}
{next_reads_html([
    ("/guides/ink-toner-or-bottle/", "Ink cartridge, toner, or bottle?", "How to tell which supply type your printer takes."),
    ("/guides/hp-cartridge-numbers-by-region/", "Why HP numbers differ by country", "When HP prints a different part number abroad."),
    ("/cartridges/hp-67/", "HP 67: which printers it fits", "A common DeskJet cartridge family."),
    ("/printers/", "Browse printers", "Start from the brand list when you know the model."),
])}
<p><a href="/printers/">Browse printers</a> · <a href="/cartridges/">Browse cartridges</a></p>
</article>'''
    write(path, page(path, "Find the printer model and cartridge number", "How to read the model number on the printer and the cartridge number on the box.", body, [article_ld("Find the model number", path, PUBLISHED_TODAY, CHECKED_1121), faq_ld(faqs)], [("/", "Home"), (path, "Find the number")], lastmod=CHECKED_1121))

def guide_ink_toner_bottle():
    path = "/guides/ink-toner-or-bottle/"
    title = "Ink cartridge, toner, or bottle: which is yours?"
    desc = "How to tell if a printer uses ink cartridges, toner, or ink bottles, with examples from HP, Canon, Epson, and Brother support pages."
    faqs = [
        ("How can I tell without opening the printer?", "The model name is usually the clue. EcoTank and MegaTank models take ink bottles, LaserJet models and Brother's drum and toner models take toner, and the rest of the printers listed on this site take ink cartridges. Open the model page for the exact number."),
        ("Is the toner drum the same part as the toner?", "No. Brother's DR730 and TN760 bundle page lists the toner and the drum as two separate numbers, TN-760 and DR-730, for the same printer."),
        ("Does a tank printer still have a part number?", "Yes, but it is a bottle number, not a cartridge number. Epson's ET-2800 FAQ and Canon's MegaTank ink types article both print bottle numbers for their tank printers, not cartridge numbers."),
    ]
    rows = [
        ("Ink cartridge", "Inkjet printers that take a small sealed cartridge", "HP DeskJet, OfficeJet, and ENVY; Canon PIXMA (non MegaTank); Epson WorkForce and Expression (non EcoTank); Brother inkjet", "/printers/hp/deskjet-2755e/", "HP DeskJet 2755e"),
        ("Toner", "Laser printers that take a toner cartridge, sometimes with a separate drum", "HP LaserJet; Brother laser models such as the MFC-L2710DW", "/printers/hp/laserjet-pro-m428/", "HP LaserJet Pro M428"),
        ("Ink bottle", "Tank printers refilled from a bottle, not a cartridge", "Epson EcoTank; Canon MegaTank (PIXMA G series, MAXIFY GX series)", "/printers/epson/et-2800/", "Epson EcoTank ET-2800"),
    ]
    table_rows = "".join(
        f'<tr><td>{E(t)}</td><td>{E(d)}</td><td>{E(fam)}</td><td><a href="{E(href)}">{E(ex)}</a></td></tr>'
        for t, d, fam, href, ex in rows
    )
    body = f'''<article class="prose"><h1>Ink cartridge, toner, or ink bottle: which does your printer use?</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p><strong>Look at the supply type, not the price.</strong> This site lists three kinds: ink cartridges, toner, and ink bottles. The printer's own name is usually the clue.</p></div>
<div class="tablewrap"><table class="list"><thead><tr><th scope="col">Supply type</th><th scope="col">What it is</th><th scope="col">Families on this site</th><th scope="col">Example model</th></tr></thead><tbody>{table_rows}</tbody></table></div>
<h2>Ink cartridges</h2><p>Inkjet printers hold a small sealed cartridge inside a carriage. Most HP DeskJet, OfficeJet, and ENVY models, most Canon PIXMA models that are not MegaTank, most Epson WorkForce and Expression models that are not EcoTank, and Brother's inkjet models such as the <a href="/printers/brother/mfc-j4335dw/">MFC-J4335DW</a> are in this group.</p>
<h2>Toner</h2><p>Laser printers use a toner cartridge, not a liquid ink cartridge. HP's replacement document for the LaserJet Pro MFP M428 lists toner cartridge 58A and the high yield 58X. Brother's TN760 page names TN-760 as a high yield black toner, and Brother's DR730 and TN760 bundle page lists a separate drum unit, DR-730, for the same printer.</p>
<h2>Ink bottles</h2><p>Tank printers refill built in tanks from a bottle, not a cartridge. Epson's ET-2800 FAQ lists bottle part numbers 522120 black, 522220 yellow, 522320 magenta, and 522420 cyan. Canon's MegaTank ink types article lists bottle numbers such as GI-20, GI-21, and GI-290 for the PIXMA G series and MAXIFY GX series.</p>
{compare_box_html("Check another supply type", [
    'Inkjet cartridge example: <a href="/printers/hp/deskjet-2755e/">HP DeskJet 2755e</a>.',
    'Toner example: <a href="/printers/hp/laserjet-pro-m428/">HP LaserJet Pro M428</a>.',
    'Ink bottle example: <a href="/printers/epson/et-2800/">Epson EcoTank ET-2800</a>.',
])}
{next_reads_html([
    ("/guides/find-the-model-number/", "Find the model number", "Where the model and cartridge numbers are printed."),
    ("/cartridges/brother-tn-760/", "Brother TN-760 printers", "A high yield toner page with ISO page yield notes."),
    ("/cartridges/epson-522/", "Epson 522 bottles", "Bottle numbers for EcoTank ET-2800."),
    ("/guides/hp-cartridge-numbers-by-region/", "Why HP numbers differ by country", "When the same printer gets a different HP number abroad."),
], "Keep reading")}
{faq_html(faqs)}
{sources_html([
    ("HP LaserJet Pro MFP M329, M428, M429: replace the toner cartridge", "https://support.hp.com/us-en/document/c06398764"),
    more.TN760,
    more.DR_BUND,
    more.ET2800,
    more.GI_TYPES,
])}
{next_reads_html([
    ("/guides/find-the-model-number/", "Find the model number", "Where the model and cartridge numbers are printed."),
    ("/cartridges/brother-tn-760/", "Brother TN-760 printers", "A high yield toner page with ISO page yield notes."),
    ("/cartridges/epson-522/", "Epson 522 bottles", "Bottle numbers for EcoTank ET-2800."),
    ("/guides/hp-cartridge-numbers-by-region/", "Why HP numbers differ by country", "When the same printer gets a different HP number abroad."),
])}
<p><a href="/printers/">Browse printers</a> · <a href="/cartridges/">Browse cartridges</a> · <a href="/cartridges/brother-tn-760/">Brother TN-760 printers</a> · <a href="/cartridges/canon-gi-21/">Canon GI-21 printers</a> · <a href="/cartridges/epson-522/">Epson 522 printers</a></p>
</article>'''
    write(path, page(path, title, desc, body, [article_ld(title, path, PUBLISHED_TODAY), faq_ld(faqs)], [("/", "Home"), (path, "Ink, toner, or bottle")], lastmod=PUBLISHED_TODAY))

def guide_hp_region():
    path = "/guides/hp-cartridge-numbers-by-region/"
    title = "Why HP cartridge numbers differ outside the US"
    desc = "HP prints a different ink cartridge number for the same printer in North America, Europe, and other regions, from HP's own cartridge list."
    raw = json.load(open(os.path.join(ROOT, "_build", "hp_catalog.json"), encoding="utf-8"))
    want = {
        "HP DeskJet 1000 printers": ("/printers/hp/deskjet-1000/", "HP DeskJet 1000"),
        "HP DeskJet 1110 All-in-One": ("/printers/hp/deskjet-1110-series/", "HP DeskJet 1110 All-in-One"),
        "HP DeskJet 1200 Series": ("/printers/hp/deskjet-1200/", "HP DeskJet 1200 Series"),
    }
    examples = []
    for s in raw["sections"]:
        if s["title"] in want and len(s.get("regions", [])) > 1:
            examples.append((s["title"], s["regions"], want[s["title"]]))
    blocks = []
    for sec_title, regions, (href, link_text) in examples:
        rows = "".join("<tr><th scope=\"row\">" + E(clean(r["region"])) + "</th><td>" + E(clean(r["text"])) + "</td></tr>" for r in regions)
        blocks.append(f'<h3><a href="{E(href)}">{E(link_text)}</a></h3><div class="tablewrap"><table class="list"><thead><tr><th scope="col">Region on HP\'s list</th><th scope="col">Numbers HP prints</th></tr></thead><tbody>{rows}</tbody></table></div>')
    faqs = [
        ("Does this happen on every HP printer?", "Only where HP's own cartridge document prints more than one region column for a model. Most of the models on this site show only one column. Open the model page and look for an \"Other regions on the same table\" section."),
        ("Which number should I buy?", "The one HP lists for the region your printer was sold in. The model page and the source document linked there are the ones to check."),
        ("Does Canon, Epson, or Brother do the same thing?", "Not in the pages this site checked " + TODAY_H + ". Those pages print one number per model, not a region table. This pattern is specific to the HP document we cite below."),
    ]
    body = f'''<article class="prose"><h1>Why HP lists a different cartridge number outside the US</h1>
<p class="sub">By {BRAND} · Last verified {TODAY_H}</p>
<div class="answer"><p><strong>HP's own cartridge document lists more than one column for some models.</strong> The ink is the same color, but the part number HP prints changes by region.</p></div>
<p>HP's support document, {ext(HP_TITLE, HP_URL)}, groups some printer sections into regional columns, such as North America, Western Europe, and Latin America. The examples below are HP's own region columns for three HP DeskJet sections, not a guess.</p>
{"".join(blocks)}
<h2>What this means for you</h2><p>If you bought the printer in a different country than the one a cartridge listing assumes, the number on the box may not match a number copied from a US page. Open the model page on this site, read the main table for your number, and check the "Other regions on the same table" section there if one is present.</p>
{compare_box_html("Check another HP path", [
    'DeskJet 1200 Series (has a region table): <a href="/printers/hp/deskjet-1200/">open the hub</a>.',
    'HP 67 cartridge page: <a href="/cartridges/hp-67/">which printers use 67</a>.',
    'Find the model first: <a href="/guides/find-the-model-number/">model and cartridge numbers</a>.',
])}
{next_reads_html([
    ("/printers/hp/deskjet-1200/", "HP DeskJet 1200 Series", "A series that shows HP 67 in one column and other numbers abroad."),
    ("/guides/find-the-model-number/", "Find the model number", "Read the name on the printer before you buy ink."),
    ("/guides/ink-toner-or-bottle/", "Ink cartridge, toner, or bottle?", "Confirm the supply type before the part number."),
    ("/cartridges/hp-67/", "HP 67: which printers it fits", "Printers on the US column for family 67."),
], "Keep reading")}
{faq_html(faqs)}
{sources_html([(HP_TITLE, HP_URL)])}
{next_reads_html([
    ("/printers/hp/deskjet-1200/", "HP DeskJet 1200 Series", "A series that shows HP 67 in one column and other numbers abroad."),
    ("/guides/find-the-model-number/", "Find the model number", "Read the name on the printer before you buy ink."),
    ("/guides/ink-toner-or-bottle/", "Ink cartridge, toner, or bottle?", "Confirm the supply type before the part number."),
    ("/cartridges/hp-67/", "HP 67: which printers it fits", "Printers on the US column for family 67."),
])}
<p><a href="/printers/hp/">All HP models</a> · <a href="/printers/">All printers</a></p>
</article>'''
    write(path, page(path, title, desc, body, [article_ld(title, path, PUBLISHED_TODAY), faq_ld(faqs)], [("/", "Home"), (path, "HP numbers by region")], lastmod=PUBLISHED_TODAY))

def guide_xl_vs_standard():
    path = "/guides/xl-vs-standard-cartridges/"
    title = "XL vs standard ink: the published page yields"
    desc = "HP 67XL is about twice HP 67. Epson 212XL black is 500 pages against 150. Canon PG-243 has no XL size."
    hp67 = "https://www.hp.com/us-en/shop/pdp/hp-67-black-original-ink-cartridge"
    hp67xl = "https://www.hp.com/us-en/shop/pdp/hp-67xl-high-yield-black-original-ink-cartridge"
    hp67c = "https://www.hp.com/us-en/shop/pdp/hp-67-tri-color-original-ink-cartridge"
    hp67xlc = "https://www.hp.com/us-en/shop/pdp/hp-67xl-high-yield-tri-color-original-ink-cartridge"
    envy = "https://www.hp.com/us-en/shop/pdp/hp-envy-6055e-all-in-one-printer"
    epson = "https://epson.com/For-Work/Printers/Inkjet/Epson-WorkForce-WF-2830-All-in-One-Printer/p/C11CG30201"
    brother = "https://www.brother-usa.com/p/inkjet-printers/MFCJ4335DW"
    canon = "https://www.usa.canon.com/support/p/pixma-ts302a-wireless-inkjet-home-printer"
    measure = "https://www.usa.canon.com/printers/inkjet-page-yields/page-measure"
    faqs = [
        ("Does XL always mean twice the pages?", "No. On the HP 67 pages checked 21 Nov 2026, the XL is about twice the standard for black (about 240 against about 120) and for tri-color (about 200 against about 100). Epson's WF-2830 page prints 500 ISO pages for 212XL black against 150 for 212 black. Brother's color XL is 5,000 pages against 1,500. Canon does not print an XL of PG-243."),
        ("Is the higher yield a lower cost per page?", "Only if the price you pay for the larger cartridge is less than its yield multiple times the smaller one. Divide the price by the approximate yield. The maker pages opened 21 Nov 2026 did not print a cartridge shelf price this page will use. HP's US shop pages showed $0.00 beside an MSRP label and a $1.99 per month line. Neither is a price for one cartridge."),
        ("Were these yields measured in my printer?", "HP's 67 footnotes say the test printer was the ENVY 6000 All-in-One series. Epson's footnote says ISO/IEC 24711 in default mode, printing continuously. Brother says the LC406 counts are approximate and calculated to ISO/IEC 24711. Canon's TS302a cell prints 100 pages and does not name the test printer in that cell."),
    ]
    rows = [
        ("HP 67 black", "3YM56AN, about 120 pages", "3YM57AN, about 240 pages", "2 times", "ENVY 6000 series"),
        ("HP 67 tri-color", "3YM55AN, about 100 pages", "3YM58AN, about 200 pages", "2 times", "ENVY 6000 series"),
        ("Epson 212 black", "150 ISO pages", "212XL, 500 ISO pages", "3 and 1/3 times", "ISO/IEC 24711, default mode"),
        ("Epson 212 color", "130 ISO pages", "212XL, 350 ISO pages", "between 2 and 3 times", "ISO/IEC 24711, default mode"),
        ("Brother LC406 black", "LC406BK, 3,000 pages", "LC406XLBK, 6,000 pages", "2 times", "ISO/IEC 24711, approximate"),
        ("Brother LC406 color", "1,500 pages each", "5,000 pages each", "3 and 1/3 times", "ISO/IEC 24711, per cartridge"),
        ("Canon PG-243 black", "100 pages, no XL of this number", "PG-245 is 180; PG-245XL is 300", "different part numbers", "TS302a spec cell"),
        ("Canon CL-244 color", "100 pages, no XL of this number", "CL-246 is 180; CL-246XL is 300", "different part numbers", "TS302a spec cell"),
    ]
    tr = "".join(
        "<tr><td>" + E(a) + "</td><td>" + E(b) + "</td><td>" + E(c) + "</td><td>" + E(d) + "</td><td>" + E(e) + "</td></tr>"
        for a, b, c, d, e in rows
    )
    mid = with_thumbs([
        ("/cartridges/hp-67/", "HP 67: which printers it fits", "The family whose shop pages print about 120 and about 240 black pages."),
        ("/cartridges/epson-212/", "Epson 212 printers", "Four models grouped on Epson's part number table."),
        ("/cartridges/brother-lc406/", "Brother LC406 printers", "Where the 3,000 and 6,000 page footnotes are already spelled out."),
        ("/cartridges/canon-pg-243-cl-244/", "Canon PG-243 and CL-244", "100 pages each, and no XL of this number."),
    ])
    end = with_thumbs([
        ("/printers/hp/deskjet-2700/", "DeskJet 2700 series hub", "Twelve models that share 67 and 67XL, with the yield notes kept on the hub."),
        ("/cartridges/canon-pg-245-cl-246/", "Canon PG-245 and CL-246", "The larger Canon numbers, including an XL, from the same spec row."),
        ("/guides/find-the-model-number/", "Find the model number", "Read the name on the printer before you compare yields."),
        ("/guides/ink-toner-or-bottle/", "Ink cartridge, toner, or bottle?", "A toner XL and an ink XL are not the same kind of supply."),
    ])
    body = f'''<article class="prose"><h1>XL or standard: the page yields the makers actually print</h1>
<p class="sub">By {BRAND} · Last verified {CHECKED_1121_H}</p>
<div class="answer"><p><strong>XL is not one multiple.</strong> HP's 67XL is about twice the 67. Epson's 212XL black is 500 pages against 150. Brother's color XL is 5,000 against 1,500. Canon does not print an XL of PG-243 at all.</p></div>
{photo_figure()}
<p>The counts below are replacement yields, the kind of figure you use when the cartridge in the printer is empty and you buy another. They are not the "year of ink in the box" lines some printer pages also print. Each figure is tied to the page that prints it, opened {CHECKED_1121_H}. Where a page did not print a number, this guide does not fill one in.</p>
<div class="tablewrap"><table class="list"><thead><tr><th scope="col">Cartridge</th><th scope="col">Standard, as printed</th><th scope="col">Larger size, as printed</th><th scope="col">How many times</th><th scope="col">What the footnote names</th></tr></thead><tbody>{tr}</tbody></table></div>
<h2>HP 67: about twice, and the test printer is not a DeskJet</h2>
<p>HP's US shop page for <a href="{E(hp67)}" rel="nofollow noopener" target="_blank">67 black, 3YM56AN</a>, prints about 120 pages. The <a href="{E(hp67xl)}" rel="nofollow noopener" target="_blank">67XL black, 3YM57AN</a>, prints about 240. Tri-color is <a href="{E(hp67c)}" rel="nofollow noopener" target="_blank">3YM55AN at about 100</a> and <a href="{E(hp67xlc)}" rel="nofollow noopener" target="_blank">3YM58AN at about 200</a>. The 67XL tri-color page also says you can print up to two times as many pages with a high yield cartridge. The black pages say the high yield prints more pages than the standard. They do not repeat the words "two times," but 240 against 120 is twice, and 200 against 100 is twice.</p>
<p>Every one of those footnotes says the same thing about the test. It was the HP ENVY 6000 All-in-One Printer series. The average is based on ISO/IEC 24711 or HP's testing method, and on continuous printing. Actual yield varies considerably with the content of the pages. The "or" matters. HP is not saying the number is only the ISO test. Details are deferred to hp.com/go/learnaboutsupplies. That address redirected, on {CHECKED_1121_H}, to a page that did not itself print these four yields.</p>
<p>HP's <a href="{E(envy)}" rel="nofollow noopener" target="_blank">ENVY 6055e shop page</a> prints all four yields in one paragraph, with the same part numbers, and points at the same learn-about-supplies address. It does not say the 6055e was the unit in the test lab. The footnote on the cartridge pages names the ENVY 6000 series. Our <a href="/printers/hp/deskjet-2700/">DeskJet 2700 hub</a> uses this ink on twelve models. The yield was not measured in those DeskJets. The <a href="/cartridges/hp-67/">HP 67 page</a> is the list of printers.</p>
<h2>Epson 212: black stretches further than color</h2>
<p>Epson's <a href="{E(epson)}" rel="nofollow noopener" target="_blank">WorkForce WF-2830 page</a> prints one pair of ISO page counts. Standard 212 is black 150 and color 130. High capacity 212XL is black 500 and color 350. Footnote 6 says replacement cartridge yields are based on ISO/IEC 24711 tests in default mode, printing continuously. It also says yields vary with the images, the settings, temperature, and humidity, and that part of the ink from the included cartridges is used for printer startup. The page prints one color number, not a separate count for cyan, magenta, and yellow.</p>
<p>500 divided by 150 is 3 and 1/3. 350 sits between two times 130 (260) and three times 130 (390). So on Epson's own counts, the black XL is a larger jump than the color XL. The four printers we group on <a href="/cartridges/epson-212/">Epson 212</a> share these cartridge numbers. The yield line we are quoting is the WF-2830 page.</p>
<h2>Brother LC406: color is a bigger jump than black</h2>
<p>Brother's <a href="{E(brother)}" rel="nofollow noopener" target="_blank">MFC-J4335DW page</a> was marked Discontinued when opened {CHECKED_1121_H}. The replacement footnote was still there. It says all page yields are approximate and calculated to ISO/IEC 24711. LC406BK is 3,000 pages. Each LC406 cyan, magenta, and yellow cartridge is 1,500. LC406XLBK is 6,000. Each LC406XL color cartridge is 5,000. The feature line above that footnote says "up to" 3,000 black and 1,500 color, or "up to" 6,000 black and 5,000 color.</p>
<p>Black XL is twice the standard black. Color XL is 3 and 1/3 times the standard color, because 5,000 divided by 1,500 is 3 and 1/3. That is the reverse of the Epson pattern, where black was the bigger jump. Brother's color figure is per cartridge. Epson's color figure is one number for "color." The <a href="/cartridges/brother-lc406/">LC406 page</a> keeps the longer note on the in-box "year of ink" line, which is a different sum and is not repeated here.</p>
<h2>Canon PG-243: the larger cartridge is a different number</h2>
<p>Canon's <a href="{E(canon)}" rel="nofollow noopener" target="_blank">PIXMA TS302a support page</a> prints PG-243 black at 100 pages and CL-244 color at 100 pages, with fills of 5.6 ml and 6.2 ml. It does not print a PG-243XL or a CL-244XL. The next line is PG-245 and CL-246: 180 and 180 standard, 300 and 300 XL. Those are other part numbers. Our <a href="/cartridges/canon-pg-243-cl-244/">PG-243 page</a> says which of our printer links include them, and where the TS302a itself is not yet a model page.</p>
<p>The TS302a cell does not contain the word ISO. <a href="{E(measure)}" rel="nofollow noopener" target="_blank">Canon's measurement page</a> says the mixed text and graphics yield is declared to ISO/IEC 24711. This guide leaves that distinction in view instead of stamping ISO onto a cell that does not say it.</p>
{compare_box_html("Check another number", [
    '<a href="/cartridges/hp-67/">HP 67</a>: about 120 black pages, about 240 for the XL.',
    '<a href="/cartridges/epson-212/">Epson 212</a>: 150 black ISO pages, 500 for the XL.',
    '<a href="/cartridges/brother-lc406/">Brother LC406</a>: 3,000 black pages, 6,000 for the XL.',
    '<a href="/cartridges/canon-pg-243-cl-244/">Canon PG-243</a>: 100 pages, and no XL of this number.',
])}
{next_reads_html(mid, "Keep reading", "nr-mid")}
<h2>Cost per page, without a made-up price</h2>
<p>Cost per page is the price you pay, divided by the approximate yield in the table. On a clean double, the XL costs less per page only when its price is less than twice the standard cartridge. HP's black and tri-color 67 rows are that kind of double. Epson's black 212 row is 3 and 1/3, so the XL can cost up to 3 and 1/3 times the standard black and still match it per page. Brother's color row is the same 3 and 1/3. Canon's PG-245 at 180 pages is 1.8 times PG-243's 100, and it is not an XL of PG-243, so the prices are not prices of two sizes of one number.</p>
<p>None of that is a dollar figure, because the pages did not print one we can use. On {CHECKED_1121_H} the four HP 67 shop pages showed an MSRP label, a line reading $1.99 per month, and $0.00. A zero is not a shelf price. A monthly line is not the price of the cartridge in your hand. Brother's printer page shows a printer price, which is not an LC406 price. Epson's WF-2830 page prints yields and does not print a cartridge price. Dividing any of those by the yield would invent a cost. Bring the price on the box, or on the shelf, and divide it by the yield in the row that matches the number on that box.</p>
<p>Two further cautions, both from the footnotes rather than from us. The yields are approximate and were measured by continuous printing, so a printer that sits for weeks can use more ink on cleaning than these rows show. And a standard black beside an XL color is fine only where that maker says the printer accepts both. This guide does not add a permission the maker page does not print.</p>
{faq_html(faqs)}
{sources_html([
    ("HP 67 Black Original Ink Cartridge, 3YM56AN", hp67),
    ("HP 67XL High Yield Black Original Ink Cartridge, 3YM57AN", hp67xl),
    ("HP 67 Tri-color Original Ink Cartridge, 3YM55AN", hp67c),
    ("HP 67XL High Yield Tri-color Original Ink Cartridge, 3YM58AN", hp67xlc),
    ("HP ENVY 6055e shop page (prints the same four yields)", envy),
    ("Epson WorkForce WF-2830", epson),
    ("Brother MFC-J4335DW", brother),
    ("Canon Support for PIXMA TS302a", canon),
    ("How Page Yields Are Measured, Canon U.S.A.", measure),
], CHECKED_1121_H)}
{next_reads_html(end, "Related reading", "nr-end")}
<p><a href="/guides/">All guides</a> · <a href="/cartridges/">Cartridges</a> · <a href="/printers/">Printers</a> · <a href="/methodology/">Sources and methods</a></p>
</article>'''
    write(path, page(
        path, title, desc, body,
        [article_ld(title, path, CHECKED_1121), faq_ld(faqs)],
        [("/", "Home"), ("/guides/", "Guides"), (path, "XL vs standard")],
        lastmod=CHECKED_1121,
    ))

def guides_hub():
    path = "/guides/"
    title = "Ink and toner guides"
    desc = "How to read a model number, tell ink from toner, compare XL and standard yields, and see why HP numbers change by country."
    faqs = [
        ("Which guide should I open first?", "If the printer is in front of you, start with the model number guide, then open that model. If you already know the cartridge number and you are choosing a standard or an XL, open the yield guide."),
        ("Do the guides list third party ink?", "No. A number appears on this site only when HP, Canon, Epson, or Brother prints it. The guides quote those pages and do not add a compatible chart from a store."),
    ]
    cards = [
        ("/guides/find-the-model-number/", "Find the model number", "Where the name sits on the printer, and where the cartridge number sits on the box."),
        ("/guides/ink-toner-or-bottle/", "Ink, toner, or bottle?", "DeskJet and PIXMA cartridges, LaserJet and Brother toner, EcoTank and MegaTank bottles."),
        ("/guides/xl-vs-standard-cartridges/", "XL vs standard page yields", "The published page counts for HP 67, Epson 212, Brother LC406, and Canon PG-243."),
        ("/guides/hp-cartridge-numbers-by-region/", "HP numbers by country", "When the same DeskJet section prints 67 in one column and 305 or 805 in another."),
    ]
    items = "".join(
        '<li class="card"><h2><a href="' + h + '">' + E(n) + "</a></h2><p>" + E(b) + "</p></li>"
        for h, n, b in cards
    )
    body = f'''<article class="prose"><h1>Guides</h1>
<p class="sub">By {BRAND} · Last verified {CHECKED_1121_H}</p>
<div class="answer"><p>Four guides. Each one answers a different question, and each one links the manufacturer page it quotes.</p></div>
{photo_figure()}
<p>Use them in order. Read the name on the front of the printer, then open that model. If the box says 67 and 67XL, the yield guide has the page counts HP prints for those two sizes, and the <a href="/printers/hp/deskjet-2700/">DeskJet 2700 hub</a> is where those counts sit for the twelve models that share them. If the number on the cartridge does not match a US listing, the region guide shows the other columns HP prints. If the supply is a bottle or a toner, the ink-or-toner guide says so before you land on a cartridge page.</p>
<ul class="cards">{items}</ul>
{compare_box_html("Not sure which to open", [
    'The name is on the printer: <a href="/guides/find-the-model-number/">find the model number</a>.',
    'You are not sure it is ink: <a href="/guides/ink-toner-or-bottle/">ink, toner, or bottle</a>.',
    'You are choosing a size: <a href="/guides/xl-vs-standard-cartridges/">XL and standard yields</a>.',
    'The number looks wrong for your country: <a href="/guides/hp-cartridge-numbers-by-region/">HP numbers by region</a>.',
])}
{faq_html(faqs)}
<p><a href="/printers/">Printers</a> · <a href="/cartridges/">Cartridges</a> · <a href="/methodology/">Sources and methods</a></p>
</article>'''
    write(path, page(
        path, title, desc, body,
        [article_ld(title, path, CHECKED_1121), faq_ld(faqs)],
        [("/", "Home"), (path, "Guides")],
        lastmod=CHECKED_1121,
    ))

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
        ("Which page should I open?", "If the printer name is in front of you, open that model. If you have the number on the cartridge, toner, or bottle, open that cartridge page. Both lists come from the manufacturer pages, checked " + TODAY_H + "."),
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
<h2>How to read the numbers</h2><p>The model number is on the printer. The cartridge, toner, or bottle number is on the box. <a href="/guides/find-the-model-number/">How to find both</a>. Not sure which supply type your printer takes? <a href="/guides/ink-toner-or-bottle/">Ink cartridge, toner, or bottle?</a> A high yield pack is not a different color. <a href="/guides/xl-vs-standard-cartridges/">XL and standard page yields</a> puts the published counts side by side. Numbers change by country. <a href="/guides/hp-cartridge-numbers-by-region/">Why some HP numbers differ by country</a>. <a href="/guides/">All guides</a>. <a href="/methodology/">How we check a page</a>.</p>
{faq_html(faqs)}'''
    write("/", page("/", "Which Ink Fits: printer ink and toner by model", "Which cartridge, toner, or ink bottle fits your HP, Canon, Epson, or Brother printer, from the manufacturer lists.", body, [faq_ld(faqs)], lastmod=CHECKED_1121))

def simple(path, title, desc, h1, inner, crumb=None, legal=False, lastmod=None, published=None):
    body = '<article class="prose"><h1>' + E(h1) + "</h1>" + inner + "</article>"
    ld = [article_ld(h1, path, published, modified=lastmod)] if published else None
    write(path, page(path, title, desc, body, ld, [("/", "Home"), (path, crumb or h1)], legal=legal, lastmod=lastmod))

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
<h2>Yields and prices</h2><p>Checked {CHECKED_1121_H}. A yield guide quotes the cartridge specification that prints the page count. It does not turn a monthly plan, a printer price, or a $0.00 display into a cost per page. If two maker pages disagree, the guide says so and does not pick a winner.</p>
<h2>Dates</h2><p>The date on a page is the day we checked the source, not a refreshed stamp. We change it when the numbers change.</p>''', lastmod=CHECKED_1121, published=TODAY)
    simple("/image-policy/", "Image policy | " + BRAND, "How Which Ink Fits handles images, logos, and diagrams.", "Image policy", f'''
<p>Last updated {CHECKED_1121_H}.</p>
<p>The mark in the header is our own drawing of an ink drop, and that image links to this page. We do not display HP, Canon, Epson, or Brother logos, and we do not use their product photos.</p>
<p>When a guide or a printer hub shows a photo, that photo is AI-generated. The caption says so, and the image links to this page. It is a plain news-style picture. It does not show a real person, a brand logo, or readable text.</p>
<p>Questions: <a href="/contact/">contact</a> or the <a href="/copyright/">copyright page</a>.</p>''', lastmod=CHECKED_1121, published=TODAY)
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
        "/privacy/": ("Privacy", f'''<p>Last updated {PUBLISHED_TODAY_H}. Which Ink Fits (whichinkfits.com) is a trade name of Joshua Israel Ventures LLC, a Florida limited liability company.</p>
<h2>Analytics</h2><p>The launch build uses Cloudflare Web Analytics and Google Analytics 4.</p><p>Cloudflare Web Analytics is on every launch page and counts page views. That product does not use cookies and does not track you across other sites.</p><p>Google Analytics 4 loads only after you accept the banner. Before that choice, Consent Mode v2 leaves analytics storage and ad storage denied, and the GA4 script is not requested. Accepting turns on analytics storage only. Ad storage stays denied. The launch build puts Cookie settings in the footer so you can accept or reject later. Rejecting keeps Google Analytics 4 unloaded.</p>
<h2>Email</h2><p>If you email joshuaofisrael@gmail.com, we use your address and message to reply, and we keep them only as long as we need to.</p>
<h2>Advertising</h2><p>Which Ink Fits includes Google AdSense account tags (publisher {ADSENSE_CLIENT}) so the site can show ads. There are no affiliate links. Consent Mode keeps ad storage denied unless you later accept advertising cookies. When ads appear, they will be labeled. You can opt out of personalized ads at Google's ad settings and at aboutads.info. See the <a href="/ad-disclosure/">advertising disclosure</a> and our <a href="/ads.txt">ads.txt</a> file.</p>
<h2>Google advertising cookies and your choices</h2><p>Third-party vendors, including Google, use cookies to serve ads based on a user's prior visits to this website or other websites. Google's use of advertising cookies enables it and its partners to serve ads based on your visit to this site and/or other sites on the Internet. You may opt out of personalized advertising by visiting <a href="https://adssettings.google.com/" rel="nofollow noopener">Google Ads Settings</a>. Alternatively, you can opt out of a third-party vendor's use of cookies for personalized advertising at <a href="https://www.aboutads.info/choices/" rel="nofollow noopener">aboutads.info/choices</a>. For more information, see <a href="https://policies.google.com/technologies/partner-sites" rel="nofollow noopener">how Google uses information from sites or apps that use its services</a>.</p>
<h2>Hosting</h2><p>The site is hosted on GitHub Pages, which may log IP addresses for security.</p>
<h2>Children</h2><p>The site is a general audience site. We do not knowingly collect information from children under 13.</p>'''),
        "/disclaimer/": ("Disclaimer", f'''<p>Last updated {D}.</p>
<h2>Not the manufacturer</h2><p>Which Ink Fits is an independent site. It is not affiliated with, endorsed by, or sponsored by HP, Canon, Epson, or Brother. Names identify the products. They do not imply a relationship.</p>
<h2>Confirm before you buy</h2><p>Cartridge numbers differ by country and can change. The manufacturer page and the label on your printer come first. A blank yield means the source we used did not print a page yield.</p>
<h2>No recommendation on other ink</h2><p>We quote what the manufacturer says about its own supplies. We do not tell you to buy or avoid third party ink or toner.</p>'''),
        "/copyright/": ("Copyright and DMCA", f'''<p>Last updated {D}. Original text and design on Which Ink Fits are owned by Joshua Israel Ventures LLC. Facts are cited to the manufacturer pages. See the <a href="/image-policy/">image policy</a>.</p>
<h2>Notice</h2><p>If you believe material on this site infringes a copyright you own, email <a href="mailto:joshuaofisrael@gmail.com">joshuaofisrael@gmail.com</a> with your name, a description of the work, the page address, a statement that you have a good faith belief the use is not authorized, a statement under penalty of perjury that the notice is accurate and that you are the owner or authorized to act for the owner, and your signature. We review notices and remove material where that is the right step.</p>
<h2>Counter notice</h2><p>If we removed something you sent and you believe that was a mistake, you may send a counter notice with the details required by 17 U.S.C. section 512(g).</p>'''),
        "/ad-disclosure/": ("Advertising disclosure", f'''<p>Last updated {PUBLISHED_TODAY_H}. Which Ink Fits is free to use and has no affiliate links. The site includes Google AdSense account tags (publisher {ADSENSE_CLIENT}) so ads can appear. Ad units are not placed yet. When ads or sponsored links appear, they will be labeled. A manufacturer cannot change a cartridge list by paying us.</p>
<p>Questions: <a href="/contact/">contact</a>.</p>'''),
    }
    for pth, (h1, inner) in legal.items():
        body = '<article class="prose"><h1>' + E(h1) + "</h1>" + inner + '<p class="legal-line">' + LEGAL_LINE + "</p></article>"
        desc = "How Which Ink Fits uses Google Analytics 4, Cloudflare Web Analytics, and AdSense." if pth == "/privacy/" else h1 + " for Which Ink Fits."
        lm = PUBLISHED_TODAY if pth in ("/privacy/", "/ad-disclosure/") else None
        write(pth, page(pth, h1 + " | " + BRAND, desc, body, None, [("/", "Home"), (pth, h1)], legal=True, lastmod=lm))

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
    rows.append({"n": "XL vs standard page yields", "u": "/guides/xl-vs-standard-cartridges/", "t": "Guide", "k": "xlvsstandardinkcartridgepageyieldcostperpage"})
    rows.append({"n": "Guides", "u": "/guides/", "t": "Guide", "k": "guidesyieldmodelnumbertoner"})
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
    open(os.path.join(ROOT, "ads.txt"), "w").write("google.com, pub-5681559774142917, DIRECT, f08c47fec0942fa0\n")
    bots = ["*", "Googlebot", "Bingbot", "Mediapartners-Google", "OAI-SearchBot", "ChatGPT-User", "GPTBot", "PerplexityBot", "Perplexity-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "Google-Extended", "Applebot", "Applebot-Extended", "DuckAssistBot", "Amazonbot", "CCBot", "Bytespider"]
    open(os.path.join(ROOT, "robots.txt"), "w").write("".join("User-agent: " + b + "\nAllow: /\n\n" for b in bots) + "Sitemap: " + BASE + "sitemap.xml\n")
    open(os.path.join(ROOT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join("<url><loc>" + url(p) + "</loc><lastmod>" + m + "</lastmod></url>\n" for p, m in PAGES) + "</urlset>\n")
    lines = ["# " + BRAND, "", "> Which Ink Fits (whichinkfits.com) lists the ink, toner, and bottle numbers HP, Canon, Epson, and Brother publish for a printer model, and the printers a number fits. Checked " + TODAY_H + ".", "", "Independent. Not affiliated with any printer maker. Confirm the number on the manufacturer page.", "", "## Guides", f"- [Guides]({url('/guides/')})", f"- [Find the model number]({url('/guides/find-the-model-number/')})", f"- [Ink cartridge, toner, or bottle?]({url('/guides/ink-toner-or-bottle/')})", f"- [XL vs standard page yields]({url('/guides/xl-vs-standard-cartridges/')})", f"- [Why HP cartridge numbers differ outside the US]({url('/guides/hp-cartridge-numbers-by-region/')})", f"- [Sources and methods]({url('/methodology/')})", "", "## Printers"]
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
    FAMS = fams
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
    guide_ink_toner_bottle()
    guide_hp_region()
    guides_hub()
    guide_xl_vs_standard()
    home(printers, fams)
    legal_pages()
    not_found()
    search_index(printers, series, fams)
    extras(printers, series, fams)
    print(len(PAGES), "sitemap urls", len(printers), "printers", len(fams), "cartridge pages", "LAUNCH" if LAUNCH else "NOINDEX")
