import pandas as pd
import re
from names_dataset import NameDataset
import numpy as np


class DataCleaner:
    """
    Une classe pour nettoyer et prétraiter les données statistiques de Metasail.
    """

    def __init__(self, file_path):
        """
        Initialise le DataCleaner et charge le jeu de données.
        :param file_path: Chemin vers le fichier Excel.
        """
        try:
            self.df = pd.read_excel(file_path)
            print("✅ Fichier Excel chargé avec succès.")
            # Initialise la base de données de prénoms pour l'assignation de sexe
            self.nd = NameDataset()
        except FileNotFoundError:
            print(f"❌ Erreur : Le fichier {file_path} n'a pas été trouvé.")
            self.df = None
        except Exception as e:
            print(f"❌ Une erreur s'est produite lors de la lecture du fichier : {e}")
            self.df = None

    def supprimer_colonnes_inutiles(self, colonnes_a_supprimer):
        """
        Supprime les colonnes spécifiées du DataFrame.
        :param colonnes_a_supprimer: Une liste de noms de colonnes à supprimer.
        """
        if self.df is None:
            return

        colonnes_existantes = [col for col in colonnes_a_supprimer if col in self.df.columns]
        self.df.drop(columns=colonnes_existantes, inplace=True, errors='ignore')
        print(f"🗑️ Colonnes supprimées : {colonnes_existantes}")

    def filtrer_statut_course(self):
        """
        Supprime les lignes où le statut de la course est 'abandonned' ou 'recall'.
        """
        if self.df is None or 'Course' not in self.df.columns:
            print("⚠️ Colonne 'Course' introuvable. Étape de filtrage de la course ignorée.")
            return

        print("🔄 Suppression des lignes 'abandonned' et 'recall'...")
        lignes_initiales = len(self.df)
        self.df = self.df[~self.df['Course'].str.contains('abandon|recall', case=False, na=False)]
        lignes_supprimees = lignes_initiales - len(self.df)
        print(f"✅ {lignes_supprimees} ligne(s) 'abandonned' ou 'recall' supprimée(s).")

    def splitter_date(self, nom_colonne_date='Date'):
        """
        Divise une colonne de date en trois nouvelles colonnes : Année, Mois, Jour.
        :param nom_colonne_date: Le nom de la colonne contenant les dates.
        """
        if self.df is None or nom_colonne_date not in self.df.columns:
            print(f"⚠️ Colonne '{nom_colonne_date}' introuvable. Le split de la date est ignoré.")
            return

        print(f"🔄 Division de la colonne '{nom_colonne_date}' en Année, Mois, Jour...")
        self.df[nom_colonne_date] = pd.to_datetime(self.df[nom_colonne_date])
        self.df['Année'] = self.df[nom_colonne_date].dt.year
        self.df['Mois'] = self.df[nom_colonne_date].dt.month
        self.df['Jour'] = self.df[nom_colonne_date].dt.day
        self.df.drop(columns=[nom_colonne_date], inplace=True)
        print(f"✅ Colonnes Année, Mois, Jour créées. Colonne '{nom_colonne_date}' supprimée.")

    def traiter_colonne_course(self):
        """
        Extrait la catégorie d'âge et le sexe de la colonne 'Course',
        et nettoie la colonne 'Course' originale.
        """
        if self.df is None or 'Course' not in self.df.columns:
            print("⚠️ Colonne 'Course' introuvable. Étape de traitement de la course ignorée.")
            return

        print("🔄 Traitement de la colonne 'Course' pour extraire la catégorie d'âge et le sexe...")
        colonne_course = self.df['Course'].astype(str)
        self.df['Sexe'] = colonne_course.str.extract(r'(Men|Women)', flags=re.IGNORECASE, expand=False).str.capitalize()
        pattern_u17 = r'U\s*17|Under\s*17|JUNIOR'
        pattern_u19 = r'U\s*19|Under\s*19|YOUTH'
        self.df["Catégorie d'âge"] = pd.Series(dtype='object')
        self.df.loc[colonne_course.str.contains(pattern_u17, flags=re.IGNORECASE, na=False), "Catégorie d'âge"] = 'U17'
        self.df.loc[colonne_course.str.contains(pattern_u19, flags=re.IGNORECASE, na=False), "Catégorie d'âge"] = 'U19'
        pattern_a_supprimer = f"({pattern_u17}|{pattern_u19}|Men|Women|IQfoil)"
        course_nettoyee = colonne_course.str.replace(pattern_a_supprimer, '', flags=re.IGNORECASE, regex=True)
        self.df['Course'] = course_nettoyee.str.replace(r'\s+', ' ', regex=True).str.strip()
        print("✅ Nouvelles colonnes 'Sexe' et 'Catégorie d'âge' créées et colonne 'Course' nettoyée.")

    def completer_sexe_manquant(self):
        """
        Remplit les valeurs manquantes dans la colonne 'Sexe' en se basant
        sur l'analyse du prénom le plus probable dans 'Nom Complet'.
        """
        if self.df is None or 'Nom Complet' not in self.df.columns or 'Sexe' not in self.df.columns:
            print("⚠️ Colonnes 'Nom Complet' ou 'Sexe' introuvables. Impossible de compléter le sexe.")
            return

        print("\n🔄 Début de la complétion des sexes manquants...")

        def predire_sexe_par_prenom(nom_complet):
            if not isinstance(nom_complet, str) or not nom_complet:
                return np.nan

            mots = nom_complet.split()
            prenom_candidat = None
            meilleur_rang = float('inf')

            for mot in mots:
                resultat = self.nd.search(mot)
                if resultat['first_name'] is not None:
                    ranks = [v for v in resultat['first_name']['rank'].values() if v is not None]
                    if ranks:
                        meilleur_rang_mot = min(ranks)
                        if meilleur_rang_mot < meilleur_rang:
                            meilleur_rang = meilleur_rang_mot
                            prenom_candidat = mot

            if prenom_candidat:
                resultat_prenom = self.nd.search(prenom_candidat)
                prob_male = resultat_prenom['first_name']['gender'].get('Male', 0)
                prob_female = resultat_prenom['first_name']['gender'].get('Female', 0)

                if prob_female > prob_male:
                    return 'Women'
                elif prob_male > prob_female:
                    return 'Men'
                else:
                    return np.nan
            else:
                return np.nan

        if 'Sexe' not in self.df.columns:
            self.df['Sexe'] = pd.Series(dtype='object')

        masque_sexe_vide = self.df['Sexe'].isnull()
        self.df.loc[masque_sexe_vide, 'Sexe'] = self.df.loc[masque_sexe_vide, 'Nom Complet'].apply(
            predire_sexe_par_prenom)

        print("\n✅ Tentative de complétion des sexes manquants terminée.")

    def completer_age_manquant(self):
        """
        Remplit les valeurs manquantes dans la colonne 'Catégorie d'âge'
        en se basant sur les valeurs non vides pour le même "Numéro de série" et "Nom Complet".
        """
        if self.df is None or "Catégorie d'âge" not in self.df.columns or 'Numéro de série' not in self.df.columns or 'Nom Complet' not in self.df.columns:
            print(
                "⚠️ Colonnes requises ('Catégorie d'âge', 'Numéro de série', 'Nom Complet') introuvables. Complétion de l'âge ignorée.")
            return

        print("\n🔄 Début de la complétion des âges manquants...")
        lignes_initiales = self.df["Catégorie d'âge"].isnull().sum()
        valeurs_valides = self.df.dropna(subset=["Catégorie d'âge"]).set_index(['Numéro de série', 'Nom Complet'])[
            "Catégorie d'âge"].to_dict()

        def appliquer_age(row):
            if pd.isnull(row["Catégorie d'âge"]):
                cle = (row['Numéro de série'], row['Nom Complet'])
                if cle in valeurs_valides:
                    return valeurs_valides.get(cle)
                else:
                    return "Senior"
            return row["Catégorie d'âge"]

        self.df["Catégorie d'âge"] = self.df.apply(appliquer_age, axis=1)
        lignes_remplies = self.df["Catégorie d'âge"].isnull().sum()
        print(f"✅ {lignes_initiales - lignes_remplies} valeurs d'âge manquantes ont été complétées.")

    def get_dataframe(self):
        """ Retourne le DataFrame nettoyé. """
        return self.df

    def save_to_excel(self, chemin_sortie):
        """ Sauvegarde le DataFrame nettoyé dans un nouveau fichier Excel. """
        if self.df is not None:
            self.df.to_excel(chemin_sortie, index=False)
            print(f"💾 Fichier nettoyé sauvegardé avec succès sous : {chemin_sortie}")


if __name__ == '__main__':
    fichier_entree = 'Metasail_Statistics_ML_test.xlsx'
    fichier_sortie = 'Metasail_Statistics_ML_test_cleaned.xlsx'

    nettoyeur = DataCleaner(fichier_entree)

    if nettoyeur.get_dataframe() is not None:
        colonnes_a_supprimer = ['Position de départ', 'Classement sortie de segment', 'Vitesse maximale (noeuds)',
                                'VMG maximale', 'VMC maximale', 'VMG moyenne']
        nettoyeur.supprimer_colonnes_inutiles(colonnes_a_supprimer)
        nettoyeur.traiter_colonne_course()
        nettoyeur.filtrer_statut_course()
        nettoyeur.splitter_date(nom_colonne_date='Date de la course')
        nettoyeur.completer_sexe_manquant()
        nettoyeur.completer_age_manquant()

        dataframe_final = nettoyeur.get_dataframe()
        nettoyeur.save_to_excel(fichier_sortie)
