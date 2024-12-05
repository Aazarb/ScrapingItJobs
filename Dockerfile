FROM selenium/standalone-chrome:latest

# Installer les dépendances nécessaires pour Python et pip
USER root
RUN apt-get update && apt-get install -y \
    python3-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Créer un répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt /app/

# Créer un environnement virtuel et installer les dépendances
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copier le reste des fichiers de l'application
COPY . /app/

# Définir le point d'entrée
CMD ["/app/venv/bin/python", "main.py"]
