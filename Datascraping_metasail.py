import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import time
import os
import glob
import random
import sys
import shutil
import tempfile
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from bs4 import BeautifulSoup

# Importations spécifiques à Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException

# --- Constantes pour un scraping plus "poli" et plus robuste ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]
MIN_DELAY_SECONDS = 9
MAX_DELAY_SECONDS = 30
MAX_RETRIES = 5

# --- Configuration du répertoire de profil persistant pour Selenium ---
PERSISTENT_DATA_DIR = os.path.join(os.path.expanduser('~'), 'selenium_chrome_profile')
if not os.path.exists(PERSISTENT_DATA_DIR):
    os.makedirs(PERSISTENT_DATA_DIR)
    print(f"Création du répertoire de profil persistant : {PERSISTENT_DATA_DIR}")


# -----------------------------------------------------------
# Fonction pour gérer l'extraction d'URLs des fichiers locaux

def find_urls_from_local_files(directory_path):
    """
    Recherche les fichiers HTML locaux et extrait les URLs Metasail qui y sont contenues.
    """
    print("Étape 1 : Recherche des URLs dans les fichiers locaux... 🔍")
    search_pattern = os.path.join(directory_path, "MetaSail for web*.html")
    html_files = glob.glob(search_pattern)
    urls = []
    url_regex = re.compile(r'https://app\.metasail\.it/ViewRecordedRace2018\.aspx\?idgara=\d+&amp;token=\w+')

    if not html_files:
        print(f"    -> ❌ Aucun fichier correspondant à '{search_pattern}' n'a été trouvé.")
        return []

    print(f"    -> ✅ Fichiers trouvés : {len(html_files)}")
    for file_path in html_files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                found_urls = [url.replace('&amp;', '&') for url in url_regex.findall(content)]
                if found_urls:
                    urls.extend(found_urls)
                    print(f"      -> ✅ Trouvé {len(found_urls)} URL(s) dans '{filename}'")
        except Exception as e:
            print(f"      -> ❌ Erreur lors de la lecture du fichier {filename}: {e}", file=sys.stderr)

    unique_urls = sorted(list(set(urls)))
    if unique_urls:
        print(f"    -> ✅ Total d'URLs uniques trouvées : {len(unique_urls)}")
    else:
        print("    -> ❌ Aucune URL de course valide n'a été trouvée dans les fichiers locaux.")

    return unique_urls


# -----------------------------------------------------------
class MetasailScraper:
    """Classe pour encapsuler la logique de scraping d'une URL Metasail."""

    def __init__(self, event_url, event_id, token, source_name, session):
        self.event_url = event_url
        self.stats_url = None
        self.event_id = event_id
        self.token = token
        self.source_name = source_name
        self.session = session
        self.event_name, self.race_name, self.event_location, self.race_date, self.stats_data = None, "N/A", "N/A", "N/A", None
        self.wind_orientation_metasail = None
        self.translations = {
            'Seriale': 'Numéro de série', 'Nome': 'Nom complet',
            'TotTempPerc': 'Temps total parcouru (s)', 'TotLungLato': 'Longueur totale du parcours (m)',
            'TotDistPerc': 'Distance totale réelle parcourue (m)', 'PosPartenza': 'Position de départ',
            'TotDistRealeSuIdeale': 'Efficacité (Distance réelle/idéale) (%)', 'SegNum': 'Numéro de segment',
            'TopSpeed': 'Vitesse maximale (noeuds)', 'TopVMG': 'VMG maximale', 'TopVMC': 'VMC maximale',
            'AvgVMG': 'VMG moyenne', 'AvgVMC': 'VMC moyenne', 'AvgSpeed': 'Vitesse moyenne (noeuds)',
            'CrtRaceSegSX': 'Bâbord (%)', 'CrtRaceSegDX': 'Tribord (%)',
            'TimeSecPercorsi': 'Temps du segment (s)', 'SegDistRealePercorsa': 'Distance réelle parcourue segment (m)',
            'LungLato': 'Longueur du segment (m)', 'DirLato': 'Cap magnétique (deg)',
            'PercEffettivo': 'Efficacité du segment (%)', 'StartSeg': 'Début du segment (timestamp)',
            'EndSeg': 'Fin du segment (timestamp)', 'SegEnteredRank': 'Classement entrée de segment',
            'SegExitRank': 'Classement sortie de segment',
        }

    def get_page_info_with_selenium(self, driver):
        """
        Récupère les informations de la page en utilisant Selenium.
        Le script fait glisser le curseur du temps pour charger les données, avec une logique de réessai.
        Le driver est passé en argument pour réutiliser la même session.
        """
        try:
            print(f"Étape 2 : Récupération des infos de la course... ⛵")
            print(f"    -> 🌐 Navigation vers : {self.event_url}")
            driver.get(self.event_url)

            wait = WebDriverWait(driver, 45)

            print("    -> ⏳ Attente de l'apparition du curseur de la barre de temps...")
            slider_handle = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'rangeSlider__handle'))
            )

            # --- Nouvelle fonctionnalité : attente pour un déplacement plus doux ---
            print("    -> ⏳ Attente de 3 secondes avant le premier déplacement du curseur...")
            time.sleep(3)

            wind_data_found = False
            for attempt_move in range(MAX_RETRIES):
                if wind_data_found:
                    break

                # Vérification initiale si les données de vent sont déjà chargées
                try:
                    wind_text = driver.find_element(By.ID, 'lblWind').text
                    if wind_text and wind_text.strip():
                        print(f"    -> ✅ Données de vent déjà présentes. Pas besoin de déplacer le curseur.")
                        wind_data_found = True
                        break
                except:
                    pass

                # --- Mise à jour de la logique de déplacement pour une fiabilité accrue ---
                print(f"    -> 🔄 Tentative de glisser-déposer du curseur {attempt_move + 1}/{MAX_RETRIES}...")

                try:
                    actions = ActionChains(driver)
                    # La méthode drag_and_drop_by_offset est plus stable car elle opère directement sur l'élément.
                    # On simule un glisser-déposer du curseur sur 100 pixels.
                    actions.drag_and_drop_by_offset(slider_handle, 100, 0).perform()
                except Exception as e:
                    print(f"    -> ❌ Le glisser-déposer a échoué : {e}. Réessai...")

                # --- Attente pour laisser le temps à la page de charger les données ---
                print("    -> ⏳ Attente de 2 secondes pour le chargement des données...")
                time.sleep(2)

                try:
                    wind_text = driver.find_element(By.ID, 'lblWind').text
                    if wind_text and wind_text.strip():
                        print(f"    -> ✅ Données de vent trouvées après un glisser-déposer réussi.")
                        wind_data_found = True
                        break
                except:
                    print("    -> ❌ Données de vent non trouvées. Réessai...")

            if not wind_data_found:
                print(
                    "    -> ❌ Le curseur n'a pas pu être déplacé ou les données de vent n'ont jamais été trouvées après plusieurs tentatives.")
                raise TimeoutException("Échec du déplacement du curseur.")

            wind_direction_text = driver.find_element(By.ID, 'lblWind').text
            wind_direction_text = re.sub(r'Wind|°', '', wind_direction_text).strip()

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            script_content = next((s.text for s in soup.find_all('script') if 'dataLayer.push' in s.text), "")

            event_name, race_name, race_date = "N/A", "N/A", "N/A"
            if script_content:
                try:
                    data_layer_match = re.search(r'dataLayer\.push\(({.*?})\);', script_content, re.DOTALL)
                    if data_layer_match:
                        json_str = data_layer_match.group(1).replace("'", '"')
                        data_dict = json.loads(json_str)
                        event_name = data_dict.get('eventName', "N/A")
                        race_name = data_dict.get('race', "N/A")
                        race_date = data_dict.get('raceDate', "N/A")
                        print("    -> ✅ Données 'dataLayer' trouvées et extraites avec succès.")
                except Exception as e:
                    print(f"    -> ❌ Erreur lors de l'analyse du JSON 'dataLayer': {e}")

            final_url = driver.current_url
            cookies_list = driver.get_cookies()
            for cookie in cookies_list:
                self.session.cookies.set(cookie['name'], cookie['value'])
            print("    -> ✅ Cookies de Selenium ajoutés à la session requests.")
            print(f"    -> ✅ Page récupérée avec succès. URL finale : {final_url}")
            print(f"    -> ✅ Orientation du vent trouvée : {wind_direction_text}")
            print(f"    -> ✅ Nom de la compétition : {event_name}")
            print(f"    -> ✅ Nom de la course : {race_name}")
            print(f"    -> ✅ Date de la course : {race_date}")

            return final_url, wind_direction_text, event_name, race_name, race_date

        except (WebDriverException, TimeoutException) as e:
            print(f"    -> ❌ Erreur lors de l'utilisation de Selenium : {e}")

        return None, None, None, None, None

    def _make_request(self, method, url, **kwargs):
        """Effectue une requête HTTP avec délais, User-Agent aléatoire et tentatives multiples."""
        print(f"\nÉtape 3 : Récupération des données statistiques... 📊")
        for attempt in range(MAX_RETRIES):
            try:
                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(
                    f"    -> ⏳ (Tentative {attempt + 1}/{MAX_RETRIES}) Pause de {delay:.2f}s avant la requête...")
                time.sleep(delay)
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "*/*",
                    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://app.metasail.it/"
                }
                if 'headers' in kwargs:
                    headers.update(kwargs['headers'])
                kwargs['headers'] = headers
                response = self.session.request(method, url, timeout=30, **kwargs)
                response.raise_for_status()
                print(f"    -> ✅ Requête réussie (code {response.status_code}).")
                return response
            except requests.exceptions.RequestException as e:
                print(f"    -> ❌ Erreur de requête (tentative {attempt + 1}): {e}", file=sys.stderr)
                if attempt + 1 == MAX_RETRIES:
                    print("    -> ❌ Nombre maximal de tentatives atteint. Abandon.")
                    return None
        return None

    def _get_stats_data(self):
        """Récupère les données statistiques via une requête POST."""
        if not self.stats_url:
            print("    -> ❌ Erreur: L'URL des statistiques n'a pas été construite.")
            return False

        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        params = {'idgara': self.event_id, 'token': self.token}
        response = self._make_request('POST', self.stats_url, headers=headers, data=params)

        if response:
            print("    -> ✅ Données brutes reçues. Nettoyage du XML...")
            xml_content = response.text
            xml_content = re.sub(r'<\?xml.*?\?>', '', xml_content).strip()

            # --- Correction de l'avertissement de dépréciation ---
            # Le paramètre 'count' est maintenant explicitement nommé pour éviter la dépréciation
            xml_content = re.sub(r'<string.*?>', '', xml_content, count=1).rsplit('</string>', 1)[0]
            self.stats_data = xml_content
            print("    -> ✅ Données statistiques prêtes à être analysées.")
            return True
        else:
            print("    -> ❌ Échec de la récupération des données statistiques après plusieurs tentatives.")
            return False

    @staticmethod
    def _extract_time_from_timestamp(timestamp):
        try:
            return datetime.fromtimestamp(float(timestamp)).strftime("%H:%M:%S")
        except (ValueError, TypeError, OSError):
            return None

    def _parse_and_prepare_dataframe(self):
        print("Étape 4 : Analyse du XML et création du DataFrame... 🗃️")
        if not self.stats_data or not self.event_name:
            print("    -> ❌ Données ou nom d'événement manquants. Échec de l'analyse.")
            return None
        try:
            root = ET.fromstring(self.stats_data)
            data_rows = []
            namespace = '{http://meteda.it/}'
            print("    -> 🔎 Début de l'extraction des données des coureurs et segments.")
            for racer_data in root.findall(f'.//{namespace}StatisticheDato'):
                racer_info = {'ID': self.source_name, 'Nom de l\'événement': self.event_name,
                              'Lieu de l\'événement': self.event_location, 'Course': self.race_name,
                              'Date de la course': self.race_date,
                              'Orientation vent metasail': self.wind_orientation_metasail}

                full_name_element = racer_data.find(f'.//{namespace}Nome')
                racer_info['Nom complet'] = full_name_element.text if full_name_element is not None else "N/A"

                print(f"      -> Traitement du coureur : {racer_info['Nom complet']}")

                for child in racer_data:
                    tag_name = child.tag.replace(namespace, '')
                    if tag_name in self.translations and tag_name != 'Nome' and child.text:
                        racer_info[self.translations[tag_name]] = child.text

                segments = racer_data.findall(f'.//{namespace}cInfoRaceSegment')
                if not segments:
                    data_rows.append(racer_info)
                    print("        -> ⚠️ Aucun segment trouvé pour ce coureur. Données générales ajoutées.")
                else:
                    for i, segment_data in enumerate(segments):
                        segment_row = racer_info.copy()
                        for child in segment_data:
                            tag_name = child.tag.replace(namespace, '')
                            if tag_name in self.translations and child.text:
                                segment_row[self.translations[tag_name]] = self._extract_time_from_timestamp(
                                    child.text) if tag_name in ['StartSeg', 'EndSeg'] else child.text
                        data_rows.append(segment_row)
                        print(f"        -> ✅ Données du segment {i + 1} ajoutées.")

            if not data_rows:
                print("    -> ❌ Aucune donnée à transformer en DataFrame.")
                return None
            df = pd.DataFrame(data_rows)
            first_cols = ['ID', 'Nom de l\'événement', 'Lieu de l\'événement', 'Course', 'Date de la course',
                          'Orientation vent metasail', 'Nom complet', self.translations['Seriale']]
            other_cols = [col for col in df.columns if col not in first_cols]
            df = df.reindex(columns=first_cols + other_cols)
            print("    -> ✅ DataFrame créé avec succès.")
            return df
        except ET.ParseError as e:
            print(f"    -> ❌ Erreur XML: {e}", file=sys.stderr)
            return None

    def scrape_and_export(self, driver, output_filename):
        final_url, wind_direction, event_name, race_name, race_date = self.get_page_info_with_selenium(driver)

        if not final_url:
            print("    -> 🛑 Arrêt du processus pour cette URL en raison d'un échec de la récupération des infos.")
            return False

        self.event_url = final_url
        self.wind_orientation_metasail = wind_direction
        self.event_name = event_name
        self.race_name = race_name
        self.race_date = race_date

        parsed_url = urlparse(self.event_url)
        session_prefix_match = re.search(r'\(S\((.*?)\)\)', self.event_url)
        session_prefix = f"(S({session_prefix_match.group(1)}))" if session_prefix_match else ""
        self.stats_url = f"https://app.metasail.it/{session_prefix}/MetaSailWS.asmx/getStatistiche?idgara={self.event_id}&token={self.token}"
        print(f"    -> ✅ URL des statistiques construite : {self.stats_url}")

        if not self._get_stats_data():
            print("    -> 🛑 Arrêt du processus pour cette URL en raison d'un échec de la récupération des données.")
            return False

        df_new = self._parse_and_prepare_dataframe()
        if df_new is not None and not df_new.empty:
            print("\nÉtape 5 : Exportation des données vers Excel... 💾")
            try:
                if os.path.exists(output_filename):
                    print(f"    -> 💾 Le fichier '{output_filename}' existe. Ajout des nouvelles données.")
                    with pd.ExcelWriter(output_filename, engine='openpyxl', mode='a',
                                        if_sheet_exists='overlay') as writer:
                        df_existing = pd.read_excel(output_filename, sheet_name='Sheet1')
                        df_final = pd.concat([df_existing, df_new], ignore_index=True)
                        df_final.to_excel(writer, index=False, sheet_name='Sheet1')
                        print("    -> ✅ Données ajoutées avec succès.")
                else:
                    print(f"    -> 💾 Le fichier '{output_filename}' n'existe pas. Création...")
                    df_new.to_excel(output_filename, index=False)
                    print("    -> ✅ Fichier créé et données exportées avec succès.")
            except Exception as e:
                print(f"    -> ❌ Erreur lors de l'exportation Excel: {e}", file=sys.stderr)
            return True
        else:
            print("    -> ❌ Échec de l'exportation : Le DataFrame est vide.")
            return False


# ====================================================================
# --- LOGIQUE PRINCIPALE DU SCRIPT ---
# ====================================================================

if __name__ == "__main__":
    print("🚀 Début du script de scraping Metasail.")

    # --- ⚠️ REMPLACEZ LES CHEMINS CI-DESSOUS ⚠️ ---
    LOCAL_DIRECTORY_PATH = r"C:\Users\Byron Barette\Downloads"
    OUTPUT_FILENAME = "Metasail_Statistics_unified.xlsx"

    urls_to_process = []
    processed_files = set()
    successful_urls = 0
    failed_urls = 0

    # --- Initialisation du driver une seule fois ---
    try:
        options = Options()
        # options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        options.add_argument(f'--user-data-dir={PERSISTENT_DATA_DIR}')
        driver = webdriver.Chrome(options=options)

        with requests.Session() as session:
            urls_to_process = find_urls_from_local_files(LOCAL_DIRECTORY_PATH)

            if not urls_to_process:
                print("    -> ❌ Aucune URL de course trouvée. Fin du script.")
                sys.exit()

            print("\nÉtape 6 : Vérification des doublons dans le fichier de sortie... 🕵️‍♀️")
            if os.path.exists(OUTPUT_FILENAME):
                try:
                    print(f"    -> 🔎 Lecture du fichier '{OUTPUT_FILENAME}'...")
                    df_existing = pd.read_excel(OUTPUT_FILENAME, sheet_name='Sheet1')
                    if 'ID' in df_existing.columns:
                        processed_files = set(df_existing['ID'].dropna().unique())
                        print(f"    -> ✅ {len(processed_files)} fichier(s) déjà traité(s) trouvé(s).")
                    else:
                        print(
                            "    -> ⚠️ Avertissement : La colonne 'ID' est absente. Impossible de vérifier les doublons.")
                except Exception as e:
                    print(f"    -> ❌ Avertissement : Impossible de lire le fichier existant. {e}")

            total_urls = len(urls_to_process)
            for i, source_url in enumerate(urls_to_process):
                source_name = urlparse(source_url).query
                print(f"\n--- 🏁 Traitement de l'URL {i + 1}/{total_urls} : {source_url} ---")
                if source_name in processed_files:
                    print(f"    -> ⏭️ L'URL '{source_name}' a déjà été traitée. Passage à la suivante.")
                    successful_urls += 1
                    continue
                try:
                    parsed_url = urlparse(source_url)
                    query_params = parse_qs(parsed_url.query)
                    event_id, token = query_params.get('idgara', [None])[0], query_params.get('token', [None])[0]
                    if not event_id or not token:
                        print(f"    -> ❌ ERREUR: idgara/token introuvable dans : {source_url}.")
                        failed_urls += 1
                        continue
                    scraper = MetasailScraper(
                        event_url=source_url,
                        event_id=event_id,
                        token=token,
                        source_name=source_name,
                        session=session
                    )
                    if scraper.scrape_and_export(driver=driver, output_filename=OUTPUT_FILENAME):
                        successful_urls += 1
                    else:
                        failed_urls += 1
                except Exception as e:
                    print(f"    -> ❌ Une erreur inattendue est survenue pour l'URL {source_url}: {e}", file=sys.stderr)
                    failed_urls += 1

    finally:
        if 'driver' in locals() and driver:
            print("\n--- 🌐 Fermeture de la session Chrome... ---")
            driver.quit()

    print("\n" + "=" * 50)
    print("--- ✅ Rapport final de scraping ✅ ---")
    print("=" * 50)
    print(f"Total d'URLs traitées : {total_urls}")
    print(f"URLs avec succès : {successful_urls} ✅")
    print(f"URLs échouées : {failed_urls} ❌")
    print("\n--- ✅ Tous les scrapings sont terminés. 🎉 ---")
