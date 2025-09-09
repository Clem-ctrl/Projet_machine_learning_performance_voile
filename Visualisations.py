import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- Chemin vers le fichier Excel ---
input_file = r"C:\Projects\Projet_machine_learning_performance_voile\Metasail_Statistics_unified_processed.xlsx"

# --- Chargement des données ---
try:
    df = pd.read_excel(input_file)
    print("Fichier Excel chargé avec succès.")
except FileNotFoundError:
    print(f"Erreur : Le fichier {input_file} n'a pas été trouvé.")
    exit()

# --- Nettoyage et préparation des données ---
df.columns = [
    "ID_course", "Nom_evenement", "Lieu_evenement", "Course", "Date_course",
    "Orientation_vent_metasail", "Nom_complet", "Numero_serie",
    "Temps_total_parcouru", "Longueur_totale_parcours",
    "Distance_reelle_totale", "Efficacite_totale", "Numero_segment",
    "Babord_pct", "Tribord_pct", "Temps_segment",
    "Distance_reelle_segment", "Longueur_segment", "Cap_magnetique",
    "Efficacite_segment_pct", "Debut_segment_ts", "Fin_segment_ts",
    "Classement_entree_segment", "Sexe", "Categorie_age", "Annee", "Mois",
    "Jour", "Debut_segment_dt", "Fin_segment_dt", "Date", "Heure_segment",
    "Vitesse_moyenne_segment_noeuds", "VMC_segment_noeuds",
    "Heure_segment_seconds", "Day", "Month", "Year", "Time", "City",
    "Latitude", "Longitude", "Temperature_C", "Pressure_hPa", "Humidity_pct",
    "Wind_Speed_kts", "Wind_Direction_deg", "Rain_mm", "Time_seconds",
    "VMC_moyenne_parcours_noeuds", "Vitesse_moyenne_parcours_noeuds",
    "Difference_parcours_theorique_reel", "Difference_segment_theorique_reel",
    "Allure", "Wind_to_speed_ratio", "Classement_sur_le_segment",
    "Classement_fin_de_segment"
]

cols_to_convert = [
    'VMC_segment_noeuds', 'Wind_Speed_kts', 'Vitesse_moyenne_segment_noeuds'
]
for col in cols_to_convert:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

df.dropna(subset=cols_to_convert + ['Allure'], inplace=True)

# Ligne mise à jour : Filtrer les données pour que Wind_Speed_kts soit >= 6
df = df[df['Wind_Speed_kts'] >= 6]

# Création de bacs (bins) pour la vitesse du vent
bins = np.arange(0, df['Wind_Speed_kts'].max() + 2, 2)
df['Wind_Speed_bin'] = pd.cut(df['Wind_Speed_kts'], bins=bins, right=False, include_lowest=True, labels=bins[:-1])

# --- Création de la visualisation dynamique ---
wind_bins = sorted(df['Wind_Speed_bin'].unique().dropna())
allures = sorted(df['Allure'].dropna().unique())

# Initialiser la figure
fig = go.Figure()

# --- Créer les frames pour le slider ---
frames = []
for i, wind_bin in enumerate(wind_bins):
    df_filtered_by_wind = df[df['Wind_Speed_bin'] == wind_bin]

    frame_data = []

    for j, allure in enumerate(allures):
        df_filtered_by_allure = df_filtered_by_wind[df_filtered_by_wind['Allure'] == allure]

        if df_filtered_by_allure.empty:
            continue

        vitesse_max = df_filtered_by_allure['Vitesse_moyenne_segment_noeuds'].max()
        if np.isnan(vitesse_max) or vitesse_max == 0:
            continue
        vitesse_bins = np.arange(0, vitesse_max + 1, 1)

        # 1. Créer la trace d'histogramme (les barres)
        hist_trace = go.Histogram(
            x=df_filtered_by_allure['Vitesse_moyenne_segment_noeuds'],
            name=f'Vitesse moyenne ({allure})',
            visible=(j == 0),
            marker_color='rgba(128, 204, 255, 0.8)',
            hovertemplate="Vitesse: %{x} noeuds<br>Fréquence: %{y}<extra></extra>"
        )
        frame_data.append(hist_trace)

        # 2. Créer la trace de la courbe pour les fréquences de la VMC
        vmc_counts = df_filtered_by_allure.groupby(pd.cut(
            df_filtered_by_allure['VMC_segment_noeuds'],
            bins=vitesse_bins,
            right=False
        )).size().reset_index(name='count')

        vmc_counts['mid_point'] = vmc_counts['VMC_segment_noeuds'].apply(lambda x: x.mid)

        vmc_curve_trace = go.Scatter(
            x=vmc_counts['mid_point'],
            y=vmc_counts['count'],
            mode='lines+markers',
            name=f'VMC ({allure})',
            line=dict(color='red', width=3),
            marker=dict(symbol='diamond', size=8, color='red'),
            visible=(j == 0),
            hovertemplate="VMC: %{x:.2f} noeuds<br>Fréquence: %{y}<extra></extra>"
        )
        frame_data.append(vmc_curve_trace)

    if frame_data:
        frame = go.Frame(
            data=frame_data,
            name=str(wind_bin),
            layout=go.Layout(
                title_text=f"Distributions de vitesse et VMC pour vents de {wind_bin} kts",
                xaxis_title="Vitesse du segment (noeuds)",
                yaxis_title="Nombre de segments (Fréquence)",
            )
        )
        frames.append(frame)

# --- Créer la figure et le layout initial ---
if frames:
    initial_frame_data = frames[0]['data']
    fig.add_traces(initial_frame_data)
else:
    print("Aucune donnée disponible pour créer la visualisation. Vérifiez les filtres et le fichier d'entrée.")
    exit()

# --- Finaliser le layout de la figure ---
fig.update_layout(
    template='plotly_dark',
    title=dict(
        text=f"Distributions de vitesse et VMC pour vents de {int(wind_bins[0])} kts",
        font=dict(size=24, family='Arial, sans-serif'),
        x=0.5,
        xanchor='center'
    ),
    xaxis=dict(
        title_text="Vitesse du segment (noeuds)",
        title_font=dict(size=18),
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        zeroline=True,
        zerolinecolor='rgba(255,255,255,0.2)'
    ),
    yaxis=dict(
        title_text="Nombre de segments (Fréquence)",
        title_font=dict(size=18),
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        zeroline=True,
        zerolinecolor='rgba(255,255,255,0.2)'
    ),
    font=dict(
        family='Arial, sans-serif',
        color='white'
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    updatemenus=[
        go.layout.Updatemenu(
            type="dropdown",
            direction="down",
            x=0.0,
            y=1.15,
            showactive=True,
            font=dict(size=16),
            buttons=[
                {
                    "label": allure,
                    "method": "update",
                    "args": [
                        {"visible": [False] * (len(allures) * 2)},
                        {"title": f"Distributions de vitesse et VMC pour l'allure: {allure}"}
                    ]
                }
                for i, allure in enumerate(allures)
            ]
        )
    ],
    sliders=[
        {
            "active": 0,
            "currentvalue": {"prefix": "Vitesse du vent: "},
            "pad": {"t": 20},
            "steps": [
                {
                    "label": f"{int(wind_bin)} kts",
                    "method": "animate",
                    "args": [
                        [str(wind_bin)],
                        {
                            "mode": "immediate",
                            "frame": {"duration": 300, "redraw": True},
                            "transition": {"duration": 300}
                        }
                    ]
                }
                for i, wind_bin in enumerate(wind_bins)
                if str(wind_bin) in [f.name for f in frames]
            ]
        }
    ],
    annotations=[
        dict(
            text="L'histogramme bleu montre la fréquence des vitesses moyennes.<br>La courbe rouge montre la fréquence des VMC.<br>Utilisez le curseur pour changer la vitesse du vent et le menu pour l'allure.",
            xref="paper", yref="paper",
            x=0.5, y=-0.2,
            showarrow=False,
            font=dict(size=12, color="white"),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="white",
            borderwidth=1,
            borderpad=4
        )
    ]
)

fig.frames = frames

# Sauvegarde de la visualisation interactive dans un fichier HTML
output_html_file = r"C:\Projects\Projet_machine_learning_performance_voile\Visualisations\visualisation_dynamique_vitesse_vent_et_allure_esthetique.html"
fig.write_html(output_html_file, auto_open=True)

print(f"Visualisation interactive sauvegardée en tant que {output_html_file}")
print("Vous pouvez maintenant partager ce fichier HTML.")