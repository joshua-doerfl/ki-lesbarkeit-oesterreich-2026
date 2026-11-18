# Ziehungsprotokoll

Studie: KI-Lesbarkeit österreichischer Websites 2026 · Methodenversion 1.5

## 1. Quelle

Common Crawl, Crawl **CC-MAIN-2026-39** (öffentlicher Index).

## 2. Kandidatenpool

1. Aus dem Index wurden alle Domains mit den Endungen .at, .wien und .tirol gezogen: **218.951 Domains**.
2. Für generische Endungen (u. a. .com, .net, .eu, .info) wurden 10 der 300 Indexdateien zufällig gezogen und daraus alle Domains mit überwiegend deutschsprachigen Seiten übernommen: **39.775 Domains**. Einschlusswahrscheinlichkeit je Domain: 1/30.
3. Die österreichischen Endungen wurden mit derselben Wahrscheinlichkeit (1/30) gezogen: **7.192 Domains**. Damit hat jede Domain unabhängig von der Endung die gleiche Einschlusswahrscheinlichkeit.
4. Ausgeschlossen wurden Domains großer Baukasten- und Hosting-Anbieter, unter denen sich viele Betreiber eine Domain teilen.
5. Ergebnis: **46.967 Kandidaten**.

## 3. Reihenfolge und zweistufige Prüfung

Die Kandidaten wurden mit dem festen Zufallsstartwert **Seed 20261019** gemischt und in dieser Reihenfolge geprüft, bis 300 österreichische Websites ausgewertet waren. Dafür wurden die ersten **2.343 Kandidaten** durchlaufen.

Die Regeln zur Österreich-Zuordnung wurden in mehreren Versionen nachgeschärft (siehe Abschnitt 6). Die Prüfung lief deshalb in zwei Stufen:

1. **Vorlauf mit Version 1.2.** Domains ohne österreichisches Merkmal und geparkte Domains wurden aussortiert. Die Österreich-Regel von Version 1.2 war großzügiger als die endgültige (das Wort „Österreich“ allein reichte), deshalb würden die so aussortierten Domains auch nach Version 1.5 nicht als österreichisch gelten. Sie wurden nicht erneut abgerufen. Im durchlaufenen Bereich betraf das **1.835 Domains** (1.816 ohne österreichisches Merkmal, 19 geparkt).
2. **Messung mit Version 1.5.** Alle übrigen Kandidaten im durchlaufenen Bereich, **508 Domains**, wurden mit der endgültigen Version 1.5 vollständig neu geprüft und gemessen. Nur dieser Lauf fließt in die Ergebnisse ein; er ist der Datensatz `daten/ergebnisse_anonym.csv`.

## 4. Einschlusskriterien

**Österreich:** Das Impressum enthält mindestens eines dieser Merkmale: österreichische UID-Nummer (ATU), Firmenbuchnummer (FN), Telefonnummer mit +43, Postleitzahl im Format A-1234, Hinweis auf die Wirtschaftskammer oder das Wort „Österreich“ zusammen mit einer vierstelligen Postleitzahl und Ort. ATU- und FN-Nummer zählen auch auf der Startseite. Impressen mit deutscher oder Schweizer Registrierung (deutsche USt-IdNr., Amtsgericht/HRB/HRA, Schweizer UID) ohne ATU- oder FN-Nummer wurden ausgeschlossen.

**Betreiber:** Untersucht werden alle Websites mit Betreiber in Österreich, unabhängig davon, ob eine Firma, ein Verein, eine Gemeinde, eine Schule oder eine Privatperson dahintersteht. Ob eine Firma dahintersteht, wird nur mitgeschrieben (Spalte `firma_check`), nicht gefiltert. Als Firmenmerkmal gilt im Impressum (oder auf der Startseite, falls kein Impressum verlinkt ist) mindestens eines davon: UID-Nummer (ATU), Firmenbuchnummer oder das Wort „Firmenbuch“, eine Rechtsform (GmbH, e.U., OG, KG, Aktiengesellschaft, GesbR, eGen), ein Gewerbe- oder Kammerhinweis (Gewerbebehörde, Gewerbeordnung, Unternehmensgegenstand, Einzelunternehmen, Wirtschaftskammer) oder ein Hinweis auf eine Berufskammer freier Berufe (Ärzte-, Zahnärzte-, Tierärzte-, Apotheker-, Rechtsanwalts-, Notariatskammer, Ziviltechniker, Steuerberater, Wirtschaftstreuhänder, Patentanwälte, Berufsbezeichnung).

**Weitere Ausschlüsse:** geparkte Domains, nicht erreichbare Websites, Serverfehler, Zugriffsverweigerung durch Server oder robots.txt.

## 5. Fallzahlen

| Status | Anzahl |
|---|---|
| Kandidaten der Reihe nach geprüft | 2.343 |
| Vorlauf (1.2): kein österreichisches Merkmal | 1.816 |
| Vorlauf (1.2): geparkte Domain | 19 |
| **Mit Version 1.5 gemessen** | **508** |
| 1.5: kein österreichisches Merkmal | 75 |
| 1.5: nicht erreichbar (Status 0: Timeout, DNS, SSL) | 78 |
| 1.5: Server verweigert Zugriff (403: 10, 429: 4, 401: 2) | 16 |
| 1.5: robots.txt verbietet automatisierten Abruf | 11 |
| 1.5: sonstige Serverfehler (404: 8, 500: 8, 503: 7, 526: 3, 502: 1, 410: 1) | 28 |
| **Ausgewertet** | **300** (228 Firmen, 72 sonstige Betreiber) |

Gesamt ohne österreichisches Merkmal: 1.891. Die 11 per robots.txt gesperrten und die 16 serverseitig abweisenden Kandidaten wurden übersprungen, bevor ihre Herkunft geprüft werden konnte. Ob sie österreichisch sind, ist unbekannt.

## 6. Qualitätssicherung

- Kalibrierung der Österreich-Zuordnung in Testläufen (Version 1.1 bis 1.5). Kalibriert wurde nur die Zuordnung, nicht die Messung. Die Änderungen je Version stehen im Kopf von `study_check.py`.
- Gegenprobe: nytimes.com (sperrt KI-Crawler nachweislich). Alle sechs Sperren wurden korrekt erkannt.
- Handkontrolle: 30 zufällig gezogene Treffer aus dem Lauf mit Version 1.5 (Seed 20261019). Zuordnung zu Österreich in 29 Fällen korrekt (Fehlerquote 3,3 %), Messung von robots.txt und llms.txt in allen 30 Fällen korrekt.
