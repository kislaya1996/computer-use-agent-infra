Build worker image:

```bash
docker build -f worker/Dockerfile -t cua-worker:local .
```

Trigger a task:

```bash
curl -X POST http://127.0.0.1:8000/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-duper-secret-key" \
  -d '{"name": "demo", "payload": "hello"}'
```
