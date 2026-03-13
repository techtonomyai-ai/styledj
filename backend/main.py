import os, uuid, hashlib, sqlite3
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        subscribed INTEGER DEFAULT 0,
        trial_start TEXT,
        stripe_customer_id TEXT,
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

# --- Auth ---
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

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
    return {"message": "StyleDJ API is running", "version": "1.0.0"}

@app.post("/register")
async def register(req: RegisterRequest):
    conn = get_db()
    user_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, trial_start) VALUES (?,?,?,?)",
            (user_id, req.email, hash_password(req.password), datetime.utcnow().isoformat())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        conn.close()
    return {"token": create_token(user_id), "user_id": user_id}

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
