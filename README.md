# Modélisation de la performance en IQFoil jeunes à partir de données de navigation et de conditions météo.

## ETL fonctionnel basé sur le webscraping Metasail et Openweathermaps aboutissant sur une régression Random Forest explorer les enjeux de course en IQFOIL.
Ce projet est un exemple d'exploration statistique mobilisant des données de navigation et de conditions météorologiques publiques et en libre accès. 

**Plusieurs étapes jalonnent ce projet :**

<details>
  <summary> <b> Automatisation de la collecte de données (web scraping) </b> </summary>
  
  - Extraction des informations structurées à partir de pages web, en utilisant un outil comme Selenium pour interagir avec le site web et récupérer le contenu.
  - Analyse du contenu récupéré, qu'il soit au format XML ou autre, pour en extraire les informations pertinentes et les organiser dans un tableau de données (DataFrame).
  - Mise en place d'un flux de travail itératif pour traiter des centaines d'URLs et gestion des données déjà collectées afin d'éviter la redondance.
  - Récupération de données météo via API (OpenWeatherMaps).
</details>

<details>
  <summary> <b> Intégration et enrichissement les ensembles de données </b> </summary>
  
  - Fusion plusieurs ensembles de données basés sur des critères communs (association de données météorologiques aux données de course).
  - Développement d'une logique pour trouver et fusion les données les plus pertinentes (par exemple, trouver les données météo dont le timestamp est le plus proche de l'événement de course).
  - Création de nouvelles variables ou métriques dérivées à partir des données existantes (par exemple, le speed to wind ratio ou l'angle Vent-Cap de la bouée).
</details>

<details>
  <summary> <b> Modélisation et Analyse Prédictive </b> </summary>
  
  - Utilisation de techniques d'encodage spécifiques (circulaire, one-hot) pour transformer les données brutes en variables exploitables.
  - Mise en œuvre d'une recherche par grille (Grid Search) pour l'optimisation des hyperparamètres.
  - Intégration d'un système de checkpoint pour l'efficacité des calculs.
  - Évaluation des performances du modèle à l'aide de métriques clés (MAE, MSE, R²).
  - Analyse de l'importance des variables qui influencent les prédictions
</details>

## Diagrammes de flux de données 
<br>
<br><table style="width:100%; border:none;">
<thead>
<tr style="border:none;">
<th style="text-align:center; padding:10px; border:none;">DDF - Data scraping Metasail</th>
<th style="text-align:center; padding:10px; border:none;">DDF - Appel API Openweathermap (météo)</th>
<th style="text-align:center; padding:10px; border:none;">DDF - Data cleaning & fusion</th>
<th style="text-align:center; padding:10px; border:none;">DDF - Data processing</th>
<th style="text-align:center; padding:10px; border:none;">DDF - Entraînement modèle RFR</th>
<th style="text-align:center; padding:10px; border:none;">DDF - Exemple de visualisation</th>
</tr>
</thead>
<tbody>
<tr style="border:none;">
<td style="text-align:center; padding:0; border:none;">
<img src="https://github.com/user-attachments/assets/2f210fcd-6d46-4aef-99ed-07d5a9ded3da" width="250" alt="DDF_scraping" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img src="https://github.com/user-attachments/assets/1e773618-b806-47cc-bfed-78eabd4022f9" width="250" alt="DDF_API_Openweathermap" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img src="https://github.com/user-attachments/assets/2b526e0d-2757-4970-8eab-8769e2153bfc" width="250" alt="DDF_cleaning" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img src="https://github.com/user-attachments/assets/19ee963b-d696-42ff-8a70-87a66bbe42e0" width="250" alt="DDF_Processing" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img src="https://github.com/user-attachments/assets/654d2b7d-ffd4-4c18-9f80-f490cb8f8a5c" width="250" alt="DDF_RFR" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img src="https://github.com/user-attachments/assets/2bebdd13-4459-423a-9fd4-74e4672573e8" width="250" alt="DDF-visualisations" />
</td>
</tr>
</tbody>
</table>

### Comment utiliser cet outil ?

1. Installer l'extension Chrome Single File (https://www.getsinglefile.com/) qui permet d'enregistrer le DOM final d'une page web, ici des compétitions Metasail à analyser. 

2. Naviguer sur la page des évènements passés du site Metasail (https://www.metasail.fr/#events - Régates - Evénements passés) pour identifer la ou les compétitions à analyser.
Ce script a été écrit pour les compétitions d'IQFOIL jeunes, mais peut être employé pour tout autre support et pour les courses Senior. 

3. Sélectionner la compétition à analyser, utiliser l'extension SingeFile sur la page de compétition (cliquez sur l'icone SingleFile pour sauvegarder la page).

4. Vous pouvez maintenant Run le script de scraping afin qu'il récupère les métadonnées de courses, d'évènement(s), et les données de navigation.
   
6. Sur le CSV de sortie, insérer les coordonnées GPS du lieu de navigation dans la colonne dédiée puis lancez le script d'appel à l'API météo.

7. Lancez le script de cleaning, puis celui de processing et enfin celui d'entraînement du modèle et de visualisation.

### Variables à disposition
<details>
  <summary>Cliquez ici pour voir la liste des variables disponibles</summary>
  
**Variables d'identification et caractéristiques de la course & du segment** :
- City, Latitude, Longitude : Informations géographiques détaillées.
- ID_course : Identifiant unique de la course.
- Nom de l'événement : Nom officiel de la compétition.
- Lieu de l'événement : Coordonnées géographiques (latitude, longitude) du lieu de la course.
- Course : Nom ou numéro spécifique de la course au sein de l'événement.
- Année, Mois, Jour : Composantes de la date de la course.
- Heure du segment : Heure moyenne du segment.
- Longueur totale du parcours (m) : Longueur théorique totale du parcours en mètres.
  
- Numéro de segment : Numéro d'un segment de course spécifique.
- Longueur du segment (m) : Longueur théorique du segment en mètres.
- Cap magnétique (deg) : Axe de la bouée de la bouée suivante en degrés pendant le segment.
- Heure du segment_seconds : Temps du segment en secondes (variante de "Temps du segment").
- Allure : Vent / axe de la bouée suivante (e.g., "Vent debout").

**Variables d'identification de l'athlète** : 
- Nom complet : Nom complet de l'athlète.
- Numéro de série : Identifiant unique de l'athlète pour la compétition.
- Sexe : Sexe de l'athlète (e.g., Women).
- Catégorie d'âge : Catégorie d'âge de l'athlète (e.g., U19).

**Variables de conditions météorologiques** : 
- Orientation vent metasail : Direction du vent en degrés pour la course selon Metasail.
- Temperature (°C) : Température ambiante en degrés Celsius.
- Pressure (hPa) : Pression atmosphérique en hectopascals.
- Humidity (%) : Humidité de l'air en pourcentage.
- Wind Speed (kts) : Vitesse du vent en nœuds.
- Rain (mm) : Quantité de pluie en millimètres.



**Variables de performance de l'athlète** : 
- Temps total parcouru (s) : Temps total mis par l'athlète pour compléter la course, en secondes.
- Distance totale réelle parcourue (m) : Distance réelle parcourue par l'athlète en mètres.
- Différence parcours théorique/réel : Différence en mètres entre la distance théorique et la distance réelle sur le parcours.
- Efficacité totale (Distance réelle/idéale) (%) : Ratio de la distance réelle sur la distance idéale, exprimé en pourcentage.
 
- Temps du segment (s) : Durée du segment de course en secondes.
- Distance réelle parcourue segment (m) : Distance parcourue pendant ce segment en mètres.
- Efficacité du segment (%) : Efficacité pour ce segment de course (distance théorique / distance réelle x 100).
- Début du segment (timestamp) : Horodatage du début du segment.
- Fin du segment (timestamp) : Horodatage de la fin du segment.
-  Bâbord (%) : Pourcentage du temps passé sur le côté bâbord.
- Tribord (%) : Pourcentage du temps passé sur le côté tribord.

- Classement entrée de segment : Rang de l'athlète à l'entrée du segment.
- Classement fin de segment : Rang de l'athlète à la fin du segment.
- Classement sur le segment : Classement de l'athlète sur le segment.
- Différence segment théorique/réel : Différence en mètres entre la distance théorique et la distance réelle sur un segment.

- Vitesse moyenne du segment (noeuds) : Vitesse moyenne en nœuds pendant le segment.
- VMC du segment (noeuds) : Vitesse en direction du vent (Velocity Made Good, VMG) pour le segment, en nœuds.
- VMC moyenne du parcours (noeuds) : Vitesse moyenne en direction du vent pour l'ensemble du parcours.
- Vitesse moyenne du parcours (noeuds) : Vitesse moyenne pour l'ensemble du parcours en nœuds.
- Vitesse maximale (noeuds) : Vitesse maximale atteinte en nœuds.
- VMG maximale : Vitesse en direction du vent maximale atteinte.
- VMC maximale : Vitesse en direction du vent maximale atteinte.
- Ratio de performance : Speed to wind ratio.
</details>

<details>
  <summary> <b> ### Comment modifier l'outil ? (développeurs & chercheurs) </b> </summary>

1. Une fois les éléments des scripts personnalisés, orchestrez les Runs de scripts via un fichier Main.
   
3. Si l'on connait les noms des compétitions que l'on veut scraper sur Metasail (ex : toutes les dernières éditions de "ILCA Senior Europeans"), il est possible de contourner la sélection manuelle SingleFile par l'emploi d'une CLI (https://github.com/gildas-lormeau/single-file-cli) associée à une fonction d'identification d'expressions régulières. Si au contraire, l'objectif est de scrape l'ensemble des compétitions indépendamment du support de course, la CLI Singlefile est aussi recommandée. 

4. Ajoutez des calculs de métriques de le script data processing

5. Modifiez les hyperparamètres dans le script d'entraînement du modèle RFR
</details>

<details>
  <summary> <b> ### Difficultés connues (work in progress...) </b> </summary>

1. Il y a parfois contradiction entre les relevés de conditions météorologiques Metasail et OpenweatherMap, certainement dûe à la localisation des capteurs employés par chaque site. 
Metasail ne fournit que l'orientation de vent en libre accès. Le projet se base donc sur l'orientation de vent fournie par Metasail et la force de vent fournie par OpenWeatherMaps. 

2. Les coordonnées GPS sont à intégrer manuellement, car Metasail ne fournit pas en libre accès la localisation des courses. Pour obtenir des coordonnées GPS précises, il est conseillé de passer par GoogleMaps (clic droit pour obtenir les coordonnées GPS).

3. Metasail ne présente pas les catégories d'âge de manière standardisée, ainsi, si le script est optimisé pour récupérer les données U19 et U17, des erreurs de catégorisation peuvent se produire pour les catégories Senior et plus jeunes (ex: U13).

4. Pour les mêmes raisons, si l'on veut étudier un support spécifique toujours vérifier le support utilisé lors de la course car certaines compétitions mêlent plusieurs supports en fonction des courses.
</details>
  
<details>  
  <summary> <b> ### Avertissement et Responsabilité (RGPD) </b> </summary>

Ce script est un outil d'extraction de données ("scraping") conçu pour collecter des informations publiquement accessibles sur la plateforme Metasail. Il est important de comprendre que ces données, même si elles sont en libre accès, peuvent inclure des informations à caractère personnel (nom, classement, performance, etc.).

L'utilisation de ce script se fait sous l'entière responsabilité de l'utilisateur.

En utilisant ce script, vous agissez en tant que responsable du traitement des données collectées et, à ce titre, vous êtes personnellement soumis aux obligations du Règlement Général sur la Protection des Données (RGPD).

Pour être en conformité, vous devez notamment :
- Déterminer une base légale : Assurez-vous d'avoir une raison légitime et légale de collecter ces données (par exemple, un intérêt légitime, à des fins de recherche ou d'analyse personnelle).
- Respecter la finalité des données : Les données doivent être utilisées uniquement pour la finalité que vous avez définie. Vous ne pouvez pas les réutiliser à d'autres fins (par exemple, à des fins commerciales) sans en informer les personnes concernées et obtenir leur consentement si nécessaire.
- Respecter les droits des personnes : Vous êtes dans l'obligation de respecter les droits des personnes dont vous collectez les données (droit d'accès, de rectification, d'opposition, à l'effacement, etc.). Si une personne vous contacte pour exercer ses droits, vous devez y répondre dans les délais légaux.
- Minimiser les données : Ne collectez que les données strictement nécessaires à votre projet. N'extrayez pas plus d'informations que ce dont vous avez réellement besoin.
- Sécuriser les données : Vous devez prendre des mesures techniques et organisationnelles pour garantir la sécurité des données collectées et éviter toute fuite ou utilisation abusive.

</details>  

### Visualisation interactive 📈

Explorez la relation entre la vitesse du vent, les allures de navigation et la performance des athlètes grâce à notre graphique interactif.
### Visualisation interactive 📈

Explorez la relation entre la vitesse du vent, les allures de navigation et la performance des athlètes grâce à notre graphique interactif.

<br>

<div align="center">
  <a href="[https://raw.githubusercontent.com/Clem-ctrl/Projet_machine_learning_performance_voile/main/Visualisations/visualisation_dynamique_vitesse_vent_et_allure_esthetique.html](https://raw.githubusercontent.com/Clem-ctrl/Projet_machine_learning_performance_voile/9b4745e95d83f5b9457ba3401d0e0be0a19f653d/Visualisations/visualisation_dynamique_vitesse_vent_et_allure_esthetique.html)" target="_blank">
    <img src="https://via.placeholder.com/600x300.png?text=Cliquez+ici+pour+la+visualisation+interactive" alt="Bouton de visualisation interactive">
  </a>
  <br>
  <br>
  [Ouvrir la visualisation interactive](https://raw.githubusercontent.com/Clem-ctrl/Projet_machine_learning_performance_voile/main/Visualisations/visualisation_dynamique_vitesse_vent_et_allure_esthetique.html)
</div>
