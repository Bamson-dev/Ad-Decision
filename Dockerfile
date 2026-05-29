# Adley — production image for Coolify / Contabo VPS
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ADLEY_DATA_DIR=/data \
    STORAGE_BACKEND=json

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 adley \
    && useradd --uid 1000 --gid adley --home-dir /app --shell /usr/sbin/nologin adley

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=adley:adley . .
RUN chmod +x /app/scripts/docker-entrypoint.sh /app/scripts/healthcheck.py \
    && mkdir -p /data \
    && chown adley:adley /data

USER adley

VOLUME ["/data"]

HEALTHCHECK --interval=60s --timeout=15s --start-period=60s --retries=3 \
    CMD python /app/scripts/healthcheck.py

ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/docker-entrypoint.sh"]
CMD ["python", "main.py"]
