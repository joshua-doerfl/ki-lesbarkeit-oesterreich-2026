# KI-Lesbarkeit österreichischer Websites 2026 (Impact Web)

Dieses Repository enthält alles, um die Zahlen der Studie nachzuvollziehen: das Messskript, das Ziehungsprotokoll und den anonymisierten Datensatz.

- Studie (Volltext): https://impact-web.at/pages/studie-ki-lesbarkeit-2026
- Autor: Joshua Dörfl, Impact Web (Maria Enzersdorf)
- Methodenversion: 1.5

## Was die Studie misst und was nicht

Gemessen werden ausschließlich öffentlich abrufbare, eindeutig prüfbare Merkmale: ob KI-Crawler per robots.txt ausgesperrt werden, ob strukturierte Daten (JSON-LD/Schema.org) vorhanden sind und welche Typen, Anzahl der H1-Überschriften, Meta-Description, Sprachangabe, llms.txt und Plattform.

Die Studie misst **nicht**, ob ChatGPT, Gemini oder andere KI-Systeme eine Website tatsächlich nennen oder als Quelle zitieren. Sie beschreibt die technischen Voraussetzungen dafür.

Untersucht werden Websites mit Betreiber in Österreich: Firmen ebenso wie Vereine, Gemeinden, Schulen und Privatpersonen. Ob eine Firma dahintersteht, wird als Spalte `firma_check` mitgeschrieben.

## Inhalt

| Datei | Inhalt |
|---|---|
| `study_check.py` | Messskript, Version 1.5 (nur Python-Standardbibliothek) |
| `auswertung_erweitert.py` | Auswertung: JSON-LD-Typen, Statusübersicht, Anonymisierung |
| `ziehungsprotokoll.md` | Kandidatenpool, Seed, zweistufige Prüfung, Fallzahlen, Qualitätssicherung |
| `daten/ergebnisse_anonym.csv` | Messwerte der 508 mit Version 1.5 gemessenen Kandidaten, ohne Domain, zufällig gemischt |
| `daten/status_uebersicht.csv` | Ausgewertete, übersprungene und gesperrte Kandidaten dieses Laufs |
| `daten/jsonld_typen.csv` | Häufigkeit der JSON-LD-Typen unter den 300 ausgewerteten Websites |

## Stichprobe in Kürze

- Quelle: Common Crawl, Crawl CC-MAIN-2026-39
- 46.967 Kandidaten mit gleicher Einschlusswahrscheinlichkeit (1/30) für alle Domainendungen, gemischt mit festem Seed 20261019 und der Reihe nach geprüft, bis 300 österreichische Websites gemessen waren
- Dafür wurden die ersten 2.343 Kandidaten der Reihenfolge durchlaufen, in zwei Stufen (Details im `ziehungsprotokoll.md`)

| Status | Anzahl |
|---|---|
| Kandidaten der Reihe nach geprüft | 2.343 |
| Im Vorlauf (Version 1.2) aussortiert: kein österreichisches Merkmal | 1.816 |
| Im Vorlauf (Version 1.2) aussortiert: geparkte Domain | 19 |
| **Mit Version 1.5 gemessen** (= Datensatz) | **508** |
| davon kein österreichisches Merkmal | 75 |
| davon nicht erreichbar (Timeout, DNS, SSL) | 78 |
| davon Server verweigert Zugriff (403, 429, 401) | 16 |
| davon robots.txt verbietet automatisierten Abruf | 11 |
| davon sonstige Serverfehler (4xx, 5xx) | 28 |
| **davon ausgewertet** | **300** (228 Firmen, 72 sonstige Betreiber) |

## Selbst nachrechnen

```
python study_check.py summary daten/ergebnisse_anonym.csv
python auswertung_erweitert.py daten/ergebnisse_anonym.csv
```

Beide Befehle liefern exakt die Zahlen der Studie. In die Auswertung fließen nur die 300 Zeilen ein, bei denen die Spalte `skipped` leer ist; bei allen anderen steht dort der Ausschlussgrund.

Die Messung selbst (`study_check.py run`) lässt sich mit einer eigenen Domainliste wiederholen. Ergebnisse können abweichen, weil sich Websites seit der Messung verändert haben.

## Datenschutz und Fairness

- Der Datensatz enthält keine Domains und keine Firmennamen. Die Zeilen sind mit festem Seed (20261105) gemischt, damit sich die Reihenfolge der Ziehung nicht rekonstruieren lässt.
- Plattformgruppen werden nur ab 10 Websites ausgewiesen. Einzelne Betreiber werden nicht genannt.
- Das Messskript gibt sich im User-Agent als Studien-Bot zu erkennen, hält 2 Sekunden Abstand zwischen Anfragen, respektiert robots.txt und umgeht keine Sperren.
- Konfidenzintervalle: 95 %, Wilson.

## Interessenkonflikt

Impact Web bietet Leistungen zur Website-Gestaltung und KI-Sichtbarkeit an. Deshalb sind Methode, Skript und Daten hier offengelegt: Jede Zahl der Studie soll unabhängig überprüfbar sein.

## Lizenz

Code: MIT-Lizenz (siehe `LICENSE`). Daten: CC BY 4.0, Nennung „Impact Web, KI-Lesbarkeit österreichischer Websites 2026“.

## Kontakt

Fragen zur Methode und Korrekturhinweise gerne als Issue in diesem Repository.
