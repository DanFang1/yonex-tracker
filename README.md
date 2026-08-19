# Yonex Price Tracker

Track prices on [yonex.com](https://www.yonex.com) and get emailed the moment an item drops to (or below) the price you're willing to pay.

## How it works

1. Sign up and log in.
2. Paste a product URL from `yonex.com` and set a target price.
3. The app scrapes the current price and starts recording a price history for it.
4. A scheduled job periodically re-scrapes tracked products, updates prices, and records a new history point.
5. Another scheduled job checks for products at or below their target price and emails the owner. A price bump above the target resets the alert so a future dip notifies again.
6. The dashboard shows each tracked product with its current price, target price, and a history graph.

## Architecture

- **Backend** (`backend/`) — Flask REST API.
  - `app.py` — routes for auth, adding/deleting tracked products, dashboard data, and price history.
  - `auth.py` — registration/login, password hashing (`passlib`/`bcrypt`).
  - `scraper.py` — fetches a product page and parses name/price with BeautifulSoup. Restricted to Yonex domains to prevent SSRF.
  - `database.py` — PostgreSQL access (`psycopg2`).
  - `price_updater.py` — scheduled jobs: `price_refresher`, `check_and_notify_targets`, `reset_notified_prices`.
  - `notifications.py` — sends price-drop alert emails via SMTP.
- **Frontend** (`frontend/`) — React app (Create React App) with login/register, a dashboard of tracked products, and a price history chart (`recharts`).
- **CI/CD** (`.github/workflows/`)
  - `ci-cd.yml` — runs backend (`pytest`) and frontend tests/build on every push/PR to `main`. Vercel and Render auto-deploy from `main` once checks pass.
  - `price-tracker-jobs.yml`, `check-targets.yml`, `reset-notified.yml` — scheduled backend jobs (currently trigger via `workflow_dispatch`; cron schedules are commented out).

## Local setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Environment variables

Create a `.env` file in the project root (gitignored) with:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `FLASK_KEY` | Flask session secret key |
| `SENDER_EMAIL` / `SENDER_PASSWORD` | SMTP credentials used to send price-drop alerts |
| `REACT_APP_API_URL` | Backend API URL consumed by the frontend |
| `FRONTEND_URL` | Frontend origin allowed by CORS |
| `REDIS_URL` | Redis instance used for API rate limiting |

## Tests

```bash
# Backend
cd backend && pytest test_routes.py -v

# Frontend
cd frontend && npm test
```
