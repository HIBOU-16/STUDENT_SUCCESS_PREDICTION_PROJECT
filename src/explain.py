"""Interprétabilité : importance globale (permutation) et explication locale d'une prédiction.

Explication locale « par substitution » (méthode agnostique au modèle) :
    pour chaque variable du profil, on la remplace par la valeur de référence de l'entraînement
    (médiane pour les numériques, modalité la plus fréquente sinon) et on mesure la variation de P(Dropout).
    contribution > 0  -> la valeur observée AUGMENTE le risque estimé par rapport à un étudiant « typique »
    contribution < 0  -> elle le DIMINUE.
Ce sont des associations apprises par le modèle, pas des causes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from src import config


def reference_profile(X_train: pd.DataFrame) -> dict:
    ref = {}
    for c in X_train.columns:
        if c in config.NOMINAL or c in config.BINARY:
            ref[c] = X_train[c].mode().iloc[0].item()
        else:
            ref[c] = float(X_train[c].median())
    return ref


def global_importance(model, X: pd.DataFrame, y, n_repeats: int = 10) -> pd.DataFrame:
    r = permutation_importance(model, X, y, scoring="f1_macro", n_repeats=n_repeats,
                               random_state=config.RANDOM_STATE, n_jobs=-1)
    return (pd.DataFrame({"variable": X.columns, "importance_mean": r.importances_mean,
                          "importance_std": r.importances_std})
            .sort_values("importance_mean", ascending=False).reset_index(drop=True))


def local_explanation(model, profile: pd.DataFrame, reference: dict, top: int = 8) -> pd.DataFrame:
    """profile : DataFrame d'UNE ligne avec les colonnes du scénario, dans l'ordre du modèle."""
    classes = list(model.classes_)
    d = classes.index(config.RISK_CLASS)
    base = model.predict_proba(profile)[0, d]
    variants = pd.concat([profile] * len(profile.columns), ignore_index=True)
    for i, c in enumerate(profile.columns):
        variants.loc[i, c] = reference[c]
    p = model.predict_proba(variants)[:, d]
    out = pd.DataFrame({
        "variable": profile.columns,
        "valeur": profile.iloc[0].values,
        "reference": [reference[c] for c in profile.columns],
        "contribution": base - p,
    })
    out = out[np.abs(out["contribution"]) > 1e-4]
    return out.reindex(out["contribution"].abs().sort_values(ascending=False).index).head(top).reset_index(drop=True)
