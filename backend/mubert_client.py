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

# Additional artists added in v2
DJ_STYLE_MAP.update({
    "Above & Beyond":       ["trance", "progressive-trance", "emotional", "uplifting"],
    "Dash Berlin":          ["trance", "uplifting-trance", "melodic"],
    "SPFDJ":                ["hard-techno", "techno", "industrial", "dark"],
    "I Hate Models":        ["techno", "industrial", "dark", "raw"],
    "Massano":              ["melodic-techno", "afterlife", "dark", "cinematic"],
    "Innellea":             ["melodic-techno", "organic", "atmospheric"],
    "Stephan Bodzin":       ["melodic-techno", "hypnotic", "driving", "dark"],
    "MK":                   ["house", "uk-garage", "deep-house", "soulful"],
    "Todd Terry":           ["house", "classic-house", "club", "soulful"],
    "Larry Heard":          ["deep-house", "chicago-house", "ambient", "spiritual"],
    "Marshall Jefferson":   ["chicago-house", "gospel-house", "classic"],
    "Patrick Topping":      ["tech-house", "driving", "underground"],
    "Hot Since 82":         ["tech-house", "deep-house", "club"],
    "Kerri Chandler":       ["deep-house", "soulful", "classic"],
    "Themba":               ["afro-house", "deep-house", "organic"],
    "Enoo Napa":            ["afro-house", "dark", "tribal"],
    "Hromoy":               ["organic-house", "afro-house", "melodic"],
    "Justice":              ["electro", "french-house", "rock-edm", "distorted"],
    "Boys Noize":           ["electro", "techno", "dark", "industrial"],
    "DJ Pierre":            ["acid-house", "chicago-house", "classic"],
    "Aphex Twin":           ["acid-techno", "experimental", "ambient", "idm"],
    "Luke Vibert":          ["acid", "breakbeat", "experimental"],
    "Slushii":              ["future-bass", "melodic", "happy"],
    "Svdden Death":         ["riddim", "heavy-dubstep", "dark", "bass"],
    "Zomboy":               ["dubstep", "bass", "heavy", "energetic"],
    "Andy C":               ["drum-and-bass", "liquid-dnb", "technical"],
    "Goldie":               ["jungle", "drum-and-bass", "classic", "atmospheric"],
    "Roni Size":            ["drum-and-bass", "jazz-dnb", "classic"],
    "MJ Cole":              ["uk-garage", "2-step", "soulful"],
    "Craig David":          ["uk-garage", "2-step", "soulful", "pop"],
    "Artful Dodger":        ["uk-garage", "2-step", "classic"],
    "Flosstradamus":        ["trap", "festival-trap", "bass"],
    "UZ":                   ["trap", "future-trap", "bass", "dark"],
    "Thomas Jack":          ["tropical-house", "chill", "melodic"],
    "Klingande":            ["tropical-house", "saxophone-house", "chill"],
    "Tycho":                ["ambient", "downtempo", "chillwave", "instrumental"],
    "Bonobo":               ["downtempo", "ambient", "jazz", "electronic"],
    "Boards of Canada":     ["ambient", "idm", "nostalgic", "atmospheric"],
    "Brian Eno":            ["ambient", "experimental", "atmospheric"],
    "Parcels":              ["nu-disco", "funk", "indie-dance"],
    "Chromeo":              ["nu-disco", "funk", "electro-pop"],
    "Tensnake":             ["nu-disco", "deep-house", "funk"],
    "Todd Terje":           ["nu-disco", "italo-disco", "funk"],
    "Headhunterz":          ["hardstyle", "festival", "uplifting"],
    "Brennan Heart":        ["hardstyle", "emotional-hardstyle", "uplifting"],
    "Zatox":                ["hardcore", "hardstyle", "energetic"],
    "Angerfist":            ["hardcore", "industrial", "dark", "aggressive"],
    "The Prodigy":          ["breakbeat", "rave", "big-beat", "aggressive"],
    "Crystal Method":       ["breakbeat", "big-beat", "electro"],
    "Fatboy Slim":          ["big-beat", "breakbeat", "funk", "house"],
    "Chemical Brothers":    ["big-beat", "breakbeat", "techno", "rock-edm"],
})

# Full genre expansion v3 — all EDM genres
DJ_STYLE_MAP.update({
    # Minimal Techno
    "Ricardo Villalobos":   ["minimal-techno", "micro-house", "hypnotic", "underground"],
    "Richie Hawtin":        ["minimal-techno", "techno", "dark", "industrial"],
    "Plastikman":           ["minimal-techno", "acid", "hypnotic", "dark"],
    "Robert Hood":          ["minimal-techno", "detroit-techno", "functional", "dark"],
    # Psytrance / Goa
    "Astrix":               ["psytrance", "goa", "psychedelic", "festival"],
    "Infected Mushroom":    ["psytrance", "progressive-psytrance", "psychedelic"],
    "Vini Vici":            ["full-on-psytrance", "festival", "uplifting", "psychedelic"],
    "Ace Ventura":          ["progressive-psytrance", "melodic", "psychedelic"],
    "Shpongle":             ["psybient", "ambient", "psychedelic", "world"],
    # Grime
    "Skepta":               ["grime", "uk-hip-hop", "bass", "urban"],
    "Wiley":                ["grime", "uk-garage", "urban", "bass"],
    "Dizzee Rascal":        ["grime", "uk-hip-hop", "energetic", "urban"],
    "JME":                  ["grime", "uk-hip-hop", "bass", "underground"],
    # Amapiano
    "DJ Maphorisa":         ["amapiano", "afro-house", "log-drum", "south-african"],
    "Kabza De Small":       ["amapiano", "piano", "afro-house", "melodic"],
    "DBN Gogo":             ["amapiano", "gqom", "afro-house", "energetic"],
    "Njelic":               ["amapiano", "melodic", "afro-house", "soulful"],
    # Baile Funk
    "DJ Marlboro":          ["baile-funk", "funk-carioca", "bass", "brazilian"],
    "MC Kevinho":           ["baile-funk", "pop-funk", "bass", "energetic"],
    "Anitta":               ["baile-funk", "pop", "latin", "energetic"],
    # Balearic Beat
    "Jose Padilla":         ["balearic", "ambient", "chill", "sunset"],
    "Ibizan Style":         ["balearic", "house", "chill", "atmospheric"],
    "Alex Paterson":        ["balearic", "ambient", "psychedelic", "atmospheric"],
    # Bhangra
    "Panjabi MC":           ["bhangra", "indian", "folk", "energetic"],
    "RDB":                  ["bhangra", "desi-pop", "indian", "urban"],
    "Surjit Bindrakhia":    ["bhangra", "traditional", "folk", "indian"],
    # IDM / Experimental
    "Autechre":             ["idm", "experimental", "glitch", "abstract"],
    "Squarepusher":         ["idm", "drum-and-bass", "jazz", "experimental"],
    "Arca":                 ["experimental", "avant-garde", "club", "abstract"],
    "Four Tet":             ["idm", "folktronica", "ambient", "melodic"],
    # Bass House
    "Dr. Fresch":           ["bass-house", "tech-house", "driving", "club"],
    "AC Slater":            ["bass-house", "night-bass", "driving", "club"],
    "Valentino Khan":       ["bass-house", "trap-house", "festival", "bass"],
    "Tchami":               ["bass-house", "future-house", "driving", "dark"],
    # Jazz Fusion / Electronica
    "GoGo Penguin":         ["jazz", "electronic", "piano", "melodic"],
    "Alfa Mist":            ["jazz-fusion", "electronic", "soulful", "melodic"],
    "Hiatus Kaiyote":       ["neo-soul", "electronic", "jazz", "soulful"],
    # Moombahton / Latin
    "Dave Nada":            ["moombahton", "reggaeton", "bass", "latin"],
    "Dillon Francis":       ["moombahton", "trap", "bass", "festival"],
    "DJ Snake":             ["latin-edm", "trap", "festival", "pop"],
    "Bad Bunny Style":      ["reggaeton", "latin-trap", "bass", "urban"],
    # Industrial / EBM
    "Nine Inch Nails":      ["industrial", "ebm", "dark", "rock"],
    "HEALTH":               ["industrial", "noise", "dark", "aggressive"],
    "Skinny Puppy":         ["ebm", "industrial", "dark", "electronic"],
    "Front Line Assembly":  ["ebm", "industrial", "futuristic", "dark"],
})
