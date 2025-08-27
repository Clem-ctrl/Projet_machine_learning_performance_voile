import requests
import pandas as pd
from datetime import datetime, date
import pytz
import os

# --- Configuration ---
API_KEY = "ce67699e859dc91888145732202e8f26"
LAT = 52.888816
LON = -4.417634
M_S_TO_KNOTS = 1.94384
start_day = date(2025, 8, 18)
end_day = date(2025, 8, 21)

# --- Fonction pour obtenir le nom de la ville ---
def get_city_name(lat, lon, api_key):
    """
    Récupère le nom de la ville à partir des coordonnées GPS en utilisant l'API Reverse Geocoding.
    """
    url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and 'local_names' in data[0] and 'fr' in data[0]['local_names']:
            return data[0]['local_names']['fr']
        elif data and 'name' in data[0]:
            return data[0]['name']
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération du nom de la ville : {e}")
    return "Ville Inconnue"

# --- Récupération des données ---
print("Début de la récupération des données...")
weather_data = []
all_days = pd.date_range(start_day, end_day, freq='D')

# Récupère le nom de la ville une seule fois avant la boucle
city_name = get_city_name(LAT, LON, API_KEY)
print(f"Récupération des données pour : {city_name}")

for day in all_days:
    for hour in range(8, 21):
        current_dt_utc = datetime(day.year, day.month, day.day, hour, tzinfo=pytz.UTC)
        timestamp = int(current_dt_utc.timestamp())
        url = (
            f"https://api.openweathermap.org/data/3.0/onecall/timemachine?"
            f"lat={LAT}&lon={LON}&dt={timestamp}&appid={API_KEY}"
        )
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                hourly_data = data["data"][0]
                extracted_metrics = {
                    "DateTimeUTC": datetime.fromtimestamp(hourly_data.get('dt', 0), tz=pytz.UTC),
                    "City": city_name,
                    "Latitude": LAT,
                    "Longitude": LON,
                    "Temperature (°C)": round(hourly_data.get('temp', 273.15) - 273.15, 2),
                    "Wind Speed (kts)": round(hourly_data.get('wind_speed', 0) * M_S_TO_KNOTS, 2)
                }
                weather_data.append(extracted_metrics)
                print(f"Données récupérées pour : {current_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        except requests.exceptions.RequestException as e:
            print(f"Une erreur est survenue lors de la récupération pour {current_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}: {e}")
            break

# --- Traitement des données et Exportation vers Excel ---
if weather_data:
    try:
        new_df = pd.DataFrame(weather_data)
        new_df['Date'] = new_df['DateTimeUTC'].dt.date
        new_df['Time'] = new_df['DateTimeUTC'].dt.strftime('%H:%M:%S')
        final_columns = ['Date', 'Time', 'City', 'Latitude', 'Longitude', 'Temperature (°C)', 'Wind Speed (kts)']
        new_df = new_df[final_columns]
        file_path = r"C:\Users\User\PycharmProjects\HelloWorld\ENVSN\OpenWeatherMap\weather_data_cleaned.xlsx"

        if os.path.exists(file_path):
            print("\nLe fichier existe, ajout des nouvelles données...")
            existing_df = pd.read_excel(file_path)
            # Concatène le DataFrame existant et le nouveau DataFrame
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
            # Supprime les doublons basés sur la date et l'heure pour éviter les entrées redondantes
            final_df.drop_duplicates(subset=['Date', 'Time'], keep='last', inplace=True)
        else:
            print("\nLe fichier n'existe pas, création d'un nouveau fichier...")
            final_df = new_df

        final_df.to_excel(file_path, index=False)
        print(f"\n✅ Exportation réussie vers '{file_path}'")
        print(f"Données enregistrées du {final_df['Date'].min()} au {final_df['Date'].max()}")
    except Exception as e:
        print(f"\n❌ Une erreur est survenue lors de l'exportation vers Excel : {e}")
else:
    print("\nAucune donnée n'a été collectée. Veuillez vérifier votre clé API et votre connexion réseau.")