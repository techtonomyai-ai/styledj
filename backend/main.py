import os, uuid, hashlib, sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request, UploadFile, File, Form
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import stripe
import jwt as pyjwt
from dotenv import load_dotenv
try:
    from backend.mubert_client import generate_track
except ImportError:
    from mubert_client import generate_track

load_dotenv()

app = FastAPI(title="StyleDJ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "styledj-secret-change-me")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

# --- DB Setup ---
DB_PATH = "styleDJ.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

ADMIN_EMAILS = ["techtonomyllc@gmail.com", "techtonomy.ai@gmail.com"]

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        subscribed INTEGER DEFAULT 0,
        trial_start TEXT,
        stripe_customer_id TEXT,
        email_verified INTEGER DEFAULT 0,
        verify_token TEXT,
        reset_token TEXT,
        reset_token_expires TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tracks (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        style TEXT,
        duration INTEGER,
        mood TEXT,
        file_url TEXT,
        tags TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()

def ensure_admin_subscribed():
    """Keep admin accounts subscribed across redeploys — INSERT if not exists, UPDATE if exists."""
    conn = get_db()
    for email in ADMIN_EMAILS:
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            conn.execute("UPDATE users SET subscribed=1 WHERE email=?", (email,))
        else:
            import uuid as _uuid
            new_id = str(_uuid.uuid4())
            # Default password hash for "techtonomy2026" — admin can reset via forgot password
            pw_hash = hash_password("techtonomy2026")
            conn.execute(
                "INSERT INTO users (id, email, password_hash, subscribed, trial_start) VALUES (?,?,?,1,?)",
                (new_id, email, pw_hash, datetime.utcnow().isoformat())
            )
    conn.commit()
    conn.close()

# --- Auth ---
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

ensure_admin_subscribed()

def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.utcnow() + timedelta(days=30)}
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def is_subscribed(user_id: str) -> bool:
    conn = get_db()
    user = conn.execute("SELECT subscribed, trial_start FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not user:
        return False
    if user["subscribed"]:
        return True
    # 7-day free trial
    if user["trial_start"]:
        trial_start = datetime.fromisoformat(user["trial_start"])
        if datetime.utcnow() - trial_start < timedelta(days=3):
            return True
    return False

# --- Models ---
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GenerateRequest(BaseModel):
    style: str = "Martin Garrix"
    duration: int = 60
    mood: str = "energetic"

class CheckoutRequest(BaseModel):
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok", "app": "StyleDJ"}

@app.get("/")
async def root():
    index = Path(__file__).parent.parent / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "StyleDJ API is running", "version": "1.0.0"}

@app.post("/register")
async def register(req: RegisterRequest):
    conn = get_db()
    user_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, trial_start, subscribed) VALUES (?,?,?,?,?)",
            (user_id, req.email, hash_password(req.password), datetime.utcnow().isoformat(),
             1 if req.email.lower() in [e.lower() for e in ADMIN_EMAILS] else 0)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        conn.close()
    return {"token": create_token(user_id), "user_id": user_id}

@app.post("/forgot-password")
async def forgot_password(req: LoginRequest):
    try:
        from backend.email_service import send_password_reset_email
    except ImportError:
        from email_service import send_password_reset_email
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}
    reset_token = str(uuid.uuid4())
    expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    conn.execute("UPDATE users SET reset_token=?, reset_token_expires=? WHERE email=?",
                 (reset_token, expires, req.email))
    conn.commit()
    send_password_reset_email(req.email, reset_token)
    return {"message": "If that email exists, a reset link has been sent."}


@app.post("/reset-password")
async def reset_password(token: str, new_password: str):
    conn = get_db()
    user = conn.execute("SELECT id, reset_token_expires FROM users WHERE reset_token=?", (token,)).fetchone()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")
    if datetime.fromisoformat(user["reset_token_expires"]) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")
    conn.execute("UPDATE users SET password_hash=?, reset_token=NULL, reset_token_expires=NULL WHERE reset_token=?",
                 (hash_password(new_password), token))
    conn.commit()
    return {"message": "Password updated! You can now log in."}


@app.get("/verify")
async def verify_email(token: str):
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE verify_token=?", (token,)).fetchone()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification link.")
    conn.execute("UPDATE users SET email_verified=1, verify_token=NULL WHERE verify_token=?", (token,))
    conn.commit()
    return FileResponse(str(Path(__file__).parent.parent / "frontend" / "index.html"))


@app.post("/login")
async def login(req: LoginRequest):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password_hash=?",
        (req.email, hash_password(req.password))
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(user["id"]), "user_id": user["id"]}

@app.get("/me")
async def me(user_id: str = Depends(verify_token)):
    conn = get_db()
    user = conn.execute("SELECT id, email, subscribed, trial_start, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user["id"],
        "email": user["email"],
        "subscribed": bool(user["subscribed"]),
        "on_trial": not user["subscribed"] and is_subscribed(user_id),
        "created_at": user["created_at"]
    }

class LyricsRequest(BaseModel):
    style: str
    theme: str = ""
    mood: str = "energetic"

class VocalsRequest(BaseModel):
    lyrics: str
    style: str
    mood: str = "energetic"
    voice: str = "nova"        # OpenAI TTS voices: alloy, echo, fable, nova, onyx, shimmer
    duration: int = 120
    music_volume: float = 0.35  # music at 35%, vocals at 100%

@app.post("/lyrics")
async def generate_lyrics(req: LyricsRequest, user_id: str = Depends(verify_token)):
    if not is_subscribed(user_id):
        raise HTTPException(status_code=402, detail="Subscription required.")
    try:
        import httpx as _httpx
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured.")
        theme_line = f"Theme/vibe: {req.theme}" if req.theme else "Theme: freedom, energy, the night"
        prompt = f"""Write song lyrics for an EDM track in the style of {req.style}.
{theme_line}
Mood: {req.mood}

Format:
[Verse 1]
(4-6 lines)

[Pre-Chorus]
(2-4 lines)

[Chorus]
(4-6 lines, memorable and repeated)

[Verse 2]
(4-6 lines)

[Chorus]
(repeat)

[Outro]
(2-4 lines)

Make them punchy, emotional, festival-ready. Use simple words that sound great when sung."""
        async with _httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}"},
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 600}
            )
        result = resp.json()
        lyrics = result["choices"][0]["message"]["content"]
        return {"lyrics": lyrics, "style": req.style, "theme": req.theme}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lyrics generation failed: {str(e)}")


@app.post("/vocals")
async def generate_with_vocals(req: VocalsRequest, user_id: str = Depends(verify_token)):
    """Generate a music track and mix AI vocals singing the lyrics over it."""
    if not is_subscribed(user_id):
        raise HTTPException(status_code=402, detail="Subscription required.")

    import tempfile, subprocess, httpx as _httpx

    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    # Step 1: Generate music track via Mubert
    try:
        from backend.mubert_client import generate_track as gen
    except ImportError:
        from mubert_client import generate_track as gen

    music_result = await gen(req.style, req.duration, req.mood)
    music_url = music_result.get("url", "")
    if not music_url:
        raise HTTPException(status_code=500, detail="Music generation failed.")

    with tempfile.TemporaryDirectory() as tmpdir:
        music_path  = os.path.join(tmpdir, "music.mp3")
        vocals_path = os.path.join(tmpdir, "vocals.mp3")
        output_path = os.path.join(tmpdir, "mixed.mp3")

        # Step 2: Download music
        async with _httpx.AsyncClient(timeout=60) as client:
            r = await client.get(music_url)
            with open(music_path, "wb") as f:
                f.write(r.content)

        # Step 3: Generate vocals via OpenAI TTS
        clean_lyrics = req.lyrics.replace('[Verse 1]','').replace('[Pre-Chorus]','') \
            .replace('[Chorus]','').replace('[Verse 2]','').replace('[Bridge]','') \
            .replace('[Outro]','').replace('[Hook]','').strip()
        # Keep it under 4096 chars (OpenAI TTS limit)
        clean_lyrics = clean_lyrics[:4000]

        async with _httpx.AsyncClient(timeout=60) as client:
            tts_resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={"model": "tts-1", "input": clean_lyrics, "voice": req.voice, "speed": 0.95}
            )
            if tts_resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"TTS failed: {tts_resp.text[:200]}")
            with open(vocals_path, "wb") as f:
                f.write(tts_resp.content)

        # Step 4: Mix with ffmpeg — loop music, vocals on top
        music_vol = req.music_volume
        vocals_vol = 1.0
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", music_path,   # loop music
            "-i", vocals_path,                          # vocals
            "-filter_complex",
            f"[0:a]volume={music_vol}[bg];[1:a]volume={vocals_vol}[fg];[bg][fg]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-codec:a", "libmp3lame", "-b:a", "192k",
            "-t", str(req.duration),
            output_path
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Mix failed: {result.stderr.decode()[:300]}")

        # Step 5: Upload mixed file — serve from memory via base64 or store temporarily
        with open(output_path, "rb") as f:
            mixed_bytes = f.read()

    # Save track record
    track_id = str(uuid.uuid4())
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO tracks (id, user_id, style, duration, mood, file_url, tags) VALUES (?,?,?,?,?,?,?)",
            (track_id, user_id, f"Vocals: {req.style}", req.duration, req.mood, music_url, req.voice)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Return mixed audio as base64 so frontend can play/download directly
    import base64
    audio_b64 = base64.b64encode(mixed_bytes).decode()
    return {
        "track_id": track_id,
        "audio_b64": audio_b64,
        "style": req.style,
        "voice": req.voice,
        "duration": req.duration,
        "music_url": music_url  # fallback instrumental
    }


@app.post("/generate")
async def generate(req: GenerateRequest, user_id: str = Depends(verify_token)):
    if not is_subscribed(user_id):
        raise HTTPException(status_code=402, detail="Subscription required. Start your free trial.")
    try:
        result = await generate_track(req.style, req.duration, req.mood)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Music generation failed: {str(e)}")
    track_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO tracks (id, user_id, style, duration, mood, file_url, tags) VALUES (?,?,?,?,?,?,?)",
        (track_id, user_id, req.style, req.duration, req.mood, result["url"], ",".join(result.get("tags", [])))
    )
    conn.commit()
    conn.close()
    return {"track_id": track_id, "download_url": result["url"], "style": req.style, "tags": result.get("tags", []), "duration": req.duration}

@app.get("/track/{track_id}")
async def get_track(track_id: str, user_id: str = Depends(verify_token)):
    conn = get_db()
    track = conn.execute("SELECT * FROM tracks WHERE id=? AND user_id=?", (track_id, user_id)).fetchone()
    conn.close()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return dict(track)

@app.post("/analyze")
async def analyze_sound(file: UploadFile = File(...), user_id: str = Depends(verify_token)):
    """Upload an audio file — AI analyzes BPM, key, energy and maps to a genre style."""
    allowed = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg", "audio/flac", "audio/x-wav",
               "audio/mp4", "audio/x-m4a", "audio/aac", "audio/webm", "audio/x-mp4", "video/mp4",
               "audio/ogg;codecs=opus", "audio/webm;codecs=opus", "application/octet-stream"]
    ct = (file.content_type or "").split(";")[0].strip()
    if ct not in allowed and not (file.filename or "").endswith((".mp3",".wav",".ogg",".flac",".mp4",".m4a",".aac",".webm")):
        raise HTTPException(status_code=400, detail="Please upload an MP3, WAV, OGG, or FLAC file.")
    
    audio_bytes = await file.read()
    if len(audio_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large. Max 20MB.")
    
    try:
        from backend.sound_match import analyze_audio
    except ImportError:
        from sound_match import analyze_audio

    analysis = analyze_audio(audio_bytes, file.filename)
    return {
        "bpm": analysis["bpm"],
        "key": analysis["key"],
        "energy": analysis["energy"],
        "mood": analysis["mood"],
        "genre_guess": analysis["genre_guess"],
        "tags": analysis["tags"],
        "analysis_success": analysis["analysis_success"]
    }


@app.post("/match")
async def match_sound(
    file: UploadFile = File(...),
    duration: int = Form(60),
    user_id: str = Depends(verify_token)
):
    """Analyze uploaded audio and generate a copyright-free track matching the vibe."""
    if not is_subscribed(user_id):
        raise HTTPException(status_code=402, detail="Subscription required.")
    # Read audio bytes
    audio_bytes = await file.read()

    # Simple heuristic analysis based on file metadata + AI prompt
    # In production: use librosa for real BPM/energy detection
    filename = file.filename.lower()
    file_size = len(audio_bytes)

    # Use OpenAI to determine style from filename/context (no librosa needed for MVP)
    import httpx as _httpx
    openai_key = os.getenv("OPENAI_API_KEY", "")

    detected_style = "progressive-house"
    detected_bpm = "128"
    detected_energy = "high"
    detected_tags = ["edm", "progressive-house", "uplifting"]

    if openai_key:
        try:
            async with _httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{
                            "role": "user",
                            "content": f"Based on the filename '{file.filename}' (size: {file_size} bytes), guess the EDM genre and return JSON: {{\"style\": \"genre name\", \"bpm\": \"estimated BPM\", \"energy\": \"low/medium/high\", \"tags\": [\"tag1\",\"tag2\",\"tag3\"]}}"
                        }],
                        "response_format": {"type": "json_object"}
                    }
                )
            ai_data = resp.json()
            result = json.loads(ai_data["choices"][0]["message"]["content"])
            detected_style = result.get("style", detected_style)
            detected_bpm = str(result.get("bpm", detected_bpm))
            detected_energy = result.get("energy", detected_energy)
            detected_tags = result.get("tags", detected_tags)
        except:
            pass

    # Generate track using detected tags via Mubert
    from backend.mubert_client import generate_track as gen
    track_data = await gen(detected_style, duration, "energetic")

    track_id = str(uuid.uuid4())
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO tracks (id, user_id, style, duration, mood, file_url, tags) VALUES (?,?,?,?,?,?,?)",
            (track_id, user_id, f"Match: {detected_style}", duration, "energetic", track_data["url"], ",".join(detected_tags))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return {
        "track_id": track_id,
        "download_url": track_data["url"],
        "genre": detected_style,
        "detected_style": detected_style,
        "bpm": detected_bpm,
        "energy": detected_energy,
        "tags": detected_tags,
        "duration": duration
    }


@app.get("/tracks")
async def list_tracks(user_id: str = Depends(verify_token)):
    conn = get_db()
    tracks = conn.execute("SELECT * FROM tracks WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
    conn.close()
    return [dict(t) for t in tracks]

@app.post("/checkout")
async def checkout(req: CheckoutRequest, user_id: str = Depends(verify_token)):
    conn = get_db()
    user = conn.execute("SELECT email, stripe_customer_id FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    try:
        customer_id = user["stripe_customer_id"]
        if not customer_id:
            customer = stripe.Customer.create(email=user["email"])
            customer_id = customer.id
            conn = get_db()
            conn.execute("UPDATE users SET stripe_customer_id=? WHERE id=?", (customer_id, user_id))
            conn.commit()
            conn.close()
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=req.success_url or f"{FRONTEND_URL}?success=true",
            cancel_url=req.cancel_url or f"{FRONTEND_URL}?canceled=true",
            metadata={"user_id": user_id}
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/subscribe")
async def admin_subscribe(email: str, secret: str):
    if secret != os.getenv("ADMIN_SECRET", ""):
        raise HTTPException(status_code=403, detail="Forbidden")
    conn = get_db()
    conn.execute("UPDATE users SET subscribed=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()
    return {"message": f"✅ {email} set to subscribed"}

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook")
    if event["type"] in ["customer.subscription.created", "customer.subscription.updated"]:
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        conn = get_db()
        conn.execute("UPDATE users SET subscribed=1 WHERE stripe_customer_id=?", (customer_id,))
        conn.commit()
        conn.close()
    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        conn = get_db()
        conn.execute("UPDATE users SET subscribed=0 WHERE stripe_customer_id=?", (customer_id,))
        conn.commit()
        conn.close()
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "StyleDJ API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
