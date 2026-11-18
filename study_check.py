#!/usr/bin/env python3
"""KI-Sichtbarkeits-Studie: deterministische On-Page-Messung (nur Standardbibliothek).

Nutzung:
  python study_check.py run urls.txt ergebnisse.csv [--ziel 300]
  python study_check.py summary ergebnisse.csv
  python study_check.py check beispiel.at
Messmethodik-Version: 1.5
Neu in 1.1: Oesterreich-Check (Impressum/Startseite), Stopp nach Ziel-Anzahl,
Fortsetzen nach Abbruch (einfach denselben Befehl nochmal starten), feste CSV-Spalten.
Neu in 1.2: Erkennung geparkter Domains, +43/Oesterreich/PLZ/WKO zaehlen nur im Impressum,
Firmen-Check (ATU, FN, Rechtsform, Gewerbe/WKO), Impressum-Link auch ueber den Linktext.
Neu in 1.3: "Oesterreich" allein reicht nicht mehr, Impressum mit deutschen/Schweizer Merkmalen
(DE-USt-IdNr., Amtsgericht, HRB, +49, CHE-UID, +41) ohne ATU/FN wird ausgeschlossen,
"AG" allein zaehlt nicht mehr als Rechtsform (Verwechslung mit Amtsgericht).
Neu in 1.4: "Oesterreich" + vierstellige PLZ mit Ort im Impressum zaehlt als Merkmal (Kurzschreibweise
ohne A- und +43), nur DE-/CH-Registermerkmale schliessen aus (Telefonnummern +49/+41 allein nicht mehr),
Firmen-Check erkennt freie Berufe (Aerzte-, Anwalts-, Ziviltechnikerkammer usw.), ein Wiederholungsversuch
bei voruebergehenden Serverfehlern (0, 429, 5xx).
Neu in 1.5: Grundgesamtheit = alle oesterreichischen Websites (Firmen, Vereine, Gemeinden, Schulen usw.).
Der Firmen-Check filtert nicht mehr, sondern wird nur als Spalte firma_check mitgeschrieben.
Die Auswertung zeigt die Kernwerte zusaetzlich getrennt nach Firmen und sonstigen Organisationen.
"""
import csv, json, os, re, sys, time, urllib.request, urllib.robotparser, urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from collections import Counter, defaultdict

METHOD_VERSION = "1.5"
UA = "ImpactWebStudieBot/1.5 (+https://impact-web.at; Forschungsabfrage, nur oeffentliche Seiten)"
AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot", "OAI-SearchBot"]
DELAY = 2.0
TIMEOUT = 15
MAXBYTES = 2_000_000

PLATFORMS = [
    ("shopify", ["cdn.shopify.com", "/cdn/shop/", "Shopify.theme"]),
    ("wix", ["wixstatic.com", "static.parastorage.com"]),
    ("squarespace", ["squarespace.com", "static1.squarespace"]),
    ("wordpress", ["/wp-content/", "/wp-includes/"]),
    ("shopware", ["shopware", "/bundles/storefront"]),
    ("webflow", ["webflow.com", "data-wf-page"]),
    ("jimdo", ["jimdo", "jimcdn.com"]),
    ("typo3", ["typo3temp", "/typo3conf/"]),
]

# Oesterreich: ATU und FN zaehlen auf Impressum und Startseite, alle anderen nur im Impressum
AT_ANYWHERE = [
    ("UID_ATU", re.compile(r"\bATU\s?\d{8}\b")),
    ("Firmenbuch_FN", re.compile(r"\bFN\s?\d{3,6}\s?[a-zA-Z]\b")),
]
AT_IMPRESSUM = [
    ("Telefon_43", re.compile(r"(?:\+|\b00)\s?43[\s\d/().-]{6,}")),
    ("Oesterreich", re.compile(r"(?:Österreich|Oesterreich|\bAustria\b)", re.I)),
    ("PLZ_A", re.compile(r"\bA-\d{4}\b")),
    ("WKO", re.compile(r"wko\.at|Wirtschaftskammer", re.I)),
    ("PLZ_Ort", re.compile(r"\b[1-9]\d{3}\s+[A-ZÄÖÜ][a-zäöüß]{2,}")),
]
SCHWEIZ = re.compile(r"\bSchweiz\b|\bSwitzerland\b|\bSuisse\b", re.I)
COPYRIGHT = re.compile(r"(?:©|\(c\)|copyright)\s*\d{4}(?:\s*[-–]\s*\d{4})?", re.I)
# Auslaendisches Impressum (Deutschland, Schweiz)
FOREIGN = [
    ("DE_UStID", re.compile(r"\bDE\s?\d{9}\b")),
    ("DE_Register", re.compile(r"Amtsgericht|\bHRB\s?\d|\bHRA\s?\d|Handelsregister", re.I)),
    ("Telefon_49", re.compile(r"(?:\+|\b00)\s?49[\s\d/().-]{6,}")),
    ("CH_UID", re.compile(r"\bCHE[-\s]?\d{3}\.?\d{3}\.?\d{3}\b")),
    ("Telefon_41", re.compile(r"(?:\+|\b00)\s?41[\s\d/().-]{6,}")),
]
# Firma: mindestens eines davon im Impressum (oder auf der Startseite, falls kein Impressum verlinkt)
FIRM_MARKS = [
    ("UID_ATU", re.compile(r"\bATU\s?\d{8}\b")),
    ("Firmenbuch", re.compile(r"\bFN\s?\d{3,6}\s?[a-zA-Z]\b|Firmenbuch", re.I)),
    ("Rechtsform", re.compile(r"\bGmbH\b|Ges\.?\s?m\.?\s?b\.?\s?H|\be\.\s?U\.|\bOG\b|\bKG\b|Aktiengesellschaft|\bGesbR\b|\beGen\b")),
    ("Gewerbe_WKO", re.compile(r"Gewerbebeh|Gewerbeordnung|Gewerbewortlaut|Unternehmensgegenstand|Einzelunternehm|wko\.at|Wirtschaftskammer|Kammerzugeh", re.I)),
    ("Kammer_Beruf", re.compile(r"Ärztekammer|Aerztekammer|Zahnärztekammer|Tierärztekammer|Apothekerkammer|Rechtsanwaltskammer|Notariatskammer"
                                r"|Ziviltechniker|Kammer der Steuerberater|Wirtschaftstreuh|Patentanwalt|Berufsbezeichnung|Berufsrecht", re.I)),
]
# Geparkte oder reine Platzhalter-Domains
PARKING = re.compile(
    r"domain\s+\S*\s*is\s+registered|domain\s+\S*\s*ist\s+registriert|diese\s+domain\s+wurde\s+registriert"
    r"|this\s+domain\s+(?:is|may\s+be)\s+for\s+sale|domain\s+kaufen|diese\s+domain\s+kann\s+(?:gekauft|erworben)"
    r"|domain\s*parking|sedoparking|sedo\.com/|parkingcrew|bodis\.com|dan\.com/|afternic", re.I)

PAGES = ["home", "impressum", "kontakt", "produkt"]
PAGE_FIELDS = ["lang", "title", "metadesc", "h1_count", "canonical", "og_title",
               "jsonld_blocks", "jsonld_invalid", "jsonld_types"]
COLUMNS = (["domain", "method", "checked", "skipped", "robots_status", "robots_blocks_all"]
           + ["bot_" + b for b in AI_BOTS]
           + ["sitemap_in_robots", "home_status", "at_check", "at_merkmale", "firma_check", "firma_merkmale", "platform", "llms_txt"]
           + [f"{p}_{f}" for p in PAGES for f in PAGE_FIELDS]
           + ["schema_organization", "schema_product", "schema_faq", "schema_breadcrumb", "pages_checked"])


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAXBYTES).decode(r.headers.get_content_charset() or "utf-8", "replace")
            return r.status, r.headers.get("Content-Type", ""), body, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", "", url
    except Exception:
        return 0, "", "", url


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = ""; self.title = ""; self._t = False
        self.h1 = 0; self.meta = {}; self.canonical = ""; self.links = []
        self.ld = []; self._ld = False; self._buf = ""
        self._skip = 0; self.text = []
        self.anchors = []; self._a = None

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("script", "style", "noscript"):
            self._skip += 1
            if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
                self._ld = True; self._buf = ""
            return
        if tag == "html": self.lang = a.get("lang", "") or ""
        elif tag == "title": self._t = True
        elif tag == "h1": self.h1 += 1
        elif tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k: self.meta[k] = a.get("content", "") or ""
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href", "") or ""
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"]); self._a = [a["href"], ""]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            if self._skip: self._skip -= 1
            if tag == "script" and self._ld:
                self._ld = False; self.ld.append(self._buf)
            return
        if tag == "title": self._t = False
        elif tag == "a" and self._a is not None:
            self.anchors.append((self._a[0], self._a[1].strip().lower())); self._a = None

    def handle_data(self, d):
        if self._t: self.title += d
        if self._ld: self._buf += d
        if not self._skip:
            self.text.append(d)
            if self._a is not None: self._a[1] += d

    def plain(self):
        return re.sub(r"\s+", " ", " ".join(self.text))


def ld_types(blobs):
    types, valid, bad = set(), 0, 0
    def walk(n):
        if isinstance(n, dict):
            t = n.get("@type")
            for x in (t if isinstance(t, list) else [t]):
                if isinstance(x, str): types.add(x)
            for v in n.values(): walk(v)
        elif isinstance(n, list):
            for v in n: walk(v)
    for b in blobs:
        try: walk(json.loads(b)); valid += 1
        except Exception: bad += 1
    return types, valid, bad


def detect_platform(html):
    low = html.lower()
    for name, marks in PLATFORMS:
        if any(m.lower() in low for m in marks): return name
    return "unbekannt"


def analyse(html):
    p = Page()
    try: p.feed(html)
    except Exception: pass
    types, ok, bad = ld_types(p.ld)
    return p, types, ok, bad


def pick_pages(base, anchors):
    out = {}
    host = urlparse(base).netloc
    for href, text in anchors:
        u = urljoin(base, href).split("#")[0]
        if urlparse(u).netloc != host: continue
        path = urlparse(u).path.lower()
        if ("impressum" in path or "imprint" in path or text in ("impressum", "imprint")) and "impressum" not in out:
            out["impressum"] = u
        elif ("kontakt" in path or text == "kontakt") and "kontakt" not in out: out["kontakt"] = u
        elif ("/products/" in path or "/produkt" in path) and "produkt" not in out: out["produkt"] = u
    return out


DECISIVE_FOREIGN = ("DE_UStID", "DE_Register", "CH_UID")


def at_check(imp_text, home_text):
    imp_text = COPYRIGHT.sub(" ", imp_text)
    strong = [n for n, r in AT_ANYWHERE if r.search(imp_text) or r.search(home_text)]
    found = list(strong)
    if imp_text:
        found += [n for n, r in AT_IMPRESSUM if r.search(imp_text)]
    decisive = [n for n in found if n not in ("Oesterreich", "PLZ_Ort")]
    if not decisive and "Oesterreich" in found and "PLZ_Ort" in found and not SCHWEIZ.search(imp_text):
        decisive = ["Oesterreich+PLZ_Ort"]
    if not decisive:
        return 0, "|".join(found)
    foreign = [n for n, r in FOREIGN if r.search(imp_text)] if imp_text else []
    blocking = [f for f in foreign if f in DECISIVE_FOREIGN]
    if blocking and not strong:
        return 0, "|".join(found + ["AUSLAND:" + f for f in foreign])
    return 1, "|".join(found + ["info:" + f for f in foreign])


def firm_check(imp_text, home_text):
    txt = imp_text or home_text
    found = [n for n, r in FIRM_MARKS if r.search(txt)]
    return int(bool(found)), "|".join(found)


def norm(line):
    d = line.strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0]
    return d


def check_site(domain):
    domain = norm(domain)
    row = {"domain": domain, "method": METHOD_VERSION, "checked": time.strftime("%Y-%m-%d")}
    root = "https://" + domain
    rp = urllib.robotparser.RobotFileParser()
    st, _, robots, _ = fetch(root + "/robots.txt"); time.sleep(DELAY)
    if st == 0:
        root = "http://" + domain
        st, _, robots, _ = fetch(root + "/robots.txt"); time.sleep(DELAY)
    row["robots_status"] = st
    if st == 200:
        rp.parse(robots.splitlines())
        row["robots_blocks_all"] = int(not rp.can_fetch("*", root + "/"))
        for b in AI_BOTS: row["bot_" + b] = "blockiert" if not rp.can_fetch(b, root + "/") else "erlaubt"
        row["sitemap_in_robots"] = int(bool(re.search(r"(?im)^sitemap:", robots)))
    else:
        row["robots_blocks_all"] = 0
        for b in AI_BOTS: row["bot_" + b] = "erlaubt" if st in (404, 410) else "unklar"
        row["sitemap_in_robots"] = 0

    def allowed(u):
        return not (st == 200 and not rp.can_fetch(UA, u))

    if not allowed(root + "/"):
        row["skipped"] = "robots.txt verbietet unseren Bot"; return row

    s, ct, home, final = fetch(root + "/"); time.sleep(DELAY)
    if s in (0, 429, 500, 502, 503, 504):
        time.sleep(15)
        s, ct, home, final = fetch(root + "/"); time.sleep(DELAY)
    row["home_status"] = s
    if s != 200:
        row["skipped"] = f"Startseite Status {s}"; return row

    p, types, ok, bad = analyse(home)
    if PARKING.search(p.plain()) or PARKING.search(home[:20000]):
        row["skipped"] = "geparkte Domain"; return row
    pages = {"home": (p, types, ok, bad)}
    links = pick_pages(final, p.anchors)

    imp_text = ""
    if "impressum" in links and allowed(links["impressum"]):
        s2, _, h2, _ = fetch(links["impressum"]); time.sleep(DELAY)
        if s2 == 200:
            pages["impressum"] = analyse(h2)
            imp_text = pages["impressum"][0].plain()

    row["at_check"], row["at_merkmale"] = at_check(imp_text, p.plain())
    if not row["at_check"]:
        row["skipped"] = "kein oesterreichisches Merkmal"; return row
    row["firma_check"], row["firma_merkmale"] = firm_check(imp_text, p.plain())

    row["platform"] = detect_platform(home)
    s, ct, body, _ = fetch(root + "/llms.txt"); time.sleep(DELAY)
    row["llms_txt"] = int(s == 200 and "html" not in ct.lower() and len(body.strip()) > 20)

    for name in ("kontakt", "produkt"):
        u = links.get(name)
        if not u or not allowed(u): continue
        s2, _, h2, _ = fetch(u); time.sleep(DELAY)
        if s2 == 200: pages[name] = analyse(h2)

    for name, (pg, ty, ok_, bad_) in pages.items():
        row[f"{name}_lang"] = pg.lang
        row[f"{name}_title"] = int(bool(pg.title.strip()))
        row[f"{name}_metadesc"] = int(bool(pg.meta.get("description", "").strip()))
        row[f"{name}_h1_count"] = pg.h1
        row[f"{name}_canonical"] = int(bool(pg.canonical))
        row[f"{name}_og_title"] = int("og:title" in pg.meta)
        row[f"{name}_jsonld_blocks"] = ok_ + bad_
        row[f"{name}_jsonld_invalid"] = bad_
        row[f"{name}_jsonld_types"] = "|".join(sorted(ty))
    allt = set().union(*[v[1] for v in pages.values()])
    row["schema_organization"] = int(bool(allt & {"Organization", "LocalBusiness", "ProfessionalService", "Corporation"}) or any("Business" in t or "Store" in t or "Service" in t for t in allt))
    row["schema_product"] = int("Product" in allt)
    row["schema_faq"] = int("FAQPage" in allt)
    row["schema_breadcrumb"] = int("BreadcrumbList" in allt)
    row["pages_checked"] = len(pages)
    return row


def cmd_run(inp, out, ziel=None):
    domains, seen = [], set()
    for l in open(inp, encoding="utf-8"):
        if not l.strip() or l.startswith("#"): continue
        d = norm(l)
        if d and d not in seen:
            seen.add(d); domains.append(d)
    done, valid = set(), 0
    if os.path.exists(out) and os.path.getsize(out) > 0:
        with open(out, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                done.add(r["domain"])
                if not r.get("skipped"): valid += 1
        print(f"Setze fort: {len(done)} Domains schon geprueft, {valid} gemessen.", file=sys.stderr)
    new = not os.path.exists(out) or os.path.getsize(out) == 0
    try:
        with open(out, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, restval="", extrasaction="ignore")
            if new: w.writeheader()
            for d in domains:
                if ziel and valid >= ziel: break
                if d in done: continue
                stand = f"{valid}/{ziel}" if ziel else str(valid)
                print(f"[{stand} gemessen] pruefe {d}", file=sys.stderr)
                row = check_site(d)
                w.writerow(row); f.flush()
                if row.get("skipped"):
                    print(f"   uebersprungen: {row['skipped']}", file=sys.stderr)
                else:
                    valid += 1
                    print(f"   OK ({row.get('platform')}, AT: {row.get('at_merkmale')}, Firma: {row.get('firma_merkmale') or 'nein'})", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nAbgebrochen. Zum Weitermachen denselben Befehl nochmal starten.", file=sys.stderr)
        return
    print(f"Fertig: {valid} Websites gemessen.", file=sys.stderr)


def cmd_summary(path):
    allrows = list(csv.DictReader(open(path, encoding="utf-8")))
    rows = [r for r in allrows if not r.get("skipped")]
    skips = Counter(r["skipped"] for r in allrows if r.get("skipped"))
    print(f"Methode {METHOD_VERSION} | geprueft: {len(allrows)} Domains | ausgewertet: {len(rows)}")
    for k, v in skips.most_common(): print(f"  uebersprungen ({k}): {v}")
    n = len(rows)
    if not n: print("Keine auswertbaren Zeilen."); return
    def pct(f, g=rows):
        g = list(g)
        return f"{100*sum(1 for r in g if f(r))/len(g):.0f} % ({sum(1 for r in g if f(r))}/{len(g)})" if g else "-"
    print()
    for b in AI_BOTS: print(f"blockiert {b}: ", pct(lambda r, b=b: r.get('bot_' + b) == 'blockiert'))
    print("llms.txt vorhanden:", pct(lambda r: r.get("llms_txt") == "1"))
    print("JSON-LD irgendwo:", pct(lambda r: int(r.get("home_jsonld_blocks") or 0) > 0))
    print("Organization/LocalBusiness-Schema:", pct(lambda r: r.get("schema_organization") == "1"))
    print("Startseite lang gesetzt:", pct(lambda r: bool(r.get("home_lang"))))
    print("Startseite genau eine H1:", pct(lambda r: r.get("home_h1_count") == "1"))
    print("Meta-Description Startseite:", pct(lambda r: r.get("home_metadesc") == "1"))
    firmen = [r for r in rows if r.get("firma_check") == "1"]
    sonst = [r for r in rows if r.get("firma_check") != "1"]
    print(f"\nNach Betreiber: Firmen n={len(firmen)} | sonstige Organisationen/Privat n={len(sonst)}")
    for label, f in (("JSON-LD irgendwo", lambda r: int(r.get("home_jsonld_blocks") or 0) > 0),
                     ("Organization/LocalBusiness-Schema", lambda r: r.get("schema_organization") == "1"),
                     ("Startseite genau eine H1", lambda r: r.get("home_h1_count") == "1"),
                     ("Meta-Description Startseite", lambda r: r.get("home_metadesc") == "1"),
                     ("llms.txt vorhanden", lambda r: r.get("llms_txt") == "1")):
        print(f"  {label}: Firmen {pct(f, firmen)} | sonstige {pct(f, sonst)}")
    by = defaultdict(list)
    for r in rows: by[r.get("platform") or "?"].append(r)
    print("\nNach Plattform (nur Gruppen mit >= 10 Seiten werden ausgewiesen):")
    for pl, g in sorted(by.items(), key=lambda x: -len(x[1])):
        if len(g) < 10: continue
        print(f"  {pl} (n={len(g)}): KI-Crawler blockiert (GPTBot)", pct(lambda r: r.get('bot_GPTBot') == 'blockiert', g),
              "| Schema Organization", pct(lambda r: r.get('schema_organization') == '1', g))


if __name__ == "__main__":
    args = sys.argv[1:]
    ziel = None
    if "--ziel" in args:
        i = args.index("--ziel"); ziel = int(args[i + 1]); del args[i:i + 2]
    if len(args) >= 3 and args[0] == "run": cmd_run(args[1], args[2], ziel)
    elif len(args) >= 2 and args[0] == "summary": cmd_summary(args[1])
    elif len(args) >= 2 and args[0] == "check": print(json.dumps(check_site(args[1]), ensure_ascii=False, indent=1))
    else: print(__doc__)
