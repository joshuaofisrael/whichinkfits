#!/usr/bin/env python3
"""Turn HP's published cartridge table into structured facts.

Source retrieved 16 Nov 2026:
https://support.hp.com/us-en/document/ish_2405837-1980674-16
"Which cartridges work with my HP printer?"

Only the first column of each region table is expanded into supply rows.
Other columns are kept as HP wrote them. Sections whose first column is not
an Americas / United States heading are skipped. Cells that say "or" or list
a universal slash group are skipped so nothing is guessed.
"""
import json, os, re, sys

SRC = sys.argv[1]
OUT = sys.argv[2]
text = open(SRC, encoding="utf-8").read()
# Drop the intro before the first series heading.
start = text.find("\nHP AMP printers\n")
text = text[start + 1:]
lines = text.splitlines()

COLOR = r"(?:Tri-color|Tri-colour|Gray Photo|Black|Cyan|Magenta|Yellow|Photo|Gray)"
NA_RX = re.compile(r"North America|United States|USA|Americas|The Americas", re.I)
SKIP_CELL = re.compile(r"\bor\b|Universal|/", re.I)

def clean_sentence(s):
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_models(sentence):
    m = re.search(r"information for (.+)$", sentence, re.I)
    if not m:
        return []
    body = m.group(1).strip().rstrip(".")
    body = re.sub(r"^(the|for)\s+", "", body, flags=re.I)
    body = re.sub(r"\s+", " ", body)
    # Trailing class words are not model names.
    body = re.sub(r"\b(e-All-in-One|All-in-One|Wide Format|Multifunction|printer series|Printer series|printers|printer|series)\b", " ", body, flags=re.I)
    body = body.replace(" and ", ", ")
    body = re.sub(r"\s+", " ", body).strip(" ,.")
    parts = [p.strip(" .") for p in body.split(",") if p.strip(" .")]
    models, prefix = [], ""
    for p in parts:
        p = re.sub(r"\s*-\s*[A-Z]\d{3,4}[a-z]{0,3}\b", "", p).strip()
        # A trailing single letter code (J510a) is a variant of a numbered model
        # already named in the sentence, not its own printer. J4580 style codes,
        # which are the model, are kept.
        if re.fullmatch(r"[A-Z]\d{3,4}[a-z]{1,2}", p or "") and any(re.search(r"\d", m) and not re.search(r"\b[A-Z]\d{3,4}\b", m.split()[-1]) for m in models):
            continue
        if not p or not re.search(r"\d", p):
            continue
        if re.match(r"(HP\b|DeskJet|ENVY|OfficeJet|LaserJet|Ink Tank|AMP)\b", p):
            full = p if p.startswith("HP ") or p.startswith("HP") else "HP " + p
            full = re.sub(r"\s+", " ", full).strip()
            models.append(full)
            pref = []
            for t in full.split():
                if re.search(r"\d", t):
                    break
                pref.append(t)
            prefix = " ".join(pref)
        elif prefix:
            models.append((prefix + " " + p).strip())
    # De-dupe, keep order.
    out, seen = [], set()
    for name in models:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out

def expand_cell(cell):
    """Return list of {sku, capacity, color} or None if the cell is ambiguous."""
    raw = re.sub(r"\s+", " ", cell).strip()
    raw = re.sub(r"\bHP\s+", "", raw)
    if not raw or SKIP_CELL.search(raw):
        return None
    rows = []
    # Walk "numbers color" pairs. Numbers may be "67 and 67XL" or "68e" or "950XL Z10".
    pat = re.compile(rf"((?:\d{{2,4}}(?:e|A|X)?(?:XL|XXL)?(?:\s+Z\d+)?(?:\s+and\s+)?)+)\s+({COLOR})", re.I)
    pos = 0
    for m in pat.finditer(raw):
        if m.start() != pos and raw[pos:m.start()].strip(" ,;"):
            return None  # leftover text, do not guess
        nums = m.group(1)
        color = m.group(2)
        color = {"Tri-colour": "Tri-color"}.get(color, color)
        bits = re.split(r"\s+and\s+", nums.strip(), flags=re.I)
        for b in bits:
            b = re.sub(r"\s+", " ", b).strip()
            if not b:
                return None
            mm = re.match(r"(\d{2,4})(e|A|X)?(XL|XXL)?(?:\s+(Z\d+))?$", b, re.I)
            if not mm:
                return None
            base, extra, cap, z = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
            capacity = "standard"
            if cap and cap.upper() == "XL":
                capacity = "high yield"
            elif cap and cap.upper() == "XXL":
                capacity = "extra high yield"
            sku = base + (extra or "") + (cap.upper() if cap else "")
            if z:
                sku += " " + z.upper()
            rows.append({"sku": sku, "base": base, "capacity": capacity, "color": color, "extra": (extra or "")})
        pos = m.end()
    if pos == 0:
        # No color named. Accept a bare "64 and 64XL" only.
        bare = re.fullmatch(r"(\d{2,4}(?:XL|XXL)?(?:\s+and\s+\d{2,4}(?:XL|XXL)?)+|\d{2,4}(?:XL|XXL)?)", raw, re.I)
        if not bare:
            return None
        for b in re.split(r"\s+and\s+", raw, flags=re.I):
            mm = re.match(r"(\d{2,4})(XL|XXL)?$", b.strip(), re.I)
            if not mm:
                return None
            cap = mm.group(2)
            capacity = "high yield" if cap and cap.upper() == "XL" else ("extra high yield" if cap and cap.upper() == "XXL" else "standard")
            sku = mm.group(1) + (cap.upper() if cap else "")
            rows.append({"sku": sku, "base": mm.group(1), "capacity": capacity, "color": "", "extra": ""})
        return rows
    if raw[pos:].strip(" ,;"):
        return None
    return rows

# Split into heading blocks. A heading is a line "HP ...." not starting with a space, not a table caption.
blocks = []
cur = None
for i, line in enumerate(lines):
    if re.match(r"HP [A-Z]", line) and not line.endswith("cartridge numbers") and "cartridge numbers" not in line and not line.startswith(" "):
        if cur:
            blocks.append(cur)
        cur = {"title": line.strip(), "lines": []}
    elif cur is not None:
        cur["lines"].append(line)
if cur:
    blocks.append(cur)

sections = []
skipped = []
for b in blocks:
    title = b["title"]
    if title.startswith("HP DesignJet") or "LaserJet" in title:
        skipped.append((title, "out of scope for this extract"))
        continue
    blob = b["lines"]
    info = ""
    for ln in blob:
        if ln.startswith("Ink cartridge information") or ln.startswith("Ink information"):
            info = clean_sentence(ln)
            break
    if not info:
        skipped.append((title, "no model sentence"))
        continue
    # Find a markdown table.
    headers, cells = [], []
    for j, ln in enumerate(blob):
        if ln.startswith("| ") and "---" not in ln and not headers:
            # header row
            headers = [c.strip() for c in ln.strip("|").split("|")]
            # data is the next non-separator row
            for ln2 in blob[j + 1:]:
                if ln2.startswith("|") and "---" not in ln2:
                    cells = [c.strip() for c in ln2.strip("|").split("|")]
                    break
            break
    bullets = [re.sub(r"\s+", " ", ln[2:]).strip() for ln in blob if ln.startswith("- ")]
    models = parse_models(info)
    retired = ""
    for ln in blob:
        if "no longer offers" in ln.lower():
            retired = clean_sentence(ln)
            break
    title_num = re.search(r"\d{3,4}", title)
    # HP's ENVY 110 heading is followed by a sentence that names ENVY 100.
    # Only that shape (one parsed model, and the heading number is not in it)
    # uses the heading. Longer model lists are kept as HP wrote them.
    if title_num and len(models) == 1 and title_num.group(0) not in models[0]:
        models = [re.sub(r"\s+(All-in-One|e-All-in-One).*$", "", title).strip()]
        heading_override = True
    else:
        heading_override = False
    if headers and cells and len(headers) == len(cells):
        if not NA_RX.search(headers[0]):
            skipped.append((title, "first column is not an Americas heading: " + headers[0][:80]))
            continue
        supplies = expand_cell(cells[0])
        if not supplies:
            skipped.append((title, "could not parse first cell: " + cells[0][:120]))
            continue
        regions = [{"region": h, "text": c} for h, c in zip(headers, cells)]
        kind = "table"
    elif bullets:
        joined = " ".join(bullets)
        supplies = expand_cell(joined.replace("HP ", ""))
        if not supplies:
            # try each bullet
            supplies = []
            ok = True
            for bu in bullets:
                part = expand_cell(re.sub(r"^HP\s+", "", bu))
                if not part:
                    ok = False
                    break
                supplies.extend(part)
            if not ok:
                skipped.append((title, "could not parse bullets: " + joined[:120]))
                continue
        regions = [{"region": "HP listed these as bullets, with no region table in this section", "text": joined}]
        kind = "bullets"
    else:
        skipped.append((title, "no table or bullets"))
        continue
    if not models:
        # The heading itself is the series name HP published.
        models = [title.rstrip(".")]
        series_only = True
    else:
        series_only = False
    sections.append({
        "title": title,
        "info": info,
        "models": models,
        "series_only": series_only,
        "kind": kind,
        "supplies": supplies,
        "regions": regions,
        "retired_note": retired,
        "heading_override": heading_override,
    })

catalog = {
    "source_url": "https://support.hp.com/us-en/document/ish_2405837-1980674-16",
    "source_title": "Which cartridges work with my HP printer?",
    "publisher": "HP",
    "retrieved": "2026-11-16",
    "sections": sections,
}
json.dump(catalog, open(OUT, "w"), indent=2, ensure_ascii=False)
print("sections", len(sections), "models", sum(len(s["models"]) for s in sections), "skipped", len(skipped))
for t, why in skipped:
    print("SKIP", t, "::", why)
