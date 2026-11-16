# Launch

The HTML committed on `main` is the preview build. Every page is `noindex, follow`. GitHub Pages deploys those files as they are. The workflow does not run the builder.

Run this on launch day, from the repository root, after whichinkfits.com serves this site.

## 1. Set the Google Analytics 4 measurement id

Open `_build/build.py` and set:

```python
GA4_ID = "G-XXXXXXXXXX"
```

Use the measurement id from the GA4 property. The constant ships as an empty string. Do not put an API secret, OAuth client secret, or service-account key in the repo. A measurement id is public once it is in the page.

`python3 _build/check.py --launch` prints `ga4-id-empty` and exits 1 while `GA4_ID` is empty or is not a `G-` id. It also exits 1 if any page is missing the Cloudflare Web Analytics beacon or the GA4 loader (`https://www.googletagmanager.com/gtag/js?id=` plus `id="ga4-loader"`).

Consent Mode v2 defaults are denied. `assets/consent.js` loads gtag only after the visitor accepts the banner. Cookie settings in the footer opens that banner again. Rejecting leaves the GA4 script unloaded. The Cloudflare beacon stays on every launch page.

## 2. Build and check

```sh
python3 _build/build.py --launch
python3 _build/check.py --launch
python3 _build/legal_gate.py check --no-queue
```

Each command must exit 0, and the check must print `issues 0`. The launch build:

- removes `noindex` except on `404.html`
- keeps root-relative paths and canonical URLs on `https://whichinkfits.com/`
- writes `CNAME` as `whichinkfits.com`
- writes `sitemap.xml` with `lastmod` on every URL
- writes `robots.txt` with `Allow: /` for Googlebot, Bingbot, and the AI crawlers, plus the sitemap line
- rewrites `llms.txt` and the IndexNow key file from the existing key
- adds the Cloudflare Web Analytics beacon, the consent banner, and the GA4 loader to every page

`python3 _build/legal_gate.py check` (without `--no-queue`) is the same gate. `--no-queue` skips writing a review queue if a page is held.

Commit the generated site and push to `main`. `.github/workflows/pages.yml` deploys it to GitHub Pages. `LAUNCH-NOTES.md` is excluded from that upload, same as `README.md`.

## 3. IndexNow

After the launch build is deployed and the home page is no longer `noindex`:

```sh
./indexnow.sh
```

While `noindex` is present, the script does not ping.

## Preview build

```sh
python3 _build/build.py
python3 _build/check.py
python3 _build/legal_gate.py check --no-queue
```

The preview build keeps `noindex` on every page and does not load Google Analytics 4 or the Cloudflare beacon.
