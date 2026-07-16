# computer-use-agent-infra

FastAPI service that enqueues browser-agent tasks into Redis, runs them in Docker (Playwright), and tracks status under `runs/`.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Docker Desktop (or Docker Engine) running and reachable from your shell
- Python 3.8 (pinned via `.python-version`)

## Run locally

### 1. Install dependencies

```bash
uv sync
```

### 2. Start Redis

```bash
docker compose up -d redis
```

Check it is up:

```bash
docker compose ps
```

### 3. Build the worker image

First build pulls the Playwright base image and can take a few minutes:

```bash
docker build -f worker/Dockerfile -t cua-worker:local .
```

Optional sanity check:

```bash
docker run --rm cua-worker:local python -c "import playwright; print(playwright.__version__)"
```

### 4. Start the API

```bash
uv run fastapi dev app/main.py
```

Server: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs

The in-process worker starts with the app and drains the Redis priority queue.

### 5. Enqueue a task

Returns **202** immediately with `status: queued`:

```bash
curl -X POST http://127.0.0.1:8000/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-duper-secret-key" \
  -d '{"name": "demo", "payload": "playwright python", "priority": "high"}'
```

`payload` is the Google search query. `priority` is one of `high`, `normal`, `low`.

### 6. Poll status

```bash
curl http://127.0.0.1:8000/tasks/<task_id> \
  -H "X-API-Key: super-duper-secret-key"
```

Statuses: `queued` → `running` → `completed` / `failed`.

### 7. Inspect artifacts

```text
runs/<task_id>/meta.json
runs/<task_id>/attempt_1.log
runs/<task_id>/attempt_N.log
```

## Auth

Map of API keys → user ids lives in `app/dependencies.py`:

| API key | User |
|---------|------|
| `super-duper-secret-key` | `user-default` |
| `kislaya-key` | `user-kislaya` |
| `kislaya2-key` | `user-kislaya2` |

Send the key as header `X-API-Key`.

## Concurrency / rate limits (env)

| Env | Default | Meaning |
|-----|---------|---------|
| `MAX_GLOBAL_RUNNING` | `3` | Max concurrent Docker tasks |
| `MAX_PER_USER_RUNNING` | `2` | Per-user concurrent cap |
| `MAX_QUEUE_DEPTH_PER_USER` | `20` | Max queued jobs per user |
| `RATE_LIMIT_PER_MINUTE` | `10` | Submit rate per user |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection |

Example:

```bash
MAX_GLOBAL_RUNNING=2 uv run fastapi dev app/main.py
```

