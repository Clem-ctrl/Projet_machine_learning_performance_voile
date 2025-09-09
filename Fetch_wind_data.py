import requests
import pandas as pd
import time
import pytz
import os
from datetime import datetime
from collections import defaultdict

# --- Configuration ---
API_KEY = "ce67699e859dc91888145732202e8f26"

INPUT_FILE = r"C:\Users\Byron Barette\PycharmProjects\Projet_machine_learning_performance_voile\Metasail_Statistics_unified.xlsx"

OUTPUT_FILE = "weather_data_from_coords.xlsx"

WEATHER_API_ENDPOINT = "https://api.openweathermap.org/data/3.0/onecall/timemachine"

M_S_TO_KNOTS = 1.94384


# --- Fonctions de traitement des données ---

def read_source_data(filepath):
    """
    Lit le fichier Excel source pour extraire les coordonnées GPS et les plages de dates consolidées.
    """
    COL_COORDS = "Lieu de l'événement"
    COL_DATE = "Date de la course"
    COL_START_TIME = "Début du segment (timestamp)"
    COL_END_TIME = "Fin du segment (timestamp)"

    required_cols = [COL_COORDS, COL_DATE, COL_START_TIME, COL_END_TIME]

    if not os.path.exists(filepath):
        print(f"❌ Erreur : Le fichier d'entrée '{filepath}' est introuvable.")
        return []

    try:
        df = pd.read_excel(filepath)
        print(f"✅ Fichier '{filepath}' lu avec succès.")

        if not all(col in df.columns for col in required_cols):
            print(f"❌ Erreur : Colonnes manquantes dans '{filepath}'.")
            print(f"    Colonnes attendues : {required_cols}")
            print(f"    Colonnes trouvées : {list(df.columns)}")
            return []

        # Nettoyage initial des lignes avec des valeurs manquantes dans les colonnes requises
        df.dropna(subset=required_cols, inplace=True)

        if df.empty:
            print("❌ Erreur : Le DataFrame est vide après avoir supprimé les lignes avec des valeurs manquantes.")
            return []

        # Combinaison de la date et de l'heure pour créer des timestamps valides
        try:
            df['start_dt'] = pd.to_datetime(df[COL_DATE].astype(str) + ' ' + df[COL_START_TIME].astype(str),
                                            errors='coerce')
            df['end_dt'] = pd.to_datetime(df[COL_DATE].astype(str) + ' ' + df[COL_END_TIME].astype(str),
                                          errors='coerce')
        except Exception as e:
            print(f"❌ Erreur lors de la conversion des dates et heures : {e}")
            return []

        df.dropna(subset=['start_dt', 'end_dt'], inplace=True)

        if df.empty:
            print("❌ Erreur : Le DataFrame est vide après la conversion et le nettoyage des dates/heures.")
            return []

        # Extraction des coordonnées de la chaîne "Latitude, Longitude"
        coords_df = df[COL_COORDS].astype(str).str.split(', ', expand=True)

        if coords_df.shape[1] < 2:
            print("❌ Erreur : La colonne de coordonnées ne contient pas de paires 'latitude, longitude' valides.")
            return []

        df['Latitude'] = pd.to_numeric(coords_df[0], errors='coerce')
        df['Longitude'] = pd.to_numeric(coords_df[1], errors='coerce')

        df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

        if df.empty:
            print("❌ Erreur : Aucune donnée de coordonnées valide n'a été trouvée dans le fichier après le nettoyage.")
            return []

        # Grouper par coordonnées pour consolider les plages de dates
        location_data_agg = defaultdict(lambda: {"lat": None, "lon": None, "start": None, "end": None})

        for _, row in df.iterrows():
            lat = round(row['Latitude'], 4)
            lon = round(row['Longitude'], 4)
            location_key = (lat, lon)

            agg = location_data_agg[location_key]
            agg["lat"], agg["lon"] = lat, lon

            if agg["start"] is None or row['start_dt'] < agg["start"]:
                agg["start"] = row['start_dt']
            if agg["end"] is None or row['end_dt'] > agg["end"]:
                agg["end"] = row['end_dt']

        locations_to_process = [
            {
                "city_name": f"Location ({data['lat']}, {data['lon']})",
                "coords": {"lat": data["lat"], "lon": data["lon"]},
                "date_ranges": [{"start_day": data["start"].date(), "end_day": data["end"].date()}]
            }
            for key, data in location_data_agg.items()
        ]

        return locations_to_process

    except Exception as e:
        print(f"❌ Une erreur est survenue lors de la lecture du fichier Excel : {e}")
        return []


# --- Reste du script (inchangé) ---

class WeatherProcessor:
    def __init__(self, api_key, weather_endpoint, output_file):
        self.api_key = api_key
        self.weather_endpoint = weather_endpoint
        self.output_file = output_file
        self.session = requests.Session()

    def fetch_historical_data(self, city_name, coords, start_day, end_day):
        weather_data = []
        all_days = pd.date_range(start_day, end_day, freq='D')

        print(f"\n🔄 Récupération des données pour : {city_name} (Lat: {coords['lat']}, Lon: {coords['lon']})")
        print(f"    Période : du {start_day} au {end_day}")

        for day in all_days:
            for hour in range(8, 21):
                current_dt_utc = datetime(day.year, day.month, day.day, hour, tzinfo=pytz.UTC)
                timestamp = int(current_dt_utc.timestamp())
                params = {
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'dt': timestamp,
                    'appid': self.api_key,
                    'units': 'metric'
                }

                try:
                    response = self.session.get(self.weather_endpoint, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("data"):
                        hourly_data = data["data"][0]
                        rain_data = hourly_data.get('rain', {})

                        extracted_metrics = {
                            "DateTimeUTC": current_dt_utc,
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
                        print(f"    -> Données récupérées pour : {current_dt_utc.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        print(f"    -> Aucune donnée pour {current_dt_utc.strftime('%Y-%m-%d %H:%M')}")

                except requests.exceptions.RequestException as e:
                    print(f"    -> ❌ Erreur de requête pour {current_dt_utc.strftime('%Y-%m-%d %H:%M')} : {e}")

                time.sleep(0.5)

        return weather_data

    def export_to_excel(self, new_df):
        if new_df.empty:
            print("\n🟡 Aucune nouvelle donnée à exporter.")
            return

        try:
            new_df['Day'] = new_df['DateTimeUTC'].dt.day
            new_df['Month'] = new_df['DateTimeUTC'].dt.month
            new_df['Year'] = new_df['DateTimeUTC'].dt.year
            new_df['Time'] = new_df['DateTimeUTC'].dt.strftime('%H:%M:%S')

            final_columns = ['Day', 'Month', 'Year', 'Time', 'City', 'Latitude', 'Longitude',
                             'Temperature (°C)', 'Pressure (hPa)', 'Humidity (%)',
                             'Wind Speed (kts)', 'Wind Direction (deg)', 'Rain (mm)']

            new_df = new_df.reindex(columns=final_columns)

            if os.path.exists(self.output_file):
                print(f"\nFichier '{self.output_file}' existant, ajout des nouvelles données...")
                existing_df = pd.read_excel(self.output_file)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                print(f"\nCréation du nouveau fichier '{self.output_file}'...")
                final_df = new_df

            final_df.drop_duplicates(subset=['Day', 'Month', 'Year', 'Time', 'City'], keep='last', inplace=True)

            final_df.to_excel(self.output_file, index=False)
            print(f"✅ Exportation réussie vers '{self.output_file}'")

        except Exception as e:
            print(f"\n❌ Une erreur est survenue lors de l'exportation vers Excel : {e}")

    def process_location(self, city_name, coords, date_ranges):
        all_location_data = []
        for date_range in date_ranges:
            start_day = date_range["start_day"]
            end_day = date_range["end_day"]
            weather_data = self.fetch_historical_data(city_name, coords, start_day, end_day)
            if weather_data:
                all_location_data.extend(weather_data)

        if not all_location_data:
            print(f"\n🟡 Aucune donnée n'a été collectée pour {city_name}.")
            return

        new_df = pd.DataFrame(all_location_data)
        self.export_to_excel(new_df)


if __name__ == "__main__":
    print("--- Lancement du script de récupération des données météo ---")

    print(f"\nÉtape 1 : Lecture du fichier source '{INPUT_FILE}'...")
    locations_to_process = read_source_data(INPUT_FILE)

    if locations_to_process:
        print("\nÉtape 2 : Lancement de la récupération des données via l'API.")
        print("Lieux et périodes à traiter :")
        for loc in locations_to_process:
            print(f"  - {loc['city_name']} : "
                  f"du {loc['date_ranges'][0]['start_day']} au {loc['date_ranges'][0]['end_day']}")

        processor = WeatherProcessor(
            api_key=API_KEY,
            weather_endpoint=WEATHER_API_ENDPOINT,
            output_file=OUTPUT_FILE
        )

        for entry in locations_to_process:
            processor.process_location(
                city_name=entry["city_name"],
                coords=entry["coords"],
                date_ranges=entry["date_ranges"]
            )

        print("\n--- ✅ Processus terminé avec succès. ---")
    else:
        print("\n--- ⏹️ Le processus est annulé car aucune donnée valide n'a été extraite du fichier source. ---")