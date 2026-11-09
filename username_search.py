#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
username_search.py — минимальный аналог Sherlock.
 
Что делает: по списку юзернеймов проверяет, занят ли ник на наборе платформ,
и печатает результат (таблица или JSON).
 
Зависимости: только стандартная библиотека (urllib + ThreadPoolExecutor),
поэтому файл легко встроить в любой проект.
 
Запуск:
    python username_search.py nick1 nick2
    python username_search.py --json nick
    python username_search.py --workers 20 nick
"""
 
import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
 
# --- Настройки HTTP -------------------------------------------------------
 
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 10  # секунд на запрос
 
# --- База сайтов ----------------------------------------------------------
# method описывает, как понять, что аккаунт существует:
#   "status"       — 200 => занят
#   "notcontains"  — 200 и строки marker нет в теле => занят
#   "contains"     — 200 и строка marker есть в теле => занят
#   "response_url" — 200 и итоговый URL совпал с запрошенным => занят
SITES = [
    {"name": "GitHub",     "url": "https://github.com/{}",                "method": "status"},
    {"name": "GitLab",     "url": "https://gitlab.com/{}",                "method": "status"},
    {"name": "Reddit",     "url": "https://www.reddit.com/user/{}",       "method": "status"},
    {"name": "Telegram",   "url": "https://t.me/{}",                      "method": "contains",    "marker": "tgme_page_title"},
    {"name": "Medium",     "url": "https://medium.com/@{}",               "method": "status"},
    {"name": "Pinterest",  "url": "https://www.pinterest.com/{}",         "method": "status"},
    {"name": "Twitch",     "url": "https://www.twitch.tv/{}",             "method": "status"},
    {"name": "SoundCloud", "url": "https://soundcloud.com/{}",            "method": "status"},
    {"name": "Steam",      "url": "https://steamcommunity.com/id/{}",     "method": "notcontains", "marker": "The specified profile could not be found"},
    {"name": "VK",         "url": "https://vk.com/{}",                    "method": "status"},
    {"name": "TikTok",     "url": "https://www.tiktok.com/@{}",           "method": "status"},
    {"name": "Instagram",  "url": "https://www.instagram.com/{}/",        "method": "status"},
    {"name": "YouTube",    "url": "https://www.youtube.com/@{}",          "method": "status"},
    {"name": "Spotify",    "url": "https://open.spotify.com/user/{}",     "method": "status"},
    {"name": "Patreon",    "url": "https://www.patreon.com/{}",           "method": "status"},
    {"name": "Behance",    "url": "https://www.behance.net/{}",           "method": "status"},
    {"name": "Dribbble",   "url": "https://dribbble.com/{}",              "method": "status"},
    {"name": "HackerNews", "url": "https://news.ycombinator.com/user?id={}", "method": "contains", "marker": "karma"},
]
 
 
# --- Ядро -----------------------------------------------------------------
 
def check_site(username: str, site: dict) -> dict:
    """Проверяет один сайт. Возвращает dict с результатом."""
    url = site["url"].format(username)
    result = {"site": site["name"], "url": url, "status": "unknown"}
 
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
            code = resp.getcode()
            final_url = resp.geturl()
            body = resp.read(200_000).decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        code = e.code
        final_url = url
        body = ""
    except Exception as e:
        result["status"] = "error"
        result["detail"] = type(e).__name__
        return result
 
    method = site["method"]
    if method == "status":
        exists = (code == 200)
    elif method == "notcontains":
        exists = (code == 200 and site.get("marker", "") not in body)
    elif method == "contains":
        exists = (code == 200 and site.get("marker", "") in body)
    elif method == "response_url":
        exists = (code == 200 and final_url.rstrip("/") == url.rstrip("/"))
    else:
        exists = (code == 200)
 
    result["status"] = "taken" if exists else "free"
    result["http"] = code
    return result
 
 
def search(username: str, workers: int = 15) -> list:
    """Проверяет юзернейм по всем сайтам параллельно."""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(check_site, username, s) for s in SITES]
        for fut in as_completed(futures):
            results.append(fut.result())
    order = {s["name"]: i for i, s in enumerate(SITES)}
    results.sort(key=lambda r: order.get(r["site"], 999))
    return results
 
 
# --- Вывод ----------------------------------------------------------------
 
ICON = {"taken": "[+] занят   ", "free": "[-] свободен", "error": "[!] ошибка  ", "unknown": "[?]        "}
 
 
def print_text(username: str, results: list) -> None:
    print(f"\n=== {username} ===")
    for r in results:
        line = f"  {ICON.get(r['status'], r['status'])}  {r['site']:<12}"
        if r["status"] == "taken":
            line += f"  {r['url']}"
        if r["status"] == "error":
            line += f"  ({r.get('detail', '')})"
        print(line)
 
 
# --- CLI ------------------------------------------------------------------
 
def main(argv=None):
    parser = argparse.ArgumentParser(description="Проверка занятости юзернейма на разных платформах.")
    parser.add_argument("usernames", nargs="+", help="один или несколько юзернеймов")
    parser.add_argument("--json", action="store_true", help="выводить результат в JSON")
    parser.add_argument("--workers", type=int, default=15, help="число параллельных запросов")
    args = parser.parse_args(argv)
 
    all_out = {}
    for username in args.usernames:
        results = search(username, workers=args.workers)
        all_out[username] = results
        if not args.json:
            print_text(username, results)
 
    if args.json:
        print(json.dumps(all_out, ensure_ascii=False, indent=2))
 
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())
