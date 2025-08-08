import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
from bs4 import BeautifulSoup
import json
import time

# Importations spécifiques à Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
# Pour gérer automatiquement le pilote du navigateur
from webdriver_manager.chrome import ChromeDriverManager
# Pour les attentes explicites
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_event_info():
    """
    Récupère les informations sur l'événement en utilisant Selenium pour charger la page
    et exécuter le JavaScript, puis analyse le DOM final.
    """
    # URL de base sans l'ID de session temporaire
    event_url = "https://app.metasail.it/ViewRecordedRace2022.aspx"
    # Ajout du token nécessaire à la requête
    params = {'idgara': '42423', 'token': '2COK'}

    print("Initialisation du navigateur et chargement de la page avec JavaScript...")

    try:
        chrome_options = Options()
        #chrome_options.add_argument("--headless")
        #chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        # Construction de l'URL complète avec les paramètres
        full_url = requests.Request('GET', event_url, params=params).prepare().url

        # Le pilote accède à l'URL. Selenium attend que la page soit entièrement chargée.
        driver.get(full_url)

        # Gestion de la bannière de cookies
        try:
            # On cherche un bouton avec le texte 'Accept all' ou similaire pour l'accepter
            # Le sélecteur CSS '.cc-btn' est un choix courant pour ces bannières
            cookie_accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'cn-accept-cookie'))
            )
            cookie_accept_button.click()
            print("Bannière de cookies acceptée.")
            # Attendre un peu après le clic pour que la page se mette à jour
            time.sleep(2)
        except Exception:
            print("Aucune bannière de cookies trouvée ou gérée, on continue.")

        # Attente explicite pour s'assurer que l'élément <script> avec dataLayer.push est chargé
        # On peut attendre que la balise body soit présente pour s'assurer que la page est rendue
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Récupération du code source de la page, y compris les modifications du DOM
        page_source = driver.page_source

        driver.quit()

        soup = BeautifulSoup(page_source, 'html.parser')
        scripts = soup.find_all('script')

        event_name, race, race_date = None, None, None

        for script in scripts:
            if script.string and 'dataLayer.push' in script.string:
                match = re.search(r"dataLayer\.push\((.*?)\);", script.string, re.DOTALL)
                if match:
                    json_like_string = match.group(1).strip()
                    try:
                        json_valid_string = re.sub(r"'([^']*)'", r'"\1"', json_like_string)
                        data_dict = json.loads(json_valid_string)
                        event_name = data_dict.get('eventName')
                        race = data_dict.get('race')
                        race_date = data_dict.get('raceDate')

                        if event_name and race and race_date:
                            print("Informations sur l'événement récupérées avec succès en analysant l'objet JSON.")
                            return event_name, race, race_date
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Avertissement : Erreur lors de l'analyse JSON : {e}")
                        continue

        print("Avertissement: Impossible de trouver les détails de l'événement dans la page.")
        return None, None, None

    except Exception as e:
        print(f"Une erreur inattendue s'est produite lors de l'analyse: {e}")
        return None, None, None


def scrape_and_export_data():
    """
    Scrapes sailing statistics from the Metasail website, parses the XML data,
    and exports it to an Excel (.xlsx) file with French headers.
    """
    event_name, race_name, race_date = get_event_info()

    if not event_name or not race_name or not race_date:
        print("Les informations de l'événement n'ont pas pu être récupérées. Arrêt du script.")
        return

    stats_url = "https://app.metasail.it/(S(zdad033v3gz42eewebidnjgb))/MetaSailWS.asmx/getStatistiche?idgara=42423"

    translations = {
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

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    params = {
        'idgara': '42423',
        'token': '1UX5'
    }

    try:
        print("\nRécupération des données statistiques via POST...")
        response = requests.post(stats_url, headers=headers, data=params)
        response.raise_for_status()

        xml_content = response.text
        xml_content = re.sub(r'<\?xml.*?\?>', '', xml_content).strip()
        xml_content = re.sub(r'<string.*?>', '', xml_content, 1)
        xml_content = xml_content.rsplit('</string>', 1)[0]

        root = ET.fromstring(xml_content)

        data_rows = []

        for racer_data in root.findall('.//{http://meteda.it/}StatisticheDato'):
            racer_info = {}
            racer_info['Nom de l\'événement'] = event_name
            racer_info['Course'] = race_name
            racer_info['Date de la course'] = race_date

            for child in racer_data:
                if child.tag.endswith('}lstSegments'):
                    continue
                tag_name = child.tag.split('}')[1]
                translated_name = translations.get(tag_name, tag_name)
                racer_info[translated_name] = child.text

            for segment_data in racer_data.findall('.//{http://meteda.it/}cInfoRaceSegment'):
                segment_num = segment_data.find('{http://meteda.it/}SegNum').text
                segment_prefix = f'Segment {segment_num} - '

                for child in segment_data:
                    tag_name = child.tag.split('}')[1]
                    translated_name = translations.get(tag_name, tag_name)
                    if tag_name == 'SegNum':
                        continue
                    full_column_name = segment_prefix + translated_name
                    racer_info[full_column_name] = child.text

            data_rows.append(racer_info)

        if data_rows:
            df = pd.DataFrame(data_rows)
            first_cols = ['Nom de l\'événement', 'Course', 'Date de la course', translations['Nome']]
            other_cols = [col for col in df.columns if col not in first_cols]
            other_cols.sort()
            df = df[first_cols + other_cols]

            output_filename = "Metasail_Statistics.xlsx"
            df.to_excel(output_filename, index=False)
            print(f"\nLes données ont été exportées avec succès vers {output_filename}")
        else:
            print("Aucune donnée statistique trouvée à exporter.")

    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des données statistiques: {e}")
    except ET.ParseError as e:
        print(f"Erreur lors de l'analyse des données XML: {e}")
    except Exception as e:
        print(f"Une erreur inattendue s'est produite: {e}")


if __name__ == "__main__":
    scrape_and_export_data()

