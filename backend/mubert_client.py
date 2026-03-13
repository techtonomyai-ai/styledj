import httpx, os, uuid
from typing import Optional

MUBERT_API_KEY = os.getenv("MUBERT_API_KEY", "")
MUBERT_EMAIL = os.getenv("MUBERT_EMAIL", "")

DJ_STYLE_MAP = {
    # --- PROGRESSIVE HOUSE / BIG ROOM ---
    "Martin Garrix":        ["edm", "progressive-house", "uplifting", "festival"],
    "Swedish House Mafia":  ["progressive-house", "edm", "festival", "anthem"],
    "Hardwell":             ["big-room", "festival", "trance", "uplifting"],
    "W&W":                  ["big-room", "edm", "festival", "trance"],
    "Nicky Romero":         ["progressive-house", "tech-house", "edm"],
    "Eric Prydz":           ["progressive-house", "deep-tech", "minimal", "hypnotic"],
    "deadmau5":             ["progressive-house", "techno", "dark", "minimal"],
    "Avicii":               ["progressive-house", "melodic", "folk-edm", "uplifting"],

    # --- TRANCE ---
    "Armin van Buuren":     ["trance", "progressive-trance", "uplifting"],
    "Tiësto":               ["trance", "edm", "club", "big-room"],
    "Paul van Dyk":         ["trance", "uplifting-trance", "melodic"],
    "Ferry Corsten":        ["trance", "tech-trance", "progressive"],
    "Andrew Rayel":         ["uplifting-trance", "melodic-trance", "emotional"],
    "KSHMR":                ["trance", "festival", "world", "epic"],

    # --- TECHNO ---
    "Charlotte de Witte":   ["techno", "dark", "industrial", "raw"],
    "Amelie Lens":          ["techno", "dark", "hypnotic", "driving"],
    "Adam Beyer":           ["techno", "industrial", "driving", "minimal"],
    "Reinier Zonneveld":    ["techno", "hard-techno", "industrial", "dark"],
    "Tale Of Us":           ["melodic-techno", "atmospheric", "dark", "emotional"],
    "Anyma":                ["melodic-techno", "afterlife", "dark", "cinematic"],

    # --- HOUSE / DEEP HOUSE ---
    "Daft Punk":            ["house", "french-house", "funk", "disco"],
    "Fisher":               ["tech-house", "driving", "club", "peak-time"],
    "Chris Lake":           ["tech-house", "deep-house", "club", "funky"],
    "John Summit":          ["tech-house", "driving", "club", "progressive"],
    "Disclosure":           ["uk-garage", "house", "deep-house", "soulful"],
    "Black Coffee":         ["afro-house", "deep-house", "organic", "minimal"],
    "Solomun":              ["deep-house", "melodic", "atmospheric", "club"],
    "Jamie Jones":          ["tech-house", "deep-house", "underground"],

    # --- ELECTRO / FRENCH ---
    "Calvin Harris":        ["edm", "pop", "future-house", "tropical"],
    "David Guetta":         ["edm", "pop", "electro-house", "club"],
    "Zedd":                 ["electro-house", "complextro", "pop", "edm"],
    "Gesaffelstein":        ["dark-electro", "industrial", "techno", "dark"],
    "Justice":              ["electro", "french-house", "rock-edm", "distorted"],

    # --- FUTURE BASS / MELODIC ---
    "Marshmello":           ["future-bass", "edm", "happy", "melodic"],
    "Illenium":             ["future-bass", "melodic-dubstep", "emotional"],
    "Porter Robinson":      ["future-bass", "ambient", "emotional", "dream"],
    "Flume":                ["future-bass", "experimental", "electronic"],
    "San Holo":             ["future-bass", "indie-dance", "guitar", "emotional"],
    "Lane 8":               ["melodic-house", "deep-house", "emotional", "journey"],

    # --- DUBSTEP / BASS ---
    "Skrillex":             ["dubstep", "bass", "electro", "trap"],
    "Excision":             ["riddim", "heavy-dubstep", "bass", "dark"],
    "Virtual Riot":         ["dubstep", "bass", "experimental", "heavy"],
    "Subtronics":           ["riddim", "bass", "heavy", "dark"],

    # --- DRUM & BASS ---
    "Chase & Status":       ["drum-and-bass", "bass", "uk-garage", "grime"],
    "Pendulum":             ["drum-and-bass", "rock-dnb", "festival", "energetic"],
    "Sub Focus":            ["drum-and-bass", "liquid-dnb", "melodic", "uplifting"],

    # --- TRAP / FUTURE ---
    "RL Grime":             ["trap", "future-trap", "bass", "dark"],
    "Baauer":               ["trap", "experimental", "bass", "club"],

    # --- CHILL / TROPICAL ---
    "Kygo":                 ["tropical-house", "chill", "melodic", "piano"],
    "The Chainsmokers":     ["future-house", "pop", "indie-dance"],
}

MOOD_MAP = {
    "energetic":    ["uplifting", "festival", "hype", "driving"],
    "dark":         ["dark", "minimal", "techno", "industrial"],
    "euphoric":     ["trance", "uplifting", "emotional", "anthem"],
    "chill":        ["ambient", "tropical", "deep", "melodic"],
    "aggressive":   ["heavy", "bass", "industrial", "raw"],
    "underground":  ["minimal", "deep", "hypnotic", "dark"],
}


async def get_mubert_token() -> str:
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
