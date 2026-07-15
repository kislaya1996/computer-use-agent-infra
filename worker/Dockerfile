FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app
COPY scripts/placeholder_task.py /app/run_task.py
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/run_task.py"]
