FROM python:3.12-slim

# Correctifs de sécurité Debian publiés depuis la construction de l'image de base
RUN apt-get update && apt-get -y --no-install-recommends upgrade && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# git : requis pour le versionnage du vault Obsidian du journal (#1787559677486)
RUN apt-get update && apt-get install -y --no-install-recommends curl git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
