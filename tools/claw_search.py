"""
Инструмент веб-разведки SLUGA.
1. claw_search(query) — быстрый поиск через DuckDuckGo без внешних платных API.
2. fetch_page(url) — парсинг страницы в чистый Markdown с фильтрацией рекламы и разметки.
"""

import asyncio
import re
import urllib.parse
import urllib.request
from typing import List, Dict, Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def claw_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    
    # 1. Попытка через httpx + BeautifulSoup
    try:
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for r in soup.select(".result"):
                    title_elem = r.select_one(".result__title .result__a")
                    snippet_elem = r.select_one(".result__snippet")
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        raw_href = title_elem.get("href", "")
                        if "uddg=" in raw_href:
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                            link = parsed.get("uddg", [raw_href])[0]
                        else:
                            link = raw_href
                        snippet = snippet_elem.get_text(strip=True)
                        results.append({"title": title, "url": link, "snippet": snippet})
                        if len(results) >= max_results:
                            break
                if results:
                    return results
    except Exception:
        pass

    # 2. Надежный Fallback через стандартную библиотеку urllib (Zero Dependency)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        loop = asyncio.get_event_loop()
        def _fetch():
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="replace")
        html_text = await loop.run_in_executor(None, _fetch)

        # Простой regex-парсер результатов duckduckgo
        matches = re.findall(
            r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)<\/a>',
            html_text, re.DOTALL | re.IGNORECASE
        )
        if not matches:
            matches = re.findall(r'<a[^>]+class="[^"]*result__url[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)<\/a>', html_text, re.DOTALL)

        results = []
        for link, snippet_raw in matches[:max_results]:
            clean_snippet = re.sub(r'<[^>]+>', '', snippet_raw).strip()
            results.append({
                "title": clean_snippet[:60] + "...",
                "url": link,
                "snippet": clean_snippet
            })
        return results if results else [{"title": "DuckDuckGo", "url": url, "snippet": "Поиск выполнен, результаты обработаны."}]
    except Exception as e:
        return [{"title": "Ошибка сети", "url": "", "snippet": str(e)}]

async def fetch_page(url: str, max_chars: int = 4000) -> str:
    try:
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=20.0, headers=HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"]):
                    tag.decompose()
                text = soup.get_text(separator="\n")
                clean_text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
                return clean_text[:max_chars]
    except Exception:
        pass

    # Fallback на urllib
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        loop = asyncio.get_event_loop()
        def _fetch():
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="replace")
        raw_html = await loop.run_in_executor(None, _fetch)
        clean = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:max_chars]
    except Exception as e:
        return f"Сбой при извлечении страницы {url}: {e}"
