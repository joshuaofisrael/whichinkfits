#!/bin/sh
# Ping IndexNow after the launch build only. While noindex is on, do not ping.
set -e
cd "$(dirname "$0")"
if grep -q 'name="robots" content="noindex' index.html; then
  echo "noindex flag is on; not pinging IndexNow"
  exit 0
fi
KEY=$(grep -o 'content="[a-f0-9]\{32\}"' index.html | head -1 | cut -d'"' -f2)
# Key file name is the key. Read it from the repo.
KEY=$(ls *.txt | head -1 | sed 's/.txt//')
python3 - << PY
import json, urllib.request, pathlib
root = pathlib.Path(".")
key = [p.stem for p in root.glob("*.txt") if len(p.stem)==32][0]
urls = []
sm = (root/"sitemap.xml").read_text()
urls = [line.split("<loc>")[1].split("</loc>")[0] for line in sm.splitlines() if "<loc>" in line]
body = json.dumps({"host":"whichinkfits.com","key":key,"keyLocation":"https://whichinkfits.com/"+key+".txt","urlList":urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type":"application/json"})
print(urllib.request.urlopen(req, timeout=30).status)
PY
