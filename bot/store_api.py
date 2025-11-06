import json
import time
import aiohttp
from pathlib import Path

APPDETAILS = 'https://store.steampowered.com/api/appdetails'
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
CACHE_FILE = DATA_DIR / 'app_cache.json'
CACHE_TTL = 30 * 24 * 3600  # 30 days

DATA_DIR.mkdir(exist_ok=True)

def _load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text('utf-8'))
        except Exception:
            return {}
    return {}

def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache), encoding='utf-8')

async def get_app_meta(appid: int) -> dict:
    cache = _load_cache()
    now = time.time()
    key = str(appid)
    hit = cache.get(key)
    if hit and now - hit.get('_ts', 0) < CACHE_TTL:
        return hit
    async with aiohttp.ClientSession() as sess:
        async with sess.get(APPDETAILS, params={'appids': appid, 'cc': 'us', 'l': 'en'}) as r:
            data = await r.json()
    node = data.get(str(appid), {})
    info = {'name': None, 'categories': []}
    if node.get('success'):
        d = node.get('data', {})
        info['name'] = d.get('name')
        info['categories'] = [c.get('description') for c in (d.get('categories') or []) if c.get('description')]
    info['_ts'] = now
    cache[key] = info
    _save_cache(cache)
    return info
