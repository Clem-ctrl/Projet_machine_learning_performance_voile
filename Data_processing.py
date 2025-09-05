import pandas as pd
import numpy as np
from scipy.stats import zscore
from datetime import timedelta, datetime
import os


class DataProcessor:
    """
    Une classe pour nettoyer les données et calculer des métriques complexes.
    Elle gère les valeurs aberrantes en se basant sur un DataFrame unique.
    """

    def __init__(self, df_metasail):
        """
        Initialise le DataProcessor avec le DataFrame Metasail nettoyé et fusionné.
        :param df_metasail: DataFrame pandas des données de Metasail fusionnées.
        """
        self.df_metasail = df_metasail
        if self.df_metasail is None or self.df_metasail.empty:
            print("❌ Le DataFrame Metasail est vide. Les calculs ne peuvent pas être effectués.")

    def remove_outliers_zscore(self, threshold=3):
        """
        Supprime les valeurs aberrantes en utilisant la méthode du z-score.
        Cible les colonnes de vitesse moyenne, VMG et efficacité de segment.
        """
        print("\n--- Suppression des outliers (Z-score) ---")
        cols_to_check = ["Vitesse moyenne (noeuds)", "VMG", "Efficacité du segment (%)"]

        if not all(col in self.df_metasail.columns for col in cols_to_check):
            print(f"❌ Colonnes requises manquantes pour le Z-score. Ignoré.")
            return

        initial_rows = len(self.df_metasail)
        z_scores = self.df_metasail[cols_to_check].apply(zscore)
        self.df_metasail = self.df_metasail[(np.abs(z_scores) < threshold).all(axis=1)]

        rows_removed = initial_rows - len(self.df_metasail)
        print(f"✅ {rows_removed} lignes aberrantes supprimées (seuil Z-score = {threshold}).")

    def remove_implausible_distances(self):
        """
        Supprime les lignes où les distances parcourues sont incohérentes
        par rapport aux distances idéales (avec une tolérance).
        """
        print("\n--- Suppression des distances incohérentes ---")

        if "Distance totale parcourue (m)" in self.df_metasail.columns and "Longueur totale du parcours (m)" in self.df_metasail.columns:
            rows_before = len(self.df_metasail)
            self.df_metasail = self.df_metasail[
                self.df_metasail["Distance totale parcourue (m)"] >= (
                            self.df_metasail["Longueur totale du parcours (m)"] - 30)
                ]
            print(
                f"✅ {rows_before - len(self.df_metasail)} lignes supprimées (Distance totale < Longueur totale - 30m).")

        if "Distance réelle du segment (m)" in self.df_metasail.columns and "Longueur du côté du segment (m)" in self.df_metasail.columns:
            rows_before = len(self.df_metasail)
            self.df_metasail = self.df_metasail[
                self.df_metasail["Distance réelle du segment (m)"] >= (
                            self.df_metasail["Longueur du côté du segment (m)"] - 30)
                ]
            print(
                f"✅ {rows_before - len(self.df_metasail)} lignes supprimées (Distance segment < Longueur segment - 30m).")

    def remove_low_efficiency(self):
        """
        Supprime les lignes où l'efficacité est inférieure à un seuil réaliste.
        """
        print("\n--- Suppression des faibles efficacités ---")

        if "Efficacité (Distance réelle/idéale) (%)" in self.df_metasail.columns:
            rows_before = len(self.df_metasail)
            self.df_metasail = self.df_metasail[self.df_metasail["Efficacité (Distance réelle/idéale) (%)"] >= 97]
            print(f"✅ {rows_before - len(self.df_metasail)} lignes supprimées (Efficacité globale < 97%).")

        if "Efficacité du segment (%)" in self.df_metasail.columns:
            rows_before = len(self.df_metasail)
            self.df_metasail = self.df_metasail[self.df_metasail["Efficacité du segment (%)"] >= 94]
            print(f"✅ {rows_before - len(self.df_metasail)} lignes supprimées (Efficacité segment < 94%).")

    def remove_wind_direction_discrepancies(self, tolerance=30):
        """
        Supprime les lignes où la direction du vent de la météo diffère trop
        de celle de Metasail.
        """
        print("\n--- Suppression des incohérences de direction du vent ---")

        required_cols = ["Wind Direction (deg)", "Orientation vent metasail"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            print(f"❌ Colonnes de vent requises manquantes. Ignoré.")
            return

        initial_rows = len(self.df_metasail)
        angle_diff = np.abs(self.df_metasail["Wind Direction (deg)"] - self.df_metasail["Orientation vent metasail"])
        angle_diff = angle_diff.apply(lambda x: min(x, 360 - x))

        self.df_metasail = self.df_metasail[angle_diff <= tolerance]

        rows_removed = initial_rows - len(self.df_metasail)
        print(f"✅ {rows_removed} lignes supprimées (différence de vent > {tolerance}°).")

    def manage_outliers(self):
        """
        Méthode principale pour orchestrer le nettoyage des données et la
        suppression des valeurs aberrantes.
        """
        print("\n" + "=" * 50)
        print("🧹 GESTION DES VALEURS ABERRANTES")
        print("=" * 50)

        initial_total_rows = len(self.df_metasail)

        self.remove_outliers_zscore()
        self.remove_implausible_distances()
        self.remove_low_efficiency()
        self.remove_wind_direction_discrepancies()

        final_total_rows = len(self.df_metasail)
        total_removed = initial_total_rows - final_total_rows

        print("\n" + "-" * 50)
        print(f"📊 Bilan du nettoyage : {total_removed} lignes supprimées au total.")
        print(f"Il reste {final_total_rows} lignes dans le DataFrame.")
        print("-" * 50)

    def calculate_new_metrics(self):
        """
        Calcule les nouvelles métriques d'efficacité par rapport au vent.
        """
        print("\n" + "=" * 50)
        print("📈 CALCUL DES NOUVELLES MÉTRIQUES LIÉES AU VENT")
        print("=" * 50)

        required_cols = ["Efficacité du segment (%)", "Wind Speed (kts)", "Cap magnétique (deg)",
                         "Wind Direction (deg)"]
        if not all(col in self.df_metasail.columns for col in required_cols):
            missing_cols = list(set(required_cols) - set(self.df_metasail.columns))
            print(f"❌ Colonnes requises manquantes : {missing_cols}. Calculs ignorés.")
            return

        self.df_metasail["Efficacité segment / Wind Speed"] = self.df_metasail["Efficacité du segment (%)"] / \
                                                              self.df_metasail["Wind Speed (kts)"]
        print("✅ 'Efficacité segment / Wind Speed' calculé.")

        angle_diff = np.abs(self.df_metasail["Cap magnétique (deg)"] - self.df_metasail["Wind Direction (deg)"])
        self.df_metasail["Angle Vent-Cap"] = angle_diff.apply(lambda x: min(x, 360 - x))

        pres_condition = self.df_metasail["Angle Vent-Cap"] < 90
        portant_condition = self.df_metasail["Angle Vent-Cap"] >= 90

        self.df_metasail["Efficacité Près (%)"] = np.nan
        self.df_metasail.loc[pres_condition, "Efficacité Près (%)"] = self.df_metasail.loc[
            pres_condition, "Efficacité du segment (%)"]
        print("✅ 'Efficacité Près (%)' calculé.")

        self.df_metasail["Efficacité Portant (%)"] = np.nan
        self.df_metasail.loc[portant_condition, "Efficacité Portant (%)"] = self.df_metasail.loc[
            portant_condition, "Efficacité du segment (%)"]
        print("✅ 'Efficacité Portant (%)' calculé.")


def main():
    """ Fonction principale pour exécuter le traitement des données. """
    input_path = "C:/Users/Byron Barette/PycharmProjects/Projet_machine_learning_performance_voile/Metasail_Statistics_unified_cleaned.xlsx"
    output_path = "C:/Users/Byron Barette/PycharmProjects/Projet_machine_learning_performance_voile/Metasail_Statistics_unified_processed.xlsx"

    try:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Fichier d'entrée Metasail introuvable : {input_path}")

        dataframe_metasail = pd.read_excel(input_path)
        print("✅ Fichier chargé avec succès.")

        processeur = DataProcessor(dataframe_metasail)

        # Gestion des outliers et nettoyage des données
        processeur.manage_outliers()

        # Calcul des nouvelles métriques
        processeur.calculate_new_metrics()

        # Sauvegarde du fichier final
        processeur.df_metasail.to_excel(output_path, index=False)
        print(f"💾 Fichier traité et calculé sauvegardé avec succès sous : {output_path}")

    except FileNotFoundError as e:
        print(f"❌ Erreur : {e}")
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue : {e}")


if __name__ == "__main__":
    main()