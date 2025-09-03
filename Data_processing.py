import pandas as pd
import numpy as np
from datetime import timedelta, datetime

# Configuration des fichiers
FICHIER_METASAIL = "Metasail_Statistics_unified_cleaned.xlsx"
FICHIER_WEATHER = "weather_data_cleaned.xlsx"
FICHIER_SORTIE = "Metasail_Statistics_unified_processed.xlsx"


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
        self.df_metasail["Date"] = pd.to_datetime(
            self.df_metasail[["Année", "Mois", "Jour"]].astype(str).agg("-".join, axis=1), errors="coerce"
        ).dt.date
        self.df_weather["Date"] = pd.to_datetime(
            self.df_weather[["Year", "Month", "Day"]].astype(str).agg("-".join, axis=1), errors="coerce"
        ).dt.date

        # Correction de la gestion des dates : Combinaison de la date et de l'heure
        base_dt = pd.to_datetime(
            self.df_metasail['Année'].astype(str) + '-' + self.df_metasail['Mois'].astype(str) + '-' + self.df_metasail[
                'Jour'].astype(str),
            errors='coerce'
        )

        start_timedelta = pd.to_timedelta(self.df_metasail["Début du segment (timestamp)"].astype(str))
        end_timedelta = pd.to_timedelta(self.df_metasail["Fin du segment (timestamp)"].astype(str))

        self.df_metasail["Début du segment_dt"] = base_dt + start_timedelta
        self.df_metasail["Fin du segment_dt"] = base_dt + end_timedelta

        # Gérer le cas où la fin du segment est le jour suivant
        self.df_metasail.loc[self.df_metasail["Fin du segment_dt"] < self.df_metasail[
            "Début du segment_dt"], "Fin du segment_dt"] += timedelta(days=1)

        # Calculer le temps central du segment pour la fusion
        self.df_metasail["Temps du segment_dt"] = (self.df_metasail["Début du segment_dt"] + (
                    self.df_metasail["Fin du segment_dt"] - self.df_metasail["Début du segment_dt"]) / 2).dt.time

        print("✅ Données de date et heure préparées.")

    def _find_closest_weather_data(self):
        """
        Recherche et fusionne les données météo les plus proches pour chaque ligne de Metasail.
        """
        print("\n" + "=" * 50)
        print("🔍 RECHERCHE ET FUSION DES DONNÉES MÉTÉO LES PLUS PROCHES")
        print("=" * 50)

        # Initialisation des colonnes de données météo
        self.df_metasail["Wind Speed (kts)"] = np.nan
        self.df_metasail["Wind Direction (deg)"] = np.nan

        # Set pour stocker les lieux déjà signalés comme manquants
        ignored_locations = set()

        # Itération sur chaque ligne du DataFrame Metasail
        for index, row_metasail in self.df_metasail.iterrows():
            if pd.isna(row_metasail["Date"]) or pd.isna(row_metasail["Temps du segment_dt"]):
                continue

            # Vérification des valeurs manquantes dans la colonne 'Lieu de l'événement'
            if pd.isna(row_metasail["Lieu de l'événement"]):
                continue

            lieu = row_metasail["Lieu de l'événement"].lower()
            date = row_metasail["Date"]

            # Correction de la syntaxe pour le filtrage
            filtered_weather = self.df_weather[
                (self.df_weather["Date"] == date) &
                (self.df_weather["City"].str.lower() == lieu)
                ].copy()

            if filtered_weather.empty:
                # Vérifie si le lieu a déjà été signalé pour cette exécution
                if lieu not in ignored_locations:
                    print(
                        f"⚠️ Aucune donnée météo trouvée pour le lieu {row_metasail['Lieu de l\'événement']} le {date}. Les lignes de cette zone seront ignorées.")
                    ignored_locations.add(lieu)
                continue

            # Calcule la différence de temps et trouve la ligne la plus proche
            filtered_weather["time_diff"] = filtered_weather["Time_dt"].apply(
                lambda x: abs(datetime.combine(datetime.min.date(), x) - datetime.combine(datetime.min.date(),
                                                                                          row_metasail[
                                                                                              "Temps du segment_dt"]))
            )
            closest_weather_index = filtered_weather["time_diff"].idxmin()
            closest_weather = filtered_weather.loc[closest_weather_index]

            # Mise à jour des colonnes dans le DataFrame original
            self.df_metasail.at[index, "Wind Speed (kts)"] = closest_weather["Wind Speed (kts)"]
            self.df_metasail.at[index, "Wind Direction (deg)"] = closest_weather["Wind Direction (deg)"]

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

        required_cols = ["Début du segment (timestamp)", "Fin du segment (timestamp)",
                         "Distance réelle parcourue segment (m)", "Longueur du segment (m)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print("❌ Colonnes requises pour le recalcule manquantes.")
            return

        # Correction : utilisation des colonnes déjà créées pour le calcul
        self.df_metasail["delta_time"] = self.df_metasail["Fin du segment_dt"] - self.df_metasail["Début du segment_dt"]
        self.df_metasail.loc[self.df_metasail["delta_time"] < timedelta(0), "delta_time"] += timedelta(days=1)
        self.df_metasail["Temps du segment (s)"] = self.df_metasail["delta_time"].dt.total_seconds()
        print("✅ 'Temps du segment (s)' recalculé avec succès.")

        safe_time = self.df_metasail["Temps du segment (s)"].replace(0, np.nan)
        self.df_metasail["Vitesse moyenne (noeuds)"] = (self.df_metasail[
                                                            "Distance réelle parcourue segment (m)"] / safe_time) * 1.94384
        print("✅ 'Vitesse moyenne (noeuds)' recalculée avec succès.")

        self.df_metasail["VMC moyenne"] = (self.df_metasail["Longueur du segment (m)"] / safe_time) * 1.94384
        print("✅ 'VMC moyenne' recalculée avec succès.")

        # Suppression des colonnes existantes de métriques pour éviter les doublons
        cols_to_drop = ["Vitesse maximale (noeuds)", "VMG maximale", "VMC maximale", "VMG moyenne"]
        self.df_metasail.drop(columns=cols_to_drop, inplace=True, errors="ignore")

    def calculate_new_metrics(self):
        """
        Calcule les nouvelles métriques d'efficacité par rapport au vent en utilisant le cap entre les bouées.
        """
        print("\n" + "=" * 50)
        print("📈 CALCUL DES NOUVELLES MÉTRIQUES LIÉES AU VENT")
        print("=" * 50)

        # Vérification des colonnes nécessaires
        required_cols = ["Efficacité du segment (%)", "Wind Speed (kts)", "Cap magnétique (deg)",
                         "Wind Direction (deg)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print(
                f"❌ Colonnes requises pour le calcul des nouvelles métriques manquantes : {list(set(required_cols) - set(self.df_metasail.columns))}")
            return

        # Efficacité (Distance réelle/idéale) (%) / wind speed
        self.df_metasail["Efficacité segment / Wind Speed"] = self.df_metasail["Efficacité du segment (%)"] / \
                                                              self.df_metasail["Wind Speed (kts)"]
        print("✅ 'Efficacité segment / Wind Speed' calculé avec succès.")

        # Calculer la différence d'angle entre le vent et le cap du segment
        # Un angle de 0° ou 360° signifie que la bouée est directement au vent.
        # Un angle de 180° signifie que la bouée est directement sous le vent.
        self.df_metasail["Angle Vent-Cap"] = np.abs(
            self.df_metasail["Cap magnétique (deg)"] - self.df_metasail["Wind Direction (deg)"])
        self.df_metasail["Angle Vent-Cap"] = self.df_metasail["Angle Vent-Cap"].apply(lambda x: min(x, 360 - x))

        # Définition des conditions de navigation (près ou portant)
        # Un segment est au "près" si l'angle entre le vent et le cap du segment est inférieur à 90 degrés.
        # Un segment est au "portant" si cet angle est supérieur ou égal à 90 degrés.
        pres_condition = (self.df_metasail["Angle Vent-Cap"] < 90)
        portant_condition = (self.df_metasail["Angle Vent-Cap"] >= 90)

        # Efficacité (Distance réelle/idéale) (%) au près
        self.df_metasail["Efficacité Près (%)"] = np.nan
        self.df_metasail.loc[pres_condition, "Efficacité Près (%)"] = self.df_metasail.loc[
            pres_condition, "Efficacité du segment (%)"]
        print("✅ 'Efficacité Près (%)' calculé avec succès.")

        # Efficacité (Distance réelle/idéale) (%) au portant
        self.df_metasail["Efficacité Portant (%)"] = np.nan
        self.df_metasail.loc[portant_condition, "Efficacité Portant (%)"] = self.df_metasail.loc[
            portant_condition, "Efficacité du segment (%)"]
        print("✅ 'Efficacité Portant (%)' calculé avec succès.")


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

        # Calcule les nouvelles métriques d'efficacité au vent
        processeur.calculate_new_metrics()

        # Sauvegarde du fichier final
        processeur.df_metasail.to_excel(FICHIER_SORTIE, index=False)
        print(f"💾 Fichier traité et calculé sauvegardé avec succès sous : {FICHIER_SORTIE}")

    except FileNotFoundError as e:
        print(f"❌ Erreur : L'un des fichiers requis n'a pas été trouvé. {e}")
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue : {e}")


if __name__ == "__main__":
    main()
