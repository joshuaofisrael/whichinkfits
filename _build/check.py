#!/usr/bin/env python3
"""QA for Which Ink Fits. Exit 0 when nothing is wrong.

  python3 _build/check.py           # expects noindex on every page
  python3 _build/check.py --launch  # index,follow except 404, beacon, and GA4

--launch fails when GA4_ID in _build/build.py is empty, and when any page
lacks the Cloudflare beacon or the GA4 loader.
"""
import glob, html, json, os, re, sys

# Paths in _build/thin-noindex.txt are intentionally noindex (AdSense low-value-content fix, 20 Nov 2026).
import os as _os
_THIN = set()
try:
    with open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "thin-noindex.txt"), encoding="utf-8") as _fh:
        _THIN = {l.strip().strip("/") for l in _fh if l.strip() and not l.startswith("#")}
except FileNotFoundError:
    pass


def _thin_rel(rel):
    r = str(rel).replace("\\", "/")
    if r.endswith("index.html"):
        r = r[: -len("index.html")]
    return r.strip("/") in _THIN


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCH = "--launch" in sys.argv
LEGAL = {"terms", "privacy", "disclaimer", "copyright", "ad-disclosure"}
INFO = {"about", "methodology", "image-policy", "contact", "terms", "privacy", "disclaimer", "copyright", "ad-disclosure"}
FOOT = [("/about/", "About"), ("/contact/", "Contact"), ("/privacy/", "Privacy"), ("/terms/", "Terms"),
        ("/disclaimer/", "Disclaimer"), ("/copyright/", "Copyright"), ("/ad-disclosure/", "Advertising"),
        ("/image-policy/", "Image policy")]

def const(name):
    text = open(os.path.join(ROOT, "_build", "build.py"), encoding="utf-8").read()
    m = re.search(r"(?m)^" + re.escape(name) + r'\s*=\s*"([^"]*)"', text)
    return m.group(1) if m else None

GA4_ID = const("GA4_ID")
BEACON = const("CF_BEACON_TOKEN")
bad = 0
if LAUNCH and not (GA4_ID and re.fullmatch(r"G-[A-Za-z0-9]+", GA4_ID)):
    print("ga4-id-empty")
    bad += 1
titles = {}
files = [f for f in glob.glob(ROOT + "/**/*.html", recursive=True) if "/_build/" not in f]
for f in files:
    h = open(f, encoding="utf-8").read()
    rel = os.path.relpath(f, ROOT)
    top = rel.split("/")[0]
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h):
        try:
            json.loads(m)
        except Exception as e:
            print("JSONLD", rel, e)
            bad += 1
    vis = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    if top not in LEGAL and re.search(r"Joshua|Israel Ventures|©", vis):
        print("LLC", rel)
        bad += 1
    if top in LEGAL and "is a trade name of Joshua Israel Ventures LLC" not in h:
        print("nolegalline", rel)
        bad += 1
    if not re.search(r'<link rel="canonical" href="https://whichinkfits.com/', h):
        print("canonical", rel)
        bad += 1
    if "github.io" in h:
        print("github.io", rel)
        bad += 1
    if h.count("<h1") != 1:
        print("h1", rel, h.count("<h1"))
        bad += 1
    desc = re.search(r'<meta name="description" content="(.*?)"', h)
    if not desc:
        print("nodesc", rel)
        bad += 1
    elif len(html.unescape(desc.group(1))) > 155:
        print("longdesc", len(html.unescape(desc.group(1))), rel)
        bad += 1
    if LAUNCH:
        if "static.cloudflareinsights.com/beacon.min.js" not in h or (BEACON and BEACON not in h):
            print("nobeacon", rel)
            bad += 1
        if "https://www.googletagmanager.com/gtag/js?id=" not in h or 'id="ga4-loader"' not in h:
            print("noga4", rel)
            bad += 1
        elif GA4_ID and ("gtag/js?id=" + GA4_ID) not in h:
            print("noga4", rel)
            bad += 1
        if "gtag('consent', 'default'" not in h or "'analytics_storage': 'denied'" not in h:
            print("noconsent", rel)
            bad += 1
        if 'id="cookie-settings"' not in h or "Cookie settings" not in h:
            print("nocookie", rel)
            bad += 1
        if "noindex" in h and rel != "404.html" and not _thin_rel(rel):
            print("noindex", rel)
            bad += 1
    elif "noindex" not in h:
        print("preview-missing-noindex", rel)
        bad += 1
    if "—" in h or "–" in h:
        print("dash", rel)
        bad += 1
    if re.search(r"amazon\.com|amzn\.to|[?&]tag=|ascsubtag", h, re.I):
        print("affiliate", rel)
        bad += 1
    t = html.unescape(re.search(r"<title>(.*?)</title>", h).group(1))
    if not t or len(t) > 59:
        print("longtitle", len(t), rel)
        bad += 1
    titles.setdefault(t, []).append(rel)
    imgs = re.findall(r"<img\b", h)
    linked = re.findall(r'<a[^>]*href="/image-policy/"[^>]*>\s*<img\b', h)
    if len(imgs) != len(linked):
        print("img-policy", rel)
        bad += 1
    for href, _label in FOOT:
        if 'href="' + href + '"' not in h:
            print("footer", rel, href)
            bad += 1
    if re.search(r'<a [^>]*href="https://whichinkfits.com', h):
        print("abs-internal", rel)
        bad += 1
    top = rel.split("/")[0]
    if rel == "index.html":
        for needle in ('"WebSite"', '"FAQPage"'):
            if needle not in h:
                print("schema", rel, needle)
                bad += 1
    elif rel != "404.html" and top in ("printers", "cartridges", "guides"):
        for needle in ('"Article"', '"FAQPage"', '"BreadcrumbList"'):
            if needle not in h:
                print("schema", rel, needle)
                bad += 1
    elif top in INFO:
        for needle in ('"Article"', '"BreadcrumbList"'):
            if needle not in h:
                print("schema", rel, needle)
                bad += 1
    if rel not in ("404.html",) and top in ("printers", "cartridges", "guides") and rel.count("/") >= (3 if top == "printers" else 2):
        sec = re.search(r'<section class="sources".*?</section>', h, re.S)
        if not sec or "http" not in sec.group(0):
            print("nosource", rel)
            bad += 1
    for link in re.findall(r'(?:href|src)="(/[^"#?]*)', h):
        p = os.path.join(ROOT, link.lstrip("/"))
        if not (os.path.isfile(p) or os.path.isfile(os.path.join(p, "index.html"))):
            print("broken", rel, link)
            bad += 1
for t, fs in titles.items():
    if len(fs) > 1:
        print("duptitle", t, fs[:4])
        bad += 1
if open(os.path.join(ROOT, "CNAME"), encoding="utf-8").read().strip() != "whichinkfits.com":
    print("CNAME")
    bad += 1
robots = open(os.path.join(ROOT, "robots.txt"), encoding="utf-8").read()
for bot in ["Googlebot", "Bingbot", "GPTBot", "ClaudeBot", "PerplexityBot", "OAI-SearchBot", "CCBot", "Google-Extended", "Applebot-Extended", "Bytespider"]:
    if "User-agent: " + bot + "\nAllow: /" not in robots:
        print("robots-missing", bot)
        bad += 1
if "Sitemap: https://whichinkfits.com/sitemap.xml" not in robots:
    print("robots-sitemap")
    bad += 1
sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
if "404" in sm or "noindex" in sm:
    print("sitemap-404")
    bad += 1
blocks = re.findall(r"<url>(.*?)</url>", sm, re.S)
if not blocks or any("<loc>" not in b or "<lastmod>" not in b for b in blocks):
    print("sitemap-lastmod")
    bad += 1
home = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
if "FAQPage" not in home or 'id="q"' not in home or "search-index.js" not in home:
    print("home-search-or-faq")
    bad += 1
contact = open(os.path.join(ROOT, "contact", "index.html"), encoding="utf-8").read()
if "mailto:joshuaofisrael@gmail.com" not in contact:
    print("contact-email")
    bad += 1
llms = open(os.path.join(ROOT, "llms.txt"), encoding="utf-8").read()
if "/printers/hp/officejet-pro-9015/" not in llms or "/cartridges/hp-67/" not in llms:
    print("llms")
    bad += 1
key = const("INDEXNOW_KEY")
key_path = os.path.join(ROOT, (key or "missing") + ".txt")
if not key or not os.path.isfile(key_path) or open(key_path, encoding="utf-8").read().strip() != key:
    print("indexnow")
    bad += 1
privacy = open(os.path.join(ROOT, "privacy", "index.html"), encoding="utf-8").read()
if "Google Analytics 4" not in privacy or "Cloudflare Web Analytics" not in privacy:
    print("privacy-analytics")
    bad += 1
print("files", len(files), "issues", bad)
sys.exit(1 if bad else 0)
