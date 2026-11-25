# Alerte précoce du décrochage universitaire

Mini-projet 7 « Programmation avancée avec Python », sujet 3 (ISI / UVT), réalisé en binôme par Mariam et Iheb.

Ce système estime, pour chaque étudiant, la probabilité d'**abandon** (*Dropout*), de **maintien en inscription** (*Enrolled*) ou de **diplomation** (*Graduate*). Il traduit cette probabilité en **risque faible / moyen / élevé** et affiche les **facteurs associés** à chaque prédiction. C'est un **outil d'aide à la décision** : il ne prend aucune décision automatique concernant un étudiant.

## Démarrage rapide (Windows)

Double-cliquez sur `lancer_application.bat`. Le script crée l'environnement, installe les dépendances, entraîne les modèles s'ils sont absents, puis ouvre l'application dans le navigateur.

Procédure manuelle :

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py            # étapes 1 à 3 + 29 tests (~3 min)
streamlit run app/streamlit_app.py
```

Pour prédire en ligne de commande :

```bash
python -m src.predict --scenario B_fin_S1 --csv data/sample/profils_fictifs_demo.csv
```

## Données

- Source : [UCI ML Repository #697](https://archive.ics.uci.edu/dataset/697) (Realinho et al., 2022, licence CC BY 4.0). Le même jeu de données est publié sur [Kaggle](https://www.kaggle.com/datasets/adilshamim8/predict-students-dropout-and-academic-success).
- Contenu : 4 424 étudiants, 36 variables et la cible `Target`. Aucune valeur manquante, aucun doublon.
- Emplacement : `data/raw/students_dropout_uci.csv`. Le chargeur accepte aussi la version Kaggle (séparateur `,`, `Nationality`) : il suffit de la placer au même endroit.
- Dictionnaire de données : `data/data_dictionary.csv`
- Jeu anonymisé : `data/processed/students_anonymized.csv` et l'échantillon `data/sample/echantillon_anonymise_30.csv`
- Profils de démonstration **fictifs** : `data/sample/profils_fictifs_demo.csv`

## Arborescence

```
src/config.py           chemins, graine, groupes de variables, scénarios A/B/C
src/data_collection.py  Étape 1 : chargement, validation, anonymisation, SQLite, dictionnaire
src/eda.py              Étape 2 : statistiques, tests, information mutuelle, figures
src/features.py         variables dérivées + préprocesseur (one-hot / standardisation)
src/models.py           modèles comparés et grilles d'hyperparamètres
src/evaluate.py         métriques, seuils de risque, équité, graphiques
src/explain.py          importance par permutation + explication locale
src/train.py            Étape 3 : protocole complet, choix du modèle, sauvegarde
src/predict.py          prédiction (application + ligne de commande)
app/streamlit_app.py    Étape 4 : interface
src/tunisia_form.py     questions du formulaire tunisien (source unique)
src/tunisia.py          conversion des réponses du formulaire + évaluation
forms/                  script Google Apps Script, aperçu et mode d'emploi du formulaire
tests/                  29 tests automatisés (pytest)
models/                 un modèle .joblib par scénario
reports/                figures, métriques, journal d'entraînement, captures, preuves des tests
docs/                   schéma d'architecture
```

## Résultats (jeu de test : 885 étudiants, jamais utilisé pour les choix)

| Scénario | Modèle retenu | Macro-F1 | Rappel Dropout | Rappel au seuil « risque moyen » |
|---|---|---|---|---|
| A : à l'inscription | Random Forest + SMOTE | 0,541 | 0,613 | 0,901 (67 % des étudiants signalés) |
| **B : fin du S1 (recommandé)** | Random Forest + SMOTE | 0,677 | 0,694 | **0,901** (52 % signalés) |
| C : fin du S2 | HistGradientBoosting | 0,691 | 0,683 | 0,912 (49 % signalés) |

En rejouant le pipeline de la présentation de référence (36 variables, même test de 885 étudiants), le Random Forest obtient un rappel Dropout de 0,771 (219/284). L'ordre de grandeur annoncé, « environ 75 % », est donc confirmé. Le détail figure dans `reports/metrics/training_summary.json`.

## Évaluation sur des étudiants tunisiens (avant la validation finale)

Le dossier `forms/` contient un **Google Form** d'évaluation : `creer_formulaire_google.gs` crée le formulaire et la feuille des réponses en un clic sur script.google.com. Le mode d'emploi est dans `forms/README.md`, et l'aperçu imprimable dans `forms/APERCU_FORMULAIRE_TUNISIE.pdf`. L'export CSV des réponses s'analyse dans la page **Évaluation Tunisie** de l'application, ou avec `python -m src.tunisia --csv <fichier>`.

Les questions sont définies **une seule fois** dans `src/tunisia_form.py`. Après toute modification, lancez `python forms/build_google_form.py`.
