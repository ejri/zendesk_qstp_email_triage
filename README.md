# Zendesk AI Triage (Open Source)

Automatically classify incoming support emails in Zendesk by priority and category using open models (e.g., Gemma 4 via OpenRouter). The system:

- Listens to Zendesk ticket updates via webhooks
- Classifies the latest customer email with an LLM
- Updates Zendesk ticket priority, tags, and adds a private internal note
- Is idempotent, auditable, and designed for self-hosting

This repo is intentionally model-agnostic. It supports:

- OpenRouter (recommended for open models like Gemma 4)
- OpenAI-compatible APIs
- Any HTTP-based LLM provider with a simple adapter

## Features

- Event-driven architecture using Zendesk webhooks
- Async worker with queue (Redis or in-memory for small setups)
- Structured classification output (priority, category, confidence, summary, rationale)
- Guardrails and policy layer (e.g., never lower existing priority, flag security/privacy issues)
- Idempotency by `(ticket_id, comment_id)` to avoid reprocessing
- Audit logging to SQLite (swap to Postgres if desired)
- Bilingual-friendly prompts (English/French-ready)
- Open models first: OpenRouter + Gemma 4, but extensible

## Architecture Overview

```text
Customer email
   ↓
Zendesk ticket created/updated
   ↓
Zendesk trigger → Webhook
   ↓
FastAPI webhook receiver
   ↓
Queue (Redis or in-memory)
   ↓
Python worker
   ↓
- Fetch ticket + comments from Zendesk
- Eligibility + deduplication
- LLM classification (OpenRouter / OpenAI / etc.)
- Policy/guardrails
- Update Zendesk (priority, tags, private note)
   ↓
Audit DB (SQLite)
```

## Prerequisites

- Python 3.10+
- A Zendesk account with:
  - Admin access to create webhooks and triggers
  - API token or OAuth app
- An LLM provider:
  - Recommended: [OpenRouter](https://openrouter.ai/) account with access to `google/gemma-4` or similar
  - Alternative: OpenAI, Anthropic, or any OpenAI-compatible endpoint
- (Optional but recommended) Redis for queueing

## Repository Structure

```text
.
├─ README.md
├─ requirements.txt
├─ .env.example
├─ docker-compose.yml            # optional, for Redis + worker + api
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ main.py                   # FastAPI webhook receiver
│  ├─ worker.py                 # background worker
│  ├─ zendesk_client.py
│  ├─ llm_client.py
│  ├─ models.py
│  ├─ triage_logic.py
│  └─ db.py
└─ scripts/
   └─ init_db.py
```

## Quick Start (Local, No Docker)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/zendesk-ai-triage.git
cd zendesk-ai-triage
```

### 2. Create virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example env file:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- Zendesk credentials
- OpenRouter (or other LLM) credentials
- Queue and DB settings

See the “Configuration” section below for details.

### 4. Initialize the database

```bash
python scripts/init_db.py
```

This creates a local `triage.db` SQLite database for audit and idempotency.

### 5. Run the webhook API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal, run the worker:

```bash
python app/worker.py
```

For local testing without a real queue, the worker uses an in-memory queue. For production, configure Redis (see “Production with Docker” below).

### 6. Expose your local API to the internet (for Zendesk webhooks)

Use a tool like [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Copy the `https://*.ngrok.io` URL; you’ll use it in Zendesk.

### 7. Configure Zendesk

1. In Zendesk Admin → **Webhooks**, create a new webhook:
   - URL: `https://<your-ngrok-url>/webhooks/zendesk/ticket-updated`
   - Method: `POST`
   - Authentication: `Basic Auth` or `API Token` as per your setup
   - Request body (JSON):

     ```json
     {
       "event_type": "zendesk.ticket.changed",
       "ticket_id": "{{ticket.id}}",
       "ticket_updated_at": "{{ticket.updated_at}}",
       "requester_id": "{{ticket.requester.id}}",
       "channel": "{{ticket.via.channel}}",
       "status": "{{ticket.status}}"
     }
     ```

   - Save and note the **signing secret**.

2. In Zendesk Admin → **Triggers**, create a trigger:
   - Name: `AI Triage – Send Ticket Event`
   - Conditions:
     - `Ticket: Is created` OR `Ticket: Is updated`
     - (Recommended) `Ticket: Channel` is `Email`
     - `Ticket: Status` is not `Closed` and not `Solved`
     - `Ticket: Tags` does not contain `ai_do_not_triage`
   - Actions:
     - `Notify active webhook` → select the webhook you created

3. In the webhook settings, add the signing secret to your `.env`:

   ```bash
   ZENDESK_WEBHOOK_SECRET="your-signing-secret"
   ```

### 8. Test end-to-end

1. Send a test email to your Zendesk support address.
2. Check:
   - Webhook receiver logs (FastAPI)
   - Worker logs
   - `triage.db` for new rows
   - Zendesk ticket for:
     - Updated priority
     - New tags (`ai_triaged`, `ai_priority_*`, `ai_category_*`)
     - A private internal note with the AI summary

---

## Configuration

### `.env` file (based on `.env.example`)

```bash
# Zendesk
ZENDESK_SUBDOMAIN="your-subdomain"
ZENDESK_ACCESS_TOKEN="your_zendesk_api_token"
ZENDESK_WEBHOOK_SECRET="your_zendesk_webhook_signing_secret"

# LLM via OpenRouter (recommended for open models)
LLM_PROVIDER="openrouter"
OPENROUTER_API_KEY="sk-or-xxxxxxxxxxxxxxxx"
OPENROUTER_MODEL="google/gemma-4"

# Alternative: direct OpenAI-compatible endpoint
# LLM_PROVIDER="openai_compat"
# OPENAI_COMPAT_BASE_URL="https://your-llm-host/v1"
# OPENAI_COMPAT_API_KEY="your-key"
# OPENAI_COMPAT_MODEL="gemma-4"

# Queue (Redis)
# For local dev, you can use in-memory by leaving REDIS_URL empty
REDIS_URL="redis://localhost:6379/0"

# Database
DATABASE_URL="sqlite:///triage.db"

# App
HOST="0.0.0.0"
PORT="8000"
LOG_LEVEL="INFO"

# Triage behaviour
DEFAULT_LANGUAGE="en"  # or "fr" for French-first prompts
MAX_EMAIL_CHARS="12000"
CONFIDENCE_HUMAN_REVIEW_THRESHOLD="70"
```

You can adjust `OPENROUTER_MODEL` to any model available on OpenRouter (e.g., `google/gemma-4`, `meta-llama/llama-3.1-70b-instruct`, etc.).

---

## Production with Docker (Optional)

A simple `docker-compose.yml` is provided to run:

- Redis
- FastAPI webhook receiver
- Worker

Example:

```bash
docker compose up -d
```

Ensure `.env` is configured and `REDIS_URL` points to `redis://redis:6379/0` inside the Docker network.

---

## How Classification Works

- The worker fetches the latest public comment from the ticket requester.
- It sends the subject + email body to the LLM with a structured prompt.
- The model returns JSON with:
  - `priority`: `urgent`, `high`, `normal`, `low`
  - `category`: e.g., `billing`, `bug_or_outage`, `security_or_privacy`, etc.
  - `confidence`: 0–100
  - `summary`, `reason`, `needs_human_review`
- Policy rules:
  - Never lower an existing higher priority
  - Force `ai_review` tag for security/privacy, legal, or low-confidence cases
  - Respect `ai_do_not_triage` tag

---

## Extending the Project

- Add French prompts by switching `DEFAULT_LANGUAGE` and extending `triage_logic.py`.
- Swap SQLite for Postgres by changing `DATABASE_URL`.
- Add more categories or custom routing rules in `triage_logic.py`.
- Integrate with other ticketing systems by adding new adapters alongside `zendesk_client.py`.

---

## Security & Privacy Notes

- Email content is sent to an external LLM provider. Ensure this complies with your data policies.
- Store API keys and secrets in environment variables or a secret manager, not in code.
- Use HTTPS for your webhook endpoint in production.
- Consider logging only metadata (ticket/comment IDs, classification) and not full email bodies.

---

## License

MIT License – see `LICENSE` file.