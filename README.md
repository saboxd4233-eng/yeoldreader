# TCG Drop Watcher

Überwacht Produktseiten von Online-Shops (Fantasy Sphere, CardCosmos, FantasiaCards,
Amazon.de, Media Markt, Cardmarket-Angebote etc.) auf Verfügbarkeit und schickt dir
eine Nachricht bei Discord und/oder Telegram, sobald ein Produkt von "ausverkauft"
zu "verfügbar" wechselt. Kein Auto-Kauf, keine Bot-Checkouts - nur Benachrichtigung,
damit du selbst manuell zuschlägst.

Komplett kostenlos: Python, requests, BeautifulSoup, Discord-Webhooks und
Telegram-Bots sind alle gratis. Für den 24/7-Betrieb ohne eigenen laufenden Rechner
nutzen wir GitHub Actions (kostenloses Kontingent reicht für diesen Zweck locker).

## 1. Discord-Benachrichtigung einrichten (kostenlos)

1. Öffne deinen Discord-Server → Kanal-Einstellungen → **Integrationen** → **Webhooks**
2. **Neuer Webhook** → Namen vergeben (z.B. "TCG Watcher") → Kanal wählen
3. **Webhook-URL kopieren** → das ist dein `DISCORD_WEBHOOK_URL`

## 2. Telegram-Benachrichtigung einrichten (kostenlos, alternativ oder zusätzlich)

1. In Telegram den Kontakt **@BotFather** öffnen → `/newbot` senden
2. Namen vergeben → du bekommst einen **Bot-Token** (= `TELEGRAM_BOT_TOKEN`)
3. Deinem neuen Bot eine Nachricht schreiben (z.B. "Hallo")
4. Im Browser aufrufen: `https://api.telegram.org/bot<DEIN_TOKEN>/getUpdates`
5. In der JSON-Antwort die `"chat":{"id": ...}` Zahl suchen → das ist deine
   `TELEGRAM_CHAT_ID`

## 3. Zwei Überwachungs-Modi in config.json

Die mitgelieferte `config.json` ist bereits mit deinen Shops vorausgefüllt.
Es gibt zwei Arten von Einträgen:

### a) `product_watches` – eine konkrete Produktseite überwachen

Für ein Produkt, dessen URL du schon kennst (z.B. ein bestimmtes ETB):

```json
{
  "name": "Pokemon ETB XY (Shop AB)",
  "url": "https://www.shop.de/produkt/etb",
  "keyword_in_stock": "In den Warenkorb",
  "keyword_out_of_stock": "Ausverkauft"
}
```

**Keywords finden:** Produktseite öffnen → Rechtsklick → "Seitenquelltext
anzeigen" (oder F12) → nach dem Text beim Kauf-Button bzw. bei "ausverkauft"
suchen. Jeder Shop formuliert das anders.

### b) `search_watches` – neue Drops auf einer Such-/Kategorieseite erkennen (dein Hauptanwendungsfall)

Das ist der Modus für "sag mir, wenn irgendwo bei diesen Shops was Neues zu
Pokémon/One Piece/Palworld auftaucht". Zwei Varianten:

**Shopify-Shops** (viele der kleinen TCG-Shops laufen auf Shopify, erkennbar
z.B. an URLs wie `/products/...`): einfach die Domain angeben, der Bot baut
sich die Such-URL für jedes Keyword selbst:

```json
{
  "shop_name": "CardCosmos",
  "platform": "shopify",
  "domain": "https://cardcosmos.de",
  "keywords": ["Booster Box", "Display", "ETB", "OP-12", "BP02"]
}
```

**Andere Shops** (`platform: "custom"`): du gibst eine oder mehrere fertige
Such-/Kategorie-URLs an, der Bot durchsucht die Ergebnisse nach deinen
Keywords im Produkttitel:

```json
{
  "shop_name": "Racoon Rises",
  "platform": "custom",
  "search_urls": ["https://racoon-rises.com/collections/pokemon"],
  "keywords": ["Booster Box", "Display", "BP02"]
}
```

Ein Eintrag mit `"skip": true` wird übersprungen – das ist bei den Shops der
Fall, bei denen ich die genaue URL nicht verifizieren konnte (Steelduck,
Härtle, Gameshop Marli, DAESU Cards, FantasiaCards, sowie die
Kategorie-URL bei Racoon Rises). **Öffne den Shop einmal im Browser, kopiere
die URL der Pokémon/One Piece/Palworld-Kategorie oder Suchergebnisseite,
trage sie ein und setze `skip` auf `false`.**

Alarme kommen, sobald ein Produkt zum ersten Mal auf einer beobachteten
Seite auftaucht und dein Keyword im Titel enthalten ist - nicht bei jedem
Lauf erneut für dasselbe Produkt.

### Große Ketten (Amazon, MediaMarkt, Saturn, Kaufland, Müller, Smyths, Mäc Geiz)

Bewusst nicht enthalten. Diese Shops haben Bot-Schutz (Cloudflare/Datadome),
der ein einfaches Skript oft schon nach wenigen Anfragen blockiert - du
bekommst dann scheinbar "keine Treffer", obwohl vielleicht doch was da wäre.
Das wäre trügerische Sicherheit. Für diese Händler ist TCG-Tracker
(tcg-tracker.de) die zuverlässigere, bereits etablierte Lösung. Falls du es
trotzdem selbst versuchen willst: sag Bescheid, dafür bräuchten wir eine
Playwright-Variante (steuert einen echten Browser statt nur HTTP-Requests
zu schicken) - technisch machbar, aber aufwändiger im Betrieb.

### Aktueller Stand deiner 11 Watches

| Shop | Status |
|---|---|
| CardCosmos | ✅ aktiv, Keyword-Suche |
| Lumius | ✅ aktiv, Keyword-Suche |
| Racoon Rises (Racoon Cave, Ulm) | ✅ aktiv, Keyword-Suche |
| GeeksHeaven | ✅ aktiv, Keyword-Suche |
| FantasiaCards | ✅ aktiv, Keyword-Suche + 2 direkte Feeds (Restocks/Vorbestellungen) |
| DAESU Cards | ✅ aktiv, Keyword-Suche |
| Steelduck | ✅ aktiv, Keyword-Suche |
| Härtle | ✅ aktiv, aber Nebenkategorie bei allgemeinem Spielwarenladen |
| P3 Comix Salzburg | ✅ aktiv, aber TCG nicht Kernfokus des Ladens |
| Gameshop Marli | ⏸️ `skip: true` - Shop blockt Anfragen mit HTTP 429 |
| Amazon/MediaMarkt/etc. | ❌ bewusst nicht eingebaut, siehe oben |

Alle Domains und Shop-Plattformen (Shopify/WooCommerce/Custom) wurden vor
dem Eintragen direkt abgerufen und geprüft, keine geratenen URLs.

## Wie viele Shops kannst du hinzufügen, ohne dass etwas "abraucht"?

Das Skript selbst hat keine Obergrenze - es arbeitet die Liste einfach
nacheinander ab, egal ob 5 oder 50 Shops. Die reale Grenze ist das
**kostenlose GitHub-Actions-Minutenkontingent**, wenn du GitHub Actions
für den 24/7-Betrieb nutzt (Abschnitt 4b):

- **Öffentliches Repo:** GitHub-Actions-Minuten sind komplett kostenlos
  und unbegrenzt. Deine Discord/Telegram-Zugangsdaten bleiben trotzdem
  geheim (sie liegen als "Secrets", nicht im sichtbaren Code) - sichtbar
  wäre nur deine Liste an Shops/Keywords. **Empfehlung: nutze ein
  öffentliches Repo**, dann kannst du beliebig viele Shops hinzufügen,
  ohne je an ein Limit zu stoßen.
- **Privates Repo:** Nur 2.000 Freiminuten/Monat. Mit ~13 Shops und
  15-Minuten-Takt ist das Kontingent (grobe Schätzung, abhängig von
  Antwortzeiten der Shops) bereits nach wenigen Tagen aufgebraucht -
  danach pausiert der Workflow einfach bis zum nächsten Monat, es
  entstehen keine Kosten, aber auch keine neuen Alerts mehr.

**Faustformel zum Selbstrechnen:**
`(Anzahl Shops × durchschnittliche Keywords pro Shop) × 2 Sekunden Pause
× (96 Läufe/Tag bei 15-Min-Takt) × 30 Tage / 60 = geschätzte Minuten/Monat`

Alternative, falls du unbedingt privat bleiben willst: Cron-Takt auf
30-60 Minuten strecken, oder das Skript stattdessen lokal auf einem
Rechner/Raspberry Pi laufen lassen (Abschnitt 4a) - dort gibt es gar
kein Minutenlimit, nur muss das Gerät durchlaufen.

## 4a. Lokal laufen lassen (auf deinem PC)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python stock_checker.py
```

Für automatische Wiederholung:
- **Linux/Mac:** Cronjob, z.B. alle 15 Min: `*/15 * * * * cd /pfad/zum/ordner && venv/bin/python stock_checker.py`
- **Windows:** Aufgabenplanung ("Task Scheduler") → Aktion "python.exe stock_checker.py" alle 15 Min

Nachteil: Der Bot läuft nur, solange dein Rechner an ist.

## 4b. Kostenlos in der Cloud laufen lassen (empfohlen, 24/7, ohne eigenen PC)

Über GitHub Actions - das im Repo enthaltene `.github/workflows/check.yml` prüft
automatisch alle 15 Minuten, auch wenn dein PC aus ist. Kostenloses Kontingent
(2.000 Minuten/Monat bei privaten Repos, unbegrenzt bei öffentlichen) reicht
für diesen Zweck bequem aus.

1. Kostenlosen GitHub-Account erstellen (falls noch nicht vorhanden)
2. Neues Repository anlegen, diesen Ordner hochladen (`git init`, `git add .`,
   `git commit`, `git push`) - **Repo auf "Private" stellen**, damit deine
   Shop-Liste nicht öffentlich sichtbar ist
3. Im Repo: **Settings → Secrets and variables → Actions → New repository secret**
   - `DISCORD_WEBHOOK_URL`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. `config.json` NICHT mit Webhook/Token darin committen, wenn das Repo doch mal
   öffentlich wird - besser die Secrets wie in Schritt 3 nutzen und in
   `config.json` nur `items` eintragen (Skript liest Discord/Telegram-Daten
   zuerst aus den Umgebungsvariablen)
5. Fertig - läuft automatisch nach dem Zeitplan in `check.yml`

## Warum bei jedem Shop dieselben Keywords?

Frühere Version hatte pro Shop unterschiedliche, teils veraltete Keywords
(z.B. noch OP-11/OP-12, obwohl die längst erschienen sind und keine neuen
Drops mehr bringen). Jetzt gilt: **eine einzige Keyword-Liste für alle
Shops**, damit kein Shop versehentlich weniger abdeckt als ein anderer.

Die Liste (`config.json`, für jeden Keyword-basierten Shop identisch)
kombiniert zwei Arten von Begriffen:

- **Generische Begriffe** ("Booster Display", "Elite Trainer Box", "Preorder"
  etc.) - die fangen JEDES neue Set automatisch ab, unabhängig von der
  genauen Set-Nummer. Das ist zukunftssicher: wenn OP-21 erscheint, wird es
  trotzdem gefunden, ohne dass du die Liste anfassen musst.
- **Aktuelle/kommende Set-Codes** (OP-18, OP-19, OP-20, EB-06, SD-01,
  ME06, BP02, BP03 etc.) - zusätzliche Präzision oben drauf, basierend auf
  der offiziellen Bandai-Produktseite (en.onepiece-cardgame.com/products)
  und bestätigten Retailer-Vorbestellungen. Alte, bereits erschienene Codes
  wie OP-11 bis OP-16 sind bewusst raus, da hier keine neuen Drops mehr zu
  erwarten sind und sie nur unnötig Requests kosten.

**Wenn ein neues Set offiziell angekündigt wird:** Öffne `config.json`,
Suchen & Ersetzen nach der aktuellen Liste (z.B. `"OP-20"`), einmal
ergänzen/anpassen - die Änderung gilt dann automatisch für alle Shops, nicht
mehr einzeln pro Shop pflegen.

## Warum läuft der Bot nicht mehr streng nacheinander?

Mit 19 Shops × 29 Keywords wären das seriell ~28 Minuten pro Durchlauf -
zu langsam für einen 15-Minuten-Takt, die Läufe würden sich überlappen.
Das Skript fragt jetzt bis zu 6 verschiedene Shops **gleichzeitig** ab
(unterschiedliche Domains, kein Problem). Innerhalb eines einzelnen Shops
bleiben die Anfragen weiterhin nacheinander mit Pause dazwischen - pro Shop
also weiterhin "höflich langsam", nur eben mehrere Shops parallel statt
strikt einer nach dem anderen. Geschätzte Laufzeit jetzt: ~3-4 Minuten
statt ~28 Minuten.

## Wichtige Hinweise

- **AGB/robots.txt respektieren:** Manche Shops verbieten automatisiertes
  Auslesen explizit in den AGB. Rechtlich ist reines Auslesen öffentlich
  sichtbarer Verfügbarkeitsinfos in einer Grauzone, aber manche Shops sperren
  bei zu häufigen Anfragen die IP. 15-Minuten-Takt ist unauffällig, unter
  5 Minuten würde ich vermeiden.
- **Kein Auto-Checkout:** Dieser Bot kauft nichts automatisch. Das wäre nicht
  nur ein AGB-Verstoß bei praktisch jedem Shop, sondern in vielen Fällen auch
  rechtlich riskanter (automatisierter Massenkauf/Scalping-Bots sind in
  einigen Ländern inzwischen ausdrücklich reguliert).
- **Amazon/Media Markt** haben oft aggressiven Bot-Schutz (Cloudflare o.ä.) -
  bei denen kann es sein, dass `requests` allein blockiert wird. Falls das
  passiert, sag mir Bescheid, dann bauen wir das für diese Shops gezielt mit
  einem Headless-Browser (z.B. Playwright, ebenfalls kostenlos) um.
- Ein einzelner "false positive" (Status uneindeutig) blockt keinen Alarm für
  immer - das Skript versucht es beim nächsten Lauf einfach wieder.
- **Erster Lauf nach dem Eintragen einer neuen search_watch:** Der Bot kennt
  noch keine "alten" Produkte dieses Shops und würde sonst alle aktuell
  gelisteten Treffer auf einmal als "neu" melden. Führe den ersten Lauf pro
  neuem Shop deshalb einmal manuell aus und ignoriere die erste Welle an
  Nachrichten - ab dem zweiten Lauf werden nur noch echte Neuzugänge gemeldet.
- Die generische Produkt-Link-Erkennung (`/products/`, `/produkt/` etc. in der
  URL) funktioniert bei den meisten Shopify- und WooCommerce-Shops out of the
  box. Bei exotischeren Shop-Systemen kann es sein, dass gar keine oder zu
  viele Links erkannt werden - meld dich dann, dann passen wir die Erkennung
  für den jeweiligen Shop gezielt an.
