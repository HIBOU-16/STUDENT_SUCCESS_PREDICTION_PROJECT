"""Étape 3 - Entraînement, comparaison, sélection et sauvegarde des modèles.

Protocole (identique pour tous les modèles -> comparaison équitable) :
  1. séparation stratifiée apprentissage 80 % / test 20 % (graine 42), le test n'est utilisé qu'à la fin ;
  2. pour chaque scénario (A inscription, B fin S1, C fin S2) et chaque modèle :
     GridSearchCV avec validation croisée stratifiée 5 plis sur l'apprentissage (refit = macro-F1) ;
     SMOTE, standardisation, encodage et sélection de variables sont DANS le pipeline -> appris pli par pli ;
  3. choix du modèle retenu par scénario, sur la validation croisée uniquement :
     parmi les modèles dont le macro-F1 CV est à moins de 0,02 du meilleur, on garde celui qui a le meilleur
     rappel Dropout CV (priorité aux faux négatifs, comme l'exige l'énoncé) ;
  4. seuils de risque faible / moyen / élevé calculés sur des prédictions out-of-fold de l'apprentissage ;
  5. évaluation finale unique sur le test, importance des variables, équité, sauvegarde.

Usage :  python -m src.train            (complet, quelques minutes)
         python -m src.train --quick    (grilles réduites, pour vérifier que tout fonctionne)
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import sklearn
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, make_scorer, recall_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src import config
from src.data_collection import load_raw, validate
from src.evaluate import (compute_metrics, dropout_detection_at, fairness_report, plot_confusion, plot_importance,
                          plot_model_comparison, plot_roc_pr, risk_level_table, risk_thresholds)
from src.explain import global_importance, reference_profile
from src.models import FROM_REFERENCE, MODEL_LABELS, REFIT, SCORING, build_models

# Résultats publiés dans la présentation de référence (diapositive 14) - à VÉRIFIER, pas à recopier.
REFERENCE_RESULTS = {
    "logistic_regression": {"accuracy": 0.72, "f1_macro": 0.69, "recall_dropout": 0.66, "recall_enrolled": 0.65, "recall_graduate": 0.78},
    "random_forest": {"accuracy": 0.77, "f1_macro": 0.70, "recall_dropout": 0.75, "recall_enrolled": 0.38, "recall_graduate": 0.93},
    "random_forest_smote": {"accuracy": 0.78, "f1_macro": 0.72, "recall_dropout": 0.73, "recall_enrolled": 0.54, "recall_graduate": 0.89},
}


def split_data(df: pd.DataFrame):
    return train_test_split(df, test_size=config.TEST_SIZE, stratify=df[config.TARGET],
                            random_state=config.RANDOM_STATE)


def select_retained(rows: list[dict], tolerance: float = 0.02) -> str:
    cands = [r for r in rows if r["model"] != "baseline_majority"]
    best = max(r["cv_f1_macro"] for r in cands)
    eligible = [r for r in cands if r["cv_f1_macro"] >= best - tolerance]
    return max(eligible, key=lambda r: r["cv_recall_dropout"])["model"]


def reproduce_reference(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Rejoue fidèlement les pipelines des diapositives 12-13 (36 variables brutes, codes traités comme des
    nombres, cible encodée par LabelEncoder) sur NOTRE séparation, pour vérifier les chiffres annoncés."""
    le = LabelEncoder().fit(config.CLASSES)
    Xtr, Xte = train[config.FEATURES], test[config.FEATURES]
    ytr, yte = le.transform(train[config.TARGET]), le.transform(test[config.TARGET])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    lr = GridSearchCV(
        Pipeline([("scaler", StandardScaler()), ("variance", VarianceThreshold()),
                  ("selectk", SelectKBest(score_func=f_classif)),
                  ("clf", LogisticRegression(max_iter=3000, class_weight="balanced"))]),
        {"clf__C": [0.1, 1], "selectk__k": [15, 20]}, cv=cv, n_jobs=-1,
        scoring=make_scorer(recall_score, labels=[0], average="macro"))
    models = {
        "logistic_regression": lr,
        "random_forest": RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=42),
        "random_forest_smote": ImbPipeline([
            ("variance", VarianceThreshold()), ("scaler", StandardScaler()),
            ("smote", SMOTE(random_state=42, sampling_strategy="not majority")),
            ("clf", RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=42))]),
    }
    out = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        pred = m.predict(Xte)
        rep = classification_report(yte, pred, output_dict=True, zero_division=0)
        out[name] = {
            "obtenu": {"accuracy": rep["accuracy"], "f1_macro": rep["macro avg"]["f1-score"],
                       "recall_dropout": rep["0"]["recall"], "recall_enrolled": rep["1"]["recall"],
                       "recall_graduate": rep["2"]["recall"]},
            "annonce_presentation": REFERENCE_RESULTS[name],
            "confusion_matrix": confusion_matrix(yte, pred).tolist(),
        }
        if name == "logistic_regression":
            out[name]["best_params"] = m.best_params_
    return out


def run(quick: bool = False) -> dict:
    t_start = time.time()
    df = load_raw()
    problems = validate(df)
    if problems:
        raise ValueError(problems)
    train, test = split_data(df)
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"row": df.index, "set": np.where(df.index.isin(test.index), "test", "train")}).to_csv(
        config.DATA_PROCESSED / "train_test_split.csv", index=False)
    print(f"Apprentissage : {len(train)} | Test : {len(test)} | classes test : "
          f"{test[config.TARGET].value_counts().to_dict()}")

    cv = StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=config.RANDOM_STATE)
    cv_rows, test_rows, summary = [], [], {"scenarios": {}}
    curves = {}

    for scen, spec in config.SCENARIOS.items():
        feats = spec["features"]
        Xtr, ytr, Xte, yte = train[feats], train[config.TARGET], test[feats], test[config.TARGET]
        fitted, scen_rows = {}, []
        for name, (pipe, grid) in build_models(feats).items():
            if quick:
                grid = {k: v[:1] for k, v in grid.items()}
            gs = GridSearchCV(pipe, grid, scoring=SCORING, refit=REFIT, cv=cv, n_jobs=-1)
            t0 = time.time()
            gs.fit(Xtr, ytr)
            search_time = time.time() - t0
            i = gs.best_index_
            row = {"scenario": scen, "model": name, "model_label": MODEL_LABELS[name],
                   "source": "présentation" if name in FROM_REFERENCE else "complément",
                   "best_params": json.dumps(gs.best_params_), "n_candidates": len(gs.cv_results_["params"]),
                   "search_time_s": round(search_time, 1),
                   "fit_time_s": round(float(gs.cv_results_["mean_fit_time"][i]), 3)}
            for m in SCORING:
                row[f"cv_{m}"] = gs.cv_results_[f"mean_test_{m}"][i]
                row[f"cv_std_{m}"] = gs.cv_results_[f"std_test_{m}"][i]
            scen_rows.append(row)
            fitted[name] = gs.best_estimator_

            t0 = time.time()
            proba = gs.best_estimator_.predict_proba(Xte)
            pred_time = (time.time() - t0) / len(Xte) * 1000
            pred = gs.best_estimator_.classes_[proba.argmax(1)]
            met = compute_metrics(yte, pred, proba, gs.best_estimator_.classes_)
            test_rows.append({"scenario": scen, "model": name, "model_label": MODEL_LABELS[name],
                              "accuracy": met["accuracy"], "balanced_accuracy": met["balanced_accuracy"],
                              "f1_macro": met["f1_macro"], "f1_weighted": met["f1_weighted"],
                              "roc_auc_ovr_macro": met["roc_auc_ovr_macro"], "roc_auc_dropout": met["roc_auc_dropout"],
                              "pr_auc_dropout": met["pr_auc_dropout"],
                              **{f"{k}_{c.lower()}": met["per_class"][c][k2] for c in config.CLASSES
                                 for k, k2 in (("precision", "precision"), ("recall", "recall"), ("f1", "f1-score"))},
                              "predict_ms_per_student": round(pred_time, 4),
                              "confusion_matrix": json.dumps(met["confusion_matrix"])})
            print(f"[{scen}] {name:24s} CV macro-F1={row['cv_f1_macro']:.3f} rappel Dropout={row['cv_recall_dropout']:.3f}"
                  f" | test macro-F1={met['f1_macro']:.3f} rappel Dropout={met['per_class']['Dropout']['recall']:.3f}"
                  f" ({search_time:.0f}s)")
        cv_rows += scen_rows

        # --- modèle retenu (décision prise sur la validation croisée seulement) -------------------
        retained = select_retained(scen_rows)
        model = fitted[retained]
        d = list(model.classes_).index(config.RISK_CLASS)
        oof = cross_val_predict(clone(model), Xtr, ytr, cv=cv, method="predict_proba", n_jobs=-1)[:, d]
        thresholds = risk_thresholds(ytr, oof)
        p_test = model.predict_proba(Xte)[:, d]
        curves[scen] = ((yte == config.RISK_CLASS).astype(int).values, p_test)
        test_row = next(r for r in test_rows if r["scenario"] == scen and r["model"] == retained)

        levels = risk_level_table(yte.values, p_test, thresholds)
        levels.to_csv(config.METRICS_DIR / f"risk_levels_{scen}.csv")
        fair = fairness_report(Xte, yte.values, p_test, thresholds["seuil_moyen"])
        fair.to_csv(config.METRICS_DIR / f"fairness_{scen}.csv", index=False)
        imp = global_importance(model, Xte, yte)
        imp.to_csv(config.METRICS_DIR / f"permutation_importance_{scen}.csv", index=False)
        plot_importance(imp, f"Importance par permutation - {spec['label']}\n({MODEL_LABELS[retained]}, jeu de test)",
                        f"model_importance_{scen}.png")
        plot_confusion(json.loads(test_row["confusion_matrix"]), config.CLASSES,
                       f"{spec['label']}\n{MODEL_LABELS[retained]} (test, n={len(test)})", f"model_confusion_{scen}.png")

        bundle = {
            "model": model, "scenario": scen, "scenario_label": spec["label"], "features": feats,
            "model_name": retained, "model_label": MODEL_LABELS[retained], "thresholds": thresholds,
            "reference_profile": reference_profile(Xtr), "classes": list(model.classes_),
            "test_metrics": {k: v for k, v in test_row.items() if k not in ("scenario", "model", "model_label")},
            "trained_at": datetime.now().isoformat(timespec="seconds"), "sklearn_version": sklearn.__version__,
            "n_train": len(Xtr), "n_test": len(Xte),
        }
        config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, config.MODELS_DIR / f"model_{scen}.joblib", compress=3)
        summary["scenarios"][scen] = {
            "retained_model": retained, "thresholds": thresholds,
            "test": {k: test_row[k] for k in ("accuracy", "f1_macro", "recall_dropout", "precision_dropout",
                                              "f1_dropout", "roc_auc_dropout", "pr_auc_dropout", "recall_enrolled",
                                              "recall_graduate")},
            "alert_at_medium": dropout_detection_at(yte.values, p_test, thresholds["seuil_moyen"]),
            "alert_at_high": dropout_detection_at(yte.values, p_test, thresholds["seuil_eleve"]),
            "risk_levels": levels.reset_index().to_dict("records"),
            "top_importance": imp.head(8).round(4).to_dict("records"),
        }
        print(f"[{scen}] -> retenu : {retained} | seuils {thresholds}")

    # Confusions de tous les modèles du scénario C (comparaison directe avec la présentation)
    for r in test_rows:
        if r["scenario"] == "C_fin_S2" and r["model"] != "baseline_majority":
            plot_confusion(json.loads(r["confusion_matrix"]), config.CLASSES,
                           f"C - fin S2 : {r['model_label']}", f"model_confusion_C_{r['model']}.png")

    cv_table, test_table = pd.DataFrame(cv_rows), pd.DataFrame(test_rows)
    cv_table.to_csv(config.METRICS_DIR / "cv_results.csv", index=False)
    test_table.to_csv(config.METRICS_DIR / "test_results.csv", index=False)
    plot_model_comparison(cv_table, "model_comparison_cv.png")
    plot_roc_pr(curves, "model_roc_pr_dropout.png")

    # Analyse de sensibilité : scénario A sans les variables dont la date de mesure est ambiguë
    a_model = joblib.load(config.MODELS_DIR / "model_A_inscription.joblib")
    strict = [f for f in config.SCENARIOS["A_inscription"]["features"] if f not in config.AMBIGUOUS_TIMING]
    pipe, _ = build_models(strict)[a_model["model_name"]]
    pipe.set_params(**{k: v for k, v in a_model["model"].get_params().items() if k.startswith(("clf__", "selectk__"))})
    res = cross_validate(pipe, train[strict], train[config.TARGET], cv=cv, scoring=SCORING, n_jobs=-1)
    a_row = next(r for r in cv_rows if r["scenario"] == "A_inscription" and r["model"] == a_model["model_name"])
    summary["sensitivity_A_without_fees_debtor"] = {
        "excluded": config.AMBIGUOUS_TIMING,
        "cv_f1_macro_with": a_row["cv_f1_macro"], "cv_f1_macro_without": float(res["test_f1_macro"].mean()),
        "cv_recall_dropout_with": a_row["cv_recall_dropout"],
        "cv_recall_dropout_without": float(res["test_recall_dropout"].mean()),
    }

    print("Reproduction de la présentation de référence ...")
    summary["reference_reproduction"] = reproduce_reference(train, test)
    summary["split"] = {"n_train": len(train), "n_test": len(test),
                        "test_class_counts": test[config.TARGET].value_counts().to_dict()}
    summary["quick_mode"] = quick
    summary["total_time_s"] = round(time.time() - t_start, 1)
    summary["versions"] = {"sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__}
    with open(config.METRICS_DIR / "training_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=float)
    print(f"Terminé en {summary['total_time_s']} s")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="grilles réduites (test rapide)")
    run(parser.parse_args().quick)
