#!/usr/bin/env python3
"""KI-Sichtbarkeits-Studie (Impact Web): erweiterte Auswertung, nur Standardbibliothek.

Liest die Ergebnis-CSV von study_check.py und erzeugt:
  1. jsonld_typen.csv        – welche JSON-LD-Typen wie oft vorkommen (mit 95-%-KI)
  2. status_uebersicht.csv   – ausgewertet / übersprungen / 403 / nicht erreichbar
  3. ergebnisse_anonym.csv   – Datensatz ohne Domains, zufällig gemischt (für GitHub)
Dazu werden alle Tabellen als Markdown in der Konsole ausgegeben (zum Einfügen in die Studie).

Nutzung (Windows):
  python auswertung_erweitert.py ergebnisse.csv
  python auswertung_erweitert.py ergebnisse.csv --out auswertung
"""
import csv, math, os, random, re, sys
from collections import Counter

# ---------------------------------------------------------------- Einstellungen
SEED_ANONYM = 20261105          # fester Seed fürs Mischen, im README dokumentieren
SPALTEN_ENTFERNEN = ["domain", "url", "final_url", "home_url", "impressum_url",
                     "kontakt_url", "produkt_url", "checked"]
TOP_TYPEN = 25                  # so viele Typen werden einzeln ausgewiesen
MIN_SEITEN_FUER_TYP = 3         # Typen mit weniger Seiten landen unter "Sonstige"
# Typen, die immer in der Tabelle stehen sollen (auch wenn selten), weil das Feedback danach fragt
PFLICHT_TYPEN = ["Organization", "LocalBusiness", "WebSite", "WebPage", "Product",
                 "FAQPage", "Event", "Service", "BreadcrumbList", "Person"]


def wilson(k, n, z=1.96):
    """95-%-Konfidenzintervall nach Wilson, Rückgabe in Prozent."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, (c - h) * 100), min(100.0, (c + h) * 100)


def fmt(k, n):
    if n == 0:
        return "-", "-"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f} %".replace(".", ","), f"{lo:.1f}–{hi:.1f} %".replace(".", ",")


def norm_typ(t):
    """'http://schema.org/Organization' oder 'schema:Organization' -> 'Organization'."""
    t = t.strip()
    t = re.sub(r"^https?://(www\.)?schema\.org/", "", t)
    t = re.sub(r"^schema:", "", t)
    return t


def lese_csv(pfad):
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ist_ausgewertet(r):
    return not (r.get("skipped") or "").strip()


# ---------------------------------------------------------------- 5c: Status
def status_uebersicht(rows):
    n = len(rows)
    zaehler = Counter()
    for r in rows:
        skip = (r.get("skipped") or "").strip()
        home = (r.get("home_status") or "").strip()
        if not skip:
            zaehler["Ausgewertet"] += 1
        elif "robots" in skip.lower():
            zaehler["Übersprungen: robots.txt verbietet Studien-Bot"] += 1
        elif home == "403":
            zaehler["Gesperrt: Startseite liefert 403 (z. B. Firewall/Cloudflare)"] += 1
        elif home in ("401", "429"):
            zaehler[f"Gesperrt: Startseite liefert {home}"] += 1
        elif home == "0" or home == "":
            zaehler["Nicht erreichbar (Timeout, DNS, SSL-Fehler)"] += 1
        elif home.startswith("4") or home.startswith("5"):
            zaehler[f"Fehler: Startseite liefert {home}"] += 1
        else:
            zaehler[f"Sonstiges: {skip}"] += 1
    tabelle = []
    for name, k in sorted(zaehler.items(), key=lambda x: -x[1]):
        anteil, ki = fmt(k, n)
        tabelle.append({"Status": name, "Anzahl": k, "Anteil": anteil, "95-%-KI": ki})
    tabelle.append({"Status": "Summe geprüfte Websites", "Anzahl": n, "Anteil": "100 %", "95-%-KI": ""})
    return tabelle


# ---------------------------------------------------------------- 5a: JSON-LD-Typen
def jsonld_typen(rows):
    ausgewertet = [r for r in rows if ist_ausgewertet(r)]
    n = len(ausgewertet)
    typ_spalten = [c for c in (rows[0].keys() if rows else []) if c.endswith("_jsonld_types")]
    alle, nur_start = Counter(), Counter()
    mit_jsonld = 0
    for r in ausgewertet:
        typen_site, typen_home = set(), set()
        for c in typ_spalten:
            werte = {norm_typ(t) for t in (r.get(c) or "").split("|") if t.strip()}
            typen_site |= werte
            if c.startswith("home_"):
                typen_home |= werte
        if typen_site:
            mit_jsonld += 1
        alle.update(typen_site)
        nur_start.update(typen_home)

    einzeln = [t for t, k in alle.most_common() if k >= MIN_SEITEN_FUER_TYP][:TOP_TYPEN]
    for t in PFLICHT_TYPEN:
        if t not in einzeln:
            einzeln.append(t)
    tabelle = []
    for t in sorted(einzeln, key=lambda x: -alle.get(x, 0)):
        k = alle.get(t, 0)
        anteil, ki = fmt(k, n)
        anteil_h, _ = fmt(nur_start.get(t, 0), n)
        tabelle.append({"Typ": t, "Websites": k, "Anteil (alle geprüften Seiten)": anteil,
                        "95-%-KI": ki, "Anteil nur Startseite": anteil_h})
    rest = sum(1 for t, k in alle.items() if t not in einzeln and k > 0)
    return tabelle, n, mit_jsonld, rest, typ_spalten


# ---------------------------------------------------------------- 6: Anonymisierung
def anonymisieren(rows):
    if not rows:
        return [], [], []
    spalten = [c for c in rows[0].keys() if c.lower() not in SPALTEN_ENTFERNEN]
    neu = [{c: r.get(c, "") for c in spalten} for r in rows]
    random.Random(SEED_ANONYM).shuffle(neu)
    for i, r in enumerate(neu, 1):
        r["laufnummer"] = i
    spalten = ["laufnummer"] + spalten
    # Sicherheitscheck: steht irgendwo noch etwas, das nach Domain/URL aussieht?
    verdacht = set()
    muster = re.compile(r"(https?://|www\.|\.[a-z]{2,6}(/|$))", re.I)
    for r in neu:
        for c in spalten:
            v = str(r.get(c, ""))
            if c.endswith("_jsonld_types") or c.endswith("_lang"):
                continue
            if muster.search(v):
                verdacht.add(c)
    return neu, spalten, sorted(verdacht)


# ---------------------------------------------------------------- Ausgabe
def schreibe_csv(pfad, tabelle, spalten=None):
    if not tabelle:
        return
    spalten = spalten or list(tabelle[0].keys())
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=spalten, delimiter=";")
        w.writeheader()
        w.writerows(tabelle)


def markdown(tabelle):
    if not tabelle:
        return "(leer)"
    k = list(tabelle[0].keys())
    zeilen = ["| " + " | ".join(k) + " |", "|" + "|".join("---" for _ in k) + "|"]
    for r in tabelle:
        zeilen.append("| " + " | ".join(str(r[c]) for c in k) + " |")
    return "\n".join(zeilen)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    eingabe = sys.argv[1]
    out = "auswertung"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)

    rows = lese_csv(eingabe)
    if not rows:
        print("Die CSV ist leer.")
        sys.exit(1)

    # 5c
    status = status_uebersicht(rows)
    schreibe_csv(os.path.join(out, "status_uebersicht.csv"), status)
    print("\n## Status aller geprüften Websites\n")
    print(markdown(status))

    # 5a
    typen, n, mit_jsonld, rest, typ_spalten = jsonld_typen(rows)
    if not typ_spalten:
        print("\nHinweis: Keine Spalten '*_jsonld_types' gefunden. JSON-LD-Typen können nicht ausgewertet werden.")
    else:
        schreibe_csv(os.path.join(out, "jsonld_typen.csv"), typen)
        a, ki = fmt(mit_jsonld, n)
        print(f"\n## JSON-LD-Typen (n = {n} ausgewertete Websites)\n")
        print(f"Websites mit mindestens einem gültigen JSON-LD-Typ: {mit_jsonld} ({a}, 95-%-KI {ki})\n")
        print(markdown(typen))
        if rest:
            print(f"\nWeitere {rest} seltene Typen sind unter 'Sonstige' zusammengefasst (nicht einzeln ausgewiesen).")

    # 6
    anonym, spalten, verdacht = anonymisieren(rows)
    schreibe_csv(os.path.join(out, "ergebnisse_anonym.csv"), anonym, spalten)
    print(f"\nAnonymisierter Datensatz: {len(anonym)} Zeilen, {len(spalten)} Spalten, gemischt mit Seed {SEED_ANONYM}.")
    if verdacht:
        print("ACHTUNG: In diesen Spalten stehen noch Werte, die nach Domain/URL aussehen. "
              "Vor dem Upload prüfen oder in SPALTEN_ENTFERNEN eintragen:")
        for c in verdacht:
            print("  -", c)
    else:
        print("Sicherheitscheck: keine Domain- oder URL-Werte mehr gefunden.")
    print(f"\nAlle Dateien liegen im Ordner '{out}'.")


if __name__ == "__main__":
    main()
