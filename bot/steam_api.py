import re
import aiohttp
from . import settings

OWNED_GAMES_URL = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'
VANITY_URL = 'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/'

_STEAMID_RE = re.compile(r'\b(76\d{13,})\b')

async def normalize_to_steamid64(s: str) -> str:
    s = s.strip()
    m = _STEAMID_RE.search(s)
    if m:
        return m.group(1)
    # Try vanity: extract last URL segment if URL given
    vanity = s
    if 'http' in s:
        try:
            vanity = s.rstrip('/').split('/')[-1]
        except Exception:
            pass
    params = {'key': settings.STEAM_API_KEY, 'vanityurl': vanity}
    async with aiohttp.ClientSession() as sess:
        async with sess.get(VANITY_URL, params=params) as r:
            data = await r.json()
    if data.get('response', {}).get('success') == 1:
        return data['response']['steamid']
    raise ValueError('Could not parse SteamID64 or resolve vanity URL.')

async def get_owned_games(steamid: str):
    params = {
        'key': settings.STEAM_API_KEY,
        'steamid': steamid,
        'include_appinfo': 1,
        'include_played_free_games': 1,
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.get(OWNED_GAMES_URL, params=params) as r:
            j = await r.json()
    games = j.get('response', {}).get('games', []) or []
    # mark visibility for status
    visible = 'public' if games else 'private_or_empty'
    return games, visible
