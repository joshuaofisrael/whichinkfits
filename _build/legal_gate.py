#!/usr/bin/env python3
"""Pre-publish legal hold gate for Which Ink Fits. Exit 0 passes. Exit 3 holds.

  python3 _build/legal_gate.py check --no-queue
"""
import datetime, glob, hashlib, html, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "whichinkfits.com"
BOT = "Which Ink Fits build"
CR = os.environ.get("CONTENT_REVIEW_DIR", "/workspace/content-review")
Q = CR + "/queue.jsonl"
DR = CR + "/drafts/whichinkfits"
HIGH = {1, 2, 6, 8}
OBJECTIVE = {3, 4}
LEGAL = ("privacy", "terms", "contact", "disclaimer", "copyright", "ad-disclosure", "about", "image-policy", "methodology")
KW = {
    1: r"\b(fraud\w*|scam\w*|corrupt(ion|ly)?|embezzl\w*|arrested|indicted|charged with|convicted|lawsuits?|sued|suing|misconduct|abus(e|ed|ive)|dishonest\w*|cover[ -]?up|criminal|bribe\w*|negligen\w*|cheat(s|ed|ing)?|rip[ -]?off)\b",
    5: r"\b(guaranteed returns?|tax advice|legal advice|medical advice|you should (sue|claim compensation)|take \d+ ?mg)\b",
    6: r"\b(election|ballot|polling (place|station)|voter registration|vote by|voting day|certified results?|electoral)\b",
    7: r"\b(official partner|endorsed by|in partnership with|certified by|approved by the|100% (safe|accurate)|guaranteed (best|quiet|fit))\b",
    8: r"\b(embargo(ed)?|cease and desist|dmca|takedown notice|legal notice|reporting restriction|correction request)\b",
}

def visible(raw):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()

def scan(raw, rel):
    text = visible(raw)
    top = rel.split("/")[0]
    legal = top in LEGAL
    R = []
    for n, rx in KW.items():
        for m in re.finditer(rx, text, re.I):
            if n == 8 and m.group(0).lower() == "dmca" and (top == "copyright" or text[max(0, m.start() - 14):m.end()] == "Copyright and DMCA"):
                continue
            if n in (5, 7) and re.search(r"\b(not|never|no|nor|isn'?t|aren'?t|without)\b[^.]{0,40}$", text[max(0, m.start() - 55):m.start()], re.I):
                continue
            R.append((n, m.group(0), "keyword tripwire"))
            break
    if not legal:
        m = re.search(r"[\w.+-]+@[\w-]+\.[a-z][\w.]+", text)
        if m:
            R.append((2, m.group(0), "email address"))
        m = re.search(r"(?<![\w/.:,-])(\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w-])", text)
        if m:
            R.append((2, m.group(0).strip(), "possible phone number"))
    for u in re.findall(r"""<(?:img|source|video)[^>]+src=["'](https?://[^"']+)""", raw, re.I):
        R.append((3, u, "remote image"))
        break
    deep = (rel.startswith("printers/") and rel.count("/") >= 3) or (rel.startswith("cartridges/") and rel.count("/") >= 2) or (rel.startswith("guides/") and rel.count("/") >= 2)
    if deep:
        sec = re.search(r'<section class="sources".*?</section>', raw, re.S)
        if not sec or not re.search(r'href="https?://', sec.group(0)):
            R.append((4, "(no source URLs)", "page cites no source"))
    return text, R

def sev(R):
    return "HIGH" if any(n in HIGH for n, _, _ in R) else ("MODERATE" if R else None)

def main(a):
    if not a or a[0] != "check":
        print(__doc__)
        return 2
    noq = "--no-queue" in a
    bad = n = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True)):
        if "/_build/" in f:
            continue
        rel = os.path.relpath(f, ROOT)
        raw = open(f, encoding="utf-8").read()
        text, R = scan(raw, rel)
        hsh = hashlib.sha256(text.encode()).hexdigest()
        n += 1
        if R:
            bad += 1
            print("HOLD_REVIEW", sev(R), rel)
            for r, x, s in R:
                print("  rule", r, x, s)
            if not noq:
                os.makedirs(DR, exist_ok=True)
                open(os.path.join(DR, rel.replace("/", "__") + ".HOLD_REVIEW.html"), "w", encoding="utf-8").write(raw)
                os.makedirs(CR, exist_ok=True)
                open(Q, "a", encoding="utf-8").write(json.dumps({
                    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                    "site": SITE, "bot": BOT, "sha256": hsh, "path": rel,
                    "flagged": "; ".join(f"[{r}] {x}" for r, x, _ in R),
                }) + "\n")
    print("pages", n, "held", bad)
    return 3 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
