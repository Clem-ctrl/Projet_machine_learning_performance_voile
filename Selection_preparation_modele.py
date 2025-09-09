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
project_folder = r"C:\Projects\Projet_machine_learning_performance_voile"
file_path = os.path.join(project_folder, "Metasail_Statistics_unified_processed.xlsx")
output_path = os.path.join(project_folder, "Metasail_random_forest_results.xlsx")
graph_output_path = os.path.join(project_folder, "feature_importance_graph.png")
warnings.filterwarnings('ignore', category=SettingWithCopyWarning)

print("✅ Étape 1 : Chargement et préparation des données...\n")

# --- 2. Chargement et vérification des données ---
try:
    df_metasail = pd.read_excel(file_path)
    print("✅ Fichier Excel chargé avec succès.")
except FileNotFoundError:
    print(f"❌ Erreur : Le fichier n'a pas été trouvé. Veuillez vérifier le chemin d'accès : {file_path}")
    exit()

# Définition des colonnes
target_col = 'Classement sur le segment'
feature_cols = [
    'Sexe', "Catégorie d'âge",
    'Wind Speed (kts)', 'Orientation vent metasail',
   'Allure', 'Temperature (°C)', 'Pressure (hPa)', 'Humidity (%)', 'Rain (mm)',
    'Classement entrée de segment'
]

# Vérification de l'existence des colonnes
all_cols_to_check = feature_cols + [target_col]
colonnes_existantes = [col for col in all_cols_to_check if col in df_metasail.columns]
colonnes_manquantes = [col for col in all_cols_to_check if col not in df_metasail.columns]

if colonnes_manquantes:
    print(f"\n❌ Erreur : Les colonnes suivantes sont manquantes et le script ne peut pas continuer : {colonnes_manquantes}")
    exit()

data = df_metasail[colonnes_existantes].copy()

# Remplacement des virgules par des points et conversion en numérique
cols_to_convert = [
    'Wind Speed (kts)', 'Vitesse moyenne du segment (noeuds)',
    'VMC du segment (noeuds)', 'Wind to speed ratio', 'Temperature (°C)',
    'Pressure (hPa)', 'Humidity (%)', 'Rain (mm)', 'Efficacité du segment (%)',
    'Classement entrée de segment', 'Classement fin de segment', target_col
]
cols_to_convert_existantes = [col for col in cols_to_convert if col in data.columns]
for col in cols_to_convert_existantes:
    data[col] = data[col].astype(str).str.replace(',', '.', regex=False).astype(float)

print("✅ Préparation des données terminée.")

# --- 3. Nettoyage et encodage des données ---
print("⚙️ Étape 3 : Nettoyage et encodage des données...\n")

if "Catégorie d'âge" in data.columns:
    data = data[data['Catégorie d\'âge'].isin(['U17', 'U19'])]
data.dropna(inplace=True)
print("✅ Données nettoyées et filtrées avec succès. Seuls les U19 et U17 sont conservés.")

# Encodage circulaire pour l'orientation du vent
def circular_encoding(df, col):
    if col in df.columns:
        angle_rad = np.radians(df[col])
        df[f'{col}_sin'] = np.sin(angle_rad)
        df[f'{col}_cos'] = np.cos(angle_rad)
        df.drop([col], axis=1, inplace=True)
    return df

data = circular_encoding(data, 'Orientation vent metasail')

# One-Hot Encoding des variables catégorielles
categorical_cols = ['Sexe', 'Catégorie d\'âge', 'Allure']
data = pd.get_dummies(data, columns=[col for col in categorical_cols if col in data.columns], dtype=int)

print("✅ Encodage des données catégorielles terminé.")
print(f"Nombre total de lignes après nettoyage : {data.shape[0]}")
print(f"Variables finales : {data.columns.tolist()}\n")

# --- 4. Division des données et entraînement du modèle ---
print("\n🧠 Étape 4 : Division des données et entraînement du modèle...\n")

# Suppression des variables à faible importance
low_importance_features = [
    'Pressure (hPa)', 'Rain (mm)'
]
features_to_drop = [col for col in low_importance_features + [target_col] if col in data.columns]
X = data.drop(columns=features_to_drop)
y = data[target_col]
print(f"✅ Nombre de variables finales pour le modèle : {X.shape[1]}")
print(f"Variables finales pour le modèle : {X.columns.tolist()}\n")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=13)
print("✅ Données divisées avec succès (80% entraînement, 20% test).")
print(f"Taille de l'ensemble d'entraînement : {X_train.shape[0]} lignes")
print(f"Taille de l'ensemble de test : {X_test.shape[0]} lignes\n")

# --- 5. Recherche des meilleurs hyperparamètres (Grid Search) ---
print("\n⚙️ Étape 5 : Recherche des meilleurs hyperparamètres (Grid Search)...\n")
# Retrait de la logique de checkpoint pour assurer la consistance des colonnes
if os.path.exists("grid_search_checkpoint.pkl"):
    os.remove("grid_search_checkpoint.pkl")
    print("⚠️ Ancien checkpoint supprimé pour éviter les erreurs de correspondance de colonnes.")

start_time = time.time()
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4, 8],
    'max_features': ['sqrt', 'log2', 1.0],
    'bootstrap': [True, False]
}
model_to_use = RandomForestRegressor(random_state=13)
grid_search = GridSearchCV(
    estimator=model_to_use, param_grid=param_grid, cv=3, n_jobs=-1, verbose=2
)
grid_search.fit(X_train, y_train)
total_training_time = time.time() - start_time
print("\n✅ GridSearch terminé.")
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
plt.title("Importance des variables pour la prédiction du classement")
plt.xlabel("Importance (score)")
plt.ylabel("Variables")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(graph_output_path)
print(f"✅ Graphique d'importance des variables sauvegardé sous : {graph_output_path}")
plt.show()

print("\n✅ Graphique d'importance des variables généré avec succès.")

# --- 9. Sauvegarde des résultats dans un fichier Excel ---
print("\n📝 Étape 9 : Sauvegarde des résultats dans un fichier Excel...\n")
results_data = {
    'Métrique': ['MAE', 'MSE', 'R²'],
    'Valeur': [mae, mse, r2]
}
results_df = pd.DataFrame(results_data)

try:
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name='Modèle_Evaluation', index=False)
        sorted_importances.to_excel(writer, sheet_name='Feature_Importance', header=True)
    print(f"✅ Résultats sauvegardés dans '{output_path}'.")
except Exception as e:
    print(f"❌ Erreur lors de la sauvegarde du fichier Excel : {e}")

print("\n🏁 Processus terminé avec succès.")