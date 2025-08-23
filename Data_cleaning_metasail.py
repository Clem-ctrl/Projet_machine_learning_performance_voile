import pandas as pd
import re
from names_dataset import NameDataset


class DataCleaner:
    """
    Une classe pour nettoyer et prétraiter les données statistiques de Metasail.
    """

    def __init__(self, file_path):
        """
        Initialise le DataCleaner et charge le jeu de données.
        :param file_path: Chemin vers le fichier CSV.
        """
        try:
            self.df = pd.read_csv(file_path)
            print("✅ Fichier chargé avec succès.")
            # Initialise la base de données de prénoms pour la correction
            self.nd = NameDataset()
        except FileNotFoundError:
            print(f"❌ Erreur : Le fichier {file_path} n'a pas été trouvé.")
            self.df = None

    def supprimer_colonnes_inutiles(self, colonnes_a_supprimer):
        """
        Supprime les colonnes spécifiées du DataFrame.

        :param colonnes_a_supprimer: Une liste de noms de colonnes à supprimer.
        """
        if self.df is None:
            return

        # Ne supprime que les colonnes qui existent réellement pour éviter les erreurs
        colonnes_existantes = [col for col in colonnes_a_supprimer if col in self.df.columns]
        self.df.drop(columns=colonnes_existantes, inplace=True)
        print(f"🗑️ Colonnes supprimées : {colonnes_existantes}")

    def nettoyer_noms(self):
        """
        Corrige les colonnes 'Prénom' et 'Nom de famille'.
        Cette méthode combine les deux champs, identifie le prénom le plus probable
        à l'aide de la librairie names-dataset, et sépare de nouveau correctement les noms.
        La recherche est maintenant effectuée en mode 'fuzzy' pour tolérer les légères différences.
        """
        if self.df is None or 'Prénom' not in self.df.columns or 'Nom de famille' not in self.df.columns:
            print("⚠️ Colonnes 'Prénom' ou 'Nom de famille' introuvables. Étape de nettoyage des noms ignorée.")
            return

        def corriger_separation_nom(row):
            # S'assure que les valeurs sont des chaînes de caractères et gère les valeurs vides (NaN)
            prenom = str(row['Prénom']) if pd.notna(row['Prénom']) else ''
            nom_famille = str(row['Nom de famille']) if pd.notna(row['Nom de famille']) else ''

            nom_complet = f"{prenom} {nom_famille}".strip()
            elements = nom_complet.split()

            # Cas où le nom complet est vide
            if not elements:
                return '', ''

            nouveau_prenom = ''
            nouveau_nom = ''

            # On vérifie d'abord si le premier mot ou le dernier est un prénom connu via fuzzy search
            premier_mot = elements[0]
            dernier_mot = elements[-1]

            # Un seuil de 0.8 est un bon compromis pour le fuzzy matching
            # Une correspondance exacte est aussi couverte par un score de 1.0

            # Vérification du premier mot
            resultat_premier = self.nd.search_fuzzy(premier_mot)
            if resultat_premier and resultat_premier[0]['score'] > 0.8:
                nouveau_prenom = premier_mot
                nouveau_nom = ' '.join(elements[1:])
                return nouveau_prenom, nouveau_nom

            # Vérification du dernier mot
            if len(elements) > 1:
                resultat_dernier = self.nd.search_fuzzy(dernier_mot)
                if resultat_dernier and resultat_dernier[0]['score'] > 0.8:
                    nouveau_prenom = dernier_mot
                    nouveau_nom = ' '.join(elements[:-1])
                    return nouveau_prenom, nouveau_nom

            # Si aucune correspondance fuzzy n'est trouvée, on utilise la logique initiale
            # pour identifier les prénoms dans le nom complet
            nouveau_prenom_elements = []
            nouveau_nom_famille_elements = []

            for element in elements:
                resultat_recherche = self.nd.search(element)
                if resultat_recherche['first_name']:
                    nouveau_prenom_elements.append(element)
                else:
                    nouveau_nom_famille_elements.append(element)

            # Si aucun prénom n'a été trouvé, on suppose que le premier mot est le prénom
            if not nouveau_prenom_elements and elements:
                nouveau_prenom = elements[0]
                nouveau_nom = ' '.join(elements[1:])
            else:
                nouveau_prenom = ' '.join(nouveau_prenom_elements)
                nouveau_nom = ' '.join(nouveau_nom_famille_elements)

            return nouveau_prenom, nouveau_nom

        print("🔄 Nettoyage des colonnes 'Prénom' et 'Nom de famille' en cours...")
        # Applique la fonction à chaque ligne du DataFrame
        self.df[['Prénom', 'Nom de famille']] = self.df.apply(corriger_separation_nom, axis=1, result_type='expand')
        print("✅ Noms nettoyés.")

    def traiter_colonne_course(self):
        """
        Extrait la catégorie d'âge et le sexe de la colonne 'Course',
        les place dans de nouvelles colonnes, et nettoie la colonne 'Course' originale.
        """
        if self.df is None or 'Course' not in self.df.columns:
            print("⚠️ Colonne 'Course' introuvable. Étape de traitement de la course ignorée.")
            return

        print("🔄 Traitement de la colonne 'Course' pour extraire la catégorie d'âge et le sexe...")
        colonne_course = self.df['Course'].astype(str)

        # --- 1. Extraire le Sexe ---
        self.df['Sexe'] = colonne_course.str.extract(r'(Men|Women)', flags=re.IGNORECASE, expand=False).str.capitalize()

        # --- 2. Extraire et unifier la Catégorie d'âge ---
        # Définition des expressions régulières pour les catégories
        pattern_u17 = r'U\s*17|Under\s*17|JUNIOR'
        pattern_u19 = r'U\s*19|Under\s*19|YOUTH'

        # Création de la nouvelle colonne
        self.df['Catégorie d\'âge'] = None

        # Assignation des catégories en fonction des patterns trouvés
        self.df.loc[colonne_course.str.contains(pattern_u17, flags=re.IGNORECASE, na=False), 'Catégorie d\'âge'] = 'U17'
        self.df.loc[colonne_course.str.contains(pattern_u19, flags=re.IGNORECASE, na=False), 'Catégorie d\'âge'] = 'U19'

        # --- 3. Nettoyer la colonne 'Course' ---
        # Combinaison de tous les éléments à supprimer dans une seule expression régulière
        pattern_a_supprimer = f"({pattern_u17}|{pattern_u19}|Men|Women|IQfoil)"

        # Remplacement de toutes les occurrences par une chaîne vide
        course_nettoyee = colonne_course.str.replace(pattern_a_supprimer, '', flags=re.IGNORECASE, regex=True)
        # Suppression des espaces superflus
        self.df['Course'] = course_nettoyee.str.replace(r'\s+', ' ', regex=True).str.strip()

        print("✅ Nouvelles colonnes 'Sexe' et 'Catégorie d\'âge' créées et colonne 'Course' nettoyée.")

    def obtenir_dataframe_nettoye(self):
        """
        Retourne le DataFrame nettoyé.
        """
        return self.df

    def sauvegarder_en_csv(self, chemin_sortie):
        """
        Sauvegarde le DataFrame nettoyé dans un nouveau fichier CSV.
        """
        if self.df is not None:
            self.df.to_csv(chemin_sortie, index=False, encoding='utf-8-sig')
            print(f"💾 Fichier nettoyé sauvegardé avec succès sous : {chemin_sortie}")


# --- Bloc d'exécution principal ---
if __name__ == '__main__':
    # Spécifiez le chemin de votre fichier d'entrée ici
    fichier_entree = 'Metasail_Statistics_ML_test.xlsx - Sheet1.csv'
    fichier_sortie = 'Metasail_Statistics_ML_test_cleaned.csv'

    # Création d'une instance du nettoyeur de données
    nettoyeur = DataCleaner(fichier_entree)

    # Vérifie si le DataFrame a été chargé correctement avant de continuer
    if nettoyeur.obtenir_dataframe_nettoye() is not None:
        # 1. Définir les colonnes à supprimer et lancer la suppression
        colonnes_a_supprimer = ['Position de départ', 'VMG maximale', 'VMG moyenne', 'Classement sortie de segment']
        nettoyeur.supprimer_colonnes_inutiles(colonnes_a_supprimer)

        # 2. Nettoyer les colonnes de nom et prénom
        nettoyeur.nettoyer_noms()

        # 3. Traiter la colonne 'Course' pour en extraire les informations
        nettoyeur.traiter_colonne_course()

        # Récupérer le DataFrame final
        dataframe_nettoye = nettoyeur.obtenir_dataframe_nettoye()

        # Afficher un aperçu des données transformées
        print("\n--- Aperçu des 5 premières lignes des données nettoyées ---")
        print(dataframe_nettoye.head())

        # Afficher des informations sur les nouvelles colonnes créées
        print("\n--- Informations sur les nouvelles colonnes ---")
        print("Valeurs uniques dans 'Sexe':", dataframe_nettoye['Sexe'].unique())
        print("Valeurs uniques dans 'Catégorie d'âge':", dataframe_nettoye['Catégorie d\'âge'].unique())
        print("\n--- Aperçu de la colonne 'Course' nettoyée ---")
        print(dataframe_nettoye['Course'].head())

        # 4. Sauvegarder le résultat
        nettoyeur.sauvegarder_en_csv(fichier_sortie)