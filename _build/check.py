#!/usr/bin/env python3
"""QA for Which Ink Fits. Exit 0 when nothing is wrong.

  python3 _build/check.py           # expects noindex on every page
  python3 _build/check.py --launch  # expects index,follow except 404, and the beacon
"""
import glob, html, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCH = "--launch" in sys.argv
LEGAL = {"terms", "privacy", "disclaimer", "copyright", "ad-disclosure"}
bad = 0
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
        if "static.cloudflareinsights.com/beacon.min.js" not in h:
            print("nobeacon", rel)
            bad += 1
        if "noindex" in h and rel != "404.html":
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
    t = re.search(r"<title>(.*?)</title>", h).group(1)
    titles.setdefault(t, []).append(rel)
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
    if bot not in robots:
        print("robots-missing", bot)
        bad += 1
if "Sitemap: https://whichinkfits.com/sitemap.xml" not in robots:
    print("robots-sitemap")
    bad += 1
sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
if "404" in sm or "noindex" in sm:
    print("sitemap-404")
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
print("files", len(files), "issues", bad)
sys.exit(1 if bad else 0)
