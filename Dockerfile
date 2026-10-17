FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends make git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DATA_DIR=/app/data/fixtures OUTPUT_ROOT=/tmp/medicare-ci DBT_SEND_ANONYMOUS_USAGE_STATS=false
CMD ["make", "ci"]
