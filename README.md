# StyleDJ — AI EDM Music Generator

Generate copyright-free DJ tracks in the style of your favorite artists. Powered by Mubert AI.

## Features
- 20 famous DJ styles (Martin Garrix, Tiësto, Deadmau5, Daft Punk, etc.)
- 100% copyright-free AI-generated tracks
- Stripe subscription ($19.99/month + 7-day free trial)
- FastAPI backend + clean dark UI

## Quick Start

### 1. Get API Keys
- **Mubert API**: Sign up at mubert.com/render → get API key
- **Stripe**: stripe.com → get secret key + create a recurring price ($19.99/month)

### 2. Setup
```bash
cd styleDJ
cp .env.example .env
# Fill in your API keys in .env

pip install -r requirements.txt
```

### 3. Run
```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open `frontend/index.html` in your browser.

### 4. Stripe Webhook (for subscription activation)
```bash
stripe listen --forward-to localhost:8000/webhook
```
Copy the webhook secret to STRIPE_WEBHOOK_SECRET in .env

## Deploy
- Backend: Railway, Render, or DigitalOcean ($5-10/month)
- Frontend: Netlify or Vercel (free)

## Revenue Model
$19.99/month × 1,000 users = $19,990/month
$19.99/month × 10,000 users = $199,900/month

Built by Techtonomy LLC — techtonomy.ai
