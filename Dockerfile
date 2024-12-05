# Utiliser l'image officielle Selenium avec Chrome
FROM selenium/standalone-chrome:latest

# Passer en tant qu'utilisateur root pour installer les dépendances
USER root

# Installer les dépendances nécessaires pour Python et pip
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Définir un répertoire de travail
WORKDIR /app

# Copier le fichier requirements.txt et installer les dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . /app/

# Définir le point d'entrée
CMD ["python3", "main.py"]
