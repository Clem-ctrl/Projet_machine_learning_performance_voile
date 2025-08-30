import requests
import json
import time
import pandas as pd
from datetime import datetime, date
import pytz
import os
from collections import defaultdict

# --- Configuration ---
API_KEY = "ce67699e859dc91888145732202e8f26"

# Constante de conversion de la vitesse du vent de mètres par seconde (m/s) à des nœuds (kts)
M_S_TO_KNOTS = 1.94384

# Points de terminaison de l'API pour OpenWeatherMap
GEO_API_ENDPOINT = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_API_ENDPOINT = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
OUTPUT_FILE = "weather_data_cleaned.xlsx"
INPUT_FILE = "Metasail_Statistics_ML_test_processed.xlsx"


# --- Classe principale du processeur de météo ---
class WeatherProcessor:
    def __init__(self, api_key, geo_endpoint, weather_endpoint, output_file):
        """Initialise le WeatherProcessor avec les détails de l'API et les chemins de fichiers."""
        self.api_key = api_key
        self.geo_endpoint = geo_endpoint
        self.weather_endpoint = weather_endpoint
        self.output_file = output_file

    def get_geolocation(self, city_name):
        """Récupère la latitude et la longitude pour un nom de ville donné."""
        print(f"Récupération de la géolocalisation pour '{city_name}'...")
        params = {'q': city_name, 'limit': 1, 'appid': self.api_key}
        try:
            response = requests.get(self.geo_endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            if data:
                location = data[0]
                return {"lat": location.get('lat'), "lon": location.get('lon')}
            else:
                print(f"Aucun résultat de géolocalisation trouvé pour '{city_name}'.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération de la géolocalisation pour '{city_name}' : {e}")
            return None

    def fetch_historical_data(self, city_name, coords, start_day, end_day):
        """
        Récupère les données météorologiques historiques pour une plage de dates spécifiée.
        Les données incluent maintenant la pression, l'humidité, la direction du vent et la pluie.
        """
        weather_data = []
        all_days = pd.date_range(start_day, end_day, freq='D')

        print(
            f"\nRécupération des données pour : {city_name} (Lat: {coords['lat']}, Lon: {coords['lon']}) du {start_day} au {end_day}")

        for day in all_days:
            for hour in range(8, 21):
                current_dt_utc = datetime(day.year, day.month, day.day, hour, tzinfo=pytz.UTC)
                timestamp = int(current_dt_utc.timestamp())

                url = (
                    f"{self.weather_endpoint}?"
                    f"lat={coords['lat']}&lon={coords['lon']}&dt={timestamp}&appid={self.api_key}&units=metric"
                )

                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()

                    if "data" in data and len(data["data"]) > 0:
                        hourly_data = data["data"][0]

                        rain_data = hourly_data.get('rain', {})

                        extracted_metrics = {
                            "DateTimeUTC": datetime.fromtimestamp(hourly_data.get('dt', 0), tz=pytz.UTC),
                            "City": city_name,
                            "Latitude": coords['lat'],
                            "Longitude": coords['lon'],
                            "Temperature (°C)": round(hourly_data.get('temp', 0), 2),
                            "Wind Speed (kts)": round(hourly_data.get('wind_speed', 0) * M_S_TO_KNOTS, 2),
                            "Pressure (hPa)": hourly_data.get('pressure'),
                            "Humidity (%)": hourly_data.get('humidity'),
                            "Wind Direction (deg)": hourly_data.get('wind_deg'),
                            "Rain (mm)": rain_data.get('1h', 0)
                        }
                        weather_data.append(extracted_metrics)
                        print(f"Données récupérées pour : {current_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    else:
                        print(f"Aucune donnée trouvée pour {current_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except requests.exceptions.RequestException as e:
                    print(
                        f"Une erreur est survenue lors de la récupération pour {current_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} : {e}")

                time.sleep(1)

        return weather_data

    def process_and_export(self, city_name, date_ranges):
        """Orchestre la récupération, le traitement et l'exportation des données pour une ville."""
        for date_range in date_ranges:
            start_day = date_range["start_day"]
            end_day = date_range["end_day"]

            coords = self.get_geolocation(city_name)
            if not coords:
                print(f"Impossible de continuer sans les données de géolocalisation pour {city_name}.")
                continue

            weather_data = self.fetch_historical_data(city_name, coords, start_day, end_day)

            if not weather_data:
                print(f"\nAucune donnée n'a été collectée pour {city_name} dans la plage de dates spécifiée.")
                continue

            new_df = pd.DataFrame(weather_data)

            new_df['Jour'] = new_df['DateTimeUTC'].dt.day
            new_df['Mois'] = new_df['DateTimeUTC'].dt.month
            new_df['Année'] = new_df['DateTimeUTC'].dt.year
            new_df['Time'] = new_df['DateTimeUTC'].dt.strftime('%H:%M:%S')

            final_columns = ['Day', 'Month', 'Year', 'Time', 'City', 'Latitude', 'Longitude', 'Temperature (°C)',
                             'Pressure (hPa)', 'Humidity (%)', 'Wind Speed (kts)', 'Wind Direction (deg)', 'Rain (mm)']
            new_df = new_df[final_columns]

            self.export_to_excel(new_df)

    def export_to_excel(self, new_df):
        """Gère la logique de création ou d'ajout au fichier Excel."""
        try:
            if os.path.exists(self.output_file):
                print(f"\nLe fichier '{self.output_file}' existe, ajout des nouvelles données...")
                existing_df = pd.read_excel(self.output_file)

                final_df = pd.concat([existing_df, new_df], ignore_index=True)
                final_df.drop_duplicates(subset=['Day', 'Month', 'Year', 'Time', 'City'], keep='last', inplace=True)
            else:
                print(f"\nLe fichier '{self.output_file}' n'existe pas, création d'un nouveau fichier...")
                final_df = new_df

            if not final_df.empty:
                final_df['Full_Date'] = pd.to_datetime(final_df[['Year', 'Month', 'Day']])
                min_date = final_df['Full_Date'].min().strftime('%Y-%m-%d')
                max_date = final_df['Full_Date'].max().strftime('%Y-%m-%d')
                final_df = final_df.drop(columns='Full_Date')
            else:
                min_date, max_date = "N/A", "N/A"

            final_df.to_excel(self.output_file, index=False)
            print(f"\n✅ Exportation réussie vers '{self.output_file}'")
            print(f"Données enregistrées du {min_date} au {max_date}")

        except Exception as e:
            print(f"\n❌ Une erreur est survenue lors de l'exportation vers Excel : {e}")


def read_metasail_data(filepath):
    """
    Lit le fichier Excel de Metasail, extrait les lieux et les plages de dates,
    et les formate pour le processeur météo.
    """
    if not os.path.exists(filepath):
        print(f"Erreur : Le fichier d'entrée '{filepath}' est introuvable.")
        return []

    try:
        df = pd.read_excel(filepath)

        # Vérification des colonnes nécessaires
        required_cols = ['Lieu de l\'événement', 'Début du segment (timestamp)', 'Fin du segment (timestamp)']
        if not all(col in df.columns for col in required_cols):
            print(f"Erreur : Le fichier '{filepath}' ne contient pas toutes les colonnes requises.")
            print(f"Colonnes attendues : {required_cols}")
            return []

        # Convertir les timestamps en datetime et gérer les valeurs manquantes
        df['start_dt'] = pd.to_datetime(pd.to_numeric(df['Début du segment (timestamp)'], errors='coerce'), unit='s')
        df['end_dt'] = pd.to_datetime(pd.to_numeric(df['Fin du segment (timestamp)'], errors='coerce'), unit='s')

        df = df.dropna(subset=['Lieu de l\'événement', 'start_dt', 'end_dt'])

        # Grouper par lieu et trouver les dates min/max pour chaque événement
        weather_data_ref = defaultdict(lambda: {"start": None, "end": None})
        for _, row in df.iterrows():
            city = row['Lieu de l\'événement']
            start_dt = row['start_dt']
            end_dt = row['end_dt']

            if not weather_data_ref[city]["start"] or start_dt < weather_data_ref[city]["start"]:
                weather_data_ref[city]["start"] = start_dt
            if not weather_data_ref[city]["end"] or end_dt > weather_data_ref[city]["end"]:
                weather_data_ref[city]["end"] = end_dt

        # Formater les données pour le script météo
        cities_to_process = [
            {"city_name": city, "date_ranges": [{"start_day": data["start"].date(), "end_day": data["end"].date()}]}
            for city, data in weather_data_ref.items() if data["start"] and data["end"]
        ]

        return cities_to_process

    except Exception as e:
        print(f"Une erreur est survenue lors de la lecture du fichier Excel : {e}")
        return []


# --- Point d'entrée du script ---
if __name__ == "__main__":
    print(f"Étape 1 : Lecture du fichier d'entrée '{INPUT_FILE}' pour récupérer les lieux et les dates.")
    cities_to_process = read_metasail_data(INPUT_FILE)

    if cities_to_process:
        print("\nÉtape 2 : Lancement de la récupération des données météo.")
        print("Villes et dates à traiter :")
        for city in cities_to_process:
            print(
                f"  - {city['city_name']}: du {city['date_ranges'][0]['start_day']} au {city['date_ranges'][0]['end_day']}")

        processor = WeatherProcessor(
            api_key=API_KEY,
            geo_endpoint=GEO_API_ENDPOINT,
            weather_endpoint=WEATHER_API_ENDPOINT,
            output_file=OUTPUT_FILE
        )
        for entry in cities_to_process:
            processor.process_and_export(entry["city_name"], entry["date_ranges"])

        print("\nProcessus d'extraction des données météo terminé avec succès.")
    else:
        print("\nAucune donnée valide n'a pu être extraite du fichier Excel. Le processus est annulé.")
