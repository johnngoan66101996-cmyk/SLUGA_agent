/**
 * Cloudflare Worker Proxy для агента SLUGA
 * Проксирует:
 * 1. Telegram Bot API (/bot<token>/...) -> https://api.telegram.org/bot<token>/...
 * 2. Google AI Studio / Gemini API (/gemini/... или /v1beta/...) -> https://generativelanguage.googleapis.com/...
 * 
 * Преодолевает региональные блокировки РФ для бесперебойной работы на хостинге/VPS.
 */

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // 1. Проксирование Telegram Bot API
    if (url.pathname.startsWith('/bot')) {
      const tgUrl = 'https://api.telegram.org' + url.pathname + url.search;
      const headers = new Headers(request.headers);
      headers.set('host', 'api.telegram.org');

      return fetch(new Request(tgUrl, {
        method: request.method,
        headers: headers,
        body: request.body
      }));
    }

    // 2. Проксирование Google AI Studio / Gemini API (OpenAI-compatible & Native v1beta)
    if (url.pathname.startsWith('/gemini/') || url.pathname.startsWith('/v1beta/')) {
      const gPath = url.pathname.replace('/gemini', '');
      const googleUrl = 'https://generativelanguage.googleapis.com' + gPath + url.search;
      const headers = new Headers(request.headers);
      headers.set('host', 'generativelanguage.googleapis.com');

      return fetch(new Request(googleUrl, {
        method: request.method,
        headers: headers,
        body: request.body
      }));
    }

    // 3. Healthcheck статус
    return new Response(JSON.stringify({ 
      status: "ok", 
      proxy: "active",
      agent: "SLUGA_agent",
      timestamp: new Date().toISOString()
    }), {
      headers: { "Content-Type": "application/json" }
    });
  }
};
