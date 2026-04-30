FROM python:3.12-slim

# Dépendances système pour Chromium (sans passer par playwright install-deps
# qui échoue sur Debian Trixie avec des noms de paquets obsolètes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates curl \
    libnss3 libnspr4 \
    libatk1.0-0t64 libatk-bridge2.0-0t64 \
    libcups2t64 libdrm2 libdbus-1-3 \
    libxkbcommon0 libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2t64 libatspi2.0-0 \
    fonts-liberation fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
