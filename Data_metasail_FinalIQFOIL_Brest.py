import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
from bs4 import BeautifulSoup
import json
import time
import openpyxl
import os  # Importez la bibliothèque pour vérifier l'existence des fichiers

# Importations spécifiques à Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MetasailScraper:
    """
    Classe pour récupérer et analyser les données de course du site Metasail.
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
            #chrome_options.add_argument("--headless")
            #chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

            params = {'idgara': self.event_id, 'token': self.token}
            full_url = requests.Request('GET', self.event_url, params=params).prepare().url
            driver.get(full_url)

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
            data_rows = []

            for racer_data in root.findall('.//{http://meteda.it/}StatisticheDato'):
                racer_info = {
                    'Nom de l\'événement': self.event_name,
                    'Course': self.race_name,
                    'Date de la course': self.race_date
                }

                for child in racer_data:
                    if child.tag.endswith('}lstSegments'):
                        continue
                    tag_name = child.tag.split('}')[1]
                    # Utiliser `in` pour vérifier si la balise est dans le dictionnaire
                    if tag_name in self.translations:
                        translated_name = self.translations[tag_name]
                        racer_info[translated_name] = child.text

                for segment_data in racer_data.findall('.//{http://meteda.it/}cInfoRaceSegment'):
                    segment_num = segment_data.find('{http://meteda.it/}SegNum').text
                    segment_prefix = f'Segment {segment_num} - '

                    for child in segment_data:
                        tag_name = child.tag.split('}')[1]
                        # Utiliser `in` pour vérifier si la balise est dans le dictionnaire
                        if tag_name in self.translations:
                            translated_name = self.translations[tag_name]
                            if tag_name == 'SegNum':
                                continue
                            full_column_name = segment_prefix + translated_name
                            racer_info[full_column_name] = child.text

                data_rows.append(racer_info)

            if not data_rows:
                print("Aucune donnée statistique trouvée après le parsing.")
                return None

            df = pd.DataFrame(data_rows)
            first_cols = ['Nom de l\'événement', 'Course', 'Date de la course', self.translations['Nome']]
            # La logique pour les autres colonnes doit aussi filtrer les tags non traduits
            all_translated_cols = [self.translations[tag] for tag in self.translations if tag in df.columns]
            other_cols = [col for col in df.columns if col not in first_cols and col in all_translated_cols]
            other_cols.sort()
            df = df[first_cols + other_cols]

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
        L'export se fait en ajoutant des lignes au fichier Excel existant.
        """
        if not self._get_event_info():
            print("Arrêt du script en raison d'une erreur de récupération des infos de l'événement.")
            return

        if not self._get_stats_data():
            print("Arrêt du script en raison d'une erreur de récupération des données statistiques.")
            return

        df_new_data = self._parse_and_prepare_dataframe()

        if df_new_data is not None:
            try:
                # Vérifier si le fichier existe déjà
                if os.path.exists(output_filename):
                    print(f"Le fichier {output_filename} existe. Ajout des nouvelles données...")
                    # Lire le fichier existant
                    df_existing = pd.read_excel(output_filename, engine='openpyxl')
                    # Concaténer les nouvelles données avec les données existantes
                    df_combined = pd.concat([df_existing, df_new_data], ignore_index=True)
                    # Réécrire le fichier avec le DataFrame combiné
                    df_combined.to_excel(output_filename, index=False, engine='openpyxl')
                    print(f"\nLes nouvelles données ont été ajoutées avec succès au fichier {output_filename}")
                else:
                    print(f"Le fichier {output_filename} n'existe pas. Création d'un nouveau fichier...")
                    # Si le fichier n'existe pas, le créer
                    df_new_data.to_excel(output_filename, index=False, engine='openpyxl')
                    print(f"\nLe fichier {output_filename} a été créé avec les données de la course.")

            except Exception as e:
                print(f"Erreur lors de l'exportation du fichier Excel: {e}")
        else:
            print("Échec de l'exportation : DataFrame vide ou non valide.")


# --- Utilisation du script ---
if __name__ == "__main__":    # Définir ici les variables que vous voulez modifier
    ID_GARA = "42391"
    TOKEN_ACCES = "WPEG"
    EVENT_URL = "https://app.metasail.it/(S(qhmcfygi2plxb5jw2xhuuvul))/ViewRecordedRace2022.aspx?idgara=42391&token=WPEG"
    STATS_URL = "https://app.metasail.it/(S(qhmcfygi2plxb5jw2xhuuvul))/MetaSailWS.asmx/getStatistiche"

    # Créez une instance de la classe en passant toutes les variables
    scraper = MetasailScraper(
        event_url=EVENT_URL,
        stats_url=STATS_URL,
        event_id=ID_GARA,
        token=TOKEN_ACCES
    )

    # Exécutez la méthode principale
    scraper.scrape_and_export()
