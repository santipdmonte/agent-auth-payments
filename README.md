# Agent Auth Payments (Template)

Python template for building agents that communicate over the phone and use a backend with email authentication (magic link) and OAuth (Google). It lets you link one or more phone numbers to an email‑verified account and includes a LangGraph agent that talks to the backend.

## Features
- Email authentication with magic link (JWT access/refresh tokens, refresh rotation).
- OAuth with Google (OpenID Connect).
- Link one or more phone numbers to a verified account.
- FastAPI backend with SQLite by default (PostgreSQL optional via `DATABASE_URL`).
- LangGraph agent that queries the backend (`graphs/agent_auth.py`).

## Requirements
- Python 3.10+ (3.11 or 3.12 recommended).
- Pip and virtualenv available.
- To run the agent: OpenAI key in `OPENAI_API_KEY` (uses `ChatOpenAI`).

## Installation
```bash
git clone https://github.com/<your-username>/agent-auth-payments.git
cd agent-auth-payments

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Environment variables
Create a `.env` file at the project root with the required values. Minimal example for local development:

```bash
# JWT secret and algorithm
SECRET_KEY="change-this-super-secret-key"
ALGORITHM="HS256"

# Database (defaults to SQLite ./test.db)
# For Postgres: DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/my_db"
DATABASE_URL="sqlite:///./test.db"

# Expirations (optional, sensible defaults)
EMAIL_TOKEN_EXPIRE_MINUTES=5
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (SMTP) to send magic links and codes
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-password-or-app-password"
SMTP_REPLY_TO="support@your-domain.com"

# Public/base URL where the backend runs (used in the magic link)
URL="http://127.0.0.1:8001"

# Google OAuth
GOOGLE_CLIENT_ID="xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxx"

# Agent / LangGraph
BACKEND_URL="http://127.0.0.1:8001"
OPENAI_API_KEY="sk-..."
```

Notes:
- `URL` is used to build the email verification link: `${URL}/auth/verify-token/?token=...`.
- `BACKEND_URL` is used by the LangGraph agent to talk to the backend.
- If you omit `DATABASE_URL`, `./test.db` (SQLite) is created/used automatically.

## How to run
This repo has two processes: the backend (FastAPI) and the agent server (LangGraph).

### 1) FastAPI backend
```bash
source .venv/bin/activate
python3 main.py
```
It starts at `http://127.0.0.1:8001` by default.

Key endpoints:
- `POST /auth/login` → sends a magic link to the provided email.
- `GET /auth/verify-token/?token=...` → returns `access_token` and `refresh_token`.
- `POST /auth/refresh` → rotates the refresh token and returns a new token pair.
- `POST /auth/logout` → logs out and revokes refresh (if provided).
- `GET /auth/google/login` → start Google login (OIDC).
- `GET /users/phone/` and `GET /users/phone/{phone_number}` → phone queries.
- `POST /users/phone/{phone}/send-verification-code/{email}` → email a code to link a phone.
- `POST /users/phone/{phone}/verify-code/{email}?code=XXXX` → verify and link the phone.

### 2) LangGraph agent
In another terminal (with the virtualenv activated):
```bash
langgraph dev
```
The CLI reads the configuration (e.g. `langgraph.json`) and exposes a UI/endpoint to interact with the graph (`graphs/agent_auth.py`). Ensure `OPENAI_API_KEY` and `BACKEND_URL` are set.

## Magic link email authentication flow
1. `POST /auth/login` with the user email to trigger the link.
2. The user opens the received link (`/auth/verify-token/?token=...`).
3. The backend responds with `access_token` and `refresh_token`.
4. Use `Authorization: Bearer <access_token>` for protected endpoints.
5. (Optional) Link a phone by sending a code to the email and confirming it.

Example (curl):
```bash
curl -X POST "http://127.0.0.1:8001/auth/login" -d "email=user@example.com"
```

## Google OAuth
- `GET /auth/google/login` redirects to Google.
- After a successful callback, the backend returns `access_token` and `refresh_token` for the app.

## Development
- Hot-reload is already enabled in `main.py` (Uvicorn `reload=True`).
- For quick testing with SQLite you don't need to set `DATABASE_URL`.
- If you use PostgreSQL, export `DATABASE_URL` in SQLAlchemy + `psycopg` format.

## Common issues
- Email not received: check `SMTP_*` and whether Gmail requires App Passwords. Check SPAM.
- 401/Invalid token: ensure `SECRET_KEY` and `ALGORITHM` match for issuing/validating.
- Agent fails to start: check `OPENAI_API_KEY` and that `BACKEND_URL` points to the running backend.

## License
This project is distributed under the license included in `LICENSE`.
