FROM python:3.8-slim

WORKDIR /app
COPY scripts/placeholder_task.py /app/run_task.py
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/run_task.py"]
