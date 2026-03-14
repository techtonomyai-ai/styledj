"""Mubert AI Music API v3 integration for StyleDJ."""
import httpx, os, asyncio
from typing import Optional

MUBERT_COMPANY_ID = os.getenv("MUBERT_COMPANY_ID", "")
MUBERT_LICENSE_TOKEN = os.getenv("MUBERT_LICENSE_TOKEN", "")

MUBERT_BASE = "https://music-api.mubert.com/api/v3"

def company_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "company-id": MUBERT_COMPANY_ID,
        "license-token": MUBERT_LICENSE_TOKEN,
    }

def customer_headers(customer_id: str, access_token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "customer-id": customer_id,
        "access-token": access_token,
    }

# ------------------------------------------------------------------ #
# DJ → Mubert tag mapping
# ------------------------------------------------------------------ #
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

DJ_STYLE_MAP.update({
    "Above & Beyond":       ["trance", "progressive-trance", "emotional", "uplifting"],
    "Dash Berlin":          ["trance", "uplifting-trance", "melodic"],
    "Markus Schulz":        ["trance", "progressive-trance", "dark", "atmospheric"],
    "Cosmic Gate":          ["trance", "progressive-trance", "melodic"],
    "Aly & Fila":           ["uplifting-trance", "goa-trance", "emotional"],
    "Boris Brejcha":        ["minimal-techno", "freak-show", "dark", "hypnotic"],
    "Maceo Plex":           ["techno", "deep-techno", "dark", "hypnotic"],
    "Adriatique":           ["melodic-techno", "deep-house", "atmospheric"],
    "Stephan Bodzin":       ["melodic-techno", "dark", "cinematic", "hypnotic"],
    "Nina Kraviz":          ["techno", "acid", "dark", "underground"],
    "Dense & Pika":         ["techno", "industrial", "hard-techno", "dark"],
    "KiNK":                 ["techno", "acid", "experimental", "live"],
    "DJ Koze":              ["deep-house", "indie-dance", "eclectic", "melodic"],
    "Peggy Gou":            ["techno", "disco", "house", "fun"],
    "Mind Against":         ["melodic-techno", "deep", "atmospheric", "dark"],
    "Innellea":             ["melodic-techno", "emotional", "cinematic"],
    "CamelPhat":            ["tech-house", "progressive", "dark", "deep"],
    "Hot Since 82":         ["tech-house", "deep-house", "driving", "progressive"],
    "Patrick Topping":      ["tech-house", "driving", "underground", "club"],
    "Gorgon City":          ["uk-garage", "house", "deep-house", "soulful"],
    "Eats Everything":      ["tech-house", "driving", "club", "funky"],
    "Richy Ahmed":          ["tech-house", "deep-house", "dark", "underground"],
    "DJ Harvey":            ["disco", "house", "eclectic", "classic"],
    "Larry Heard":          ["deep-house", "chicago-house", "soulful", "classic"],
    "Frankie Knuckles":     ["house", "chicago-house", "classic", "soulful"],
    "Ron Hardy":            ["house", "chicago-house", "underground", "classic"],
    "Larry Levan":          ["garage-house", "deep-house", "soulful", "classic"],
    "Honey Dijon":          ["house", "disco", "funky", "club"],
    "Artwork":              ["electro-house", "big-room", "festival", "energetic"],
    "Boys Noize":           ["electro", "techno", "dark", "industrial"],
    "Crookers":             ["electro-house", "hip-hop", "funky", "bass"],
    "Bakermat":             ["deep-house", "nu-disco", "soulful", "melodic"],
    "Oliver":               ["french-house", "electro", "funky", "disco"],
    "Club Cheval":          ["french-house", "electro", "dark", "club"],
    "Thomass Jackson":      ["deep-house", "disco", "soulful", "melodic"],
    "Bicep":                ["melodic-house", "trance", "emotional", "club"],
    "Mall Grab":            ["lo-fi-house", "underground", "raw", "club"],
    "DJ Stingray":          ["electro", "techno", "futuristic", "dark"],
    "Rustie":               ["future-bass", "club", "electronic", "experimental"],
    "Spor":                 ["drum-and-bass", "neurofunk", "dark", "heavy"],
    "Andy C":               ["drum-and-bass", "liquid-dnb", "energetic", "club"],
    "Noisia":               ["drum-and-bass", "neurofunk", "dark", "heavy"],
    "Logistics":            ["liquid-dnb", "melodic", "uplifting", "drum-and-bass"],
    "Hybrid Minds":         ["liquid-dnb", "melodic", "emotional", "drum-and-bass"],
    "Skeptical":            ["drum-and-bass", "deep", "dark", "underground"],
    "Camo & Krooked":       ["drum-and-bass", "melodic", "festival", "energetic"],
    "High Contrast":        ["liquid-dnb", "soulful", "melodic", "drum-and-bass"],
    "LTJ Bukem":            ["liquid-dnb", "atmospheric", "jazz", "drum-and-bass"],
    "Goldie":               ["drum-and-bass", "jungle", "classic", "dark"],
    "DJ Hype":              ["drum-and-bass", "jump-up", "energetic", "rave"],
    "Shy FX":               ["drum-and-bass", "jungle", "uk-garage", "bass"],
    "General Levy":         ["jungle", "ragga", "bass", "classic"],
    "Todd Terry":           ["house", "uk-garage", "classic", "driving"],
    "MJ Cole":              ["uk-garage", "2-step", "soulful", "melodic"],
    "Craig David":          ["uk-garage", "2-step", "r&b", "soulful"],
    "El-B":                 ["uk-garage", "grime", "dark", "underground"],
    "Skepta":               ["grime", "uk-hip-hop", "bass", "urban"],
    "Wiley":                ["grime", "uk-garage", "urban", "bass"],
    "Dizzee Rascal":        ["grime", "uk-hip-hop", "energetic", "urban"],
    "JME":                  ["grime", "uk-hip-hop", "bass", "underground"],
    "DJ Maphorisa":         ["amapiano", "afro-house", "log-drum", "south-african"],
    "Kabza De Small":       ["amapiano", "piano", "afro-house", "melodic"],
    "DBN Gogo":             ["amapiano", "gqom", "afro-house", "energetic"],
    "Njelic":               ["amapiano", "melodic", "afro-house", "soulful"],
    "DJ Marlboro":          ["baile-funk", "funk-carioca", "bass", "brazilian"],
    "MC Kevinho":           ["baile-funk", "pop-funk", "bass", "energetic"],
    "Anitta":               ["baile-funk", "pop", "latin", "energetic"],
    "Jose Padilla":         ["balearic", "ambient", "chill", "sunset"],
    "Panjabi MC":           ["bhangra", "indian", "folk", "energetic"],
    "RDB":                  ["bhangra", "desi-pop", "indian", "urban"],
    "Aphex Twin":           ["idm", "experimental", "ambient", "glitch"],
    "Autechre":             ["idm", "experimental", "glitch", "abstract"],
    "Squarepusher":         ["idm", "drum-and-bass", "jazz", "experimental"],
    "Arca":                 ["experimental", "avant-garde", "club", "abstract"],
    "Four Tet":             ["idm", "folktronica", "ambient", "melodic"],
    "Dr. Fresch":           ["bass-house", "tech-house", "driving", "club"],
    "AC Slater":            ["bass-house", "night-bass", "driving", "club"],
    "Valentino Khan":       ["bass-house", "trap-house", "festival", "bass"],
    "Tchami":               ["bass-house", "future-house", "driving", "dark"],
    "Bonobo":               ["downtempo", "electronica", "jazz", "melodic"],
    "GoGo Penguin":         ["jazz", "electronic", "piano", "melodic"],
    "Dave Nada":            ["moombahton", "reggaeton", "bass", "latin"],
    "Dillon Francis":       ["moombahton", "trap", "bass", "festival"],
    "DJ Snake":             ["latin-edm", "trap", "festival", "pop"],
    "Nine Inch Nails":      ["industrial", "ebm", "dark", "rock"],
    "HEALTH":               ["industrial", "noise", "dark", "aggressive"],
    "Ricardo Villalobos":   ["minimal-techno", "micro-house", "hypnotic", "underground"],
    "Richie Hawtin":        ["minimal-techno", "techno", "dark", "industrial"],
    "Plastikman":           ["minimal-techno", "acid", "hypnotic", "dark"],
    "Robert Hood":          ["minimal-techno", "detroit-techno", "functional", "dark"],
    "Astrix":               ["psytrance", "goa", "psychedelic", "festival"],
    "Infected Mushroom":    ["psytrance", "progressive-psytrance", "psychedelic"],
    "Vini Vici":            ["full-on-psytrance", "festival", "uplifting", "psychedelic"],
    "Ace Ventura":          ["progressive-psytrance", "melodic", "psychedelic"],
    "Shpongle":             ["psybient", "ambient", "psychedelic", "world"],
})

MOOD_MAP = {
    "energetic":    ["uplifting", "festival", "hype", "driving"],
    "dark":         ["dark", "minimal", "techno", "industrial"],
    "euphoric":     ["trance", "uplifting", "emotional", "anthem"],
    "chill":        ["ambient", "tropical", "deep", "melodic"],
    "aggressive":   ["heavy", "bass", "industrial", "raw"],
    "underground":  ["minimal", "deep", "hypnotic", "dark"],
}

DEMO_TRACKS = {
    "energetic":  "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "dark":       "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "euphoric":   "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "chill":      "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3",
    "aggressive": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
    "default":    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
}

def _demo_track(mood: str, style: str, all_tags: list, duration: int) -> dict:
    url = DEMO_TRACKS.get(mood or "default", DEMO_TRACKS["default"])
    return {"url": url, "style": style, "tags": all_tags, "duration": duration, "demo": True}


async def get_or_create_customer(user_id: str) -> tuple[str, str]:
    """Get or create a Mubert customer for this user. Returns (customer_id, access_token)."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{MUBERT_BASE}/service/customers",
            headers=company_headers(),
            json={"custom_id": user_id}
        )
        data = resp.json()
        customer = data.get("data", {})
        cid = customer.get("id", "")
        token = (customer.get("access") or {}).get("token", "")
        return cid, token


async def generate_track(style: str, duration: int = 60, mood: str = "energetic", user_id: str = "anonymous") -> dict:
    try:
        tags = DJ_STYLE_MAP.get(style) or ["edm", "progressive-house"]
        mood_tags = MOOD_MAP.get(mood) or []
        all_tags = list(set(tags + mood_tags))[:5]
    except Exception:
        all_tags = ["edm", "progressive-house"]

    if not MUBERT_COMPANY_ID or not MUBERT_LICENSE_TOKEN or os.getenv("DEMO_MODE", "").lower() in ("true", "1"):
        return _demo_track(mood, style, all_tags, duration)

    try:
        # 1. Register/get customer token
        cid, access_token = await get_or_create_customer(user_id)
        if not cid or not access_token:
            return _demo_track(mood, style, all_tags, duration)

        # 2. Generate track via prompt (v3 TTM)
        prompt = " ".join(all_tags) + f" {style} music"
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{MUBERT_BASE}/public/tracks",
                headers=customer_headers(cid, access_token),
                json={
                    "prompt": prompt,
                    "duration": duration,
                    "mode": "track",
                    "intensity": "high",
                    "format": "mp3",
                    "bitrate": 128
                }
            )
            data = resp.json()
            track_data = data.get("data", {})
            track = track_data[0] if isinstance(track_data, list) else track_data
            track_id = track.get("id", "")

            if not track_id:
                return _demo_track(mood, style, all_tags, duration)

            # 3. Poll for completion (up to 80s)
            for _ in range(20):
                await asyncio.sleep(4)
                poll = await client.get(
                    f"{MUBERT_BASE}/public/tracks/{track_id}",
                    headers=customer_headers(cid, access_token)
                )
                pd_raw = poll.json().get("data", {})
                pd = pd_raw[0] if isinstance(pd_raw, list) else pd_raw
                gens = pd.get("generations", [])
                if gens:
                    url = gens[0].get("url", "")
                    if url:
                        return {"url": url, "style": style, "tags": all_tags, "duration": duration}

        return _demo_track(mood, style, all_tags, duration)
    except Exception as e:
        print(f"Mubert error: {e}")
        return _demo_track(mood, style, all_tags, duration)
