import httpx, os, uuid
from typing import Optional

MUBERT_API_KEY = os.getenv("MUBERT_API_KEY", "")
MUBERT_EMAIL = os.getenv("MUBERT_EMAIL", "")

DJ_STYLE_MAP = {
    "Martin Garrix": ["edm", "progressive-house", "uplifting", "festival"],
    "Tiësto": ["trance", "edm", "club", "big-room"],
    "Deadmau5": ["progressive-house", "techno", "dark", "minimal"],
    "Daft Punk": ["house", "french-house", "funk", "disco"],
    "Calvin Harris": ["edm", "pop", "future-house", "tropical"],
    "Avicii": ["progressive-house", "melodic", "folk-edm", "uplifting"],
    "David Guetta": ["edm", "pop", "electro-house", "club"],
    "Skrillex": ["dubstep", "bass", "electro", "trap"],
    "Marshmello": ["future-bass", "edm", "happy", "melodic"],
    "The Chainsmokers": ["future-house", "pop", "indie-dance"],
    "Hardwell": ["big-room", "hardstyle", "festival", "trance"],
    "Armin van Buuren": ["trance", "progressive-trance", "uplifting"],
    "Eric Prydz": ["progressive-house", "deep-tech", "minimal"],
    "Swedish House Mafia": ["progressive-house", "edm", "festival"],
    "Kygo": ["tropical-house", "chill", "melodic", "piano"],
    "Illenium": ["future-bass", "melodic-dubstep", "emotional"],
    "Zedd": ["electro-house", "complextro", "pop", "edm"],
    "Porter Robinson": ["future-bass", "ambient", "emotional", "dream"],
    "Disclosure": ["uk-garage", "house", "deep-house"],
    "Flume": ["future-bass", "experimental", "electronic"]
}

MOOD_MAP = {
    "energetic": ["uplifting", "festival", "hype"],
    "dark": ["dark", "minimal", "techno"],
    "euphoric": ["trance", "uplifting", "emotional"],
    "chill": ["ambient", "tropical", "deep"]
}


async def get_mubert_token() -> str:
    """Retrieve a Personal Access Token (PAT) from Mubert API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.mubert.com/v2/GetServiceAccess",
            json={
                "method": "GetServiceAccess",
                "params": {
                    "email": MUBERT_EMAIL,
                    "license": "ttmmubertlicense",
                    "token": MUBERT_API_KEY,
                    "mode": "loop"
                }
            }
        )
        data = resp.json()
        return data.get("data", {}).get("pat", "")


async def generate_track(style: str, duration: int = 60, mood: str = "energetic") -> dict:
    """
    Generate a music track via Mubert based on DJ style and mood.
    Returns dict with url, style, tags, duration.
    """
    tags = DJ_STYLE_MAP.get(style, ["edm", "progressive-house"])
    mood_tags = MOOD_MAP.get(mood, [])
    all_tags = list(set(tags + mood_tags))[:5]

    pat = await get_mubert_token()

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.mubert.com/v2/RecordTrackTTM",
            json={
                "method": "RecordTrackTTM",
                "params": {
                    "pat": pat,
                    "tags": all_tags,
                    "duration": duration,
                    "mode": "track",
                    "bitmask": 1
                }
            }
        )
        data = resp.json()
        track_url = data.get("data", {}).get("tasks", [{}])[0].get("download_link", "")
        return {
            "url": track_url,
            "style": style,
            "tags": all_tags,
            "duration": duration
        }
