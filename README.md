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

## Illustrations de l'exploration de données 


### Visualisation interactive 📈

Explorez la relation entre la vitesse du vent, les allures de navigation et la performance des athlètes grâce à notre graphique interactif.

<div align="center">
  <a href="https://raw.githubusercontent.com/Clem-ctrl/Projet_machine_learning_performance_voile/main/Visualisations/visualisation_dynamique_vitesse_vent_et_allure_esthetique.html" download>
    <img src="https://via.placeholder.com/600x300.png?text=Bouton+de+visualisation+interactive" alt="Bouton de visualisation interactive">
  </a>
</div>


### Entraînement de modèle (Random Forest Regression)

💡 Objectif du Modèle

Ce modèle de régression est entraîné pour prédire la Velocity Made Course (VMC) du segment (noeuds). Il s'agit de la Vitesse Maximale au Cap, une métrique qui représente la vitesse de progression vers la bouée.

Absolument. Voici une version plus professionnelle et structurée, conçue pour une présentation à un recruteur, en utilisant un langage plus formel et technique.

Modélisation de la Vitesse Maximale au Cap (VMC) avec un Random Forest Regressor


1. Variables d'entrée (Features)


    Variables quantitatives :

        Longueur totale du parcours (en mètres)

        Température (en °C)

        Pression (en hPa)

        Humidité (en %)

        Vitesse du vent (en nœuds)

        Classement entrée de segment

    Variables qualitatives :

        Allure

        Sexe

Ces variables qualitatives ont été encodées numériquement via une technique de One-Hot Encoding afin d'être intégrées au modèle de machine learning.

2. Optimisation des hyperparamètres (Grid Search)

Afin de garantir la robustesse et la performance du modèle, j'ai mis en œuvre une approche de recherche par grille (Grid Search). Cette méthode a permis de tester de manière exhaustive différentes combinaisons d'hyperparamètres pour le Random Forest Regressor et d'identifier la configuration optimale. Les paramètres que j'ai optimisés sont les suivants :

    n_estimators : Le nombre d'arbres dans la forêt (testé : 100, 200).

    max_depth : La profondeur maximale de chaque arbre (testée : 10, 20, 30).

    min_samples_split : Le nombre minimum d'échantillons requis pour diviser un nœud interne (testé : 2, 5, 10).

    min_samples_leaf : Le nombre minimum d'échantillons requis pour former un nœud feuille (testé : 1, 2, 4, 8).

    max_features : Le nombre de features à considérer à chaque division ('sqrt', 'log2', 1.0).

    bootstrap : La méthode d'échantillonnage (True, False).

3. Évaluation de la performance du modèle

Après l'entraînement, la performance du modèle final a été rigoureusement évaluée sur un jeu de données de test indépendant. Les métriques de performance utilisées sont :

    Mean Absolute Error (MAE)

    Mean Squared Error (MSE)

    Coefficient de Détermination (R²)

L'analyse de l'importance des variables, une des forces des algorithmes de type Random Forest, a également été réalisée pour identifier les facteurs les plus influents dans la prédiction de la VMC. 


## **Analyse Globale du Graphique**

Ce diagramme à barres horizontales illustre l'**importance relative** de chaque variable (ou "feature") utilisée par le modèle pour effectuer ses prédictions.

* **Axe Y (Variables)** : Liste toutes les variables prises en compte par le modèle, des plus importantes (en haut) aux moins importantes (en bas).
* **Axe X (Importance - score)** : Représente le score d'importance. 

En résumé, ce graphique vous montre le **classement des facteurs les plus déterminants** pour prédire la performance (VMC) d'un segment de navigation.

---

## **Interprétation Détaillée des Variables Principales**

Les variables en haut du graphique sont les plus prédictives.

1.  **Classement entrée de segment** : C'est de loin la variable la plus importante, avec un score d'environ 0.55.
    * **Signification** : La position d'un concurrent au début d'un segment est le meilleur prédicteur de sa VMC sur ce même segment.
    * **Hypothèse** : Les concurrents déjà bien classés ont probablement une meilleure vitesse, une meilleure tactique, ou naviguent dans des conditions de vent plus favorables (air "propre"), ce qui leur permet de maintenir une VMC élevée.

2.  **Wind Speed (kts)** : La vitesse du vent est le deuxième facteur le plus influent (score ≈ 0.17).
    * **Signification** : Cela confirme une évidence en voile : la vitesse du vent est un moteur fondamental de la performance.
    * **Hypothèse** : Une augmentation de la vitesse du vent conduit généralement à une augmentation de la VMC, jusqu'à un certain seuil où le bateau devient plus difficile à contrôler.

3.  **Temperature (°C)** et **Humidity (%)** : Ces deux variables météorologiques ont une importance notable et similaire (score ≈ 0.10).
    * **Signification** : Elles influencent la densité de l'air. Un air plus dense (plus froid et plus sec) exerce une poussée plus forte sur les voiles, ce qui peut améliorer la performance.
    * **Hypothèse** : Le modèle a appris que ces variations subtiles de la densité de l'air ont un impact quantifiable sur la VMC.

4.  **Orientation vent metasail (sin/cos)** : Ces deux composantes, qui représentent l'angle du vent, ont une importance modérée.
    * **Signification** : La direction du vent est cruciale pour déterminer l'allure du bateau et donc sa VMC potentielle. Le modèle utilise ces deux variables pour reconstruire l'angle du vent.

---

## **Analyse des Variables Moins Influentes**

Les variables situées en bas du graphique ont un impact très faible sur les prédictions du modèle.

* **Les Allures (Reaching, Portantes, etc.)** : Il est surprenant que les allures spécifiques aient une si faible importance.
    * **Hypothèse possible** : L'information de l'allure pourrait être déjà implicitement contenue dans la combinaison de la vitesse du vent (`Wind Speed`) et de son orientation (`Orientation vent metasail`). Le modèle pourrait donc considérer ces variables comme redondantes.

* **Sexe (Men/Women)** et **Catégorie d'âge (U17/U19)** : Ces caractéristiques démographiques semblent avoir une influence quasi nulle selon le modèle.
    * **Signification** : Pour ce jeu de données, les performances (VMC) ne semblent pas dépendre du genre ou de la catégorie d'âge des navigateurs, une fois que les autres facteurs (classement, météo) sont pris en compte.

---

## **Synthèse et 'Interprétation**

### **Template de Rapport d'Analyse d'Importance des Variables**

**Titre :** Analyse de l'Importance des Variables pour la Prédiction de la VMC

**1. Introduction**
Ce document présente l'analyse de l'importance des variables issues d'un modèle de régression Random Forest. L'objectif du modèle est de prédire la `VMC du segment (noeuds)`. Le graphique ci-dessous classe les variables en fonction de leur contribution à la performance prédictive du modèle.

**2. Analyse des Facteurs Prédictifs Majeurs**
Le modèle identifie clairement deux catégories principales de facteurs influents : la performance relative et les conditions météorologiques.

* **Facteur de Performance Dominant :**
    * La variable **`Classement entrée de segment`** est, de manière écrasante, la plus influente (score : [insérer le score, ex: ~0.55]). Cela indique que la performance passée (le classement) est le meilleur indicateur de la performance immédiate. Les leaders tendent à maintenir leur avantage.

* **Facteurs Météorologiques Clés :**
    * La **`Wind Speed (kts)`** (score : [~0.17]) est le deuxième facteur le plus important, ce qui est cohérent avec les principes fondamentaux de la navigation à voile.
    * La **`Temperature (°C)`** et l'**`Humidity (%)`** (scores : [~0.10]) jouent également un rôle significatif, probablement en influençant la densité de l'air et donc l'efficacité de la propulsion vélique.

**3. Analyse des Facteurs d'Influence Secondaire**
Certaines variables, bien que moins critiques, contribuent tout de même au modèle :

* L'**`Orientation vent metasail`** (via ses composantes sinus et cosinus) est modérément importante, soulignant le rôle de l'angle du vent dans la détermination de la VMC.

**4. Variables à Faible Impact**
Il est notable que plusieurs variables ont une importance prédictive très faible dans ce modèle :

* Les différentes **allures spécifiques** (`Allure_Reaching`, `Allure_Portantes`, etc.) ont un score quasi nul. Cela suggère que leur information est redondante par rapport à d'autres variables plus importantes comme l'angle et la vitesse du vent.
* Les caractéristiques démographiques comme le **`Sexe`** et la **`Catégorie d'âge`** n'apparaissent pas comme des différenciateurs de performance significatifs dans ce contexte.

**5. Conclusion et Recommandations**
L'analyse révèle que pour prédire la VMC, le modèle s'appuie principalement sur le **classement actuel du concurrent et les conditions météorologiques** (vitesse du vent, température, humidité).

* **Recommandation Opérationnelle :** Pour améliorer la performance, l'accent doit être mis sur les stratégies permettant de gagner et de conserver un bon classement (tactique, départs).
* **Recommandation pour le Modèle :** Étant donné la faible importance de certaines variables, une simplification du modèle en retirant les caractéristiques les moins pertinentes pourrait être envisagée pour réduire la complexité et potentiellement améliorer la généralisation, bien que les modèles de type "forêt" soient robustes à ce genre de situation.


