# Modélisation de la performance en IQFoil jeunes à partir de données de navigation et de conditions météo.

## ETL fonctionnel basé sur le webscraping Metasail et Openweathermaps aboutissant sur une régression Random Forest pour explorer les enjeux de course en IQFOIL.
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
  <summary> <b> Intégration et enrichissement des ensembles de données </b> </summary>
  
  - Fusion de plusieurs ensembles de données basés sur des critères communs (association de données météorologiques aux données de course).
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
<img width="1270" height="3840" alt="DDF_scraping_metasail" src="https://github.com/user-attachments/assets/834c7766-3ac3-459f-8b01-cdc645fa764f" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img width="1405" height="3839" alt="DDF_API_Openweathermap" src="https://github.com/user-attachments/assets/184b0eba-06f0-4e17-9d5f-4f8bcd33345c" />
</td>
<img width="930" height="3840" alt="DDF_cleaning" src="https://github.com/user-attachments/assets/0aed3364-666f-4631-8569-575ca7ed6c14" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img width="1439" height="3840" alt="DDF_Processing" src="https://github.com/user-attachments/assets/a6b5b5b8-b321-46f8-b570-1982fa0d0138" />
</td>
<td style="text-align:center; padding:0; border:none;">
<img width="633" height="3839" alt="DDF_RFR" src="https://github.com/user-attachments/assets/96280402-5472-4e78-b287-17240f163a7c" />
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
- VMC du segment (noeuds) : Vitesse de progression vers la bouée (Velocity Made Course, VMC) pour le segment, en nœuds.
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
  <a href="https://remicorniere.github.io/test_pages/">
    <img src="https://via.placeholder.com/600x300.png?text=Cliquez+ici+pour+la+visualisation+interactive" alt="Visualisation interactive">
  </a>
</div>

# Entraînement de modèle (Random Forest Regression)

💡 Objectif du Modèle

Ce modèle de régression est entraîné pour prédire la Velocity Made Course (VMC) du segment (noeuds), une métrique qui représente la vitesse de progression vers la bouée.


## 1. Variables d'entrée (Features)


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

## 2. Optimisation des hyperparamètres (Grid Search)

Afin de garantir la robustesse et la performance du modèle, j'ai mis en œuvre une approche de recherche par grille (Grid Search). Cette méthode a permis de tester de manière exhaustive différentes combinaisons d'hyperparamètres pour le Random Forest Regressor et d'identifier la configuration optimale. Une validation croisée à 3 plis (3-fold cross-validation) a été utilisée pour évaluer chaque combinaison d'hyperparamètres du param_grid sur l'ensemble de données d'entraînement.

Les paramètres que j'ai optimisés sont les suivants :

    n_estimators : Le nombre d'arbres dans la forêt (testé : 100, 200).

    max_depth : La profondeur maximale de chaque arbre (testée : 10, 20, 30).

    min_samples_split : Le nombre minimum d'échantillons requis pour diviser un nœud interne (testé : 2, 5, 10).

    min_samples_leaf : Le nombre minimum d'échantillons requis pour former un nœud feuille (testé : 1, 2, 4, 8).

    max_features : Le nombre de features à considérer à chaque division ('sqrt', 'log2', 1.0).

    bootstrap : La méthode d'échantillonnage (True, False).

## 3. Résultats  de la performance du modèle

**Meilleurs hyperparamètres trouvés :** 
{'bootstrap': True, 'max_depth': 20, 'max_features': 'sqrt', 'min_samples_leaf': 2, 'min_samples_split': 10, 'n_estimators': 100}
 
✅  **Métriques d'évaluation du meilleur modèle :**

Erreur Absolue Moyenne (MAE) : 2.01

Erreur Quadratique Moyenne (MSE) : 8.28

Coefficient de Détermination (R²) : 0.68

Les prédictions du modèle s'écartent des valeurs réelles de VMC d'environ 2.01 noeuds, ce qui est très satisfaisant notamment compte tenu de la simplicité des hyperparamètres du modèle. La MSE permet de calculer la RMSE, qui indique que les prédictions du modèle s'écartent des valeurs réelles d'environ 2.88 nœuds en moyenne. La valeur de la RMSE étant légèrement supérieure à celle de la MAE, cela indique qu'il y a quelques erreurs plus significatives qui tirent la moyenne quadratique vers le haut. Possiblement des faits de course. Enfin, le modèle explique 68 % de la variance des données ce qui est performant à très performant. Il pourrait cependant être amélioré avec l'ajout de variables complémentaires telles que les réglages du Foil, les performances passées des coureurs ou encore la stratégie de course. 

## **Analyse du Graphique**
<img width="1200" height="800" alt="Figure_VMC_prediction" src="https://github.com/user-attachments/assets/f938a67e-b291-4fb1-b335-ea3f843dff51" />

Ce diagramme à barres horizontales illustre l'**importance relative** de chaque variable (ou "feature") utilisée par le modèle pour effectuer ses prédictions.

* **Axe Y (Variables)** : Liste toutes les variables prises en compte par le modèle, des plus importantes (en haut) aux moins importantes (en bas).
* **Axe X (Importance - score)** : Représente le score d'importance. 

En résumé, ce graphique vous montre le **classement des facteurs les plus déterminants** pour prédire la performance (VMC) d'un segment de navigation.

**Importance des variables pour la prédiction de 'VMC du segment (noeuds):**

Allure_Vent debout                 0.242579

Longueur totale du parcours (m)    0.183537

Classement entrée de segment       0.101078

Allure_Reaching                    0.096722

Humidity (%)                       0.078402

Wind Speed (kts)                   0.073492

Temperature (°C)                   0.061241

Pressure (hPa)                     0.039830

Allure_Allures remontantes         0.038490

Allure_Allures portantes           0.034117

Allure_Vent arrière                0.019631

Sexe_Men                           0.018730

Sexe_Women                         0.012151


---

### **Interprétation des variables principales**

Les variables en haut du graphique sont celles que le modèle a jugées les plus décisives pour prédire la VMC (Velocity Made Course).

1.  **Allure_Vent debout** : C'est, de loin, la variable la plus influente (score ≈ 0.24).
    * **Signification** : Le fait de naviguer au près serré (contre le vent) est le facteur le plus déterminant pour la VMC. C'est une allure où la performance est la plus difficile à atteindre et la plus variable d'un concurrent à l'autre.
    * **Hypothèse** : Une VMC élevée au vent debout est un marqueur de grande technicité et de bon réglage. Le modèle a donc appris que savoir si un segment est au "Vent debout" est une information cruciale pour prédire la vitesse de progression vers la bouée.

2.  **Longueur totale du parcours (m)** : Cette variable a une importance très élevée (score ≈ 0.18).
    * **Signification** : La distance totale de la course influence la VMC sur un segment donné.
    * **Hypothèse** : Cela pourrait s'expliquer par la gestion de l'effort et la stratégie. Sur un parcours long, les navigateurs pourraient gérer leur rythme différemment que sur un sprint. La fatigue ou la stratégie à long terme peut donc impacter la VMC d'un segment intermédiaire.

3.  **Classement entrée de segment** : Ce facteur reste un prédicteur très fort (score ≈ 0.11).
    * **Signification** : Comme dans l'analyse précédente, la position d'un bateau au début d'un segment est un excellent indicateur de sa performance future sur ce même segment.
    * **Hypothèse** : Les leaders naviguent souvent dans un vent "propre" (non perturbé par les autres bateaux) et ont démontré une vitesse ou une tactique supérieure, qu'ils tendent à maintenir. De plus, les leaders auront certainement une VMC légèrement supérieure dûe à leur niveau de navigation général et sur la course en particulier. 

4.  **Allure_Reaching** : Le reaching (vent de travers) est également très important (score ≈ 0.10).
    * **Signification** : Le reaching est généralement l'allure la plus rapide pour un voilier.
    * **Hypothèse** : Sans surprise, le modèle est affecté par l'angle entre l'axe du vent et celui de la bouée à atteindre. Il identifie cette allure comme un indicateur clé d'une VMC potentiellement élevée. Sa présence dans un segment est un fort signal positif pour la prédiction.

5.  **Variables Météorologiques (Humidity, Wind Speed, Temperature, Pressure)** : Ce groupe de variables a une importance modérée mais significative (scores entre 0.04 et 0.08).
    * **Signification** : Les conditions atmosphériques de base (humidité, vitesse du vent, température, pression) influencent directement la puissance que le support peut tirer du vent.
    * **Hypothèse** : La vitesse du vent (`Wind Speed`) est le moteur, tandis que la température, l'humidité et la pression (`Temperature`, `Humidity`, `Pressure`) affectent la densité de l'air, et donc l'efficacité des voiles. Le modèle les utilise conjointement pour affiner sa prédiction de la performance brute.

---

### **Analyse des Variables Moins Influentes**

Ces variables, situées en bas du graphique, ont un impact plus faible sur les prédictions du modèle mais ne sont pas nécessairement inutiles.

* **Autres Allures (remontantes, portantes, Vent arrière)** : Ces allures ont une importance moindre que le "Vent debout" ou le "Reaching".
    * **Hypothèse** : Elles représentent peut-être des conditions de performance moins extrêmes. Leur impact sur la VMC est moins discriminant que celui des allures où la technique (vent debout) ou la vitesse pure (reaching) sont primordiales.

* **Sexe (Men/Women)** : Ces deux variables ont la plus faible importance.
    * **Signification** : Une fois que toutes les autres variables (allure, classement, météo) sont prises en compte, le genre du navigateur n'est pas un facteur prédictif de la VMC selon ce modèle. La performance s'explique par les conditions et les compétences techniques, pas par le sexe.

---

### **4. Synthèse et recommandations**

#### **Synthèse**

L'analyse de ce modèle révèle que la prédiction de la VMC repose sur une hiérarchie claire de facteurs. La **nature de l'allure**, en particulier les allures extrêmes comme le **vent debout** (très technique) et le **reaching** (très rapide), est le facteur le plus déterminant. Le **contexte de la course** (`Longueur totale du parcours`) et la **dynamique de performance** (`Classement entrée de segment`) sont également des prédicteurs de premier plan. Enfin, les **conditions météorologiques** forment un socle d'informations de fond essentiel pour affiner la prédiction. Les facteurs démographiques, quant à eux, semblent moins primordiaux dans la prédiction.

**Conclusion et Recommandations**

Prédire la VMC d'un coureur peut s'avérer utile pour anticiper les contraintes mécaniques s'exerçant sur son matériel, ainsi que les contraintes biomécaniques s'exerçant sur lui. Ainsi, sur le long terme, l'anticipation de cette métrique permettrait d'optimiser les réglages et la stratégie de course en fonction des variables énoncées, mais aussi en fonction des sensations du coureur avant la course.  

* **Recommandation Stratégique :** La VMC a une corrélation linéaire avec le classement de fin de segment. Ainsi les variables impactant cette métrique seraient à considérer comme prioritaires pour l'entrainement. D'après les résultats du modèle, l'entraînement et la stratégie devraient se concentrer en priorité sur l'amélioration de la performance dans les allures les plus techniques (vent debout) et l'exploitation maximale des allures rapides (reaching) plutot que les allures intermédiaires. 
* **Recommandation pour le Modèle :** Le modèle semble robuste et cohérent avec l'expertise du domaine. La forte importance de la `Longueur totale du parcours` pourrait faire l'objet d'une analyse plus approfondie pour comprendre les effets de la fatigue ou de la stratégie à long terme.
