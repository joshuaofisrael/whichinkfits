# Which Ink Fits (whichinkfits.com)

Which cartridge, toner, or ink bottle fits a printer, and which printers a number fits. Static HTML for GitHub Pages (branch `main`, folder `/`). Joshua Israel Ventures LLC. Independent of HP, Canon, Epson, and Brother.

## Build

```
python3 _build/build.py
python3 _build/check.py
python3 _build/legal_gate.py check --no-queue
```

`python3 _build/build.py --launch` is the live switch: it removes `noindex`, adds the Cloudflare beacon, and keeps root paths, canonicals on https://whichinkfits.com/, and the CNAME file. The default build puts `noindex, follow` on every page, including the home page, until that flag is used. Do not run `--launch` until the domain serves this site.

Canonicals, the sitemap, robots.txt, llms.txt, and JSON-LD always use https://whichinkfits.com/. Paths in the HTML are root relative.

## Data

`_build/hp_catalog.json` is the structured extract of HP's support document "Which cartridges work with my HP printer?" (retrieved 16 Nov 2026). `_build/extract_hp.py` rebuilds that file from a saved copy of the document. `_build/more.py` holds the Canon, Epson, and Brother rows, each tied to a manufacturer URL. The builder does not invent a cartridge number. Page yield is blank when the source does not print one.

Checked 16 Nov 2026: 826 printer pages, 70 cartridge and bottle pages, series hubs, and the legal pages. `sitemap.xml` lists the indexable URLs. `404.html` is `noindex` and is not in the sitemap.

## Launch

The CNAME file is `whichinkfits.com`. While `noindex` is present, `./indexnow.sh` does not ping. After `--launch` and a deploy, run `./indexnow.sh`.

Contact mail goes to joshuaofisrael@gmail.com. There are no affiliate links and no ads.
