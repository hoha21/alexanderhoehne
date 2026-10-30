"""Erzeugt sitemap.xml und (falls ein Blog vorhanden ist) feed.xml neu.

Aufruf im Hauptordner der Webseite:   python tools/sitemap_feed.py

Grundsätze
- Aufgenommen werden die Grundseiten (Start, Blog, Über mich, Impressum) und alle
  Beiträge in blog/. Entwürfe ausserhalb von blog/ (entwuerfe/, _entwuerfe/) bleiben aussen vor.
- Seiten mit <meta name="robots" content="noindex"> (Weiterleitungen, Platzhalter)
  werden übersprungen.
- Titel, Beschreibung, Datum und Rubrik kommen aus dem JSON-LD-Block des Beitrags
  (headline, description, datePublished, dateModified, articleSection).
- In feed.xml bereits vorhandene Beschreibungstexte werden übernommen.
- lastmod (nie später als heute): bei Beiträgen dateModified (falls vorhanden), sonst datePublished;
  bei Start- und Blogseite das Datum des neuesten Beitrags; sonst das Datum des
  letzten Git-Commits der Datei.
"""
import json
import re
import subprocess
from datetime import date, datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DOMAIN = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
BASE = f"https://{DOMAIN}"
ZONE = ZoneInfo("Europe/Zurich")
GRUNDSEITEN = ["index.html", "blog/index.html", "ueber-mich.html", "impressum.html"]


def lies(pfad):
    return pfad.read_text(encoding="utf-8")


def noindex(html):
    return re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', html, re.I) is not None


def json_ld(html):
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            daten = json.loads(block)
        except json.JSONDecodeError:
            continue
        if daten.get("@type") == "BlogPosting":
            return daten
    return {}


def git_datum(pfad):
    try:
        aus = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(pfad)],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        return aus or date.today().isoformat()
    except (OSError, subprocess.CalledProcessError):
        return date.today().isoformat()


def url_von(rel):
    if rel == "index.html":
        return f"{BASE}/"
    if rel.endswith("/index.html"):
        return f"{BASE}/{rel[:-len('index.html')]}"
    return f"{BASE}/{rel}"


def beitraege():
    liste = []
    for datei in sorted((ROOT / "blog").glob("*.html")):
        if datei.name == "index.html":
            continue
        html = lies(datei)
        if noindex(html):
            continue
        ld = json_ld(html)
        if not ld.get("datePublished"):
            print(f"Übersprungen (kein datePublished im JSON-LD): {datei.name}")
            continue
        liste.append({
            "rel": f"blog/{datei.name}",
            "titel": ld.get("headline", ""),
            "beschreibung": ld.get("description", ""),
            "datum": ld["datePublished"][:10],
            "geaendert": (ld.get("dateModified") or ld["datePublished"])[:10],
            "rubrik": ld.get("articleSection", ""),
        })
    liste.sort(key=lambda b: (b["datum"], b["rel"]), reverse=True)
    return liste


def schreibe_sitemap(posts):
    neuester = max((b["geaendert"] for b in posts), default=None)
    heute = date.today().isoformat()
    eintraege = []
    for rel in GRUNDSEITEN:
        pfad = ROOT / rel
        if not pfad.exists() or noindex(lies(pfad)):
            continue
        if rel in ("index.html", "blog/index.html") and neuester:
            lastmod = max(neuester, git_datum(pfad))
        else:
            lastmod = git_datum(pfad)
        eintraege.append((url_von(rel), lastmod))
    eintraege += [(url_von(b["rel"]), b["geaendert"]) for b in posts]
    # Kein Änderungsdatum in der Zukunft (vordatierte Beiträge)
    eintraege = [(url, min(lastmod, heute)) for url, lastmod in eintraege]
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in eintraege:
        zeilen += ["  <url>", f"    <loc>{escape(url)}</loc>", f"    <lastmod>{lastmod}</lastmod>", "  </url>"]
    zeilen.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(zeilen) + "\n", encoding="utf-8", newline="\n")
    print(f"sitemap.xml: {len(eintraege)} Seiten")


def schreibe_feed(posts):
    feed = ROOT / "feed.xml"
    if not feed.exists():
        return
    alt = lies(feed)
    kopf = re.split(r"\n\s*<item>\s*\n", alt, maxsplit=1)[0]
    kopf = re.sub(r"\s*<!--.*?-->", "", kopf, flags=re.S).rstrip()
    # Von Hand formulierte Feed-Texte bleiben erhalten
    bisher = dict(re.findall(r"<link>([^<]+)</link>.*?<description>(.*?)</description>", alt, re.S))
    teile = [kopf, "    <!-- Wird von tools/sitemap_feed.py erzeugt; nicht von Hand bearbeiten -->"]
    for b in posts:
        url = url_von(b["rel"])
        zeit = datetime.fromisoformat(b["datum"]).replace(hour=8, tzinfo=ZONE)
        teile += ["    <item>",
                  f"      <title>{escape(b['titel'])}</title>",
                  f"      <link>{url}</link>",
                  f'      <guid isPermaLink="true">{url}</guid>',
                  f"      <pubDate>{format_datetime(zeit)}</pubDate>"]
        if b["rubrik"]:
            teile.append(f"      <category>{escape(b['rubrik'])}</category>")
        text = bisher.get(url) or escape(b["beschreibung"])
        teile += [f"      <description>{text}</description>", "    </item>"]
    teile += ["  </channel>", "</rss>"]
    feed.write_text("\n".join(teile) + "\n", encoding="utf-8", newline="\n")
    print(f"feed.xml: {len(posts)} Beiträge")


if __name__ == "__main__":
    posts = beitraege() if (ROOT / "blog").is_dir() else []
    schreibe_sitemap(posts)
    schreibe_feed(posts)
