"""Évaluation du modèle sur des étudiants tunisiens (réponses du Google Form).

Étapes :
  1. read_responses()   lit l'export CSV de Google Sheets (en-têtes = titres des questions) ;
  2. map_responses()    convertit les réponses en variables du modèle (codes UCI) + statut réel ;
  3. evaluate()         prédit avec les modèles sauvegardés et compare au statut réel, pour chaque scénario.

Usage :  python -m src.tunisia --csv data/tunisia/reponses.csv

Approximations de conversion (à citer dans le rapport) :
  - moyenne du bac /20 x 10 -> admission_grade et previous_qualification_grade (échelle portugaise 0-200) ;
  - nationalité tunisienne -> code « national » (1) ; autre nationalité -> code rare + international = 1 ;
  - indicateurs macro-économiques (chômage, inflation, PIB) -> médiane de l'apprentissage portugais (neutre),
    car le modèle n'a vu que 10 années portugaises ;
  - moyenne du semestre = 0 si aucun module validé (convention du dataset UCI).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from src import config
from src.evaluate import RISK_LEVELS, dropout_detection_at
from src.predict import load_bundle, predict
from src.tunisia_form import SECTIONS, all_questions, choices_of, question

TUNISIA_DIR = config.ROOT / "data" / "tunisia"
RESULTS_PATH = config.METRICS_DIR / "tunisia_evaluation.json"
MACRO = ["unemployment_rate", "inflation_rate", "gdp"]
FOREIGN_NATIONALITY_CODE = 100       # code UCI rare -> regroupé avec les nationalités peu fréquentes
MIN_KNOWN, MIN_DROPOUT = 30, 10      # en dessous : pas de conclusion


# ---------------------------------------------------------------------------------------- lecture
def _norm(text) -> str:
    return " ".join(str(text).replace(" ", " ").split()).strip().lower()


def read_responses(path) -> pd.DataFrame:
    """Lit l'export CSV et renomme les colonnes « titre de question » en identifiants internes."""
    raw = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", dtype=str)
    by_title = {_norm(q["title"]): q["id"] for q in all_questions()}
    by_title.update({q["id"]: q["id"] for q in all_questions()})
    return raw.rename(columns={c: by_title.get(_norm(c), c) for c in raw.columns})


def _number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False).str.strip()
                         .replace({"": np.nan, "nan": np.nan}), errors="coerce")


def _choice(series: pd.Series, qid: str, issues: list) -> pd.Series:
    mapping = {_norm(k): v for k, v in choices_of(question(qid)).items()}
    keys = series.map(lambda v: _norm(v) if isinstance(v, str) and v.strip() else None)
    unknown = sorted({k for k in keys.dropna() if k not in mapping})
    if unknown:
        issues.append(f"{qid} : réponses non reconnues {unknown}")
    return keys.map(lambda k: mapping.get(k, np.nan) if k is not None else np.nan)


# ---------------------------------------------------------------------------------------- conversion
def map_responses(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, list[str]]:
    """Renvoie (variables du modèle, statut réel, variables complémentaires, problèmes détectés)."""
    issues: list[str] = []
    df = raw.copy()
    if "consentement" in df.columns:
        consent = _choice(df["consentement"], "consentement", issues)
        refused = int((consent != 1).sum())
        if refused:
            issues.append(f"{refused} réponse(s) sans consentement ignorée(s)")
        df = df[consent == 1]
    df = df.reset_index(drop=True)
    X = pd.DataFrame(index=df.index)

    for q in all_questions():
        if "maps_to" not in q or q["id"] not in df.columns:
            continue
        col = q["maps_to"]
        X[col] = _choice(df[q["id"]], q["id"], issues) if q["type"] == "choice" else _number(df[q["id"]])

    nat = _choice(df["nationalite"], "nationalite", issues)
    X["nationality"] = nat.map({"TN": 1, "AUTRE": FOREIGN_NATIONALITY_CODE})
    X["international"] = nat.map({"TN": 0, "AUTRE": 1})
    bac = _number(df["moyenne_bac"])
    X["admission_grade"] = bac * 10
    X["previous_qualification_grade"] = bac * 10
    X["application_order"] = X["application_order"].clip(upper=9)
    reference = load_bundle("C_fin_S2")["reference_profile"]
    for m in MACRO:
        X[m] = reference[m]

    for sem in ("1st", "2nd"):
        enrolled, approved, credited = (f"cu_{sem}_sem_{k}" for k in ("enrolled", "approved", "credited"))
        if approved not in X:
            continue
        too_many = (X[approved] > X[enrolled] + X[credited]).fillna(False)
        if too_many.any():
            issues.append(f"{int(too_many.sum())} réponse(s) : plus de modules validés qu'inscrits ({sem}) -> plafonné")
            X.loc[too_many, approved] = X.loc[too_many, enrolled] + X.loc[too_many, credited]
        X.loc[X[approved] == 0, f"cu_{sem}_sem_grade"] = 0.0

    if "s2_fait" in df.columns:  # S2 non suivi -> variables S2 inconnues
        skipped = _choice(df["s2_fait"], "s2_fait", issues) != "s2"
        X.loc[skipped, [c for c in config.SEM2 if c in X]] = np.nan

    X = X.reindex(columns=config.FEATURES)
    y = _choice(df["statut"], "statut", issues).replace("", np.nan) if "statut" in df else pd.Series(np.nan, index=df.index)
    extra_ids = [q["id"] for q in all_questions() if q.get("extra") or q["id"] in ("annee_entree", "repondant",
                                                                                 "section_bac", "filiere")]
    extras = df[[c for c in extra_ids if c in df.columns]].copy()
    return X, y.rename(config.TARGET), extras, issues


# ---------------------------------------------------------------------------------------- évaluation
def _bootstrap(y_true, y_pred, p_dropout, threshold, n=1000, seed=config.RANDOM_STATE) -> dict:
    rng = np.random.default_rng(seed)
    f1s, recalls = [], []
    y_true, y_pred, p_dropout = map(np.asarray, (y_true, y_pred, p_dropout))
    for _ in range(n):
        i = rng.integers(0, len(y_true), len(y_true))
        f1s.append(f1_score(y_true[i], y_pred[i], labels=config.CLASSES, average="macro", zero_division=0))
        d = y_true[i] == config.RISK_CLASS
        if d.any():
            recalls.append(float((p_dropout[i][d] >= threshold).mean()))
    q = lambda v: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)] if v else None
    return {"f1_macro_ic95": q(f1s), "rappel_alerte_ic95": q(recalls)}


def verdict(res: dict) -> str:
    """Règle de décision proposée par le binôme (seuils choisis par nous, à discuter avec l'encadrante)."""
    if res["n_evaluables"] < MIN_KNOWN or res["n_dropout"] < MIN_DROPOUT:
        return (f"Données insuffisantes pour conclure ({res['n_evaluables']} réponses évaluables, "
                f"{res['n_dropout']} abandons). Continuer la collecte : objectif au moins 100 réponses dont 30 abandons.")
    ok_recall = res["alerte_risque_moyen"]["rappel"] >= 0.80
    ok_f1 = res["f1_macro"] >= res["reference_portugal"]["f1_macro"] - 0.10
    if ok_recall and ok_f1:
        return "Performances proches du cas portugais : le modèle peut être testé à titre expérimental, à confirmer."
    return ("Écart important avec le cas portugais : il faut ré-entraîner le modèle avec des données tunisiennes "
            "(les réponses collectées peuvent servir de base).")


def evaluate(X: pd.DataFrame, y: pd.Series) -> dict:
    out = {"date": datetime.now().isoformat(timespec="seconds"), "n_reponses": int(len(X)),
           "n_statut_connu": int(y.notna().sum()),
           "statuts": {k: int(v) for k, v in y.value_counts().items()}, "scenarios": {}}
    for scen, spec in config.SCENARIOS.items():
        feats = spec["features"]
        bundle = load_bundle(scen)
        complete = X[feats].notna().all(axis=1)
        res = {"label": spec["label"], "modele": bundle["model_label"], "n_complets": int(complete.sum())}
        if complete.any():
            pred_all = predict(X.loc[complete, feats], scen)
            res["niveaux_risque_tous"] = {k: int(v) for k, v in pred_all["niveau_risque"].value_counts()
                                          .reindex(RISK_LEVELS, fill_value=0).items()}
        mask = complete & y.notna()
        res["n_evaluables"] = int(mask.sum())
        res["n_dropout"] = int((y[mask] == config.RISK_CLASS).sum())
        ref = bundle["test_metrics"]
        res["reference_portugal"] = {"f1_macro": ref["f1_macro"], "accuracy": ref["accuracy"],
                                     "recall_dropout": ref["recall_dropout"]}
        if mask.any():
            p = predict(X.loc[mask, feats], scen)
            yt, yp = y[mask].values, p["statut_predit"].values
            thr = bundle["thresholds"]["seuil_moyen"]
            res.update({
                "accuracy": accuracy_score(yt, yp),
                "f1_macro": f1_score(yt, yp, labels=config.CLASSES, average="macro", zero_division=0),
                "recall_dropout": float((yp[yt == config.RISK_CLASS] == config.RISK_CLASS).mean()) if res["n_dropout"] else None,
                "confusion_matrix": confusion_matrix(yt, yp, labels=config.CLASSES).tolist(),
                "alerte_risque_moyen": dropout_detection_at(yt, p["p_dropout"].values, thr),
                **_bootstrap(yt, yp, p["p_dropout"].values, thr),
            })
            res["verdict"] = verdict(res)
        else:
            res["verdict"] = "Aucune réponse évaluable (statut réel inconnu ou réponses incomplètes)."
        out["scenarios"][scen] = res
    return out


def distribution_shift(X: pd.DataFrame) -> pd.DataFrame:
    """Compare quelques moyennes tunisiennes aux moyennes portugaises (indice de différence entre populations)."""
    from src.data_collection import load_raw
    pt = load_raw()
    rows = []
    for col, label in [("age_at_enrollment", "Âge à l'entrée"), ("admission_grade", "Note d'admission (/200)"),
                       ("scholarship_holder", "Part de boursiers"), ("tuition_fees_up_to_date", "Frais à jour"),
                       ("cu_1st_sem_enrolled", "Modules inscrits S1"), ("cu_1st_sem_approved", "Modules validés S1"),
                       ("cu_1st_sem_grade", "Moyenne S1 (/20)")]:
        rows.append({"variable": label, "Portugal (UCI)": round(float(pt[col].mean()), 2),
                     "Tunisie (formulaire)": round(float(X[col].mean()), 2) if X[col].notna().any() else None})
    return pd.DataFrame(rows)


def run(path) -> dict:
    X, y, extras, issues = map_responses(read_responses(path))
    res = evaluate(X, y)
    res["problemes_conversion"] = issues
    res["source"] = Path(path).name
    TUNISIA_DIR.mkdir(parents=True, exist_ok=True)
    pd.concat([X, y, extras], axis=1).to_csv(TUNISIA_DIR / "reponses_converties.csv", index=False)
    config.METRICS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    return res


# ---------------------------------------------------------------------------------------- données FICTIVES
def fictitious_responses(n: int = 120, seed: int = 0) -> pd.DataFrame:
    """Réponses INVENTÉES, au format de l'export Google Sheets, pour tester le code et la démonstration.
    Elles ne représentent aucun étudiant réel et ne doivent jamais être présentées comme des résultats."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        status = rng.choice(["J'ai obtenu le diplôme de cette formation",
                             "J'ai quitté cette formation sans le diplôme (abandon, réorientation, autre établissement)",
                             "Je suis encore inscrit(e) et j'ai dépassé la durée normale (redoublement)",
                             "Je suis encore inscrit(e), dans la durée normale"], p=[.45, .3, .15, .1])
        drop = status.startswith("J'ai quitté")
        enrolled = int(rng.integers(6, 10))
        approved = int(np.clip(rng.normal(2.5 if drop else enrolled - 1, 1.5), 0, enrolled))
        did_s2 = not (drop and rng.random() < 0.4)
        r = {"Horodateur": "2026/11/20 10:00:00", "consentement": "Oui, j'accepte",
             "repondant": "Je réponds pour moi-même (étudiant ou ancien étudiant)",
             "annee_entree": str(int(rng.integers(2016, 2024))),
             "filiere": rng.choice(list(choices_of(question("filiere")))[:4]),
             "genre": rng.choice(["Homme", "Femme"]), "age_entree": str(int(rng.integers(18, 24))),
             "etat_civil": "Célibataire", "nationalite": "Tunisienne", "diplome_avant": "Baccalauréat",
             "section_bac": rng.choice(["Mathématiques", "Sciences de l'informatique", "Sciences techniques"]),
             "moyenne_bac": f"{rng.normal(12 if drop else 13.5, 1.5):.2f}".replace(".", rng.choice([".", ","])),
             "mode_admission": "Orientation universitaire - 1er tour", "rang_choix": str(int(rng.integers(1, 8))),
             "regime": "Cours du jour", "niveau_mere": rng.choice(list(choices_of(question("niveau_mere")))),
             "niveau_pere": rng.choice(list(choices_of(question("niveau_pere")))),
             "profession_mere": rng.choice(list(choices_of(question("profession_mere")))),
             "profession_pere": rng.choice(list(choices_of(question("profession_pere")))),
             "loge_hors_famille": rng.choice(["Oui", "Non"]), "besoins_specifiques": "Non",
             "boursier": rng.choice(["Oui", "Non"], p=[.2, .8] if drop else [.4, .6]),
             "frais_a_jour": rng.choice(["Oui", "Non"], p=[.7, .3] if drop else [.97, .03]),
             "dette": rng.choice(["Oui", "Non"], p=[.25, .75] if drop else [.05, .95]),
             "s1_inscrits": str(enrolled), "s1_credites": "0", "s1_evaluations": str(enrolled + int(rng.integers(0, 3))),
             "s1_valides": str(approved), "s1_moyenne": f"{np.clip(rng.normal(8 if drop else 12, 2), 0, 20):.2f}",
             "s1_sans_eval": str(int(rng.integers(0, 3)) if drop else 0),
             "s2_fait": "Oui" if did_s2 else "Non", "statut": status}
        if did_s2:
            a2 = int(np.clip(approved + rng.integers(-2, 2), 0, enrolled))
            r.update({"s2_inscrits": str(enrolled), "s2_credites": "0", "s2_evaluations": str(enrolled),
                      "s2_valides": str(a2), "s2_moyenne": f"{np.clip(rng.normal(8 if drop else 12, 2), 0, 20):.2f}",
                      "s2_sans_eval": "0"})
        rows.append(r)
    # Comme un vrai export Google Sheets : toutes les questions en colonnes, vides si sans réponse.
    df = pd.DataFrame(rows).reindex(columns=["Horodateur"] + [q["id"] for q in all_questions()]).fillna("")
    return df.rename(columns={q["id"]: q["title"] for q in all_questions()})


def main() -> None:
    parser = argparse.ArgumentParser(description="Évaluer le modèle sur les réponses du formulaire tunisien")
    parser.add_argument("--csv", required=True, help="export CSV de la feuille Google Sheets des réponses")
    res = run(parser.parse_args().csv)
    print(f"{res['n_reponses']} réponses, {res['n_statut_connu']} avec statut connu {res['statuts']}")
    for issue in res["problemes_conversion"]:
        print("  !", issue)
    for scen, r in res["scenarios"].items():
        print(f"\n[{r['label']}] {r['n_evaluables']} évaluables dont {r['n_dropout']} abandons")
        if "f1_macro" in r:
            a = r["alerte_risque_moyen"]
            print(f"  macro-F1 {r['f1_macro']:.3f} (Portugal {r['reference_portugal']['f1_macro']:.3f}) | "
                  f"rappel alerte {a['rappel']:.2f} | IC95 % {r['rappel_alerte_ic95']}")
        print("  ->", r["verdict"])
    print(f"\nRésultats : {RESULTS_PATH.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
