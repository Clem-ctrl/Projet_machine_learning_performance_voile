import pandas as pd
import re
from names_dataset import NameDataset
import numpy as np
from datetime import timedelta, datetime
from thefuzz import fuzz


class DataCleaner:
    """
    Nettoie, enrichit et fusionne des données Metasail et météo.
    """

    def __init__(self, metasail_path: str, weather_path: str):
        """
        Initialise l'objet et charge les dataframes.
        Args:
            metasail_path (str): Chemin vers le fichier Excel de Metasail.
            weather_path (str): Chemin vers le fichier Excel de météo.
        """
        self.metasail_path = metasail_path
        self.weather_path = weather_path
        self.df_metasail = None
        self.df_weather = None
        self.ready_to_process = False
        self.nd = NameDataset()

        self._load_data()

    def _load_data(self):
        """Charge les fichiers Excel et gère les erreurs."""
        try:
            # Spécifier les types de données pour éviter les erreurs de conversion
            self.df_metasail = pd.read_excel(self.metasail_path)
            self.df_weather = pd.read_excel(self.weather_path,
                                            dtype={'Day': str, 'Month': str, 'Year': str})
            print("✅ Fichiers Excel chargés avec succès.")
            self.ready_to_process = True
        except FileNotFoundError as e:
            print(f"❌ Erreur : Fichier non trouvé - {e}")
        except Exception as e:
            print(f"❌ Une erreur s'est produite lors de la lecture des fichiers : {e}")

    def run_pipeline(self):
        """Exécute l'ensemble des étapes de nettoyage et de prétraitement."""
        if not self.ready_to_process:
            print("❌ Traitement annulé : Les DataFrames n'ont pas été chargés correctement.")
            return

        print("\n" + "=" * 50)
        print("🚀 DÉMARRAGE DU NETTOYAGE ET DU PRÉTRAITEMENT")
        print("=" * 50)

        # Les étapes sont exécutées séquentiellement
        self._clean_metasail_data()
        self._process_datetime()
        self._process_metasail_metrics()
        self._merge_with_weather_data()
        self._calculate_final_metrics()

        print("\n" + "=" * 50)
        print("✅ FIN DU NETTOYAGE ET DU PRÉTRAITEMENT")
        print("=" * 50)

    def _clean_metasail_data(self):
        """Nettoie et filtre le DataFrame Metasail."""
        print("\n" + "---" * 15)
        print("🗑️ ÉTAPE 1 : NETTOYAGE DES DONNÉES BRUTES METASAIL")
        print("---" * 15)

        # Suppression des colonnes inutiles
        cols_to_drop = [
            'Position de départ', 'Classement sortie de segment', 'Vitesse maximale (noeuds)',
            'VMG maximale', 'VMC maximale', 'VMG moyenne'
        ]
        self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors='ignore')
        print(f"🗑️ Colonnes supprimées : {cols_to_drop}")

        # Nettoyage et unification des noms
        if 'Nom complet' in self.df_metasail.columns:
            self.df_metasail['Nom complet'] = self.df_metasail['Nom complet'].astype(str).str.strip().str.replace("'",
                                                                                                                  " ")
            self._unify_names()
            self._complete_missing_gender()
            self._complete_missing_age()
            print("🧹 Nettoyage, unification des noms et complétion des données de profil terminés.")

        # Traitement de la colonne 'Course'
        self._extract_info_from_course()
        self._filter_rows_based_on_rules()

    def _unify_names(self, threshold: int = 85):
        """Unifie les noms complets qui sont très similaires en utilisant TheFuzz."""
        unique_names = self.df_metasail['Nom complet'].dropna().unique()
        name_map = {name: name for name in unique_names}
        for i, name1 in enumerate(unique_names):
            if name1 not in name_map: continue
            for name2 in unique_names[i + 1:]:
                if name2 not in name_map: continue
                if fuzz.ratio(name1.lower(), name2.lower()) > threshold:
                    unified_name = name1 if len(name1) > len(name2) else name2
                    name_map[name2] = unified_name
        self.df_metasail['Nom complet'] = self.df_metasail['Nom complet'].map(name_map)

    def _extract_info_from_course(self):
        """Extrait la catégorie d'âge et le sexe de la colonne 'Course'."""
        if 'Course' not in self.df_metasail.columns:
            print("⚠️ Colonne 'Course' introuvable. Extraction de la course ignorée.")
            return

        print("🔄 Extraction d'informations de la colonne 'Course'...")
        course_series = self.df_metasail['Course'].astype(str)

        self.df_metasail['Sexe'] = course_series.str.extract(r'(Men|Women)', flags=re.IGNORECASE,
                                                             expand=False).str.capitalize()
        u17_pattern = r'U\s*17|Under\s*17|JUNIOR'
        u19_pattern = r'U\s*19|Under\s*19|YOUTH'
        self.df_metasail["Catégorie d'âge"] = np.nan
        self.df_metasail.loc[
            course_series.str.contains(u17_pattern, flags=re.IGNORECASE, na=False), "Catégorie d'âge"] = 'U17'
        self.df_metasail.loc[
            course_series.str.contains(u19_pattern, flags=re.IGNORECASE, na=False), "Catégorie d'âge"] = 'U19'

        self.df_metasail['Course'] = course_series.str.replace(
            f"({u17_pattern}|{u19_pattern}|Men|Women|IQfoil)", '', flags=re.IGNORECASE, regex=True
        ).str.replace(r'\s+', ' ', regex=True).str.strip()
        print("✅ 'Sexe' et 'Catégorie d'âge' extraites. Colonne 'Course' nettoyée.")

    def _filter_rows_based_on_rules(self):
        """Filtre les lignes en fonction de critères spécifiques."""
        initial_count = len(self.df_metasail)
        if 'Course' in self.df_metasail.columns:
            self.df_metasail = self.df_metasail[
                ~self.df_metasail['Course'].str.contains('abandon|recall', case=False, na=False)]
        if "Nom de l'événement" in self.df_metasail.columns and 'Course' in self.df_metasail.columns:
            self.df_metasail = self.df_metasail[
                ~((self.df_metasail["Nom de l'événement"] == "COPPA ITALIA T293 e IQFOIL SFERRACAVALLO 2024") &
                  (~self.df_metasail["Course"].str.contains("IQFOIL", case=False, na=False)))
            ]
        rows_dropped = initial_count - len(self.df_metasail)
        print(f"🗑️ {rows_dropped} ligne(s) ont été supprimées suite aux règles de filtrage.")

    def _complete_missing_gender(self):
        """Remplit les sexes manquants en se basant sur le prénom le plus probable."""
        if 'Nom complet' not in self.df_metasail.columns or 'Sexe' not in self.df_metasail.columns:
            return
        missing_gender_mask = self.df_metasail['Sexe'].isnull()
        if not missing_gender_mask.any():
            return
        print("🔄 Complétion des sexes manquants...")

        def infer_gender(name):
            first_name = name.split()[0]
            data = self.nd.search(first_name)
            if data and 'first_name' in data and data['first_name'] and 'gender' in data['first_name']:
                gender_probs = data['first_name']['gender']
                if gender_probs.get('Male', 0) > gender_probs.get('Female', 0):
                    return 'Men'
                elif gender_probs.get('Female', 0) > gender_probs.get('Male', 0):
                    return 'Women'
            return np.nan

        self.df_metasail.loc[missing_gender_mask, 'Sexe'] = self.df_metasail.loc[
            missing_gender_mask, 'Nom complet'].apply(infer_gender)
        print("✅ Tentative de complétion des sexes manquants terminée.")

    def _complete_missing_age(self):
        """Remplit les âges manquants en se basant sur le même athlète."""
        required_cols = ["Catégorie d'âge", 'Numéro de série', 'Nom complet']
        if not all(col in self.df_metasail.columns for col in required_cols):
            return
        print("🔄 Complétion des âges manquants...")
        age_map = self.df_metasail.dropna(subset=["Catégorie d'âge"]).set_index(['Numéro de série', 'Nom complet'])[
            "Catégorie d'âge"].to_dict()

        def fill_age(row):
            if pd.isnull(row["Catégorie d'âge"]):
                key = (row['Numéro de série'], row['Nom complet'])
                return age_map.get(key, "Senior")
            return row["Catégorie d'âge"]

        self.df_metasail["Catégorie d'âge"] = self.df_metasail.apply(fill_age, axis=1)
        print("✅ Complétion des âges manquants terminée.")

    def _process_datetime(self):
        """
        Convertit les colonnes de date et de temps en objets datetime pour le DataFrame Metasail.
        """
        print("\n" + "---" * 15)
        print("⏰ ÉTAPE 2 : PRÉPARATION DES DONNÉES DE TEMPS")
        print("---" * 15)

        # Correction : utilisation de la colonne existante 'Date de la course' pour créer Année, Mois, Jour
        if "Date de la course" not in self.df_metasail.columns:
            print("❌ Colonne 'Date de la course' manquante. Étape ignorée.")
            return

        self.df_metasail["Date de la course"] = pd.to_datetime(self.df_metasail["Date de la course"])
        self.df_metasail['Année'] = self.df_metasail["Date de la course"].dt.year
        self.df_metasail['Mois'] = self.df_metasail["Date de la course"].dt.month
        self.df_metasail['Jour'] = self.df_metasail["Date de la course"].dt.day

        required_cols = ["Année", "Mois", "Jour", "Début du segment (timestamp)", "Fin du segment (timestamp)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes de date/heure manquantes. Étape ignorée.")
            return

        base_dt = pd.to_datetime(self.df_metasail['Année'].astype(str) + '-' +
                                 self.df_metasail['Mois'].astype(str) + '-' +
                                 self.df_metasail['Jour'].astype(str), errors='coerce')

        self.df_metasail["Début du segment_dt"] = pd.to_timedelta(
            self.df_metasail["Début du segment (timestamp)"]) + base_dt
        self.df_metasail["Fin du segment_dt"] = pd.to_timedelta(
            self.df_metasail["Fin du segment (timestamp)"]) + base_dt
        self.df_metasail.loc[self.df_metasail["Fin du segment_dt"] < self.df_metasail[
            "Début du segment_dt"], "Fin du segment_dt"] += timedelta(days=1)

        self.df_metasail['Date'] = self.df_metasail["Début du segment_dt"].dt.date
        self.df_metasail['Heure du segment'] = (self.df_metasail["Début du segment_dt"] + (
                    self.df_metasail["Fin du segment_dt"] - self.df_metasail["Début du segment_dt"]) / 2).dt.time
        print("✅ Colonnes de temps préparées.")

    def _process_metasail_metrics(self):
        """
        Recalcule les métriques de performance du segment et supprime les colonnes obsolètes.
        """
        print("\n" + "---" * 15)
        print("📈 ÉTAPE 3 : RECALCUL DES MÉTRIQUES METASAIL")
        print("---" * 15)

        required_cols = ["Début du segment_dt", "Fin du segment_dt", "Distance réelle parcourue segment (m)",
                         "Longueur du segment (m)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour le recalcule manquantes. Étape ignorée.")
            return

        self.df_metasail["Temps du segment (s)"] = (
                    self.df_metasail["Fin du segment_dt"] - self.df_metasail["Début du segment_dt"]).dt.total_seconds()
        safe_time = self.df_metasail["Temps du segment (s)"].replace(0, np.nan)
        self.df_metasail["Vitesse moyenne du segment (noeuds)"] = (self.df_metasail[
                                                                       "Distance réelle parcourue segment (m)"] / safe_time) * 1.94384
        self.df_metasail["VMC du segment (noeuds)"] = (self.df_metasail[
                                                           "Longueur du segment (m)"] / safe_time) * 1.94384

        cols_to_drop = ["Vitesse moyenne (noeuds)", "VMC moyenne"]
        self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors="ignore")
        print("✅ Métriques de performance de segment recalculées.")

    def _merge_with_weather_data(self):
        """
        Fusionne le dataframe Metasail avec les données météo en trouvant la mesure la plus proche.
        """
        print("\n" + "---" * 15)
        print("🗺️ ÉTAPE 4 : FUSION AVEC LES DONNÉES MÉTÉO")
        print("---" * 15)

        # Préparation du dataframe météo
        self.df_weather['Date'] = pd.to_datetime(self.df_weather['Year'].astype(str) + '-' +
                                                 self.df_weather['Month'].astype(str) + '-' +
                                                 self.df_weather['Day'].astype(str), errors='coerce').dt.date

        # Correction : Convertir l'heure en secondes pour la fusion numérique
        self.df_weather['Time_seconds'] = pd.to_timedelta(self.df_weather['Time'].astype(str)).dt.total_seconds()
        self.df_weather['Lieu_key'] = self.df_weather['City'].astype(str)

        # Préparation du dataframe Metasail
        if "Lieu de l'événement" not in self.df_metasail.columns:
            print("❌ Colonne 'Lieu de l'événement' manquante. Impossible de fusionner.")
            return

        coords = self.df_metasail["Lieu de l'événement"].astype(str).str.split(", ", expand=True)
        if coords.shape[1] < 2:
            print("❌ Format de coordonnées invalide. Impossible de fusionner.")
            return

        self.df_metasail['Lat_rounded'] = pd.to_numeric(coords[0], errors='coerce').round(4)
        self.df_metasail['Lon_rounded'] = pd.to_numeric(coords[1], errors='coerce').round(4)

        # Correction : Convertir l'heure du segment en secondes pour la fusion numérique
        self.df_metasail['Heure du segment_seconds'] = (
                                                               self.df_metasail["Début du segment_dt"].dt.hour * 3600 +
                                                               self.df_metasail["Début du segment_dt"].dt.minute * 60 +
                                                               self.df_metasail["Début du segment_dt"].dt.second
                                                       ) + self.df_metasail["Temps du segment (s)"] / 2

        self.df_metasail['Lieu_key'] = 'Location (' + self.df_metasail['Lat_rounded'].astype(str) + ', ' + \
                                       self.df_metasail['Lon_rounded'].astype(str) + ')'

        merged_rows = []
        metasail_grouped = self.df_metasail.dropna(subset=['Lieu_key']).groupby(['Lieu_key', 'Date'])

        for (location, date), metasail_group in metasail_grouped:
            weather_group = self.df_weather[
                (self.df_weather['Lieu_key'] == location) & (self.df_weather['Date'] == date)]

            if weather_group.empty:
                print(f"⚠️ Aucune donnée météo trouvée pour '{location}' le {date}. Lignes ignorées.")
                continue

            # Utilisation de la nouvelle colonne en secondes pour la fusion
            temp_df = pd.merge_asof(
                metasail_group.sort_values('Heure du segment_seconds'),
                weather_group.sort_values('Time_seconds').reset_index(),
                left_on='Heure du segment_seconds',
                right_on='Time_seconds',
                direction='nearest',
                suffixes=('', '_weather')
            )
            merged_rows.append(temp_df)

        if merged_rows:
            self.df_metasail = pd.concat(merged_rows, ignore_index=True)
            cols_to_drop = ['Lat_rounded', 'Lon_rounded', 'Lieu_key', 'index'] + [col for col in
                                                                                  self.df_metasail.columns if
                                                                                  col.endswith('_weather') and col[
                                                                                      :-8] in self.df_metasail.columns]
            self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors='ignore')
            print("✅ Fusion des données météo terminée.")
        else:
            print(
                "❌ Aucune donnée de fusion n'a été trouvée. Le DataFrame Metasail n'a pas été enrichi avec les données météo.")
    def _calculate_final_metrics(self):
        """
        Calcule les métriques globales pour l'ensemble du parcours.
        """
        print("\n" + "---" * 15)
        print("📊 ÉTAPE 5 : CALCUL DES MÉTRIQUES DE PARCOURS COMPLETS")
        print("---" * 15)

        required_cols = ["Temps total parcouru (s)", "Longueur totale du parcours (m)",
                         "Distance totale réelle parcourue (m)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour les calculs de parcours manquantes. Étape ignorée.")
            return

        safe_time = self.df_metasail["Temps total parcouru (s)"].replace(0, np.nan)
        self.df_metasail["VMC moyenne du parcours (noeuds)"] = (self.df_metasail[
                                                                    "Longueur totale du parcours (m)"] / safe_time) * 1.94384
        self.df_metasail["Vitesse moyenne du parcours (noeuds)"] = (self.df_metasail[
                                                                        "Distance totale réelle parcourue (m)"] / safe_time) * 1.94384
        print("✅ 'VMC moyenne du parcours' et 'Vitesse moyenne du parcours' calculées.")

    def save_to_excel(self, output_path: str):
        """Sauvegarde le DataFrame traité dans un nouveau fichier Excel."""
        if self.df_metasail is not None and not self.df_metasail.empty:
            self.df_metasail.to_excel(output_path, index=False)
            print(f"💾 Fichier traité sauvegardé avec succès sous : {output_path}")
        else:
            print("❌ Le DataFrame est vide ou non initialisé. Sauvegarde annulée.")

    def get_dataframe(self) -> pd.DataFrame:
        """Retourne le DataFrame Metasail traité."""
        return self.df_metasail


if __name__ == '__main__':
    metasail_file = 'Metasail_Statistics_unified.xlsx'
    weather_file = 'weather_data_from_coords.xlsx'
    output_file = 'Metasail_Statistics_unified_cleaned.xlsx'

    data_cleaner = DataCleaner(metasail_file, weather_file)
    data_cleaner.run_pipeline()
    data_cleaner.save_to_excel(output_file)