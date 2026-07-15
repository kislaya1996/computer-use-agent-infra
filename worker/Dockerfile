FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

RUN python -m pip install --no-cache-dir playwright==1.61.0

COPY scripts/placeholder_task.py /app/run_task.py
ENV PYTHONUNBUFFERED=1

CMD ["sleep", "infinity"]
