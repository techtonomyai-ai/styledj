"""
Sound Match Engine — analyzes uploaded audio and maps to Mubert generation tags.
Uses librosa to extract BPM, energy, and spectral features.
"""
import io
import numpy as np

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


def analyze_audio(audio_bytes: bytes, filename: str = "track.mp3") -> dict:
    """
    Analyze audio file and return detected musical characteristics.
    Returns: bpm, energy, key, mood, tags, genre_guess
    """
    if not LIBROSA_AVAILABLE:
        return _fallback_analysis()

    try:
        y, sr = librosa.load(io.BytesIO(audio_bytes), duration=60, mono=True)

        # Tempo / BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo)

        # Energy (RMS)
        rms = librosa.feature.rms(y=y)[0]
        energy = float(np.mean(rms))
        energy_norm = min(1.0, energy * 20)  # normalize 0-1

        # Spectral centroid (brightness)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        brightness = float(np.mean(centroid)) / (sr / 2)

        # Zero crossing rate (percussive vs melodic)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = float(np.mean(zcr))

        # Key detection
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_idx = int(np.argmax(np.mean(chroma, axis=1)))
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        detected_key = keys[key_idx]

        # Genre mapping based on BPM + energy + brightness
        genre_guess, tags = _map_to_genre(bpm, energy_norm, brightness, zcr_mean)

        # Mood mapping
        mood = _detect_mood(energy_norm, brightness, bpm)

        return {
            "bpm": round(bpm, 1),
            "key": detected_key,
            "energy": round(energy_norm, 2),
            "brightness": round(brightness, 2),
            "mood": mood,
            "genre_guess": genre_guess,
            "tags": tags,
            "analysis_success": True
        }

    except Exception as e:
        return _fallback_analysis()


def _map_to_genre(bpm: float, energy: float, brightness: float, zcr: float) -> tuple:
    """Map audio features to EDM genre and Mubert tags."""

    if bpm < 80:
        return "Ambient / Downtempo", ["ambient", "atmospheric", "chill", "melodic"]

    elif bpm < 110:
        if energy < 0.4:
            return "Chillout / Lo-Fi", ["chill", "lofi", "ambient", "relaxed"]
        return "Tropical House / Chill", ["tropical-house", "chill", "melodic", "piano"]

    elif bpm < 120:
        if energy > 0.6:
            return "Nu-Disco / Funk", ["nu-disco", "funk", "groove", "dance"]
        return "Deep House", ["deep-house", "soulful", "melodic", "atmospheric"]

    elif bpm < 126:
        if brightness > 0.5:
            return "House / Tech House", ["tech-house", "house", "club", "driving"]
        return "Deep House / Organic", ["deep-house", "organic", "atmospheric"]

    elif bpm < 132:
        if energy > 0.7:
            return "Big Room / Festival EDM", ["big-room", "festival", "edm", "uplifting"]
        elif brightness > 0.5:
            return "Progressive House", ["progressive-house", "melodic", "uplifting"]
        return "Tech House", ["tech-house", "driving", "underground", "club"]

    elif bpm < 138:
        if energy > 0.7:
            return "Electro House", ["electro-house", "festival", "aggressive"]
        return "Trance / Progressive Trance", ["trance", "uplifting", "melodic", "emotional"]

    elif bpm < 145:
        if zcr > 0.1:
            return "Dubstep / Future Bass", ["dubstep", "bass", "future-bass", "melodic"]
        return "Uplifting Trance", ["uplifting-trance", "emotional", "epic", "melodic"]

    elif bpm < 155:
        if energy > 0.7:
            return "Dubstep / Riddim", ["dubstep", "riddim", "bass", "heavy"]
        return "Melodic Dubstep", ["melodic-dubstep", "emotional", "bass", "cinematic"]

    elif bpm < 170:
        if energy > 0.7:
            return "Drum & Bass", ["drum-and-bass", "bass", "energetic", "driving"]
        return "Liquid DnB", ["liquid-dnb", "melodic", "drum-and-bass", "atmospheric"]

    else:
        return "Hardstyle / Hardcore", ["hardstyle", "hardcore", "hard", "aggressive"]


def _detect_mood(energy: float, brightness: float, bpm: float) -> str:
    if energy > 0.7 and bpm > 128:
        return "energetic"
    elif brightness < 0.3 and energy > 0.5:
        return "dark"
    elif energy > 0.6 and brightness > 0.5:
        return "euphoric"
    elif bpm < 110 or energy < 0.3:
        return "chill"
    elif energy > 0.5:
        return "aggressive"
    return "energetic"


def _fallback_analysis() -> dict:
    return {
        "bpm": 128.0,
        "key": "A",
        "energy": 0.7,
        "brightness": 0.5,
        "mood": "energetic",
        "genre_guess": "Progressive House",
        "tags": ["progressive-house", "edm", "uplifting", "festival"],
        "analysis_success": False
    }
