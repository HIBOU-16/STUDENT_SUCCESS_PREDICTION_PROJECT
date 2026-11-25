"""Prédiction pour un ou plusieurs étudiants à partir d'un modèle sauvegardé.

Utilisé par l'application Streamlit ET utilisable en ligne de commande :
    python -m src.predict --scenario B_fin_S1 --csv data/sample/profils_fictifs_demo.csv
"""
from __future__ import annotations

import argparse
from functools import lru_cache

import joblib
import pandas as pd

from src import config
from src.data_collection import normalize_columns
from src.evaluate import risk_level
from src.explain import local_explanation

DISCLAIMER = ("Estimation statistique fondée sur des données historiques d'un établissement portugais. "
              "Ce n'est PAS une décision : elle sert uniquement à prioriser un accompagnement humain "
              "(tutorat, entretien, aide sociale) et ne doit jamais servir à sanctionner un étudiant.")


@lru_cache(maxsize=None)
def load_bundle(scenario: str) -> dict:
    path = config.MODELS_DIR / f"model_{scenario}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Modèle absent : {path}. Lancez d'abord : python -m src.train")
    return joblib.load(path)


def prepare(df: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    """Normalise les noms de colonnes et impose EXACTEMENT les variables et l'ordre utilisés à l'entraînement."""
    df = normalize_columns(df)
    missing = [c for c in bundle["features"] if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes pour le scénario {bundle['scenario']} : {missing}")
    X = df[bundle["features"]].apply(pd.to_numeric, errors="raise")
    if X.isna().any().any():
        raise ValueError("Valeurs manquantes dans le profil : " + str(X.columns[X.isna().any()].tolist()))
    return X


def predict(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Renvoie, pour chaque ligne : statut prédit, probabilités des 3 classes et niveau de risque de décrochage."""
    bundle = load_bundle(scenario)
    X = prepare(df, bundle)
    proba = bundle["model"].predict_proba(X)
    out = pd.DataFrame(proba, columns=[f"p_{c.lower()}" for c in bundle["classes"]], index=df.index)
    out.insert(0, "statut_predit", [bundle["classes"][i] for i in proba.argmax(1)])
    out["niveau_risque"] = risk_level(out["p_dropout"].values, bundle["thresholds"])
    return out


def explain(df_one_row: pd.DataFrame, scenario: str, top: int = 8) -> pd.DataFrame:
    bundle = load_bundle(scenario)
    return local_explanation(bundle["model"], prepare(df_one_row, bundle), bundle["reference_profile"], top)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prédire le risque de décrochage à partir d'un CSV")
    parser.add_argument("--scenario", default="B_fin_S1", choices=list(config.SCENARIOS))
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.csv, sep=None, engine="python", encoding="utf-8-sig")
    res = predict(df, args.scenario)
    ids = df["pseudo_id"] if "pseudo_id" in df.columns else df.index
    print(pd.concat([pd.Series(ids, name="id", index=df.index), res.round(3)], axis=1).to_string(index=False))
    print("\n" + DISCLAIMER)


if __name__ == "__main__":
    main()
