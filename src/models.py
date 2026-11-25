"""Définition des modèles comparés et de leurs grilles d'hyperparamètres.

Modèles issus de la présentation de référence :
    logistic_regression   Standardisation + VarianceThreshold + SelectKBest + régression logistique pondérée
    random_forest         Random Forest sans rééquilibrage
    random_forest_smote   Random Forest avec SMOTE (dans un pipeline imblearn -> SMOTE seulement à l'entraînement)
Modèles complémentaires proposés par nous :
    hist_gradient_boosting  Gradient boosting par histogrammes, pondéré par classe
    baseline_majority       Référence naïve (prédit toujours la classe majoritaire)
"""
from __future__ import annotations

from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import make_scorer, recall_score, f1_score
from sklearn.pipeline import Pipeline

from src.config import RANDOM_STATE, RISK_CLASS
from src.features import FeatureEngineer, build_preprocessor

MODEL_LABELS = {
    "baseline_majority": "Référence (classe majoritaire)",
    "logistic_regression": "Régression logistique",
    "random_forest": "Random Forest",
    "random_forest_smote": "Random Forest + SMOTE",
    "hist_gradient_boosting": "HistGradientBoosting (complément)",
}
FROM_REFERENCE = {"logistic_regression", "random_forest", "random_forest_smote"}

SCORING = {
    "f1_macro": "f1_macro",
    "recall_dropout": make_scorer(recall_score, labels=[RISK_CLASS], average="macro", zero_division=0),
    "f1_dropout": make_scorer(f1_score, labels=[RISK_CLASS], average="macro", zero_division=0),
    "balanced_accuracy": "balanced_accuracy",
    "accuracy": "accuracy",
    "roc_auc_ovr": "roc_auc_ovr",
}
REFIT = "f1_macro"   # critère d'optimisation des hyperparamètres (équilibre entre les 3 classes)


def _steps(features):
    return [("features", FeatureEngineer()), ("prep", build_preprocessor(features))]


def build_models(features: list[str]) -> dict:
    """Renvoie {nom: (pipeline, grille)} pour une liste de variables (un scénario)."""
    rf_grid = {"clf__n_estimators": [200, 400], "clf__max_depth": [None, 12], "clf__min_samples_leaf": [1, 4]}
    return {
        "baseline_majority": (
            Pipeline(_steps(features) + [("clf", DummyClassifier(strategy="most_frequent"))]), {}),
        "logistic_regression": (
            Pipeline(_steps(features) + [
                ("variance", VarianceThreshold()),
                ("selectk", SelectKBest(score_func=f_classif)),
                ("clf", LogisticRegression(max_iter=3000, class_weight="balanced")),
            ]),
            {"clf__C": [0.1, 1, 10], "selectk__k": [20, 40, "all"]}),
        "random_forest": (
            Pipeline(_steps(features) + [("clf", RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1))]),
            rf_grid),
        "random_forest_smote": (
            ImbPipeline(_steps(features) + [
                ("smote", SMOTE(sampling_strategy="not majority", random_state=RANDOM_STATE)),
                ("clf", RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1)),
            ]),
            rf_grid),
        "hist_gradient_boosting": (
            Pipeline(_steps(features) + [("clf", HistGradientBoostingClassifier(
                class_weight="balanced", max_iter=300, early_stopping=True, random_state=RANDOM_STATE))]),
            {"clf__learning_rate": [0.05, 0.1], "clf__max_leaf_nodes": [15, 31]}),
    }
