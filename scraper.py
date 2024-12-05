import os
import logging
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from playwright.sync_api import sync_playwright

# Configuration des logs
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Charger les variables d'environnement
load_dotenv()

# Récupérer les valeurs des variables d'environnement
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPEN_TOKEN = os.getenv("OPEN_TOKEN")

# Créer une instance de FastAPI
app = FastAPI()


# --- Fonction pour scraper les URLs des offres ---
def scraper_offres_sync():
    """
    Scrape les URLs des offres d'emploi depuis Free-Work en utilisant Playwright synchronisé.

    Returns:
        list[str]: Liste des URLs des offres.
    """
    offres = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.free-work.com/fr/tech-it/jobs?query=Java", timeout=60000)

            # Récupérer les URLs des offres
            annonces = page.query_selector_all("a.after\\:absolute.after\\:inset-0")
            for annonce in annonces:
                lien = annonce.get_attribute("href")
                if lien:
                    offres.append(f"https://www.free-work.com{lien}")

            browser.close()

        logging.info(f"{len(offres)} URL d'offres récupérées.")
    except Exception as e:
        logging.error(f"Erreur dans scraper_offres : {e}")

    return offres


# --- Fonction pour générer un prompt OpenAI ---
def generer_prompt(offres):
    """
    Génère un prompt pour analyser les URL des offres.

    Args:
        offres (list[str]): Liste des URLs des offres.

    Returns:
        str: Le prompt formaté.
    """
    prompt = (
        "Voici une liste d'URL d'offres d'emploi. Analyse chaque page pour extraire "
        "les informations suivantes :\n"
        "- Lieu\n"
        "- Expérience requise\n"
        "- Stack technique\n"
        "- TJM (Tarif Journalier Moyen, si applicable)\n"
        "- Rythme de télétravail\n"
        "- Informations complémentaires utiles.\n\n"
        "Retourne les résultats dans le format JSON suivant :\n\n"
        "```json\n"
        "{\n"
        "  \"offres\": [\n"
        "    {\n"
        "      \"url\": \"<URL>\",\n"
        "      \"lieu\": \"<Lieu>\",\n"
        "      \"experience_requise\": \"<Expérience>\",\n"
        "      \"stack_technique\": \"<Stack>\",\n"
        "      \"tjm\": \"<TJM>\",\n"
        "      \"teletravail\": \"<Télétravail>\",\n"
        "      \"informations_complementaires\": \"<Informations complémentaires>\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n\n"
    )

    for url in offres:
        prompt += f"- {url}\n"

    return prompt


# --- Fonction pour analyser les offres via OpenAI ---
def analyser_liste_offres_avec_openai(offres):
    """
    Analyse une liste d'URLs d'offres via un appel OpenAI.

    Args:
        offres (list[str]): Liste des URLs des offres.

    Returns:
        list[dict]: Liste des résultats analysés pour chaque offre.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPEN_TOKEN}",
        "Content-Type": "application/json"
    }

    # Construire le prompt avec toutes les URLs
    prompt = generer_prompt(offres)

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,  # Ajustez en fonction de la taille des réponses attendues
    }

    try:
        # Envoyer la requête à OpenAI
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Lever une exception pour les codes d'erreur HTTP
        resultat = response.json()

        # Log de la réponse brute pour débogage
        logging.info(f"Réponse brute complète d'OpenAI : {resultat}")

        # Extraire le contenu textuel
        if "choices" in resultat and resultat["choices"]:
            contenu = resultat["choices"][0]["message"]["content"]
            logging.info(f"Réponse brute d'OpenAI : {contenu}")

            # Tenter de parser le contenu comme JSON
            try:
                analyses = eval(contenu.strip("```json\n").strip())["offres"]
                return analyses
            except Exception as e:
                logging.error(f"Erreur lors du parsing JSON : {e}")
                raise ValueError("La réponse d'OpenAI n'est pas un JSON valide.")

        else:
            raise ValueError("Aucune réponse valide reçue d'OpenAI.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur HTTP : {e.response.status_code} - {e.response.text}")
        raise ValueError(f"Erreur HTTP {e.response.status_code} : {e.response.text}")

    except Exception as e:
        logging.error(f"Erreur inattendue : {e}")
        raise ValueError(f"Erreur inattendue lors de l'appel OpenAI : {e}")


# --- Fonction principale pour traiter les offres ---
def traiter_offres():
    """
    Fonction principale pour scraper, analyser et envoyer les offres.
    """
    try:
        # Étape 1 : Scraper les offres
        offres = scraper_offres_sync()
        logging.info(f"{len(offres)} URL d'offres récupérées.")

        if not offres:
            logging.warning("Aucune offre récupérée.")
            return

        # Étape 2 : Analyser les offres avec OpenAI
        analyses = analyser_liste_offres_avec_openai(offres)
        logging.info(f"Analyses reçues pour {len(analyses)} offres.")

        # Étape 3 : Envoyer les résultats via Telegram
        message = ""
        for analyse in analyses:
            message += (
                f"[Offre]({analyse['url']})\n"
                f"Lieu : {analyse.get('lieu', 'Non spécifié')}\n"
                f"Expérience requise : {analyse.get('experience_requise', 'Non spécifiée')}\n"
                f"Stack technique : {analyse.get('stack_technique', 'Non spécifiée')}\n"
                f"TJM : {analyse.get('tjm', 'Non spécifié')}\n"
                f"Télétravail : {analyse.get('teletravail', 'Non spécifié')}\n"
                f"Informations complémentaires : {analyse.get('informations_complementaires', 'RAS')}\n\n"
            )

        logging.info("Message envoyé :")
        logging.info(message)

    except Exception as e:
        logging.error(f"Erreur lors du traitement des offres : {e}")


# --- Endpoint FastAPI ---
@app.get("/test", summary="Tester le scraping et l'analyse des offres")
def test_bot():
    """
    Endpoint pour tester le scraping des offres et leur analyse.
    """
    try:
        traiter_offres()
        return {"status": "success", "message": "Les offres ont été traitées et envoyées avec succès."}
    except Exception as e:
        logging.error(f"Erreur dans /test : {e}")
        raise HTTPException(status_code=500, detail=f"Une erreur est survenue : {str(e)}")
