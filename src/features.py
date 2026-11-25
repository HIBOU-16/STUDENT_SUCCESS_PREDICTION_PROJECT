"""Ingénierie de variables et prétraitement.

Tout est encapsulé dans des objets scikit-learn afin que les transformations soient :
  * apprises uniquement sur les données d'entraînement (pas de fuite de données en validation croisée) ;
  * sauvegardées avec le modèle et réappliquées à l'identique par l'application.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src import config


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return pd.Series(np.where(den > 0, num / den.where(den > 0, 1), 0.0), index=num.index)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Ajoute des indicateurs dérivés, uniquement à partir des colonnes disponibles dans le scénario.

    - cu_<sem>_approval_rate : unités validées / unités inscrites (taux de réussite du semestre)
    - cu_<sem>_eval_per_unit : évaluations passées / unités inscrites (proxy d'engagement, l'assiduité
      n'étant pas mesurée dans le dataset)
    - grade_trend : moyenne S2 - moyenne S1 (seulement si les deux semestres sont connus)
    """

    def fit(self, X: pd.DataFrame, y=None):
        self.feature_names_in_ = np.array(X.columns)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        for sem in ("1st", "2nd"):
            enrolled = f"cu_{sem}_sem_enrolled"
            if enrolled in X.columns:
                X[f"cu_{sem}_approval_rate"] = _safe_ratio(X[f"cu_{sem}_sem_approved"], X[enrolled])
                X[f"cu_{sem}_eval_per_unit"] = _safe_ratio(X[f"cu_{sem}_sem_evaluations"], X[enrolled])
        if {"cu_1st_sem_grade", "cu_2nd_sem_grade"} <= set(X.columns):
            X["grade_trend"] = X["cu_2nd_sem_grade"] - X["cu_1st_sem_grade"]
        return X

    def get_feature_names_out(self, input_features=None):
        return np.array(engineered_columns(list(self.feature_names_in_)))


def engineered_columns(features: list[str]) -> list[str]:
    """Liste des colonnes en sortie de FeatureEngineer pour une liste de variables d'entrée."""
    out = list(features)
    for sem in ("1st", "2nd"):
        if f"cu_{sem}_sem_enrolled" in features:
            out += [f"cu_{sem}_approval_rate", f"cu_{sem}_eval_per_unit"]
    if {"cu_1st_sem_grade", "cu_2nd_sem_grade"} <= set(features):
        out.append("grade_trend")
    return out


def build_preprocessor(features: list[str]) -> ColumnTransformer:
    """One-hot pour les codes nominaux (catégories rares < 20 regroupées), standardisation des numériques,
    variables binaires conservées telles quelles (déjà 0/1)."""
    cols = engineered_columns(features)
    nominal = [c for c in cols if c in config.NOMINAL]
    binary = [c for c in cols if c in config.BINARY]
    numeric = [c for c in cols if c not in nominal and c not in binary]
    return ColumnTransformer(
        [
            ("nominal", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20,
                                      sparse_output=False), nominal),
            ("binary", "passthrough", binary),
            ("numeric", StandardScaler(), numeric),
        ],
        verbose_feature_names_out=False,
    )


def split_xy(df: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    return df[features].copy(), df[config.TARGET].copy()
