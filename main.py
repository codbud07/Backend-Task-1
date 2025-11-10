from fastapi import FastAPI
import httpx

app = FastAPI()
cache = []
cache_expiry = 0
CACHE_TTL = 30  # seconds

async def fetch_dex_tokens():
    url = "https://api.dexscreener.com/latest/dex/search?q=meme"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        data = r.json()
        return [
            {
                "token_address": p.get("tokenAddress"),
                "token_name": p.get("tokenName"),
                "token_ticker": p.get("tokenSymbol"),
                "price_sol": p.get("priceUsd"),
                "volume_sol": p.get("volume"),
            }
            for p in data.get("pairs", [])
        ]

async def fetch_gecko_tokens():
    url = "https://api.geckoterminal.com/api/v2/networks/solana/tokens"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        data = r.json()
        return [
            {
                "token_address": t.get("address"),
                "token_name": t.get("name"),
                "token_ticker": t.get("symbol"),
                "price_sol": t.get("price_usd"),
                "volume_sol": t.get("volume_24h"),
            }
            for t in data.get("data", {}).get("tokens", [])
        ]

def merge_tokens(list1, list2):
    map_tokens = {t["token_address"]: t for t in list1}
    for t in list2:
        k = t["token_address"]
        if k in map_tokens:
            ex = map_tokens[k]
            ex["volume_sol"] = max(ex.get("volume_sol") or 0, t.get("volume_sol") or 0)
            ex["price_sol"] = t.get("price_sol") or ex.get("price_sol")
        else:
            map_tokens[k] = t
    return list(map_tokens.values())

import time
async def get_tokens():
    global cache, cache_expiry
    now = time.time()
    if cache and now < cache_expiry:
        return cache
    dex = await fetch_dex_tokens()
    geo = await fetch_gecko_tokens()
    merged = merge_tokens(dex, geo)
    cache = merged
    cache_expiry = now + CACHE_TTL
    return merged

@app.get("/tokens")
async def tokens(limit: int = 20):
    tokens = await get_tokens()
    tokens.sort(key=lambda t: t.get("volume_sol") or 0, reverse=True)
    return tokens[:limit]
