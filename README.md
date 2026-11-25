# Wastewise for AWS

**Find the cloud spend you're wasting.**

Wastewise is a web app that connects to an AWS account with read-only access,
finds wasted cloud spending, shows how much each fix would save per month, and
generates a Terraform change for each fix. It also ships a demo mode so anyone
can try it without an AWS account and see real, honest pricing.

---

## What's here (Phase 1)

- **Backend** — FastAPI + boto3 + SQLite.
- **Frontend** — React + Tailwind (scaffolded; dashboard screens come in a later phase).
- **Config system** — every price, threshold, region and the product name/tagline
  live in `backend/config/*.yaml` and `backend/config/language.en.json`, or in `.env`.
  Nothing is hardcoded in code.
- **Demo mode** — a realistic fake account loaded from an editable JSON seed
  (`backend/data/demo_seed.json`). No AWS account needed.
- **Pricing module** — fetches live on-demand prices from the AWS Price List API,
  caches them with an expiry, and falls back to the last cached price (never a
  made-up number) when the API is unreachable.

### Detectors (planned — Phase 2)

Idle EC2 instances, unattached EBS volumes, old EBS snapshots, unattached Elastic
IPs, oversized RDS databases, and idle load balancers.

---

## Run it locally

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Start the API:

```bash
python -m app.main            # http://127.0.0.1:8000
```

Smoke-test a few endpoints:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/branding
curl http://127.0.0.1:8000/api/demo/account
```

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Open http://localhost:5173 — you should see the branding from the backend, the
demo account status, and the pricing panel.

### Demo pricing (one-time, optional)

The AWS Price List **Query** API (boto3 `pricing` client) requires credentials,
and the unauthenticated **Bulk** API files are ~480 MB — too large for a demo.
So demo mode shows *real* AWS prices from a small dated snapshot you seed once:

```bash
cd backend
python scripts/seed_demo_prices.py   # needs any read-only AWS creds; writes data/price_snapshot.json
```

Without that snapshot, demo pricing honestly reports "price unavailable" and
**never invents a number** (this is the tested fallback path). Real AWS mode
(Phase 5) fetches live through the same pipeline using the read-only role.

### 3. Tests

```bash
cd backend && pytest          # backend unit tests (pricing, config, demo)
cd frontend && npm test       # basic frontend test for the i18n helpers
```

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed (paths, cache TTL, currency,
demo on/off). Non-secret defaults live in `backend/config/app.yaml`; detector
thresholds live in `backend/config/rules.yaml`; all on-screen text and branding
live in `backend/config/language.en.json`.

No AWS credentials are required in demo mode. The app is strictly read-only and
never calls a create/modify/delete API.