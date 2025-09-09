import pandas as pd
import numpy as np
import warnings
from pandas.errors import SettingWithCopyWarning
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt
import pickle
import os
import time
from datetime import datetime

# --- 1. Chemin du fichier et gestion des avertissements ---
file_path = r"C:\Projects\Projet_machine_learning_performance_voile\Metasail_Statistics_unified_processed.xlsx"
output_path = r"C:\Projects\Projet_machine_learning_performance_voile\Metasail_random_forest.xlsx"
warnings.filterwarnings('ignore', category=SettingWithCopyWarning)

print("✅ Étape 1 : Chargement et préparation des données...\n")

# --- 2. Chargement et vérification des données ---
try:
    df_metasail = pd.read_excel(file_path)
    print("✅ Fichier Excel chargé avec succès.")
except FileNotFoundError:
    print(f"❌ Erreur : Le fichier n'a pas été trouvé. Veuillez vérifier le chemin d'accès : {file_path}")
    exit()

print("🔍 Noms des colonnes dans le fichier Excel :")
print(df_metasail.columns.tolist())

# Définition des colonnes
target_col = 'Classement sur le segment'
feature_cols = [
    'Efficacité du segment (%)', 'Sexe', "Catégorie d'âge",
    'Wind Speed (kts)', 'Orientation vent metasail',
    'Vitesse moyenne du segment (noeuds)', 'VMC du segment (noeuds)',
    'Allure', 'Wind to speed ratio',
    'Temperature (°C)', 'Pressure (hPa)', 'Humidity (%)', 'Rain (mm)',
    'Classement entrée de segment', 'Classement fin de segment'
]

# Vérification de l'existence des colonnes
colonnes_existantes = [col for col in feature_cols + [target_col] if col in df_metasail.columns]
colonnes_manquantes = [col for col in feature_cols + [target_col] if col not in df_metasail.columns]

if colonnes_manquantes:
    print(
        f"\n❌ Erreur : Les colonnes suivantes sont manquantes et le script ne peut pas continuer : {colonnes_manquantes}")
    exit()

data = df_metasail[colonnes_existantes].copy()

# Remplacement des virgules par des points et conversion en numérique
cols_to_convert = [
    'Wind Speed (kts)', 'Vitesse moyenne du segment (noeuds)',
    'VMC du segment (noeuds)', 'Wind to speed ratio', 'Temperature (°C)',
    'Pressure (hPa)', 'Humidity (%)', 'Rain (mm)', 'Efficacité du segment (%)',
    'Classement entrée de segment', 'Classement fin de segment', 'Classement sur le segment'
]
cols_to_convert_existantes = [col for col in cols_to_convert if col in data.columns]

for col in cols_to_convert_existantes:
    data[col] = data[col].astype(str).str.replace(',', '.', regex=False).astype(float)

print("✅ Préparation des données terminée.")

# --- 3. Nettoyage et encodage des données ---
print("⚙️ Étape 3 : Nettoyage et encodage des données...\n")

# Conservation des données U17 et U19
if "Catégorie d'âge" in data.columns:
    data = data[data['Catégorie d\'âge'].isin(['U17', 'U19'])]


# Encodage circulaire pour l'orientation du vent
def circular_encoding(df, col):
    """Effectue un encodage circulaire pour une colonne d'angle."""
    if col in df.columns:
        angle_rad = np.radians(df[col])
        df[f'{col}_sin'] = np.sin(angle_rad)
        df[f'{col}_cos'] = np.cos(angle_rad)
        df.drop([col], axis=1, inplace=True)
    return df


data = circular_encoding(data, 'Orientation vent metasail')

# Encodage des variables catégorielles (One-Hot Encoding)
categorical_cols = ['Sexe', 'Catégorie d\'âge', 'Allure']
categorical_cols_existantes = [col for col in categorical_cols if col in data.columns]
data = pd.get_dummies(data, columns=categorical_cols_existantes, dtype=int)

# Suppression des valeurs manquantes
data.dropna(inplace=True)

print("✅ Données nettoyées et encodées avec succès.")
print(f"Nombre total de lignes après nettoyage : {data.shape[0]}")
print(f"Variables finales : {data.columns.tolist()}\n")

# --- 4. Division des données et entraînement du modèle ---
print("\n🧠 Étape 4 : Division des données et entraînement du modèle...\n")

X = data.drop(columns=[target_col])
y = data[target_col]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=13)
print("✅ Données divisées avec succès (80% entraînement, 20% test).")
print(f"Taille de l'ensemble d'entraînement : {X_train.shape[0]} lignes")
print(f"Taille de l'ensemble de test : {X_test.shape[0]} lignes\n")

# --- 5. Recherche des meilleurs hyperparamètres (Grid Search) ---
print("\n⚙️ Étape 5 : Recherche des meilleurs hyperparamètres (Grid Search)...\n")
CHECKPOINT_PATH = "grid_search_checkpoint.pkl"

if os.path.exists(CHECKPOINT_PATH):
    print("✅ Checkpoint trouvé. Chargement de l'objet GridSearch...")
    with open(CHECKPOINT_PATH, 'rb') as f:
        grid_search = pickle.load(f)
    print("✅ GridSearch chargé avec succès.")
    total_training_time = 0.0  # Temps non disponible
else:
    print("❌ Aucun checkpoint trouvé. Lancement de GridSearch...")
    start_time = time.time()

    # Nouvelle grille de paramètres
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }

    model_to_use = RandomForestRegressor(random_state=13)

    grid_search = GridSearchCV(
        estimator=model_to_use,
        param_grid=param_grid,
        cv=3,
        n_jobs=-1,
        verbose=2
    )

    grid_search.fit(X_train, y_train)

    total_training_time = time.time() - start_time
    with open(CHECKPOINT_PATH, 'wb') as f:
        pickle.dump(grid_search, f)
    print("\n✅ Checkpoint GridSearch sauvegardé.")
    print(f"⏳ Temps d'entraînement total : {total_training_time:.2f} secondes.")

print(f"\n✅ Meilleurs hyperparamètres trouvés : {grid_search.best_params_}")
print(f"✅ Meilleur score R² sur l'ensemble d'entraînement : {grid_search.best_score_:.2f}")

best_model = grid_search.best_estimator_

MODEL_PATH = "best_random_forest_model.pkl"
with open(MODEL_PATH, 'wb') as f:
    pickle.dump(best_model, f)
print(f"✅ Le meilleur modèle a été sauvegardé sous : {MODEL_PATH}")
print("\n✅ Le meilleur modèle a été sélectionné pour les prédictions finales.")

# --- 6. Prédictions et évaluation du meilleur modèle ---
print("\n📈 Étape 6 : Prédictions et évaluation du meilleur modèle...\n")
y_pred = best_model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print("✅ Métriques d'évaluation du meilleur modèle :")
print(f"Erreur Absolue Moyenne (MAE) : {mae:.2f}")
print(f"Erreur Quadratique Moyenne (MSE) : {mse:.2f}")
print(f"Coefficient de Détermination (R²) : {r2:.2f}")

# --- 7. Analyse de l'importance des variables ---
print("\n🔍 Étape 7 : Analyse de l'importance des variables...\n")
feature_importances = pd.Series(best_model.feature_importances_, index=X.columns)
sorted_importances = feature_importances.sort_values(ascending=False)
print("Importance des variables pour la prédiction du 'Classement sur le segment':")
print(sorted_importances)

# --- 8. Visualisation de l'importance des variables ---
print("\n📊 Étape 8 : Création du graphique d'importance des variables...\n")
plt.figure(figsize=(12, 8))
sorted_importances.plot(kind='barh', color='skyblue')
plt.title("Importance des variables pour la prédiction du classement sur le segment")
plt.xlabel("Importance (score)")
plt.ylabel("Variables")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
print("\n✅ Graphique d'importance des variables généré avec succès.")

# --- 9. Sauvegarde des résultats dans un fichier Excel ---
print("\n📝 Étape 9 : Sauvegarde des résultats dans un fichier Excel...\n")

# Création du nom de la feuille de calcul
now = datetime.now()
sheet_name_train = now.strftime("%Y-%m-%d_%H-%M-%S")
sheet_name_test = "Resultats_Test"

# Création du DataFrame pour les résultats d'entraînement et d'importance
results_df = pd.DataFrame(columns=['Nom', 'Valeur'])
results_df = pd.concat([results_df, pd.DataFrame([
    {'Nom': 'Meilleurs hyperparamètres', 'Valeur': str(grid_search.best_params_)},
    {'Nom': 'Meilleur score R²', 'Valeur': grid_search.best_score_},
    {'Nom': 'Temps d\'entraînement (s)', 'Valeur': total_training_time},
])], ignore_index=True)

# Ajout de l'importance des variables
importance_df = pd.DataFrame(sorted_importances).reset_index()
importance_df.columns = ['Variable', 'Importance']

# Création du DataFrame pour les résultats du test
test_results_df = pd.DataFrame(columns=['Métrique', 'Valeur'])
test_results_df = pd.concat([test_results_df, pd.DataFrame([
    {'Métrique': 'Erreur Absolue Moyenne (MAE)', 'Valeur': mae},
    {'Métrique': 'Erreur Quadratique Moyenne (MSE)', 'Valeur': mse},
    {'Métrique': 'Coefficient de Détermination (R²)', 'Valeur': r2},
])], ignore_index=True)

# Utilisation de l'API pd.ExcelWriter pour écrire sur plusieurs feuilles
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    # Écriture des données d'entraînement et d'importance
    data.to_excel(writer, sheet_name=sheet_name_train, index=False)

    # Écriture des résultats d'entraînement en dessous des données
    startrow_results = len(data) + 2
    results_df.to_excel(writer, sheet_name=sheet_name_train, startrow=startrow_results, index=False)

    # Écriture de l'importance des variables
    startrow_importance = startrow_results + len(results_df) + 2
    importance_df.to_excel(writer, sheet_name=sheet_name_train, startrow=startrow_importance, index=False)

    # Écriture des résultats de test sur une nouvelle feuille
    test_results_df.to_excel(writer, sheet_name=sheet_name_test, index=False)

print(f"✅ Résultats et données d'entraînement sauvegardés dans '{output_path}'.")
print("\n🏁 Processus terminé avec succès.")