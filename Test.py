import numpy as np
from names_dataset import NameDataset


def predire_sexe_par_prenom(nom_complet):
    """
    Prédit le sexe à partir d'un nom complet en utilisant la base de données NameDataset.
    Gère les noms multiples et les cas où les informations sont manquantes.

    :param nom_complet: Le nom complet à analyser (chaîne de caractères).
    :return: 'Women' ou 'Men', ou None si la prédiction est impossible.
    """
    nd = NameDataset()  # L'initialisation se fait à l'intérieur pour la démonstration.
    # Dans un script plus grand, il est préférable de l'initialiser une seule fois.
    if not isinstance(nom_complet, str) or not nom_complet:
        return None

    mots = nom_complet.split()
    prenom_candidat = None

    # 1. Trouver un prénom candidat en cherchant les mots du nom complet
    for mot in mots:
        if not isinstance(mot, str) or mot.isdigit():
            continue

        resultat = nd.search(mot)
        if resultat is not None and 'first_name' in resultat and resultat['first_name'] is not None:
            # S'il y a un résultat valide pour un prénom, on le prend et on s'arrête
            prenom_candidat = mot
            break

    # 2. Prédire le sexe avec le prénom candidat trouvé
    if prenom_candidat:
        resultat_prenom = nd.search(prenom_candidat)

        # Vérifications robustes pour éviter les erreurs de type 'NoneType'
        if resultat_prenom is not None and 'first_name' in resultat_prenom:
            first_name_data = resultat_prenom['first_name']
            if first_name_data is not None and 'gender' in first_name_data:
                prob_male = first_name_data['gender'].get('Male', 0)
                prob_female = first_name_data['gender'].get('Female', 0)

                if prob_female > prob_male:
                    return 'Women'
                elif prob_male > prob_female:
                    return 'Men'

    return None


if __name__ == '__main__':
    while True:
        full_name = input("Entrez un nom complet (ou 'q' pour quitter) : ")
        if full_name.lower() == 'q':
            break

        sexe_predit = predire_sexe_par_prenom(full_name)

        if sexe_predit:
            print(f"Le sexe prédit pour '{full_name}' est : {sexe_predit}\n")
        else:
            print(f"Impossible de prédire le sexe pour '{full_name}'.\n")