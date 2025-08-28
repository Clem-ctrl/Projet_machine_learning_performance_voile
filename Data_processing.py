import pandas as pd
import numpy as np
from datetime import timedelta, datetime

# Configuration des fichiers
FICHIER_METASAIL = 'Metasail_Statistics_ML_test_cleaned.xlsx'
FICHIER_WEATHER = 'weather_data_cleaned.xlsx'
FICHIER_SORTIE = 'Metasail_Statistics_ML_test_processed.xlsx'


class DataProcessor:
    """
    Une classe pour calculer des métriques complexes à partir de données nettoyées.
    Elle intègre des données de deux sources différentes.
    """

    def __init__(self, df_metasail, df_weather):
        """
        Initialise le DataProcessor avec les DataFrames de Metasail et de météo.
        :param df_metasail: DataFrame pandas des données de Metasail.
        :param df_weather: DataFrame pandas des données météo.
        """
        self.df_metasail = df_metasail
        self.df_weather = df_weather
        if self.df_metasail is None or self.df_metasail.empty:
            print("❌ Le DataFrame Metasail est vide. Les calculs ne peuvent pas être effectués.")
        if self.df_weather is None or self.df_weather.empty:
            print("❌ Le DataFrame météo est vide. Les calculs de vent et de courant ne peuvent pas être effectués.")

    def _prepare_data_for_merge(self):
        """
        Prépare les DataFrames pour la fusion.
        Crée une clé de jointure combinant la date, le lieu et l'heure.
        """
        print("\n" + "=" * 50)
        print("🛠️ PRÉPARATION DES DONNÉES POUR LA FUSION")
        print("=" * 50)

        # Création de la colonne de date pour les deux DataFrames
        self.df_metasail['Date'] = pd.to_datetime(
            self.df_metasail[['Année', 'Mois', 'Jour']].astype(str).agg('-'.join, axis=1), errors='coerce'
        ).dt.date
        self.df_weather['Date'] = pd.to_datetime(
            self.df_weather[['Year', 'Month', 'Day']].astype(str).agg('-'.join, axis=1), errors='coerce'
        ).dt.date

        # Traitement des heures pour trouver le timestamp de l'heure centrale
        self.df_metasail['Début du segment_dt'] = pd.to_datetime(
            self.df_metasail['Début du segment (timestamp)'], format='%H:%M:%S', errors='coerce'
        )
        self.df_metasail['Fin du segment_dt'] = pd.to_datetime(
            self.df_metasail['Fin du segment (timestamp)'], format='%H:%M:%S', errors='coerce'
        )
        self.df_metasail['Temps du segment_dt'] = self.df_metasail.apply(
            lambda row: (
                    row['Début du segment_dt'] + (row['Fin du segment_dt'] - row['Début du segment_dt']) / 2).time()
            if pd.notna(row['Début du segment_dt']) and pd.notna(row['Fin du segment_dt']) and row[
                'Début du segment_dt'] <= row['Fin du segment_dt']
            else (row['Début du segment_dt'] + timedelta(days=1) + (
                    row['Fin du segment_dt'] - row['Début du segment_dt'] + timedelta(
                days=1)) / 2).time() if pd.notna(row['Début du segment_dt']) and pd.notna(row['Fin du segment_dt'])
            else np.nan,
            axis=1
        )

        self.df_weather['Time_dt'] = pd.to_datetime(self.df_weather['Time'], format='%H:%M:%S', errors='coerce').dt.time

        print("✅ Données de date et heure préparées.")

    def _find_closest_weather_data(self):
        """
        Recherche et fusionne les données météo les plus proches pour chaque ligne de Metasail.
        """
        print("\n" + "=" * 50)
        print("🔍 RECHERCHE ET FUSION DES DONNÉES MÉTÉO LES PLUS PROCHES")
        print("=" * 50)

        # Initialisation des colonnes de données météo
        self.df_metasail['Wind Speed (kts)'] = np.nan
        self.df_metasail['Wind Direction (deg)'] = np.nan

        # Set pour stocker les lieux déjà signalés comme manquants
        ignored_locations = set()

        # Itération sur chaque ligne du DataFrame Metasail
        for index, row_metasail in self.df_metasail.iterrows():
            if pd.isna(row_metasail['Date']) or pd.isna(row_metasail['Temps du segment_dt']):
                continue

            lieu = row_metasail["Lieu de l'événement"].lower()
            date = row_metasail['Date']

            # Correction de la syntaxe pour le filtrage
            filtered_weather = self.df_weather[
                (self.df_weather['Date'] == date) &
                (self.df_weather['City'].str.lower() == lieu)
                ].copy()

            if filtered_weather.empty:
                # Vérifie si le lieu a déjà été signalé pour cette exécution
                if lieu not in ignored_locations:
                    print(
                        f"⚠️ Aucune donnée météo trouvée pour le lieu {row_metasail['Lieu de l\'événement']} le {date}. Les lignes de cette zone seront ignorées.")
                    ignored_locations.add(lieu)
                continue

            # Calcule la différence de temps et trouve la ligne la plus proche
            filtered_weather['time_diff'] = filtered_weather['Time_dt'].apply(
                lambda x: abs(datetime.combine(datetime.min.date(), x) - datetime.combine(datetime.min.date(),
                                                                                          row_metasail[
                                                                                              'Temps du segment_dt']))
            )
            closest_weather_index = filtered_weather['time_diff'].idxmin()
            closest_weather = filtered_weather.loc[closest_weather_index]

            # Mise à jour des colonnes dans le DataFrame original
            self.df_metasail.at[index, 'Wind Speed (kts)'] = closest_weather['Wind Speed (kts)']
            self.df_metasail.at[index, 'Wind Direction (deg)'] = closest_weather['Wind Direction (deg)']

        print("✅ Fusion des données météo terminée.")

    def recalculer_et_nettoyer_metriques(self):
        """
        Recalcule le temps de segment, la VMC moyenne et la vitesse moyenne.
        """
        if self.df_metasail is None:
            return

        print("\n" + "=" * 50)
        print("🔧 RECALCUL DES MÉTRIQUES DE PERFORMANCE DU SEGMENT")
        print("=" * 50)

        required_cols = ['Début du segment (timestamp)', 'Fin du segment (timestamp)',
                         'Distance réelle du segment (m)', 'Longueur du côté du segment (m)']
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour le recalcule manquantes.")
            return

        # Correction : utilisation des colonnes déjà créées pour le calcul
        self.df_metasail['delta_time'] = self.df_metasail['Fin du segment_dt'] - self.df_metasail['Début du segment_dt']
        self.df_metasail.loc[self.df_metasail['delta_time'] < timedelta(0), 'delta_time'] += timedelta(days=1)
        self.df_metasail['Temps du segment (s)'] = self.df_metasail['delta_time'].dt.total_seconds()
        print("✅ 'Temps du segment (s)' recalculé avec succès.")

        safe_time = self.df_metasail['Temps du segment (s)'].replace(0, np.nan)
        self.df_metasail['Vitesse moyenne (noeuds)'] = (self.df_metasail[
                                                            'Distance réelle du segment (m)'] / safe_time) * 1.94384
        print("✅ 'Vitesse moyenne (noeuds)' recalculée avec succès.")

        self.df_metasail['VMC moyenne'] = (self.df_metasail['Longueur du côté du segment (m)'] / safe_time) * 1.94384
        print("✅ 'VMC moyenne' recalculée avec succès.")

        # Suppression des colonnes existantes de métriques pour éviter les doublons
        cols_to_drop = ['Vitesse maximale (noeuds)', 'VMG maximale', 'VMC maximale', 'VMG moyenne']
        self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors='ignore')

    def calculer_vent_apparent_courant(self):
        """
        Calcule le vent apparent et l'influence du courant en utilisant des opérations vectorielles.
        """
        if self.df_metasail is None:
            return

        required_cols = [
            'Wind Speed (kts)', 'Wind Direction (deg)',
            'Vitesse moyenne (noeuds)', 'Direction du côté du segment',
            'VMC moyenne'
        ]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour le calcul du vent apparent et du courant manquantes après la fusion.")
            return

        print("\n" + "=" * 50)
        print("🧮 CALCUL DU VENT APPARENT ET DE L'INFLUENCE DU COURANT")
        print("=" * 50)

        def to_math_rad(deg):
            return np.radians(90 - deg)

        # 1. Calcul des vecteurs du vent réel et du bateau
        self.df_metasail['tw_angle_rad'] = self.df_metasail['Wind Direction (deg)'].apply(to_math_rad)
        self.df_metasail['tw_x'] = self.df_metasail['Wind Speed (kts)'] * np.cos(self.df_metasail['tw_angle_rad'])
        self.df_metasail['tw_y'] = self.df_metasail['Wind Speed (kts)'] * np.sin(self.df_metasail['tw_angle_rad'])
        self.df_metasail['sog_angle_rad'] = self.df_metasail['Direction du côté du segment'].apply(to_math_rad)
        self.df_metasail['sog_x'] = self.df_metasail['Vitesse moyenne (noeuds)'] * np.cos(
            self.df_metasail['sog_angle_rad'])
        self.df_metasail['sog_y'] = self.df_metasail['Vitesse moyenne (noeuds)'] * np.sin(
            self.df_metasail['sog_angle_rad'])

        # 2. Calcul du vent apparent (AW = TW - SOG) avec AW = apparent wind, TW = true wind, SOG = speed over ground
        self.df_metasail['aw_x'] = self.df_metasail['tw_x'] - self.df_metasail['sog_x']
        self.df_metasail['aw_y'] = self.df_metasail['tw_y'] - self.df_metasail['sog_y']
        self.df_metasail['Vitesse du vent apparent (noeuds)'] = np.sqrt(
            self.df_metasail['aw_x'] ** 2 + self.df_metasail['aw_y'] ** 2)
        self.df_metasail['Direction du vent apparent (deg)'] = (90 - np.degrees(
            np.arctan2(self.df_metasail['aw_y'], self.df_metasail['aw_x']))) % 360
        print("✅ Colonnes 'Vitesse du vent apparent (noeuds)' et 'Direction du vent apparent (deg)' créées.")

        # 3. Calcul de l'influence du courant (CUR = SOG - STW) avec la VMC moyenne comme une approximation de la STW.
        # CUR = influence du courant, STW = Speed Through Water
        self.df_metasail['stw_angle_rad'] = self.df_metasail['Direction du côté du segment'].apply(to_math_rad)
        self.df_metasail['stw_x'] = self.df_metasail['VMC moyenne'] * np.cos(self.df_metasail['stw_angle_rad'])
        self.df_metasail['stw_y'] = self.df_metasail['VMC moyenne'] * np.sin(self.df_metasail['stw_angle_rad'])
        self.df_metasail['cur_x'] = self.df_metasail['sog_x'] - self.df_metasail['stw_x']
        self.df_metasail['cur_y'] = self.df_metasail['sog_y'] - self.df_metasail['stw_y']
        self.df_metasail['Vitesse de courant (noeuds)'] = np.sqrt(
            self.df_metasail['cur_x'] ** 2 + self.df_metasail['cur_y'] ** 2)
        self.df_metasail['Direction du courant (deg)'] = (90 - np.degrees(
            np.arctan2(self.df_metasail['cur_y'], self.df_metasail['cur_x']))) % 360
        print("✅ Colonnes 'Vitesse de courant (noeuds)' et 'Direction du courant (deg)' créées.")

        # Suppression des colonnes intermédiaires
        cols_to_drop = [col for col in self.df_metasail.columns if
                        col.startswith(('tw_', 'sog_', 'aw_', 'stw_', 'cur_'))]
        cols_to_drop.extend(['Début du segment_dt', 'Fin du segment_dt', 'delta_time', 'Date', 'Temps du segment_dt'])
        self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors='ignore')

        print("✅ Les calculs sont terminés.")

    def calculer_vmg(self):
        """
        Calcule la Velocity Made Good (VMG) en utilisant le cap du voilier et la direction du vent.
        VMG = VitesseFond * cos(angle_réel)
        """
        if self.df_metasail is None:
            return

        print("\n" + "=" * 50)
        print("📐 CALCUL DE LA VELOCITY MADE GOOD (VMG)")
        print("=" * 50)

        required_cols = ['Vitesse moyenne (noeuds)', 'Direction du côté du segment', 'Wind Direction (deg)']
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour le calcul de la VMG manquantes.")
            return

        # Calcul de l'angle entre le cap du voilier et la direction du vent réel
        angle_diff = np.abs(self.df_metasail['Direction du côté du segment'] - self.df_metasail['Wind Direction (deg)'])
        angle_to_use = np.where(angle_diff > 180, 360 - angle_diff, angle_diff)

        # Conversion de l'angle en radians pour la fonction cosinus de numpy
        angle_rad = np.radians(angle_to_use)

        # Calcul de la VMG
        self.df_metasail['VMG'] = self.df_metasail['Vitesse moyenne (noeuds)'] * np.cos(angle_rad)
        print("✅ Colonne 'VMG' calculée avec succès.")

    def get_dataframe(self):
        """ Retourne le DataFrame avec les nouvelles métriques calculées. """
        return self.df_metasail


def main():
    """ Fonction principale pour exécuter le traitement des données. """
    try:
        # Chargez les deux fichiers
        dataframe_metasail = pd.read_excel(FICHIER_METASAIL)
        dataframe_weather = pd.read_excel(FICHIER_WEATHER)
        print("✅ Fichiers chargés avec succès.")

        # Étape 1 : Traitement et calcul des métriques
        processeur = DataProcessor(dataframe_metasail, dataframe_weather)

        # Prépare et fusionne les données météo
        processeur._prepare_data_for_merge()
        processeur._find_closest_weather_data()

        # Recalcule les métriques de performance
        processeur.recalculer_et_nettoyer_metriques()

        # Calcule le vent apparent et l'influence du courant
        processeur.calculer_vent_apparent_courant()

        # NOUVELLE ÉTAPE : Calcul de la VMG
        processeur.calculer_vmg()

        dataframe_final = processeur.get_dataframe()

        print("\n--- Aperçu des 5 premières lignes des données finales ---")
        print(dataframe_final.head())
        print("\n--- Aperçu des colonnes de vent, de courant et de VMG :")
        print(dataframe_final[['Vitesse du vent apparent (noeuds)', 'Direction du vent apparent (deg)',
                               'Vitesse de courant (noeuds)', 'Direction du courant (deg)', 'VMG']].head())

        # Sauvegarde du fichier final
        dataframe_final.to_excel(FICHIER_SORTIE, index=False)
        print(f"💾 Fichier traité et calculé sauvegardé avec succès sous : {FICHIER_SORTIE}")

    except FileNotFoundError as e:
        print(f"❌ Erreur : L'un des fichiers requis n'a pas été trouvé. {e}")
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue : {e}")


if __name__ == '__main__':
    main()