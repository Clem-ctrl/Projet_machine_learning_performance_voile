# Modélisation de la performance en IQFoil jeunes
## ETL fonctionnel basé sur le webscraping Metasail et Openweathermaps pour une régression Random Forest

Ce projet est un exemple d'exploration statistique mobilisant des données de navigation et de conditions météorologiques publiques et en libre accès.

**Plusieurs étapes jalonnent ce projet :**

<details>
  <summary><b>Automatisation de la collecte de données (web scraping)</b></summary>
  - Extraction des informations à partir de pages web (Selenium).
  - Analyse du contenu pour l'extraction des données pertinentes et leur organisation en DataFrame.
  - Mise en place d'un flux de travail itératif pour éviter la redondance.
  - Récupération de données météo via l'API OpenWeatherMaps.
</details>

<details>
  <summary><b>Intégration et enrichissement des ensembles de données</b></summary>
  - Fusion de plusieurs ensembles de données sur des critères communs.
  - Développement d'une logique pour trouver et fusionner les données les plus pertinentes (par exemple, données météo dont le timestamp est le plus proche de l'événement).
  - Création de nouvelles variables (par exemple, le "speed to wind ratio").
</details>

<details>
  <summary><b>Modélisation et Analyse Prédictive</b></summary>
  - Utilisation de techniques d'encodage (circulaire, one-hot).
  - Mise en œuvre d'une recherche par grille (Grid Search) pour l'optimisation des hyperparamètres.
  - Intégration d'un système de checkpoint pour l'efficacité des calculs.
  - Évaluation des performances du modèle à l'aide de métriques clés (MAE, MSE, R²).
  - Analyse de l'importance des variables qui influencent les prédictions.
</details>

---

## Diagrammes de flux de données

<p align="center">
<img src="https://github.com/user-attachments/assets/2f210fcd-6d46-4aef-99ed-07d5a9ded3da" width="250" alt="DDF_scraping" title="DDF - Data scraping Metasail" />
<img src="https://github.com/user-attachments/assets/1e773618-b806-47cc-bfed-78eabd4022f9" width="250" alt="DDF_API_Openweathermap" title="DDF - Appel API Openweathermap (météo)" />
<img src="https://github.com/user-attachments/assets/2b526e0d-2757-4970-8eab-8769e2153bfc" width="250" alt="DDF_cleaning" title="DDF - Data cleaning & fusion" />
<img src="https://github.com/user-attachments/assets/19ee963b-d696-42ff-8a70-87a66bbe42e0" width="250" alt="DDF_Processing" title="DDF - Data processing" />
<img src="https://github.com/user-attachments/assets/654d2b7d-ffd4-4c18-9f80-f490cb8f8a5c" width="250" alt="DDF_RFR" title="DDF - Entraînement modèle RFR" />
<img src="https://github.com/user-attachments/assets/2bebdd13-4459-423a-9fd4-74e4672573e8" width="250" alt="DDF-visualisations" title="DDF - Exemple de visualisation" />
</p>

---

### Comment utiliser cet outil ?

1.  Installez l'extension Chrome Single File pour sauvegarder les pages web.
2.  Naviguez sur la page des événements passés de [Metasail](https://www.metasail.fr/#events). Le script a été conçu pour les compétitions d'IQFOIL jeunes mais peut être adapté pour d'autres supports.
3.  Utilisez l'extension SingleFile sur la page de compétition pour la sauvegarder.
4.  Lancez le script de scraping pour récupérer les métadonnées de courses et les données de navigation.
5.  Insérez les coordonnées GPS du lieu de navigation dans le fichier CSV de sortie, puis lancez le script d'appel à l'API météo.
6.  Lancez les scripts de "cleaning", "processing", puis l'entraînement du modèle et la visualisation.

---

### Variables à disposition
<details>
  <summary>Cliquez ici pour voir la liste des variables disponibles</summary>
  
  **Variables d'identification et caractéristiques de la course & du segment :**
  - City, Latitude, Longitude : Informations géographiques détaillées.
  - ID_course : Identifiant unique de la course.
  - Nom de l'événement, Lieu de l'événement, Course, Année, Mois, Jour, Heure du segment.
  - Longueur totale du parcours (m).
  - Numéro de segment, Longueur du segment (m), Cap magnétique (deg), Allure.

  **Variables d'identification de l'athlète :**
  - Nom complet, Numéro de série, Sexe, Catégorie d'âge.

  **Variables de conditions météorologiques :**
  - Orientation vent metasail (deg), Température (°C), Pression (hPa), Humidité (%), Vitesse du vent (kts), Pluie (mm).

  **Variables de performance de l'athlète :**
  - Temps total parcouru (s), Distance totale réelle parcourue (m), Efficacité totale (%), Temps du segment (s).
  - Vitesse moyenne du segment (noeuds), VMC du segment (noeuds), Ratio de performance (Speed to wind ratio).
</details>

---

<details>
  <summary><b>### Comment modifier l'outil ? (développeurs & chercheurs)</b></summary>
  1. Orchestrez les scripts via un fichier Main.
  2. Si vous connaissez les noms des compétitions à scraper, vous pouvez utiliser la CLI (Command Line Interface) Singlefile (https://github.com/gildas-lormeau/single-file-cli) pour automatiser la collecte.
  3. Ajoutez des calculs de métriques dans le script de "data processing".
  4. Modifiez les hyperparamètres dans le script d'entraînement du modèle RFR.
</details>

<details>
  <summary><b>### Difficultés connues (work in progress...)</b></summary>
  - Contradiction entre les relevés de vent Metasail et OpenweatherMap.
  - Les coordonnées GPS doivent être intégrées manuellement car Metasail ne les fournit pas.
  - Le script peut rencontrer des erreurs de catégorisation d'âge car Metasail ne les standardise pas.
  - Vérifiez toujours le support de course (foil, planche) car certaines compétitions mélangent plusieurs disciplines.
</details>

<details>
  <summary><b>### Avertissement et Responsabilité (RGPD)</b></summary>
  Ce script est un outil de "scraping" pour collecter des informations publiquement accessibles sur Metasail, incluant des données personnelles. L'utilisation du script se fait sous l'entière responsabilité de l'utilisateur. En tant que responsable du traitement des données, vous êtes soumis aux obligations du RGPD, notamment le respect d'une base légale, de la finalité, des droits des personnes concernées, la minimisation et la sécurisation des données.
</details>

---

## Visualisation interactive 📈

Explorez la relation entre la vitesse du vent, les allures de navigation et la performance des athlètes grâce à notre graphique interactif.

<p align="center">
  <a href="https://clem-cbt.github.io/Projet_machine_learning_performance_voile/Visualisations/visualisation_dynamique_vitesse_vent_et_allure_esthetique.html" target="_blank">
    <img src="https://via.placeholder.com/600x300.png?text=Cliquez+pour+voir+la+visualisation+interactive" alt="Bouton de visualisation interactive" style="width: 100%; max-width: 600px;">
  </a>
</p>
