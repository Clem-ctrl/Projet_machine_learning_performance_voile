import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import json
import time
import os
import glob
import random  # Importation pour les choix et délais aléatoires
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Importations spécifiques à Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- NOUVEAU : Constantes pour un scraping plus "poli" ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]
MIN_DELAY_SECONDS = 4
MAX_DELAY_SECONDS = 9
MAX_RETRIES = 3


# -----------------------------------------------------------

def find_html_files_and_extract_urls(directory_path):
    search_pattern = os.path.join(directory_path, "MetaSail for web*.html")
    html_files = glob.glob(search_pattern)
    urls_by_file = {}
    url_regex = re.compile(r'https://app\.metasail\.it/ViewRecordedRace2018\.aspx\?idgara=\d+&token=\w+')

    print(f"Recherche de fichiers correspondant à '{search_pattern}'...")
    for file_path in html_files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                found_urls = url_regex.findall(content)
                if found_urls:
                    urls_by_file[filename] = sorted(list(set(found_urls)))
                    print(f"  - Trouvé {len(urls_by_file[filename])} URL(s) dans '{filename}'")
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {filename}: {e}")
    if not urls_by_file:
        print("\nAucun fichier HTML avec des URLs valides n'a été trouvé.")
    return urls_by_file


class MetasailScraper:
    def __init__(self, event_url, stats_url, event_id, token, source_filename, session):
        self.event_url = event_url
        self.stats_url = stats_url
        self.event_id = event_id
        self.token = token
        self.source_filename = source_filename
        self.session = session  # NOUVEAU : Utilisation d'un objet session
        self.event_name, self.event_location, self.race_name, self.race_date, self.stats_data = None, None, None, None, None
        self.translations = {
            'Seriale': 'Numéro de série', 'Nome': 'Nom complet du coureur',
            'TotTempPerc': 'Temps total parcouru (s)', 'TotLungLato': 'Longueur totale du parcours (m)',
            'TotDistPerc': 'Distance totale parcourue (m)', 'PosPartenza': 'Position de départ',
            'TotDistRealeSuIdeale': 'Efficacité (Distance réelle/idéale) (%)', 'SegNum': 'Numéro de segment',
            'TopSpeed': 'Vitesse maximale (noeuds)', 'TopVMG': 'VMG maximale', 'TopVMC': 'VMC maximale',
            'AvgVMG': 'VMG moyenne', 'AvgVMC': 'VMC moyenne', 'AvgSpeed': 'Vitesse moyenne (noeuds)',
            'CrtRaceSegSX': 'Bâbord (%)', 'CrtRaceSegDX': 'Tribord (%)',
            'TimeSecPercorsi': 'Temps du segment (s)', 'SegDistRealePercorsa': 'Distance réelle du segment (m)',
            'LungLato': 'Longueur du côté du segment (m)', 'DirLato': 'Direction du côté du segment',
            'PercEffettivo': 'Efficacité du segment (%)', 'StartSeg': 'Début du segment (timestamp)',
            'EndSeg': 'Fin du segment (timestamp)', 'SegEnteredRank': 'Classement entrée de segment',
            'SegExitRank': 'Classement sortie de segment',
        }

    # --- NOUVEAU : Méthode centralisée pour les requêtes avec mesures anti-ban ---
    def _make_request(self, method, url, **kwargs):
        """Effectue une requête HTTP avec délais, User-Agent aléatoire et tentatives multiples."""
        for attempt in range(MAX_RETRIES):
            try:
                # 1. Attendre un délai aléatoire pour simuler un comportement humain
                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"(Tentative {attempt + 1}/{MAX_RETRIES}) Pause de {delay:.2f}s avant la requête vers {url}")
                time.sleep(delay)

                # 2. Préparer des headers réalistes
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "*/*",
                    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://app.metasail.it/"
                }
                # Mettre à jour avec les headers spécifiques si fournis
                if 'headers' in kwargs:
                    headers.update(kwargs['headers'])
                kwargs['headers'] = headers

                response = self.session.request(method, url, timeout=30, **kwargs)
                response.raise_for_status()  # Lève une exception pour les codes 4xx/5xx
                return response
            except requests.exceptions.RequestException as e:
                print(f"Erreur de requête (tentative {attempt + 1}): {e}")
                if attempt + 1 == MAX_RETRIES:
                    print("Nombre maximal de tentatives atteint. Abandon.")
                    return None
        return None

    @staticmethod
    def _split_name(full_name):
        parts = full_name.split()
        return (" ".join(parts[:-1]).strip(), parts[-1].strip()) if len(parts) > 1 else ("", full_name)

    @staticmethod
    def _extract_time_from_timestamp(timestamp):
        try:
            return datetime.fromtimestamp(float(timestamp)).strftime("%H:%M:%S")
        except (ValueError, TypeError, OSError):
            return None

    def _get_event_info(self):
        # Selenium simule déjà un vrai navigateur, donc pas besoin de headers custom ici.
        # Mais on garde une gestion d'erreur robuste.
        print("Initialisation de Selenium pour récupérer les informations de l'événement...")
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.get(self.event_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            page_source = driver.page_source
            driver.quit()

            soup = BeautifulSoup(page_source, 'html.parser')
            # ... (le reste de la logique de parsing est inchangé) ...
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'dataLayer.push' in script.string:
                    match = re.search(r"dataLayer\.push\((.*?)\);", script.string, re.DOTALL)
                    if match:
                        json_like_string = match.group(1).strip()
                        try:
                            json_valid_string = re.sub(r'(\w+):', r'"\1":', json_like_string).replace("'", '"')
                            data_dict = json.loads(json_valid_string)
                            self.event_name, self.race_name, self.race_date = data_dict.get('eventName'), data_dict.get(
                                'race'), data_dict.get('raceDate')
                            if self.event_name: self._split_event_name_and_location()
                            if self.event_name and self.race_name and self.race_date:
                                print("Informations sur l'événement récupérées avec succès.")
                                return True
                        except (json.JSONDecodeError, ValueError) as e:
                            print(f"Erreur de décodage JSON pour le script dataLayer : {e}")
            print("Avertissement: Impossible de trouver les détails de l'événement.")
            return False
        except Exception as e:
            print(f"Erreur inattendue lors de l'analyse avec Selenium: {e}")
            return False

    def _split_event_name_and_location(self):
        # Inchangé
        if not self.event_name: return
        match = re.search(r"^(.*?)(?:\s-\s|\s(?=\d{4})|\s([A-Z\s]+)(?=\s\d{4})|\s([A-Z\s]+)$)(.*)$", self.event_name)
        if match:
            self.event_name, self.event_location = match.group(1).strip(), match.group(4).strip()
        else:
            self.event_location = "N/A"

    # --- MODIFIÉ : Utilise maintenant la nouvelle méthode _make_request ---
    def _get_stats_data(self):
        print("\nRécupération des données statistiques via POST...")
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        params = {'idgara': self.event_id, 'token': self.token}

        response = self._make_request('POST', self.stats_url, headers=headers, data=params)

        if response:
            xml_content = response.text
            xml_content = re.sub(r'<\?xml.*?\?>', '', xml_content).strip()
            xml_content = re.sub(r'<string.*?>', '', xml_content, 1).rsplit('</string>', 1)[0]
            self.stats_data = xml_content
            print("Données statistiques récupérées avec succès.")
            return True
        else:
            print("Échec de la récupération des données statistiques après plusieurs tentatives.")
            return False

    # Le reste de la classe (_parse_and_prepare_dataframe, scrape_and_export) est inchangé...
    def _parse_and_prepare_dataframe(self):
        if not self.stats_data or not self.event_name: return None
        try:
            root = ET.fromstring(self.stats_data)
            data_rows = []
            namespace = '{http://meteda.it/}'
            for racer_data in root.findall(f'.//{namespace}StatisticheDato'):
                racer_info = {'ID': self.source_filename, 'Nom de l\'événement': self.event_name,
                              'Lieu de l\'événement': self.event_location, 'Course': self.race_name,
                              'Date de la course': self.race_date}
                full_name = racer_data.find(f'.//{namespace}Nome').text if racer_data.find(
                    f'.//{namespace}Nome') is not None else "N/A"
                last_name, first_name = self._split_name(full_name)
                racer_info['Nom de famille'], racer_info['Prénom'] = last_name, first_name
                for child in racer_data:
                    tag_name = child.tag.replace(namespace, '')
                    if tag_name in self.translations and child.text:
                        racer_info[self.translations[tag_name]] = child.text
                segments = racer_data.findall(f'.//{namespace}cInfoRaceSegment')
                if not segments:
                    data_rows.append(racer_info)
                else:
                    for segment_data in segments:
                        segment_row = racer_info.copy()
                        for child in segment_data:
                            tag_name = child.tag.replace(namespace, '')
                            if tag_name in self.translations and child.text:
                                segment_row[self.translations[tag_name]] = self._extract_time_from_timestamp(
                                    child.text) if tag_name in ['StartSeg', 'EndSeg'] else child.text
                        data_rows.append(segment_row)
            if not data_rows: return None
            df = pd.DataFrame(data_rows)
            if 'Nom complet du coureur' in df.columns: df.drop(columns=['Nom complet du coureur'], inplace=True)
            first_cols = ['ID', 'Nom de l\'événement', 'Lieu de l\'événement', 'Course', 'Date de la course',
                          'Nom de famille', 'Prénom', self.translations['Seriale']]
            other_cols = [col for col in df.columns if col not in first_cols]
            df = df.reindex(columns=first_cols + other_cols)
            return df
        except ET.ParseError as e:
            print(f"Erreur XML: {e}");
            return None

    def scrape_and_export(self, output_filename="Metasail_Statistics.xlsx"):
        if not (self._get_event_info() and self._get_stats_data()):
            print("Arrêt du processus pour cette URL en raison d'erreurs.");
            return
        df_new = self._parse_and_prepare_dataframe()
        if df_new is not None and not df_new.empty:
            try:
                if os.path.exists(output_filename):
                    print(f"\nAjout des données à '{output_filename}'...")
                    with pd.ExcelWriter(output_filename, engine='openpyxl', mode='a',
                                        if_sheet_exists='overlay') as writer:
                        df_existing = pd.read_excel(output_filename)
                        df_final = pd.concat([df_existing, df_new], ignore_index=True)
                        df_final.to_excel(writer, index=False, sheet_name='Sheet1')
                else:
                    print(f"\nCréation de '{output_filename}'...")
                    df_new.to_excel(output_filename, index=False)
                print("Données exportées avec succès.")
            except Exception as e:
                print(f"Erreur lors de l'exportation Excel: {e}")
        else:
            print("Échec de l'exportation : DataFrame vide.")


if __name__ == "__main__":
    DOWNLOADS_PATH = r"C:\Users\User\Downloads"
    OUTPUT_FILENAME = "Metasail_Statistics_ML_test.xlsx"

    urls_to_process_by_file = find_html_files_and_extract_urls(DOWNLOADS_PATH)
    processed_files = set()
    if os.path.exists(OUTPUT_FILENAME):
        try:
            print(f"\nLecture du fichier '{OUTPUT_FILENAME}' pour vérifier les doublons...")
            df_existing = pd.read_excel(OUTPUT_FILENAME)
            if 'ID' in df_existing.columns:
                processed_files = set(df_existing['ID'].dropna().unique())
                print(f"{len(processed_files)} fichier(s) déjà traité(s) trouvé(s).")
        except Exception as e:
            print(f"Avertissement : Impossible de lire le fichier existant. {e}")

    # --- MODIFIÉ : Création d'une session unique pour toutes les requêtes ---
    with requests.Session() as session:
        file_counter = 0
        total_files = len(urls_to_process_by_file)
        for filename, urls in urls_to_process_by_file.items():
            file_counter += 1
            print(f"\n--- Traitement du fichier {file_counter}/{total_files} : {filename} ---")

            if filename in processed_files:
                print(f"Le fichier '{filename}' a déjà été traité. Passage au suivant.")
                continue

            for i, source_url in enumerate(urls):
                print(f"\n--- Lancement du scraping pour l'URL {i + 1}/{len(urls)} de ce fichier ---\n")
                try:
                    parsed_url = urlparse(source_url)
                    query_params = parse_qs(parsed_url.query)
                    event_id, token = query_params.get('idgara', [None])[0], query_params.get('token', [None])[0]

                    if not event_id or not token:
                        print(f"ERREUR: idgara/token introuvable dans : {source_url}.");
                        continue

                    print(f"ID Gara: {event_id}, Token: {token}")

                    # --- MODIFIÉ : La requête GET initiale utilise aussi les mesures de politesse ---
                    delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                    print(f"Pause de {delay:.2f}s avant la requête GET initiale...")
                    time.sleep(delay)
                    headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": "https://www.google.com/"}
                    response = session.get(source_url, timeout=10, headers=headers)
                    response.raise_for_status()
                    final_event_url = response.url

                    url_base = final_event_url.rsplit('/', 1)[0]
                    stats_url = f"{url_base}/MetaSailWS.asmx/getStatistiche?idgara={event_id}&token={token}"

                    scraper = MetasailScraper(
                        event_url=final_event_url,
                        stats_url=stats_url,
                        event_id=event_id,
                        token=token,
                        source_filename=filename,
                        session=session  # On passe la session au scraper
                    )
                    scraper.scrape_and_export(output_filename=OUTPUT_FILENAME)

                except requests.exceptions.RequestException as e:
                    print(f"Une erreur réseau est survenue pour l'URL {source_url}: {e}")
                except Exception as e:
                    print(f"Une erreur inattendue est survenue pour l'URL {source_url}: {e}")

    print("\n\n--- Tous les scrapings sont terminés. ---")