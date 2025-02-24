from flask import Flask, render_template, request, jsonify
import pandas as pd
from io import BytesIO
import datetime
#Indexnew ou jsdefff

app = Flask(__name__)


def convert_time_objects(data):
    if isinstance(data, list):
        return [convert_time_objects(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_time_objects(value) for key, value in data.items()}
    elif isinstance(data, pd.Timestamp):
        return data.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(data, datetime.time):
        return data.strftime('%H:%M:%S')
    else:
        return data


def generate_diagnostics(df_sens, df_first, diagnostics_name):
    diagnostics = []

    # Normalisation des noms de colonnes pour éviter les problèmes de casse ou d'espaces
    df_first.columns = df_first.columns.str.strip().str.lower()

    max_voyageurs = df_sens.groupby('Tranche 5 Min').sum().max(axis=1)

    for tranche, max_voyageur in max_voyageurs.items():
        # Retrouver la fréquence et le nombre de rames existants pour chaque tranche
        matching_row = df_first[df_first['tranche horaire'] == tranche]

        if not matching_row.empty:
            nb_rames = matching_row['nb rames existante'].values[0]
            frequence = matching_row['fréquence existante'].values[0]
            tranche_offre = matching_row['tranches offre'].values[0]  # Utilisation de la version normalisée du nom
        else:
            nb_rames = None
            frequence = None
            tranche_offre = None  # Si pas de correspondance, on met None

        diagnostics.append({
            'tranche': tranche.strftime('%H:%M:%S') if isinstance(tranche, pd.Timestamp) else str(tranche),
            'max_voyageurs': max_voyageur,
            'nb_rames': nb_rames,
            'frequence': frequence,
            'tranches_offre': tranche_offre  # Ajout de la colonne Tranches Offre
        })

    return {diagnostics_name: convert_time_objects(diagnostics)}



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_first_file', methods=['POST'])
def upload_first_file():
    try:
        file = request.files['firstFile']
        in_memory_file = BytesIO(file.read())
        excel_file = pd.ExcelFile(in_memory_file, engine='openpyxl')
        sheet_names = excel_file.sheet_names
        return jsonify(sheet_names=sheet_names)
    except Exception as e:
        return jsonify(error=f'Erreur lors de la lecture du fichier : {str(e)}')


@app.route('/process_files', methods=['POST'])
def process_files():
    try:
        first_file = request.files['firstFile']
        selected_sheet = request.form.get('sheet')

        sens_aller_file = request.files['secondFile']
        sens_retour_file = request.files['thirdFile']

        df_first = pd.read_excel(first_file, sheet_name=selected_sheet, engine='openpyxl')
        df_sens_aller = pd.read_excel(sens_aller_file, engine='openpyxl')
        df_sens_retour = pd.read_excel(sens_retour_file, engine='openpyxl')

        # Générer les diagnostics pour le sens aller et le sens retour
        diagnostics_aller = generate_diagnostics(df_sens_aller, df_first, 'diagnostic_sens_aller')
        diagnostics_retour = generate_diagnostics(df_sens_retour, df_first, 'diagnostic_sens_retour')

        # Retourner les diagnostics combinés
        diagnostics_combined = {**diagnostics_aller, **diagnostics_retour}

        return jsonify(diagnostics_combined)
    except Exception as e:
        return jsonify(error=f'Erreur lors du traitement des fichiers : {str(e)}')


if __name__ == '__main__':
    app.run(debug=True)

