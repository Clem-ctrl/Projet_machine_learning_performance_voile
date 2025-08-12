import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import json
import time
import os
from urllib.parse import urlparse, parse_qs

# Importations spécifiques à Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


class MetasailScraper:
    """
    Classe pour récupérer et analyser les données de course du site Metasail.
    (Your class code remains the same as you provided)
    """

    def __init__(self, event_url, stats_url, event_id, token):
        """
        Initialise le scraper avec les URLs, l'ID de l'événement et le token.

        Args:
            event_url (str): L'URL de la page de l'événement.
            stats_url (str): L'URL du service web pour les statistiques.
            event_id (str): L'identifiant de la course.
            token (str): Le token de session pour l'authentification.
        """
        self.event_url = event_url
        self.stats_url = stats_url
        self.event_id = event_id
        self.token = token

        # Attributs pour stocker les données récupérées
        self.event_name = None
        self.race_name = None
        self.race_date = None
        self.stats_data = None

        # Dictionnaire de traduction pour les en-têtes du DataFrame
        self.translations = {
            'Seriale': 'Numéro de série',
            'Nome': 'Nom du coureur',
            'TotTempPerc': 'Temps total parcouru (s)',
            'TotLungLato': 'Longueur totale du parcours (m)',
            'TotDistPerc': 'Distance totale parcourue (m)',
            'PosPartenza': 'Position de départ',
            'TotDistRealeSuIdeale': 'Efficacité (Distance réelle/idéale) (%)',
            'SegNum': 'Numéro de segment',
            'TopSpeed': 'Vitesse maximale (noeuds)',
            'TopVMG': 'VMG maximale',
            'TopVMC': 'VMC maximale',
            'AvgVMG': 'VMG moyenne',
            'AvgVMC': 'VMC moyenne',
            'AvgSpeed': 'Vitesse moyenne (noeuds)',
            'CrtRaceSegSX': 'Bâbord (%)',
            'CrtRaceSegDX': 'Tribord (%)',
            'TimeSecPercorsi': 'Temps du segment (s)',
            'SegDistRealePercorsa': 'Distance réelle du segment (m)',
            'LungLato': 'Longueur du côté du segment (m)',
            'DirLato': 'Direction du côté du segment',
            'PercEffettivo': 'Efficacité du segment (%)',
            'StartSeg': 'Début du segment (timestamp)',
            'EndSeg': 'Fin du segment (timestamp)',
            'SegEnteredRank': 'Classement entrée de segment',
            'SegExitRank': 'Classement sortie de segment',
        }

    def _get_event_info(self):
        """
        Méthode privée pour récupérer les informations de l'événement en utilisant Selenium.
        """
        print("Initialisation du navigateur et chargement de la page avec JavaScript...")
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # Utiliser le self.event_url qui inclut déjà la session et les paramètres
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.get(self.event_url)

            try:
                cookie_accept_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, 'cn-accept-cookie'))
                )
                cookie_accept_button.click()
                print("Bannière de cookies acceptée.")
                time.sleep(2)
            except Exception:
                print("Aucune bannière de cookies trouvée ou gérée, on continue.")

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            page_source = driver.page_source
            driver.quit()

            soup = BeautifulSoup(page_source, 'html.parser')
            scripts = soup.find_all('script')

            for script in scripts:
                if script.string and 'dataLayer.push' in script.string:
                    match = re.search(r"dataLayer\.push\((.*?)\);", script.string, re.DOTALL)
                    if match:
                        json_like_string = match.group(1).strip()
                        try:
                            json_valid_string = re.sub(r"'([^']*)'", r'"\1"', json_like_string)
                            data_dict = json.loads(json_valid_string)
                            self.event_name = data_dict.get('eventName')
                            self.race_name = data_dict.get('race')
                            self.race_date = data_dict.get('raceDate')

                            if self.event_name and self.race_name and self.race_date:
                                print("Informations sur l'événement récupérées avec succès.")
                                return True
                        except (json.JSONDecodeError, ValueError):
                            continue
            print("Avertissement: Impossible de trouver les détails de l'événement dans la page.")
            return False

        except Exception as e:
            print(f"Une erreur inattendue s'est produite lors de l'analyse: {e}")
            return False

    def _get_stats_data(self):
        """
        Méthode privée pour récupérer les données statistiques via une requête POST.
        """
        print("\nRécupération des données statistiques via POST...")
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        params = {'idgara': self.event_id, 'token': self.token}

        try:
            # Note: We now use the stats_url passed during initialization
            response = requests.post(self.stats_url, headers=headers, data=params)
            response.raise_for_status()

            xml_content = response.text
            xml_content = re.sub(r'<\?xml.*?\?>', '', xml_content).strip()
            xml_content = re.sub(r'<string.*?>', '', xml_content, 1)
            xml_content = xml_content.rsplit('</string>', 1)[0]

            self.stats_data = xml_content
            print("Données statistiques récupérées avec succès.")
            return True

        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des données statistiques: {e}")
            return False
        except Exception as e:
            print(f"Une erreur inattendue s'est produite lors de la récupération des stats: {e}")
            return False

    def _parse_and_prepare_dataframe(self):
        """
        Méthode privée pour parser les données XML et préparer le DataFrame.
        """
        if not self.stats_data or not self.event_name:
            print("Données manquantes pour créer le DataFrame.")
            return None

        try:
            root = ET.fromstring(self.stats_data)
            if len(list(root)) == 0:
                print("Avertissement : L'objet root est vide. Le parsing a probablement échoué.")
                return None
            else:
                print("Le parsing a réussi et des éléments ont été trouvés.")

            data_rows = []
            namespace = '{http://meteda.it/}'

            for racer_data in root.findall(f'.//{namespace}StatisticheDato'):
                racer_info = {
                    'Nom de l\'événement': self.event_name,
                    'Course': self.race_name,
                    'Date de la course': self.race_date
                }
                for child in racer_data:
                    tag_name = child.tag.replace(namespace, '')
                    if tag_name in ['Nome', 'Seriale'] and child.text:
                        racer_info[self.translations.get(tag_name)] = child.text

                segments = racer_data.findall(f'.//{namespace}cInfoRaceSegment')
                if not segments:
                    data_rows.append(racer_info)
                else:
                    for segment_data in segments:
                        segment_row = racer_info.copy()
                        for child in segment_data:
                            tag_name = child.tag.replace(namespace, '')
                            if tag_name in self.translations and child.text:
                                segment_row[self.translations.get(tag_name)] = child.text
                        data_rows.append(segment_row)

            if not data_rows:
                print("Aucune donnée statistique trouvée après le parsing.")
                return None

            df = pd.DataFrame(data_rows)
            timestamp_cols = ['Début du segment (timestamp)', 'Fin du segment (timestamp)']
            for col in timestamp_cols:
                if col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col].astype(str).str.strip(), errors='coerce')
                        df[col] = pd.to_datetime(df[col], unit='s', errors='coerce')
                        df[col] = df[col].dt.strftime('%Y/%m/%d %H:%M:%S')
                    except Exception as e:
                        print(f"Erreur de conversion de la colonne {col}: {e}")

            first_cols = ['Nom de l\'événement', 'Course', 'Date de la course', self.translations['Nome'],
                          self.translations['Seriale']]
            translated_tags = [self.translations[tag] for tag in self.translations.keys()]
            other_cols = [col for col in df.columns if col not in first_cols and col in translated_tags]
            other_cols.sort(key=lambda x: list(self.translations.values()).index(x) if x in list(
                self.translations.values()) else -1)

            final_cols = first_cols + other_cols
            df = df.reindex(columns=final_cols)  # Use reindex for safety

            print("Aperçu du DataFrame final :")
            print(df.head())
            return df

        except ET.ParseError as e:
            print(f"Erreur lors de l'analyse des données XML: {e}")
            return None
        except Exception as e:
            print(f"Une erreur inattendue s'est produite lors de la préparation du DataFrame: {e}")
            return None

    def scrape_and_export(self, output_filename="Metasail_Statistics.xlsx"):
        """
        Méthode principale pour exécuter le processus complet de scraping et d'export.
        """
        if not self._get_event_info():
            print("Arrêt du script en raison d'une erreur de récupération des infos de l'événement.")
            return

        if not self._get_stats_data():
            print("Arrêt du script en raison d'une erreur de récupération des données statistiques.")
            return

        df_new = self._parse_and_prepare_dataframe()
        if df_new is not None:
            try:
                if os.path.exists(output_filename):
                    print(f"\nLe fichier '{output_filename}' existe, ajout des nouvelles données.")
                    df_existing = pd.read_excel(output_filename)
                    df_final = pd.concat([df_existing, df_new], ignore_index=True)
                    df_final.to_excel(output_filename, index=False)
                    print(f"Les données ont été ajoutées avec succès à {output_filename}")
                else:
                    print(f"\nLe fichier '{output_filename}' n'existe pas, création d'un nouveau fichier.")
                    df_new.to_excel(output_filename, index=False)
                    print(f"Les données ont été exportées avec succès vers {output_filename}")
            except Exception as e:
                print(f"Erreur lors de l'exportation du fichier Excel: {e}")
        else:
            print("Échec de l'exportation : DataFrame vide ou non valide.")


# --- NOUVELLE PARTIE : UTILISATION AUTOMATISÉE DU SCRIPT ---
if __name__ == "__main__":

    # C'est la seule liste que vous avez besoin de modifier.
    # Ajoutez simplement les URL sources des courses que vous voulez scraper.
    SOURCE_URLS = [
        "https://app.metasail.it/ViewRecordedRace2018.aspx?idgara=42375&token=PT35",
        "https://app.metasail.it/ViewRecordedRace2018.aspx?idgara=42368&token=WCEO"
        # Ajoutez d'autres URL ici
    ]

    OUTPUT_FILENAME = "Metasail_Statistics.xlsx"

    # Boucle sur chaque URL source pour extraire les informations et lancer le scraper
    for i, source_url in enumerate(SOURCE_URLS):
        print(f"\n--- Lancement du scraping pour l'URL {i + 1}/{len(SOURCE_URLS)} ---\n")

        try:
            # 1. Analyser l'URL source pour extraire idgara et token
            parsed_url = urlparse(source_url)
            query_params = parse_qs(parsed_url.query)

            event_id = query_params.get('idgara', [None])[0]
            token = query_params.get('token', [None])[0]

            if not event_id or not token:
                print(f"ERREUR: idgara ou token introuvable dans l'URL : {source_url}. Passage au suivant.")
                continue

            print(f"ID Gara: {event_id}, Token: {token} extraits de l'URL source.")

            # 2. Obtenir l'URL de session en faisant une requête GET
            print("Récupération de l'URL de session...")
            response = requests.get(source_url, timeout=10)
            response.raise_for_status()  # S'assure que la requête a réussi

            # L'URL de l'événement est l'URL finale après redirection, incluant les paramètres
            final_event_url = response.url
            print(f"URL de session trouvée : {final_event_url}")

            # 3. Construire l'URL des statistiques à partir de l'URL de l'événement
            # On prend la base de l'URL de l'événement et on remplace la fin
            url_base = final_event_url.rsplit('/', 1)[0]
            stats_url = f"{url_base}/MetaSailWS.asmx/getStatistiche?={event_id}&{token}"
            print(f"URL des statistiques construite : {stats_url}")

            # 4. Initialiser et lancer le scraper avec les informations trouvées
            scraper = MetasailScraper(
                event_url=final_event_url,  # On passe l'URL complète avec session et paramètres
                stats_url=stats_url,
                event_id=event_id,
                token=token
            )
            scraper.scrape_and_export(output_filename=OUTPUT_FILENAME)

        except requests.exceptions.RequestException as e:
            print(f"Une erreur réseau est survenue pour l'URL {source_url}: {e}")
        except Exception as e:
            print(f"Une erreur inattendue est survenue pour l'URL {source_url}: {e}")

    print("\n\n--- Tous les scrapings sont terminés. ---")