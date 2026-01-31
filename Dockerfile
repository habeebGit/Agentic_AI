# Development Dockerfile for FastAPI app
FROM python:3.11-slim

# install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

# create app user
RUN useradd -m appuser
WORKDIR /app

# copy requirements first for caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy app sources
COPY . /app
RUN chown -R appuser:appuser /app

USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
