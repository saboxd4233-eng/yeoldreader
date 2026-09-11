#!/usr/bin/env python3
"""
TCG Drop Watcher
-----------------
Zwei Ueberwachungsmodi:

1. product_watches: Eine feste Produkt-URL wird auf "verfuegbar"/"ausverkauft"
   geprueft.

2. search_watches: Eine Such-/Kategorie-Seite eines Shops wird regelmaessig
   abgerufen. Neue Produkt-Links, deren Titel eines deiner Keywords enthaelt,
   werden gemeldet, sobald sie zum ersten Mal auftauchen.

Parallelisierung: Verschiedene Shops werden GLEICHZEITIG abgefragt (mehrere
Worker-Threads), aber innerhalb eines einzelnen Shops laufen die Anfragen
weiterhin nacheinander mit Pause dazwischen - so bleibt es pro Domain hoeflich
langsam, während der Gesamtlauf trotzdem schnell genug für einen 15-Minuten-
Takt bleibt.

Kein Auto-Checkout, kein aggressives Scraping - nur Benachrichtigung.
Bitte robots.txt und AGB der jeweiligen Shops respektieren.
"""

import json
import os
import re
import sys
import time
import random
import concurrent.futures
from datetime import datetime, timezone
from urllib.parse import urljoin, quote_plus

import requests
from bs4 import BeautifulSoup

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 10  # Sekunden - straffer als vorher, damit ein einzelner haengender Shop nicht alles ausbremst
MIN_DELAY_BETWEEN_REQUESTS = 1.2  # Sekunden, Mindestpause zwischen Anfragen AN DENSELBEN SHOP
MAX_CONCURRENT_SHOPS = 6  # wie viele verschiedene Shops gleichzeitig abgefragt werden

# Typische URL-Bausteine, an denen man Produkt-Links in TCG-Shops erkennt.
PRODUCT_LINK_HINTS = ["/products/", "/produkt/", "/product/", "/artikel/", "/item/", "/p/", ".html", "/product-page/"]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_product(item):
    """
    Gibt True zurueck, wenn das Produkt als 'verfuegbar' eingestuft wird,
    False wenn ausverkauft, None wenn nicht eindeutig ermittelbar.
    """
    try:
        resp = requests.get(item["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] Fehler beim Abrufen von {item['name']}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator=" ", strip=True).lower()

    out_kw = item.get("keyword_out_of_stock", "").lower()
    in_kw = item.get("keyword_in_stock", "").lower()

    if out_kw and out_kw in text:
        return False
    if in_kw and in_kw in text:
        return True
    return None


def notify_discord(webhook_url, title, url):
    payload = {"content": f"🟢 **{title}**\n{url}"}
    try:
        requests.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        print(f"[WARN] Discord-Benachrichtigung fehlgeschlagen: {e}")


def notify_telegram(bot_token, chat_id, title, url):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = f"🟢 {title}\n{url}"
    try:
        requests.post(api_url, data={"chat_id": chat_id, "text": text}, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        print(f"[WARN] Telegram-Benachrichtigung fehlgeschlagen: {e}")


def send_alert(discord_webhook, telegram_token, telegram_chat_id, title, url):
    if discord_webhook:
        notify_discord(discord_webhook, title, url)
    if telegram_token and telegram_chat_id:
        notify_telegram(telegram_token, telegram_chat_id, title, url)


def fetch_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_product_links(soup, base_url):
    results = []
    seen_urls = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not any(hint in href.lower() for hint in PRODUCT_LINK_HINTS):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 3:
            img = a.find("img")
            if img and img.get("alt"):
                title = img["alt"].strip()
        if not title:
            continue
        # Bugfix: Sternebewertungs-Links ("5.0", "4.9" etc.) faelschlich als
        # Produkt erkannt, weil ihr Linktext nur eine Zahl ist. Ein echter
        # Produktname enthaelt immer mindestens ein paar Buchstaben.
        if not re.search(r"[A-Za-zÀ-ÿ]{3,}", title):
            continue
        full_url = urljoin(base_url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        results.append((title, full_url))
    return results


def process_product_watch(item, state, discord_webhook, telegram_token, telegram_chat_id):
    """Ein einzelner Produkt-Watch. Laeuft als eigener Thread/Task."""
    name = item["name"]
    was_in_stock = state.get(name, {}).get("in_stock", False)

    is_in_stock = check_product(item)
    time.sleep(MIN_DELAY_BETWEEN_REQUESTS + random.random())

    if is_in_stock is None:
        return

    if is_in_stock and not was_in_stock:
        print(f"[ALERT] {name} ist jetzt verfuegbar!")
        send_alert(discord_webhook, telegram_token, telegram_chat_id, f"Verfuegbar: {name}", item["url"])
    else:
        print(f"[INFO] {name}: verfuegbar={is_in_stock}")

    state[name] = {
        "in_stock": bool(is_in_stock),
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }


def process_search_watch(watch, state, discord_webhook, telegram_token, telegram_chat_id):
    """
    Ein einzelner Shop-Watch (Keyword-Suche oder feste Such-/Kategorie-URLs).
    Laeuft als eigener Thread/Task - andere Shops laufen gleichzeitig, aber
    die Anfragen INNERHALB dieses Shops bleiben seriell mit Pause dazwischen.
    """
    if watch.get("skip"):
        print(f"[SKIP] {watch.get('shop_name')}: als 'skip' markiert")
        return

    shop_name = watch["shop_name"]
    keywords = [k.lower() for k in watch.get("keywords", [])]
    platform = watch.get("platform", "custom")

    if platform == "shopify":
        domain = watch["domain"].rstrip("/")
        urls_to_check = [(kw, f"{domain}/search?q={quote_plus(kw)}&type=product") for kw in watch.get("keywords", [])]
    elif platform == "woocommerce":
        domain = watch["domain"].rstrip("/")
        urls_to_check = [(kw, f"{domain}/?s={quote_plus(kw)}&post_type=product") for kw in watch.get("keywords", [])]
    elif platform == "magento":
        domain = watch["domain"].rstrip("/")
        urls_to_check = [(kw, f"{domain}/catalogsearch/result/?q={quote_plus(kw)}") for kw in watch.get("keywords", [])]
    elif platform == "epages":
        domain = watch["domain"].rstrip("/")
        urls_to_check = [(kw, f"{domain}/search?q={quote_plus(kw)}") for kw in watch.get("keywords", [])]
    else:
        urls_to_check = [(None, u) for u in watch.get("search_urls", [])]

    state_key = f"search::{shop_name}"
    known_urls = set(state.get(state_key, []))
    newly_known = set(known_urls)

    for kw, page_url in urls_to_check:
        try:
            soup = fetch_soup(page_url)
        except requests.RequestException as e:
            print(f"[WARN] {shop_name}: Fehler beim Abrufen von {page_url}: {e}")
            time.sleep(MIN_DELAY_BETWEEN_REQUESTS + random.random())
            continue

        products = extract_product_links(soup, page_url)
        for title, product_url in products:
            title_lower = title.lower()
            matched = kw is not None or any(k in title_lower for k in keywords)
            if not matched:
                continue
            if product_url not in known_urls:
                print(f"[ALERT] {shop_name}: neues Produkt '{title}'")
                send_alert(discord_webhook, telegram_token, telegram_chat_id, f"Neu bei {shop_name}: {title}", product_url)
            newly_known.add(product_url)

        time.sleep(MIN_DELAY_BETWEEN_REQUESTS + random.random())

    state[state_key] = list(newly_known)


def main():
    config = load_json(CONFIG_PATH, None)
    if not config:
        print("Keine config.json gefunden oder leer. Bitte zuerst einrichten.")
        sys.exit(1)

    product_watches = config.get("product_watches", config.get("items", []))
    search_watches = config.get("search_watches", [])

    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL") or config.get("discord_webhook_url")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("telegram_bot_token")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("telegram_chat_id")

    state = load_json(STATE_PATH, {})

    print(
        f"[{datetime.now(timezone.utc).isoformat()}] Starte parallelen Check: "
        f"{len(product_watches)} Produkt-Watches, {len(search_watches)} Shop-Watches "
        f"(bis zu {MAX_CONCURRENT_SHOPS} gleichzeitig)..."
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SHOPS) as executor:
        futures = []
        for item in product_watches:
            futures.append(executor.submit(
                process_product_watch, item, state, discord_webhook, telegram_token, telegram_chat_id
            ))
        for watch in search_watches:
            futures.append(executor.submit(
                process_search_watch, watch, state, discord_webhook, telegram_token, telegram_chat_id
            ))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] Ein Watch ist fehlgeschlagen: {e}")

    save_json(STATE_PATH, state)
    print("Fertig.")


if __name__ == "__main__":
    main()
