import pandas as pd
import re
from names_dataset import NameDataset
import numpy as np
from datetime import timedelta, datetime
from thefuzz import fuzz


class DataCleaningAndPreprocessing:
    """
    Une classe pour nettoyer, prétraiter, et fusionner des données statistiques
    provenant de Metasail avec des données météo.
    """

    def __init__(self, file_path_metasail, file_path_weather):
        """
        Initialise la classe et charge les jeux de données.
        :param file_path_metasail: Chemin vers le fichier Excel de Metasail.
        :param file_path_weather: Chemin vers le fichier Excel de météo.
        """
        try:
            self.df_metasail = pd.read_excel(file_path_metasail)
            self.df_weather = pd.read_excel(file_path_weather)
            print("✅ Fichiers Excel chargés avec succès.")

            self.nd = NameDataset()  # Initialise la base de données de prénoms
        except FileNotFoundError:
            print(f"❌ Erreur : Un des fichiers n'a pas été trouvé.")
            self.df_metasail = None
            self.df_weather = None
        except Exception as e:
            print(f"❌ Une erreur s'est produite lors de la lecture des fichiers : {e}")
            self.df_metasail = None
            self.df_weather = None

        self.ready_to_process = self.df_metasail is not None and self.df_weather is not None

    def run_cleaning_and_preprocessing(self):
        """
        Exécute l'ensemble des étapes de nettoyage et de prétraitement des données.
        """
        if not self.ready_to_process:
            print("❌ Traitement annulé : Les DataFrames n'ont pas été chargés correctement.")
            return

        print("\n" + "=" * 50)
        print("🚀 DÉBUT DU NETTOYAGE ET DU PRÉTRAITEMENT")
        print("=" * 50)

        # 1. Nettoyage des données Metasail
        self._clean_metasail_data()

        # 2. Préparation et fusion des données météo
        self._prepare_data_for_merge()
        self._find_closest_weather_data()

        # 3. Calcul des métriques
        self._recalculate_and_clean_metrics()

        print("\n" + "=" * 50)
        print("✅ FIN DU NETTOYAGE ET DU PRÉTRAITEMENT")
        print("=" * 50)

    def _clean_metasail_data(self):
        """
        Nettoie et prétraite le DataFrame Metasail.
        """
        if self.df_metasail is None:
            return

        print("\n" + "---" * 15)
        print("🗑️ ÉTAPE 1 : NETTOYAGE DES DONNÉES METASAIL")
        print("---" * 15)

        colonnes_a_supprimer = [
            'Position de départ', 'Classement sortie de segment', 'Vitesse maximale (noeuds)',
            'VMG maximale', 'VMC maximale', 'VMG moyenne'
        ]
        self.df_metasail.drop(columns=colonnes_a_supprimer, inplace=True, errors='ignore')
        print(f"🗑️ Colonnes supprimées : {colonnes_a_supprimer}")

        if 'Nom complet' in self.df_metasail.columns:
            self.df_metasail['Nom complet'] = self.df_metasail['Nom complet'].astype(str).str.strip().str.replace("'",
                                                                                                                  " ")
            self._unify_names()
            print("🧹 Nettoyage et unification des noms complets effectués.")

        self._process_course_column()
        self._filter_race_status()
        self._split_date()
        self._complete_missing_gender()
        self._complete_missing_age()

    def _unify_names(self, threshold=85):
        """
        Unifie les noms complets qui sont très similaires en utilisant TheFuzz.
        :param threshold: Seuil de similarité (de 0 à 100).
        """
        unique_names = self.df_metasail['Nom complet'].dropna().unique()
        name_mapping = {}
        for name in unique_names:
            found_group = False
            if name in name_mapping.keys():
                continue
            for group_name in name_mapping.keys():
                if fuzz.ratio(name.lower(), group_name.lower()) > threshold:
                    name_mapping[name] = group_name
                    found_group = True
                    break
            if not found_group:
                name_mapping[name] = name
        self.df_metasail['Nom complet'] = self.df_metasail['Nom complet'].map(name_mapping)

    def _process_course_column(self):
        """Extrait la catégorie d'âge et le sexe de la colonne 'Course'."""
        if 'Course' not in self.df_metasail.columns:
            print("⚠️ Colonne 'Course' introuvable. Traitement de la course ignoré.")
            return
        print("🔄 Traitement de la colonne 'Course'...")
        colonne_course = self.df_metasail['Course'].astype(str)
        self.df_metasail['Sexe'] = colonne_course.str.extract(r'(Men|Women)', flags=re.IGNORECASE,
                                                              expand=False).str.capitalize()
        pattern_u17 = r'U\s*17|Under\s*17|JUNIOR'
        pattern_u19 = r'U\s*19|Under\s*19|YOUTH'
        self.df_metasail["Catégorie d'âge"] = pd.Series(dtype='object')
        self.df_metasail.loc[
            colonne_course.str.contains(pattern_u17, flags=re.IGNORECASE, na=False), "Catégorie d'âge"] = 'U17'
        self.df_metasail.loc[
            colonne_course.str.contains(pattern_u19, flags=re.IGNORECASE, na=False), "Catégorie d'âge"] = 'U19'
        pattern_a_supprimer = f"({pattern_u17}|{pattern_u19}|Men|Women|IQfoil)"
        course_nettoyee = colonne_course.str.replace(pattern_a_supprimer, '', flags=re.IGNORECASE, regex=True)
        self.df_metasail['Course'] = course_nettoyee.str.replace(r'\s+', ' ', regex=True).str.strip()
        print("✅ Colonnes 'Sexe' et 'Catégorie d'âge' créées et colonne 'Course' nettoyée.")

    def _filter_race_status(self):
        """Supprime les lignes 'abandonned' ou 'recall'."""
        if 'Course' not in self.df_metasail.columns:
            print("⚠️ Colonne 'Course' introuvable. Filtrage de la course ignoré.")
            return
        lignes_initiales = len(self.df_metasail)
        self.df_metasail = self.df_metasail[
            ~self.df_metasail['Course'].str.contains('abandon|recall', case=False, na=False)]
        lignes_supprimees = lignes_initiales - len(self.df_metasail)
        print(f"✅ {lignes_supprimees} ligne(s) 'abandonned' ou 'recall' supprimée(s).")

    def _split_date(self, nom_colonne_date='Date de la course'):
        """Divise une colonne de date en Année, Mois, Jour."""
        if nom_colonne_date not in self.df_metasail.columns:
            print(f"⚠️ Colonne '{nom_colonne_date}' introuvable. Split de la date ignoré.")
            return
        self.df_metasail[nom_colonne_date] = pd.to_datetime(self.df_metasail[nom_colonne_date])
        self.df_metasail['Année'] = self.df_metasail[nom_colonne_date].dt.year
        self.df_metasail['Mois'] = self.df_metasail[nom_colonne_date].dt.month
        self.df_metasail['Jour'] = self.df_metasail[nom_colonne_date].dt.day
        self.df_metasail.drop(columns=[nom_colonne_date], inplace=True)
        print(f"✅ Colonnes Année, Mois, Jour créées et colonne '{nom_colonne_date}' supprimée.")

    def _complete_missing_gender(self):
        """
        Remplit les sexes manquants en utilisant 'Nom complet' en trouvant le prénom
        le plus probable.
        """
        if 'Nom complet' not in self.df_metasail.columns or 'Sexe' not in self.df_metasail.columns:
            print("⚠️ Colonnes 'Nom complet' ou 'Sexe' introuvables. Impossible de compléter le sexe.")
            return
        print("🔄 Complétion des sexes manquants...")

        def predire_sexe_par_prenom(nom_complet):
            if not isinstance(nom_complet, str) or not nom_complet:
                return np.nan
            mots = nom_complet.split()
            best_first_name_data = None
            max_first_name_rank = float('inf')
            for mot in mots:
                resultat = self.nd.search(mot)
                if resultat and 'first_name' in resultat and resultat['first_name'] and 'rank' in resultat[
                    'first_name']:
                    ranks = {k: v for k, v in resultat['first_name']['rank'].items() if v is not None}
                    if ranks:
                        best_rank_country = min(ranks, key=ranks.get)
                        current_rank = ranks[best_rank_country]
                        if current_rank < max_first_name_rank:
                            max_first_name_rank = current_rank
                            best_first_name_data = resultat['first_name']
            if best_first_name_data and 'gender' in best_first_name_data:
                prob_male = best_first_name_data['gender'].get('Male', 0)
                prob_female = best_first_name_data['gender'].get('Female', 0)
                if prob_female > prob_male:
                    return 'Women'
                elif prob_male > prob_female:
                    return 'Men'
            return np.nan

        masque_sexe_vide = self.df_metasail['Sexe'].isnull()
        self.df_metasail.loc[masque_sexe_vide, 'Sexe'] = self.df_metasail.loc[masque_sexe_vide, 'Nom complet'].apply(
            predire_sexe_par_prenom)
        print("✅ Tentative de complétion des sexes manquants terminée.")

    def _complete_missing_age(self):
        """
        Remplit les âges manquants en se basant sur le même "Numéro de série" et "Nom complet".
        """
        if "Catégorie d'âge" not in self.df_metasail.columns or 'Numéro de série' not in self.df_metasail.columns or 'Nom complet' not in self.df_metasail.columns:
            print("⚠️ Colonnes d'âge ou d'identification manquantes. Complétion de l'âge ignorée.")
            return
        print("🔄 Complétion des âges manquants...")
        valeurs_valides = \
        self.df_metasail.dropna(subset=["Catégorie d'âge"]).set_index(['Numéro de série', 'Nom complet'])[
            "Catégorie d'âge"].to_dict()

        def appliquer_age(row):
            if pd.isnull(row["Catégorie d'âge"]):
                cle = (row['Numéro de série'], row['Nom complet'])
                return valeurs_valides.get(cle, "Senior")
            return row["Catégorie d'âge"]

        self.df_metasail["Catégorie d'âge"] = self.df_metasail.apply(appliquer_age, axis=1)
        print("✅ Complétion des âges manquants terminée.")

    def _prepare_data_for_merge(self):
        """
        Prépare les DataFrames Metasail et météo pour la fusion.
        """
        print("\n" + "---" * 15)
        print("🛠️ ÉTAPE 2 : PRÉPARATION ET FUSION DES DONNÉES")
        print("---" * 15)

        # Préparation des dates de Metasail
        self.df_metasail["Date"] = pd.to_datetime(
            self.df_metasail[["Année", "Mois", "Jour"]].astype(str).agg("-".join, axis=1), errors="coerce").dt.date
        base_dt_metasail = pd.to_datetime(
            self.df_metasail['Année'].astype(str) + '-' + self.df_metasail['Mois'].astype(str) + '-' + self.df_metasail[
                'Jour'].astype(str), errors='coerce')
        start_timedelta = pd.to_timedelta(self.df_metasail["Début du segment (timestamp)"].astype(str))
        end_timedelta = pd.to_timedelta(self.df_metasail["Fin du segment (timestamp)"].astype(str))
        self.df_metasail["Début du segment_dt"] = base_dt_metasail + start_timedelta
        self.df_metasail["Fin du segment_dt"] = base_dt_metasail + end_timedelta
        self.df_metasail.loc[self.df_metasail["Fin du segment_dt"] < self.df_metasail[
            "Début du segment_dt"], "Fin du segment_dt"] += timedelta(days=1)
        self.df_metasail["Temps du segment_dt"] = (self.df_metasail["Début du segment_dt"] + (
                    self.df_metasail["Fin du segment_dt"] - self.df_metasail["Début du segment_dt"]) / 2).dt.time

        # Préparation des dates de météo
        self.df_weather["Date"] = pd.to_datetime(
            self.df_weather[["Year", "Month", "Day"]].astype(str).agg("-".join, axis=1), errors="coerce").dt.date
        self.df_weather['Time_dt'] = pd.to_datetime(self.df_weather['Time'].astype(str), format='%H:%M:%S').dt.time

        print("✅ Données de date et heure préparées.")

    def _find_closest_weather_data(self):
        """
        Recherche et fusionne les données météo les plus proches pour chaque ligne de Metasail.
        """
        print("🔍 Fusion des données météo...")

        # Préparez la colonne de lieu dans Metasail pour la fusion
        if "Lieu de l'événement" not in self.df_metasail.columns:
            print("❌ Colonne 'Lieu de l'événement' manquante. Impossible de fusionner les données météo.")
            return

        coords = self.df_metasail["Lieu de l'événement"].astype(str).str.split(", ", expand=True)
        if coords.shape[1] < 2:
            print("❌ Format de coordonnées invalide. Impossible de fusionner les données météo.")
            return

        self.df_metasail['Lat_rounded'] = pd.to_numeric(coords[0], errors='coerce').round(4)
        self.df_metasail['Lon_rounded'] = pd.to_numeric(coords[1], errors='coerce').round(4)
        self.df_metasail['Lieu_key'] = 'Location (' + self.df_metasail['Lat_rounded'].astype(str) + ', ' + \
                                       self.df_metasail['Lon_rounded'].astype(str) + ')'

        # Préparez la colonne de ville météo pour la fusion
        self.df_weather['City_key'] = self.df_weather['City'].astype(str)

        # Effectuez une fusion pour chaque couple Lieu/Date
        final_df_list = []
        ignored_locations = set()

        # Itere sur les combinaisons uniques de lieu et de date du dataframe metasail
        unique_locations_dates = self.df_metasail[['Lieu_key', 'Date']].drop_duplicates()

        for _, row in unique_locations_dates.iterrows():
            lieu_key = row['Lieu_key']
            date = row['Date']

            metasail_subset = self.df_metasail[
                (self.df_metasail['Lieu_key'] == lieu_key) & (self.df_metasail['Date'] == date)].copy()
            weather_subset = self.df_weather[
                (self.df_weather['City_key'] == lieu_key) & (self.df_weather['Date'] == date)].copy()

            if weather_subset.empty:
                if lieu_key not in ignored_locations:
                    print(
                        f"⚠️ Aucune donnée météo trouvée pour '{lieu_key}' le {date}. Les lignes de cette zone seront ignorées.")
                    ignored_locations.add(lieu_key)
                continue

            # Pour chaque ligne de metasail, trouvez la correspondance météo la plus proche
            for idx, row_metasail in metasail_subset.iterrows():
                # Calcul de la différence de temps
                time_diffs = weather_subset['Time_dt'].apply(
                    lambda x: abs(datetime.combine(datetime.min.date(), x) - datetime.combine(datetime.min.date(),
                                                                                              row_metasail[
                                                                                                  'Temps du segment_dt']))
                )

                # Trouver l'index de la correspondance la plus proche
                closest_weather_index = time_diffs.idxmin()

                # Récupérer la ligne météo correspondante
                closest_weather_row = weather_subset.loc[closest_weather_index]

                # Assigner les valeurs météo
                self.df_metasail.loc[idx, "Wind Speed (kts)"] = closest_weather_row["Wind Speed (kts)"]
                self.df_metasail.loc[idx, "Wind Direction (deg)"] = closest_weather_row["Wind Direction (deg)"]

        # Nettoyage des colonnes temporaires
        self.df_metasail.drop(columns=['Lat_rounded', 'Lon_rounded', 'Lieu_key'], inplace=True, errors='ignore')

        print("✅ Fusion des données météo terminée.")
    def _recalculate_and_clean_metrics(self):
        """
        Recalcule le temps de segment, la VMC moyenne et la vitesse moyenne.
        """
        if self.df_metasail is None:
            return

        print("\n" + "---" * 15)
        print("📈 ÉTAPE 3 : CALCUL DES NOUVELLES MÉTRIQUES")
        print("---" * 15)

        required_cols = ["Début du segment_dt", "Fin du segment_dt", "Distance réelle parcourue segment (m)",
                         "Longueur du segment (m)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour le recalcule manquantes.")
            return

        self.df_metasail["delta_time"] = self.df_metasail["Fin du segment_dt"] - self.df_metasail["Début du segment_dt"]
        self.df_metasail.loc[self.df_metasail["delta_time"] < timedelta(0), "delta_time"] += timedelta(days=1)
        self.df_metasail["Temps du segment (s)"] = self.df_metasail["delta_time"].dt.total_seconds()

        safe_time = self.df_metasail["Temps du segment (s)"].replace(0, np.nan)
        self.df_metasail["Vitesse moyenne (noeuds)"] = (self.df_metasail[
                                                            "Distance réelle parcourue segment (m)"] / safe_time) * 1.94384
        self.df_metasail["VMC moyenne"] = (self.df_metasail["Longueur du segment (m)"] / safe_time) * 1.94384

        cols_to_drop = ["Vitesse maximale (noeuds)", "VMG maximale", "VMC maximale", "VMG moyenne"]
        self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors="ignore")
        print("✅ Métriques de performance recalculées et nettoyées.")

    def save_to_excel(self, chemin_sortie):
        """ Sauvegarde le DataFrame traité dans un nouveau fichier Excel. """
        if self.df_metasail is not None:
            self.df_metasail.to_excel(chemin_sortie, index=False)
            print(f"💾 Fichier traité sauvegardé avec succès sous : {chemin_sortie}")

    def get_dataframe(self):
        """Retourne le DataFrame Metasail traité."""
        return self.df_metasail


if __name__ == '__main__':
    fichier_entree_metasail = 'Metasail_Statistics_unified.xlsx'
    fichier_entree_weather = 'weather_data_from_coords.xlsx'
    fichier_sortie = 'Metasail_Statistics_unified_cleaned.xlsx'

    data_processor = DataCleaningAndPreprocessing(fichier_entree_metasail, fichier_entree_weather)

    if data_processor.ready_to_process:
        data_processor.run_cleaning_and_preprocessing()
        data_processor.save_to_excel(fichier_sortie)