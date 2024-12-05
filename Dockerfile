FROM selenium/standalone-chrome:latest

USER root

# Installer les paquets nécessaires à la création d'un venv et à pip
RUN apt-get update && apt-get install -y \
    python3-full \
    python3-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier et installer les dépendances dans un environnement virtuel isolé
COPY requirements.txt /app/
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copier le reste du code de l’application
COPY . /app/

# Exécuter l’application à partir de l’environnement virtuel
CMD ["/app/venv/bin/python", "main.py"]
