The worker container runs a headless-Chromium (Playwright) script that performs a
Google search and captures the first 5 results. The search query is taken from the
task `payload`.

Build worker image (large: pulls the Playwright base image the first time):

```bash
docker build -f worker/Dockerfile -t cua-worker:local .
```

Trigger a task (payload = search query):

```bash
curl -X POST http://127.0.0.1:8000/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-duper-secret-key" \
  -d '{"name": "demo", "payload": "playwright python"}'
```

The container's live output is streamed to `runs/<container_id>_<timestamp>/worker.log`.

Note: Google may present a consent wall or CAPTCHA to automated headless browsers;
the script dismisses common consent dialogs best-effort and logs a clear message if
no results could be captured. This was added to add more edge cases and help with manual testing of the pipeline.
