from fastapi import FastAPI
import httpx
import time
app = FastAPI()
CACHE_TTL = 30  # seconds
cache = None
cache_expiry = 0
async def fetch_dexscreener():
    url = "https://api.dexscreener.com/latest/dex/search?q=meme"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return [
            {
                "token_address": p.get("tokenAddress"),
                "token_name": p.get("tokenName"),
                "token_ticker": p.get("tokenSymbol"),
                "price_sol": p.get("priceUsd"),
                "volume_sol": p.get("volume"),
            } for p in r.json().get("pairs", [])
        ]
async def fetch_geckoterminal():
    url = "https://api.geckoterminal.com/api/v2/networks/solana/tokens"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return [
            {
                "token_address": t.get("address"),
                "token_name": t.get("name"),
                "token_ticker": t.get("symbol"),
                "price_sol": t.get("price_usd"),
                "volume_sol": t.get("volume_24h"),
            } for t in r.json().get("data", {}).get("tokens", [])
        ]
def merge_tokens(list1, list2):
    tokens = {t["token_address"]: t for t in list1}
    for t in list2:
        if t["token_address"] in tokens:
            ex = tokens[t["token_address"]]
            ex["volume_sol"] = max(ex.get("volume_sol") or 0, t.get("volume_sol") or 0)
            ex["price_sol"] = t.get("price_sol") or ex.get("price_sol")
        else:
            tokens[t["token_address"]] = t
    return list(tokens.values())
async def get_tokens():
    global cache, cache_expiry
    now = time.time()
    if cache and now < cache_expiry:
        return cache
    dex = await fetch_dexscreener()
    geo = await fetch_geckoterminal()
    merged = merge_tokens(dex, geo)
    cache = merged
    cache_expiry = now + CACHE_TTL
    return merged
@app.get("/tokens")
async def tokens(limit: int = 20):
    data = await get_tokens()
    sorted_data = sorted(data, key=lambda t: t.get("volume_sol") or 0, reverse=True)
    return sorted_data[:limit]
