# Xiaohongshu Trend Digest

Daily Xiaohongshu trend digest service for collecting topic-level AI note signals through provider interfaces, ranking the hottest posts, rendering a digest, and sending it by email.

## Setup

Requirements:

- Python 3.11+
- PostgreSQL 15+ for persisted runs
- A supported Xiaohongshu data provider account
- SMTP credentials for email delivery

Create a local environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create local configuration:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`, `settings.yaml`, and `tags.yaml` for the target environment. Do not commit `.env`, API tokens, SMTP passwords, cookies, exported user data, or raw provider payloads.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | SQLAlchemy/Postgres connection string. Local Docker uses `postgresql+psycopg://xhs_digest:xhs_digest@postgres:5432/xhs_digest`. |
| `XHS_PROVIDER` | Yes | Provider name. The default planned provider is `justone`. |
| `XHS_API_TOKEN` | Yes | Provider API token. Keep this secret. |
| `XHS_API_BASE_URL` | Yes | Provider API base URL. |
| `OPENAI_API_KEY` | Yes, when AI summarization is enabled | OpenAI-compatible API key for digest synthesis. |
| `OPENAI_BASE_URL` | No | Optional OpenAI-compatible base URL override. Use `https://api.deepseek.com` for DeepSeek. |
| `OPENAI_MODEL` | Yes, when AI summarization is enabled | Model name used for digest synthesis, for example `deepseek-chat`. |
| `SMTP_HOST` | Yes | SMTP server hostname. |
| `SMTP_PORT` | Yes | SMTP server port, commonly `587`. |
| `SMTP_USER` | Yes | SMTP username. |
| `SMTP_PASSWORD` | Yes | SMTP password or app password. Keep this secret. |
| `SMTP_FROM` | Yes | Sender address used for digest email. |
| `MAIL_TO` | Yes | Recipient address or comma-separated recipient list. |
| `DIGEST_TIMEZONE` | Yes | IANA timezone for scheduling and date labels. |
| `LOG_LEVEL` | No | Logging level, for example `INFO` or `DEBUG`. |

Runtime behavior belongs in `settings.yaml`; topic and tag selection belongs in `tags.yaml`.

The email always includes a `今日AI最热帖子` section. It is generated from all collected AI notes and sorted by the deterministic heat score. The default broad AI collection tag is `AI最热帖子`, and `digest.hot_posts_count` controls how many ranked posts are shown.

For a server with local mail transfer available, set `SMTP_HOST=sendmail`, `SMTP_FROM=your-sender@example.com`, and `MAIL_TO=recipient@example.com`; SMTP username/password are then not required.

## Commands

Run tests:

```powershell
pytest
```

Show the public CLI:

```powershell
daily-digest --help
```

Initialize database tables:

```powershell
daily-digest init-db
```

Generate today's digest without sending email:

```powershell
daily-digest run --date today --dry-run
```

Generate and send today's digest:

```powershell
daily-digest run --date today
```

Send a test email:

```powershell
daily-digest test-email
```

Run the built-in daily scheduler:

```powershell
daily-digest schedule
```

Run the AI Trend Galaxy API and bundled frontend:

```powershell
daily-digest serve --host 127.0.0.1 --port 8000
```

During frontend development, run the Vite app from `web/`:

```powershell
cd web
npm install
npm run dev -- --port 5173
```

Then open `http://127.0.0.1:5173`. The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

Collect public AI trend signals from the enabled provider registry:

```powershell
daily-digest collect-trends --limit-per-entity 10 --window-hours 24
```

Build the container:

```powershell
docker build -t xhs-trend-digest .
```

Start local services:

```powershell
docker compose up --build
```

Stop local services:

```powershell
docker compose down
```

## Docker

The `Dockerfile` installs the package and runs `daily-digest schedule` by default. The Compose stack includes:

- `app`: digest service container
- `postgres`: local PostgreSQL database

Use `.env` for local Compose secrets. Keep deployment secrets in the cloud provider secret manager or runtime environment configuration.

## Cloud Deployment

Recommended deployment shape:

1. Build the image from this repository.
2. Push the image to the target registry.
3. Provision a managed PostgreSQL database.
4. Configure secrets as runtime environment variables.
5. Mount or package `settings.yaml` and `tags.yaml`.
6. Run the service on a schedule using the platform scheduler, a cron container, or the built-in scheduler once implemented.
7. Send logs to the platform log collector and alert on failed digest runs.

For a single-host deployment, use Docker Compose with a production `.env` file stored outside the repository. For managed platforms, map the environment variables above directly into the service configuration.

## Sync Convention

After every meaningful code or documentation change:

1. Run the relevant tests.
2. Commit a small, reviewable change with a clear message.
3. Push `main` to `https://github.com/cym00001-code/xiaohongshu`.

Do not sync secrets, Xiaohongshu session data, cookies, proxy credentials, or raw exported user datasets.

## Provider Boundary

Data collection should stay behind provider interfaces under `src/xhs_digest/providers/`. Do not add captcha bypass, account pools, proxy evasion, private-message collection, media downloaders, or other platform-circumvention code.

## AI Trend Galaxy

The repository now includes a Chinese-first 3D trend visualization surface for AI topics:

- Backend API: `src/xhs_digest/api.py`
- Trend aggregation: `src/xhs_digest/trend_service.py`
- Provider-neutral registry: `src/xhs_digest/providers/trend_sources.py`
- Frontend app: `web/`

The first screen is the usable visualization: a multi-galaxy AI trend map with global models, China AI products, frontier AI, and AI tooling. Node size represents heat, pulse represents growth, color represents sentiment, and orbit rings represent source platforms. Clicking a node opens trend details, heat breakdown, platform distribution, top signals, and a summary.

The live refresh default is 30 minutes. The frontend polls the API and falls back to deterministic demo data when no provider credentials or stored notes are available.
