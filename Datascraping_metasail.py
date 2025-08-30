import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import json
import time
import os
import glob
import random
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import subprocess
from bs4 import BeautifulSoup

# --- Constantes pour un scraping plus "poli" ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]
MIN_DELAY_SECONDS = 9
MAX_DELAY_SECONDS = 30
MAX_RETRIES = 1


class MetasailScraper:
    def __init__(self, event_url, stats_url, event_id, token, source_filename, session):
        self.event_url = event_url
        self.stats_url = stats_url
        self.event_id = event_id
        self.token = token
        self.source_filename = source_filename
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

    def _make_request(self, method, url, **kwargs):
        """Effectue une requête HTTP avec délais, User-Agent aléatoire et tentatives multiples."""
        for attempt in range(MAX_RETRIES):
            try:
                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"(Tentative {attempt + 1}/{MAX_RETRIES}) Pause de {delay:.2f}s avant la requête vers {url}")
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
                return response
            except requests.exceptions.RequestException as e:
                print(f"Erreur de requête (tentative {attempt + 1}): {e}")
                if attempt + 1 == MAX_RETRIES:
                    print("Nombre maximal de tentatives atteint. Abandon.")
                    return None
        return None

    def _scrape_page_with_cli(self, url):
        """
        Utilise single-file-cli pour scraper le contenu complet d'une page.
        """
        print(f"\nRécupération du contenu de la page avec single-file-cli...")
        command = [
            "single-file",
            "--dump-content",
            url
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=60, encoding='utf-8')
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'exécution de single-file-cli : {e.stderr}")
        except FileNotFoundError:
            print("Erreur : La commande 'single-file' n'a pas été trouvée. Vérifiez votre PATH.")
        except subprocess.TimeoutExpired:
            print("Erreur : La commande single-file a dépassé le temps d'exécution imparti.")
        return None

    def _get_event_and_wind_info(self):
        """
        Scrape les informations sur l'événement et l'orientation du vent à l'aide de single-file-cli.
        """
        page_source = self._scrape_page_with_cli(self.event_url)
        if not page_source:
            return False

        # Utilisation de BeautifulSoup pour une extraction plus robuste du titre de la page
        soup = BeautifulSoup(page_source, 'html.parser')
        title_element = soup.find('div', id='lblTitle') or soup.find('div', class_='title')
        if title_element and title_element.text.strip():
            self.event_name = title_element.text.strip()
            print(f"Nom de la compétition récupéré : '{self.event_name}'")
        else:
            print("Avertissement: Impossible de trouver le nom de la compétition sur la page.")

        # Utilisation de regex pour l'orientation du vent
        wind_regex = re.search(r'<div id=lblWind>Wind\s(\d+)°<\/div>', page_source)
        if wind_regex:
            self.wind_orientation_metasail = wind_regex.group(1)
            print(f"Orientation du vent trouvée : {self.wind_orientation_metasail}°")
        else:
            print("Avertissement : Orientation du vent non trouvée dans le code source.")

        return self.event_name is not None or self.wind_orientation_metasail is not None

    def _get_stats_data(self):
        """Récupère les données statistiques via une requête POST."""
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

    @staticmethod
    def _extract_time_from_timestamp(timestamp):
        try:
            return datetime.fromtimestamp(float(timestamp)).strftime("%H:%M:%S")
        except (ValueError, TypeError, OSError):
            return None

    def _parse_and_prepare_dataframe(self):
        if not self.stats_data or not self.event_name: return None
        try:
            root = ET.fromstring(self.stats_data)
            data_rows = []
            namespace = '{http://meteda.it/}'
            for racer_data in root.findall(f'.//{namespace}StatisticheDato'):
                racer_info = {'ID': self.source_filename, 'Nom de l\'événement': self.event_name,
                              'Lieu de l\'événement': self.event_location, 'Course': self.race_name,
                              'Date de la course': self.race_date,
                              'Orientation vent metasail': self.wind_orientation_metasail}

                full_name_element = racer_data.find(f'.//{namespace}Nome')
                if full_name_element is not None:
                    racer_info['Nom complet'] = full_name_element.text
                else:
                    racer_info['Nom complet'] = "N/A"

                for child in racer_data:
                    tag_name = child.tag.replace(namespace, '')
                    if tag_name in self.translations and tag_name != 'Nome' and child.text:
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
            first_cols = ['ID', 'Nom de l\'événement', 'Lieu de l\'événement', 'Course', 'Date de la course',
                          'Orientation vent metasail', 'Nom complet', self.translations['Seriale']]
            other_cols = [col for col in df.columns if col not in first_cols]
            df = df.reindex(columns=first_cols + other_cols)
            return df
        except ET.ParseError as e:
            print(f"Erreur XML: {e}");
            return None

    def scrape_and_export(self, output_filename="Metasail_Statistics_ML_test_V2.xlsx"):
        if not (self._get_event_and_wind_info() and self._get_stats_data()):
            print("Arrêt du processus pour cette URL en raison d'erreurs.")
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


def find_metasail_urls_from_webpage(url, session):
    """
    Récupère le contenu d'une page web via single-file-cli et en extrait toutes les URLs Metasail.
    """
    print(f"Récupération des URLs depuis la page : {url}")
    scraper = MetasailScraper(url, "", "", "", "", session)
    page_source = scraper._scrape_page_with_cli(url)
    if not page_source:
        print("Erreur : Impossible de récupérer le contenu de la page pour extraire les URLs.")
        return []

    found_urls = []
    soup = BeautifulSoup(page_source, 'html.parser')
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('https://app.metasail.it/ViewRecordedRace2018.aspx'):
            # Normaliser l'URL en remplaçant &amp; par &
            normalized_href = href.replace('&amp;', '&')
            found_urls.append(normalized_href)

    if found_urls:
        unique_urls = sorted(list(set(found_urls)))
        print(f"  - Trouvé {len(unique_urls)} URL(s) de courses valides.")
        return unique_urls

    print("  - Aucune URL de course valide n'a été trouvée sur cette page.")
    return []


if __name__ == "__main__":
    # --- Modifiez cette URL pour le point de départ de votre recherche d'URLs ---
    # Remplacez cette URL par une page Metasail contenant des liens vers des courses enregistrées.
    STARTING_URLS = ["https://www.metasail.fr/past/738/"]
                     #"https://www.metasail.fr/past/732", "https://www.metasail.fr/past/670", ""]

    OUTPUT_FILENAME = "Metasail_Statistics_ML_test_V2.xlsx"

    urls_to_process = []
    processed_files = set()

    # Vérifier les doublons à partir du fichier Excel existant
    if os.path.exists(OUTPUT_FILENAME):
        try:
            print(f"\nLecture du fichier '{OUTPUT_FILENAME}' pour vérifier les doublons...")
            df_existing = pd.read_excel(OUTPUT_FILENAME)
            if 'ID' in df_existing.columns:
                processed_files = set(df_existing['ID'].dropna().unique())
                print(f"{len(processed_files)} fichier(s) déjà traité(s) trouvé(s).")
        except Exception as e:
            print(f"Avertissement : Impossible de lire le fichier existant. {e}")

    with requests.Session() as session:
        for url in STARTING_URLS:
            urls_to_process.extend(find_metasail_urls_from_webpage(url, session))

        total_urls = len(urls_to_process)
        for i, source_url in enumerate(urls_to_process):
            # Utilisez l'URL comme un identifiant unique dans la colonne 'ID'
            source_filename = urlparse(source_url).query
            print(f"\n--- Traitement de l'URL {i + 1}/{total_urls} : {source_url} ---")
            if source_filename in processed_files:
                print(f"L'URL '{source_filename}' a déjà été traitée. Passage à la suivante.")
                continue

            try:
                parsed_url = urlparse(source_url)
                query_params = parse_qs(parsed_url.query)
                event_id, token = query_params.get('idgara', [None])[0], query_params.get('token', [None])[0]
                if not event_id or not token:
                    print(f"ERREUR: idgara/token introuvable dans : {source_url}.");
                    continue

                print(f"ID Gara: {event_id}, Token: {token}")

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
                    source_filename=source_filename,
                    session=session
                )

                scraper.scrape_and_export(output_filename=OUTPUT_FILENAME)

            except requests.exceptions.RequestException as e:
                print(f"Une erreur réseau est survenue pour l'URL {source_url}: {e}")
            except Exception as e:
                print(f"Une erreur inattendue est survenue pour l'URL {source_url}: {e}")

    print("\n\n--- Tous les scrapings sont terminés. ---")