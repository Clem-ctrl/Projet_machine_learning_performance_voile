import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta


class PerformanceVerifier:
    """
    Une classe pour valider les métriques de performance des segments Metasail
    et détecter les valeurs aberrantes.
    """

    def __init__(self, file_path):
        """
        Initialise le vérificateur de performance et charge les données.
        :param file_path: Chemin vers le fichier Excel contenant les données.
        """
        try:
            self.df = pd.read_excel(file_path)
            print(f"✅ Fichier '{file_path}' chargé avec succès.")
        except FileNotFoundError:
            print(f"❌ Erreur : Le fichier {file_path} n'a pas été trouvé.")
            self.df = None
        except Exception as e:
            print(f"❌ Une erreur s'est produite lors de la lecture du fichier : {e}")
            self.df = None

    def detect_outliers_on_distance(self):
        """
        Détecte les valeurs aberrantes sur la 'Distance réelle du segment (m)'
        en utilisant la méthode du Z-Score.
        """
        if self.df is None:
            return

        col = 'Distance réelle du segment (m)'
        if col not in self.df.columns:
            print(f"⚠️ Colonne '{col}' introuvable pour la détection des valeurs aberrantes.")
            return

        print("\n" + "=" * 50)
        print("🔎 DÉTECTION DES VALEURS ABERRANTES SUR LA DISTANCE RÉELLE DU SEGMENT")
        print("=" * 50)

        # --- Méthode du Z-Score ---
        mean = self.df[col].mean()
        std = self.df[col].std()
        z_score_threshold = 3.0
        outliers_zscore = self.df[np.abs((self.df[col] - mean) / std) > z_score_threshold]

        print(f"\n--- Rapport d'anomalies pour la colonne '{col}' ---")

        if not outliers_zscore.empty:
            print(f"  🔹 {len(outliers_zscore)} valeur(s) aberrante(s) détectée(s) par la méthode Z-Score.")
            print("Aperçu des valeurs aberrantes (Z-Score) :")
            print(outliers_zscore[[col, 'Nom Complet']].head().to_string(index=False))
        else:
            print("\n  ✅ Aucune valeur aberrante détectée par la méthode Z-Score.")

        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        sns.boxplot(x=self.df[col])
        plt.title(f'Boxplot de "{col}" (pour identifier les valeurs aberrantes)')

        plt.subplot(1, 2, 2)
        sns.histplot(self.df[col], kde=True)
        plt.title(f'Distribution de "{col}"')

        plt.tight_layout()
        plt.show()

    def identify_short_distances(self, tolerance=30):
        """
        Identifie et affiche les lignes où la distance réelle est inférieure
        à la longueur du côté du segment, avec une tolérance.
        :param tolerance: Marge de tolérance en mètres.
        """
        if self.df is None:
            return

        required_cols = ['Distance réelle du segment (m)', 'Longueur du côté du segment (m)']
        if not all(col in self.df.columns for col in required_cols):
            print("❌ Colonnes requises pour la comparaison des distances manquantes.")
            return

        short_distances_df = self.df[
            self.df['Distance réelle du segment (m)'] < (self.df['Longueur du côté du segment (m)'] - tolerance)]

        print("\n" + "=" * 50)
        print("📏 ANALYSE DES DISTANCES RÉELLES INFÉRIEURES À LA LONGUEUR DU SEGMENT")
        print(f"**Tolérance appliquée : {tolerance} mètres**")
        print("=" * 50)

        if not short_distances_df.empty:
            print(
                f"🔹 {len(short_distances_df)} lignes trouvées où la 'Distance réelle' est anormalement plus courte que la 'Longueur du côté'.")
            print("\nAperçu des 5 premières lignes :")
            print(short_distances_df[['Nom Complet', 'Nom de l\'événement', 'Distance réelle du segment (m)',
                                      'Longueur du côté du segment (m)']].head().to_string(index=False))
        else:
            print(f"✅ Aucune ligne anormale trouvée avec une tolérance de {tolerance} mètres.")

    def check_total_distance_consistency(self, tolerance=30):
        """
        Meme vérif mais sur tout le parcours. Vérifie la cohérence entre la distance totale parcourue et la longueur
        totale du parcours, avec une tolérance.
        :param tolerance: Marge de tolérance en mètres.
        """
        if self.df is None:
            return

        required_cols = ['Longueur totale du parcours (m)', 'Distance totale parcourue (m)',
                         'Efficacité (Distance réelle/idéale) (%)']
        if not all(col in self.df.columns for col in required_cols):
            print("❌ Colonnes requises pour la vérification de la distance totale manquantes.")
            return

        # Appliquer la tolérance de 30m ici
        inconsistent_df = self.df[
            self.df['Distance totale parcourue (m)'] < (self.df['Longueur totale du parcours (m)'] - tolerance)].copy()

        print("\n" + "=" * 50)
        print("🔎 VÉRIFICATION DE LA COHÉRENCE DES DISTANCES TOTALES")
        print(f"**Tolérance appliquée : {tolerance} mètres**")
        print("=" * 50)

        if not inconsistent_df.empty:
            print(
                f"🔹 {len(inconsistent_df)} lignes trouvées où 'Distance totale' est inférieure à 'Longueur totale du parcours' de plus de {tolerance}m.")

            efficiency_issues = inconsistent_df[inconsistent_df['Efficacité (Distance réelle/idéale) (%)'] >= 100]

            if not efficiency_issues.empty:
                print("\n⚠️ Incohérence détectée : 'Efficacité' >= 100% pour certaines de ces lignes.")
                print(f"Nombre de lignes concernées : {len(efficiency_issues)}")
                print("\nAperçu des 5 premières lignes avec cette incohérence :")
                print(efficiency_issues[['Nom Complet', 'Nom de l\'événement', 'Distance totale parcourue (m)',
                                         'Longueur totale du parcours (m)',
                                         'Efficacité (Distance réelle/idéale) (%)']].head().to_string(index=False))
            else:
                print(
                    "\n✅ Pour toutes ces lignes, la colonne 'Efficacité' est bien inférieure à 100%, ce qui est cohérent.")
        else:
            print(f"✅ Aucune incohérence trouvée avec une tolérance de {tolerance} mètres.")

    def supprimer_anomalies(self):
        """
        Supprime les lignes du DataFrame où des anomalies et des valeurs aberrantes
        ont été détectées sur la base de critères prédéfinis.
        """
        if self.df is None:
            return

        print("\n" + "=" * 50)
        print("🗑️ SUPPRESSION DES LIGNES AVEC ANOMALIES ET VALEURS ABERRANTES")
        print("=" * 50)

        initial_rows = len(self.df)

        # Critère 1 : Z-Score élevé sur la 'différence' entre distance réel
        col_distance = 'Longueur du segment (m)'
        col_parcourue = 'Distance réelle parcourue segment (m)'

        if col_distance in self.df.columns and col_parcourue in self.df.columns:
            # Calcul de la nouvelle colonne
            self.df['diff_distance'] = self.df[col_distance] - self.df[col_parcourue]

            # Application du Z-Score sur la différence
            mean_diff = self.df['diff_distance'].mean()
            std_diff = self.df['diff_distance'].std()
            z_score_threshold = 3.0

            outlier_mask = np.abs((self.df['diff_distance'] - mean_diff) / std_diff) > z_score_threshold
            self.df = self.df[~outlier_mask]

            print(
                f"✅ {outlier_mask.sum()} lignes supprimées en raison de valeurs aberrantes (Z-Score) sur la différence de distance.")

            # Suppression de la colonne temporaire
            self.df = self.df.drop(columns=['diff_distance'])
        else:
            print(
                f"⚠️ Colonnes requises ('{col_distance}' ou '{col_parcourue}') introuvables. Le critère 1 n'a pas été appliqué.")

        # Critère 2 : 'Distance réelle du segment' plus courte que le segment
        col_longueur = 'Longueur du côté du segment (m)'
        if col_distance in self.df.columns and col_longueur in self.df.columns:
            tolerance = 30
            short_distance_mask = self.df[col_distance] < (self.df[col_longueur] - tolerance)
            self.df = self.df[~short_distance_mask]
            print(
                f"✅ {short_distance_mask.sum()} lignes supprimées en raison de distances réelles anormalement courtes.")

        # Critère 3 : Incohérence de la distance totale et de l'efficacité
        col_parcouru_total = 'Distance totale parcourue (m)'
        col_longueur_totale = 'Longueur totale du parcours (m)'
        if col_parcouru_total in self.df.columns and col_longueur_totale in self.df.columns:
            tolerance = 30
            inconsistent_mask = self.df[col_parcouru_total] < (self.df[col_longueur_totale] - tolerance)
            self.df = self.df[~inconsistent_mask]
            print(f"✅ {inconsistent_mask.sum()} lignes supprimées en raison d'incohérences sur les distances totales.")

        final_rows = len(self.df)
        print(f"Un total de {initial_rows - final_rows} ligne(s) a été supprimé(e).")

    def check_wind_direction_alignment(self):
        """
        Vérifie la concordance entre 'wind_orientation_metasail' et 'Wind Direction (deg)'.
        Affiche un résumé du nombre de lignes avec un écart de plus de 10 degrés.
        """
        print("\n" + "=" * 50)
        print("✔️ VÉRIFICATION DE LA CONCORDANCE DES DIRECTIONS DU VENT")
        print("=" * 50)

        # Vérifier si les colonnes nécessaires existent
        if "wind_orientation_metasail" not in self.df.columns or "Wind Direction (deg)" not in self.df.columns:
            print(
                "❌ Colonnes 'wind_orientation_metasail' ou 'Wind Direction (deg)' manquantes. Vérification impossible.")
            return

        # Remplacer les NaN par une valeur qui sera ignorée
        df_temp = self.df.dropna(subset=["wind_orientation_metasail", "Wind Direction (deg)"]).copy()

        if df_temp.empty:
            print("⚠️ Aucune ligne valide pour la vérification de la direction du vent.")
            return

        # Calculer la différence d'angle en tenant compte du passage à 360/0 degrés
        angle_diff = np.abs(df_temp["wind_orientation_metasail"] - df_temp["Wind Direction (deg)"])
        adjusted_angle_diff = np.minimum(angle_diff, 360 - angle_diff)

        # Compter le nombre de lignes où l'écart est supérieur à 10 degrés
        mismatched_lines = adjusted_angle_diff[adjusted_angle_diff > 10].count()
        total_lines = len(df_temp)

        print(f"📊 Résultat de la vérification :")
        print(f"  - Total de lignes avec des données de vent : {total_lines}")
        print(f"  - Lignes avec un écart > 10 degrés : {mismatched_lines}")
        print(f"  - Pourcentage d'écart : {(mismatched_lines / total_lines * 100):.2f}%")
        print("✅ Vérification terminée.")


# --- Bloc d'exécution principal ---
if __name__ == '__main__':
    fichier_nettoye = 'Metasail_Statistics_ML_test_cleaned.xlsx'

    verifier = PerformanceVerifier(fichier_nettoye)

    if verifier.df is not None:
        verifier.detect_outliers_on_distance()
        verifier.identify_short_distances(tolerance=30)
        verifier.check_total_distance_consistency(tolerance=30)
        verifier.check_wind_direction_alignment()  # Appel de la nouvelle fonction
        verifier.supprimer_anomalies()