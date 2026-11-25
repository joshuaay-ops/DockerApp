
import json
import os

import redis
import requests
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Redis connection (settings from .env via Compose)
client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)

# CoinGecko API: keyless works; a free Demo key raises the rate limit
API_BASE = "https://api.coingecko.com/api/v3"
API_KEY = os.getenv("COINGECKO_API_KEY", "")
HEADERS = {"x-cg-demo-api-key": API_KEY} if API_KEY else {} 

COINS = [("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL"), ("nvidia-xstock", "NVDA"),
    ("amd-xstock", "AMD"),
    ("palantir-xstock", "PLTR")]


def cached_get(cache_key, path, params, ttl):
    """Return API data from Redis if cached, otherwise call the API and cache it."""
    cached = client.get(cache_key)
    if cached:
        return json.loads(cached)
    #call to coingecko
    resp = requests.get(API_BASE + path, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    client.setex(cache_key, ttl, json.dumps(data))  # expires after ttl seconds
    return data


LAYOUT = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Current Prices</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #0d1117; color: #e6edf3; }
    nav { display: flex; gap: 24px; align-items: center; padding: 16px 32px; background: #161b22; border-bottom: 1px solid #30363d; }
    nav .logo { font-weight: 700; font-size: 20px; color: #3fb950; margin-right: auto; }
    nav a { color: #8b949e; text-decoration: none; }
    nav a:hover { color: #e6edf3; } 
    main { max-width: 900px; margin: 48px auto; padding: 0 24px; }
    h1 { margin-top: 0; }
    .muted { color: #8b949e; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 32px 0; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }
    .coin { font-weight: 600; color: #8b949e; }
    .price { font-size: 28px; font-weight: 700; margin: 8px 0; }
    .up { color: #3fb950; }
    .down { color: #f85149; }
    .big { font-size: 72px; font-weight: 800; color: #3fb950; margin: 16px 0; }
  </style>
</head>
<body>
  <nav>
    <span class="logo">Joshops Watchlist</span>
    <a href="/">Home</a>
    <a href="/count">Views</a>
  </nav>
  <main>
    {{ content | safe }}
  </main>
</body>
</html>
"""


@app.route("/")
def welcome():
    try:
        prices = cached_get(
            "prices",
            "/simple/price",
            {"ids": ",".join(c for c, _ in COINS), "vs_currencies": "usd", "include_24hr_change": "true"},
            ttl=60,
        )
    except requests.RequestException:
        prices = None

    if prices:
        cards = ""
        for coin_id, symbol in COINS:
            p = prices.get(coin_id, {})
            change = p.get("usd_24h_change", 0)
            css = "up" if change >= 0 else "down" 
            cards += f"""
            <div class="card">
              <div class="coin">{symbol}</div>
              <div class="price">${p.get('usd', 0):,.2f}</div>
              <div class="{css}">{change:+.2f}% (24h)</div>
            </div>"""
    else:
        cards = '<div class="card down">Price data unavailable right now. Try again shortly.</div>'

    content = f"""
     <h1>Welcome to Joshops Market Watchlist</h1>
   <!-- <p class="muted">Live prices from CoinGecko, cached in Redis for 60 seconds.</p> -->
    <div class="cards">{cards}</div>
    <div class="card">
      <div class="coin">BTC, last 1 hour</div>
      <canvas id="btcChart" height="120"></canvas>
    </div> 
   <!-- <p class="muted">Data provided by CoinGecko.</p> -->
    <script>
      fetch("/api/btc-chart") 
        .then(r => r.json())
        .then(d => {{
          new Chart(document.getElementById("btcChart"), {{
            type: "line",
            data: {{ labels: d.labels, datasets: [{{ data: d.values, borderColor: "#3fb950", pointRadius: 0, tension: 0.2 }}] }},
            options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ color: "#8b949e", maxTicksLimit: 7 }} }}, y: {{ ticks: {{ color: "#8b949e" }} }} }} }}
          }});
        }});
    </script>
    """
    return render_template_string(LAYOUT, content=content)


@app.route("/api/btc-chart")
def btc_chart():
    try:
        data = cached_get(
            "btc_chart_1h",
            "/coins/bitcoin/market_chart",
            {"vs_currency": "usd", "days": "1"},
            ttl=60,
        )
    except requests.RequestException:
        return jsonify({"labels": [], "values": []}), 503
    from datetime import datetime, timezone
    points = data.get("prices", [])[-12:]
    labels = [datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%d %b %H:%M") for ms, _ in points]
    values = [round(price, 2) for _, price in points]
    return jsonify({"labels": labels, "values": values})


@app.route("/count")
def count():
    visits = client.incr("visitor_count")
    content = f"""
    <h1>View Counter</h1>
    <div class="card">
      <div class="muted">You are viewer number</div>
      <div class="big">{visits}</div>
     <!-- <div class="muted">Stored in Redis, so it survives restarts.</div> -->
    </div> 
    """
    return render_template_string(LAYOUT, content=content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)