import os
import logging
import time
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration des logs avec stockage journalier
LOG_DIR = "./logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/app_{time.strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)

# Variables d'environnement
URL_FREEWORK = os.getenv("URL_FREEWORK")
if not URL_FREEWORK:
    raise ValueError("L'URL de FreeWork (URL_FREEWORK) doit être définie dans les variables d'environnement.")

# --- Base de données SQLite ---
def init_db():
    conn = sqlite3.connect('offres.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offres_freework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            date_traitee TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def url_deja_traitee(url):
    conn = sqlite3.connect('offres.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM offres_freework WHERE url = ?', (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def enregistrer_url(url):
    conn = sqlite3.connect('offres.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO offres_freework (url) VALUES (?)', (url,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # L'URL existe déjà
    conn.close()

def nettoyer_anciennes_entrees(age_max_jours=30):
    conn = sqlite3.connect('offres.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM offres_freework WHERE date_traitee < DATETIME("now", ?)', (f'-{age_max_jours} days',))
    conn.commit()
    conn.close()

# --- Scraping ---
def scraper_offres():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)

    try:
        logging.info(f"Accès à la page : {URL_FREEWORK}")
        driver.get(URL_FREEWORK)

        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Gérer la bannière de cookies
        try:
            accept_cookies = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")), timeout=5)
            accept_cookies.click()
        except Exception:
            pass

        offres = []
        annonces = driver.find_elements(By.CSS_SELECTOR, "a.after\\:absolute.after\\:inset-0")
        for annonce in annonces:
            lien = annonce.get_attribute("href")
            if lien:
                offres.append(lien)

        logging.info(f"{len(offres)} offres récupérées.")
        return offres
    except Exception as e:
        logging.error(f"Erreur dans scraper_offres : {e}")
        return []
    finally:
        driver.quit()

def traiter_offres():
    try:
        logging.info("Début de la fonction traiter_offres.")
        offres = scraper_offres()

        if not offres:
            logging.info("Aucune offre récupérée.")
            return

        for url in offres:
            if not url_deja_traitee(url):
                logging.info(f"Nouvelle offre détectée : {url}")
                enregistrer_url(url)
            else:
                logging.info(f"L'offre {url} a déjà été traitée.")

        logging.info("Traitement des offres terminé avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors du traitement des offres : {e}")

# --- Main ---
def main():
    init_db()
    nettoyer_anciennes_entrees()
    traiter_offres()

if __name__ == "__main__":
    main()
