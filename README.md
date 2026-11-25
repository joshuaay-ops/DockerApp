# JayOps Watchlist

A multi container application that display's a market watchlist and tracks the views. It shows live prices for BTC, ETH, SOL, NVDA, AMD and PLTR, also the btc price chart.

The purpose of the project was the setup around it: multiple containers, a load balancer, caching and keeping secrets out of the repo.

## Objective

- Flask web app with two routes: a welcome page /count: increments and shows a visitor count stored which was stored in Redis.
- The Redis database: a key-value store that keeps track of the visitor count.
- Persistent storage: so the count survives after a restart.
- Dockerise both services:
  A Dockerfile for the Flask app and one for Redis.
  Docker Compose to manage the multi-container app.
- Environment variables - from .env with os.getenv() for Redis host and ports.
- Api call to display live market prices and btc chart.
- Redis caching of API responses 60s TTL(time to live) to stay under the rate limit.
- Scaling and load balancing: 5 Flask containers behind an NGINX load balancer.

Browser -> NGINX (port 8000) -> Flask app (5 containers) -> Redis -> CoinGecko API

## Stack

Python, Flask, Docker, Docker Compose, NGINX, Redis, CoinGecko API

## Running it

1. Clone the repo
2. Copy `.env.example` to `.env` (an API key is optional, the keyless CoinGecko API works)
3. Run:
   docker compose up --build --scale web=5 -d
4. Open http://localhost:8000
<p></p>
<p></p>
<img width="956" height="515" alt="image" src="https://github.com/user-attachments/assets/aca977a1-d1aa-4e7e-8b1f-c6105f9a6252" />

click on views to view the site visitor count page or visit http://localhost:8000/count
<p></p>
<p></p>
<img width="806" height="248" alt="image" src="https://github.com/user-attachments/assets/2d87a7b2-c76e-4a24-ba84-165fbbac4970" />



Check everything is up with `docker compose ps -a`.
  
## Troubleshooting/problems encountered

**Scaling the web app**
When I tried to run more than one web container with `--scale web=5`, only one would start. I got `port is already allocated`. This was because all the containers were trying to use port 8000 on my laptop, and only one container can have a port. I fixed it by taking the laptop port off the web service and adding NGINX in front, so NGINX is the only thing on port 8000 and it shares the traffic between the web containers.

**NGINX kept stopping**
After adding NGINX, `docker compose up` looked fine but the site didn't load. When I checked `docker compose ps -a`, NGINX had exited. The logs said `no "events" section in configuration`. My nginx.conf replaces the whole main config, so it needed an `events {}` block as well as `http {}`. I added it and NGINX started running.

**Redis wouldn't start**
I changed the Redis image from `redis:alpine` to `redis:7-alpine` and Redis crashed with `Can't handle RDB format version`. The data in my volume had been saved by Redis 8, and Redis 7 couldn't read it. I changed it to `redis:8-alpine` and my count was still there. I had to pin the version so it doesn't change by itself in future.
