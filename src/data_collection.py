"""Étape 1 - Collecte, validation, anonymisation et stockage des données étudiantes.

Fonctions principales :
    load_raw()            lit le CSV UCI (séparateur ';') ou Kaggle (',') et normalise les noms de colonnes
    validate()            vérifie le schéma, les types, les plages de valeurs et la cible
    anonymize()           supprime les identifiants directs, ajoute un pseudo-identifiant, mesure le k-anonymat
    StudentStore          stockage SQLite (bibliothèque standard) des étudiants et des prédictions
    build_data_dictionary() produit le dictionnaire de données (CSV)

Usage en ligne de commande :  python -m src.data_collection
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src import config

# ---------------------------------------------------------------------------
# Libellés des codes (documentation UCI, Realinho et al., 2022)
# ---------------------------------------------------------------------------
LABELS = {
    "course": {
        33: "Biofuel Production Technologies", 171: "Animation and Multimedia Design",
        8014: "Social Service (evening)", 9003: "Agronomy", 9070: "Communication Design",
        9085: "Veterinary Nursing", 9119: "Informatics Engineering", 9130: "Equinculture",
        9147: "Management", 9238: "Social Service", 9254: "Tourism", 9500: "Nursing",
        9556: "Oral Hygiene", 9670: "Advertising and Marketing Management",
        9773: "Journalism and Communication", 9853: "Basic Education", 9991: "Management (evening)",
    },
    "marital_status": {1: "Célibataire", 2: "Marié(e)", 3: "Veuf/veuve", 4: "Divorcé(e)",
                       5: "Union libre", 6: "Séparé(e) légalement"},
    "application_mode": {
        1: "1re phase - contingent général", 2: "Ordonnance 612/93", 5: "1re phase - contingent spécial (Açores)",
        7: "Titulaires d'autres diplômes supérieurs", 10: "Ordonnance 854-B/99", 15: "Étudiant international (licence)",
        16: "1re phase - contingent spécial (Madère)", 17: "2e phase - contingent général",
        18: "3e phase - contingent général", 26: "Ordonnance 533-A/99 b2", 27: "Ordonnance 533-A/99 b3",
        39: "Plus de 23 ans", 42: "Transfert", 43: "Changement de cursus",
        44: "Diplôme de spécialisation technologique", 51: "Changement d'établissement/cursus",
        53: "Diplôme de cycle court", 57: "Changement d'établissement/cursus (international)",
    },
    "previous_qualification": {
        1: "Enseignement secondaire", 2: "Licence (bachelor)", 3: "Diplôme supérieur", 4: "Master", 5: "Doctorat",
        6: "Études supérieures suivies", 9: "12e année non terminée", 10: "11e année non terminée",
        12: "Autre - 11e année", 14: "10e année", 15: "10e année non terminée",
        19: "Enseignement de base 3e cycle", 38: "Enseignement de base 2e cycle",
        39: "Cours de spécialisation technologique", 40: "Diplôme supérieur (1er cycle)",
        42: "Cours technique supérieur professionnel", 43: "Master (2e cycle)",
    },
    "nationality": {
        1: "Portugaise", 2: "Allemande", 6: "Espagnole", 11: "Italienne", 13: "Néerlandaise", 14: "Anglaise",
        17: "Lituanienne", 21: "Angolaise", 22: "Cap-verdienne", 24: "Guinéenne", 25: "Mozambicaine",
        26: "Santoméenne", 32: "Turque", 41: "Brésilienne", 62: "Roumaine", 100: "Moldave", 101: "Mexicaine",
        103: "Ukrainienne", 105: "Russe", 108: "Cubaine", 109: "Colombienne",
    },
    "gender": {1: "Homme", 0: "Femme"},
    "daytime_evening_attendance": {1: "Jour", 0: "Soir"},
}
YES_NO = {1: "Oui", 0: "Non"}

DESCRIPTIONS = {
    "marital_status": "Statut marital (code nominal)",
    "application_mode": "Mode de candidature (code nominal)",
    "application_order": "Rang du vœu de l'étudiant (0 = premier choix, 9 = dernier)",
    "course": "Cursus suivi (code nominal)",
    "daytime_evening_attendance": "Cours de jour (1) ou du soir (0)",
    "previous_qualification": "Diplôme obtenu avant l'entrée (code nominal)",
    "previous_qualification_grade": "Note du diplôme précédent (0-200)",
    "nationality": "Nationalité (code nominal)",
    "mother_qualification": "Niveau d'études de la mère (code nominal)",
    "father_qualification": "Niveau d'études du père (code nominal)",
    "mother_occupation": "Profession de la mère (code nominal)",
    "father_occupation": "Profession du père (code nominal)",
    "admission_grade": "Note d'admission (0-200)",
    "displaced": "Étudiant déplacé (logement hors domicile familial) : 1 = oui",
    "educational_special_needs": "Besoins éducatifs particuliers : 1 = oui",
    "debtor": "Étudiant débiteur envers l'établissement : 1 = oui",
    "tuition_fees_up_to_date": "Frais de scolarité à jour : 1 = oui",
    "gender": "Sexe : 1 = homme, 0 = femme",
    "scholarship_holder": "Boursier : 1 = oui",
    "age_at_enrollment": "Âge à l'inscription (années)",
    "international": "Étudiant international : 1 = oui",
    "unemployment_rate": "Taux de chômage national l'année d'entrée (%)",
    "inflation_rate": "Taux d'inflation national l'année d'entrée (%)",
    "gdp": "Croissance du PIB l'année d'entrée (%)",
    config.TARGET: "Statut final : Dropout (abandon), Enrolled (encore inscrit), Graduate (diplômé)",
}
for sem, sem_fr in (("1st", "1er"), ("2nd", "2e")):
    DESCRIPTIONS.update({
        f"cu_{sem}_sem_credited": f"Unités curriculaires créditées (équivalences) au {sem_fr} semestre",
        f"cu_{sem}_sem_enrolled": f"Unités curriculaires inscrites au {sem_fr} semestre",
        f"cu_{sem}_sem_evaluations": f"Nombre d'évaluations passées au {sem_fr} semestre",
        f"cu_{sem}_sem_approved": f"Unités curriculaires validées au {sem_fr} semestre",
        f"cu_{sem}_sem_grade": f"Moyenne des notes au {sem_fr} semestre (0-20)",
        f"cu_{sem}_sem_without_evaluations": f"Unités sans aucune évaluation au {sem_fr} semestre",
    })

# Colonnes identifiantes qui ne doivent jamais être stockées en clair.
DIRECT_IDENTIFIERS = {"name", "nom", "prenom", "first_name", "last_name", "email", "phone", "telephone",
                      "student_id", "id", "matricule", "cin", "address", "adresse", "birth_date"}


def _key(name: str) -> str:
    """Clé de comparaison tolérante : minuscules, sans ponctuation ni espaces (gère BOM et tabulations)."""
    key = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return key.replace("nationality", "nacionality")


_CANONICAL_BY_KEY = {_key(orig): canon for canon, orig in config.COLUMNS.items()}
_CANONICAL_BY_KEY.update({_key(canon): canon for canon in config.COLUMNS})
_CANONICAL_BY_KEY.update({"output": config.TARGET, "status": config.TARGET})


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renomme les colonnes (UCI, Kaggle ou snake_case) vers les noms canoniques du projet."""
    mapping = {c: _CANONICAL_BY_KEY.get(_key(c), c) for c in df.columns}
    return df.rename(columns=mapping)


def load_raw(path: Path | str = config.DATA_RAW) -> pd.DataFrame:
    """Charge le CSV en détectant automatiquement le séparateur (';' pour UCI, ',' pour Kaggle)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {path}\nTéléchargez-le depuis "
            "https://archive.ics.uci.edu/dataset/697 et placez data.csv dans data/raw/students_dropout_uci.csv")
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    df = normalize_columns(df)
    if config.TARGET in df.columns:
        df[config.TARGET] = df[config.TARGET].astype(str).str.strip()
    return df


def validate(df: pd.DataFrame, require_target: bool = True, features: list[str] | None = None) -> list[str]:
    """Renvoie la liste des problèmes détectés (liste vide = données conformes).
    `features` limite le contrôle aux variables d'un scénario (ex. profil saisi à l'inscription)."""
    problems = []
    features = features or config.FEATURES
    expected = features + ([config.TARGET] if require_target else [])
    missing = [c for c in expected if c not in df.columns]
    if missing:
        problems.append(f"Colonnes manquantes : {missing}")
        return problems
    non_numeric = [c for c in features if not pd.api.types.is_numeric_dtype(df[c])]
    if non_numeric:
        problems.append(f"Colonnes non numériques : {non_numeric}")
    na = df[expected].isna().sum()
    if na.any():
        problems.append(f"Valeurs manquantes : {na[na > 0].to_dict()}")
    for c in [c for c in config.BINARY if c in features]:
        if not set(df[c].dropna().unique()) <= {0, 1}:
            problems.append(f"{c} doit être binaire (0/1)")
    for c in [c for c in ("admission_grade", "previous_qualification_grade") if c in features]:
        if ((df[c] < 0) | (df[c] > 200)).any():
            problems.append(f"{c} hors de l'intervalle [0, 200]")
    for c in [c for c in ("cu_1st_sem_grade", "cu_2nd_sem_grade") if c in features]:
        if ((df[c] < 0) | (df[c] > 20)).any():
            problems.append(f"{c} hors de l'intervalle [0, 20]")
    if "age_at_enrollment" in features and ((df["age_at_enrollment"] < 15) | (df["age_at_enrollment"] > 100)).any():
        problems.append("age_at_enrollment hors de l'intervalle [15, 100]")
    for sem in [s for s in ("1st", "2nd") if f"cu_{s}_sem_approved" in features]:
        if (df[f"cu_{sem}_sem_approved"] > df[f"cu_{sem}_sem_enrolled"] + df[f"cu_{sem}_sem_credited"]).any():
            problems.append(f"Semestre {sem} : plus d'unités validées qu'inscrites + créditées")
    if require_target and not set(df[config.TARGET].unique()) <= set(config.CLASSES):
        problems.append(f"Cible inattendue : {sorted(df[config.TARGET].unique())}")
    return problems


def pseudo_id(row_key: str, salt: str = "isi-uvt-projet7") -> str:
    """Pseudo-identifiant non réversible (SHA-256 salé, 12 caractères)."""
    return "ETU-" + hashlib.sha256(f"{salt}:{row_key}".encode()).hexdigest()[:12].upper()


def anonymize(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les identifiants directs et ajoute un pseudo-identifiant."""
    out = df.drop(columns=[c for c in df.columns if _key(c) in {_key(i) for i in DIRECT_IDENTIFIERS}])
    out.insert(0, "pseudo_id", [pseudo_id(str(i)) for i in range(len(out))])
    return out


def k_anonymity(df: pd.DataFrame, quasi_identifiers=("gender", "age_at_enrollment", "nationality", "course")) -> int:
    """Taille du plus petit groupe d'étudiants partageant les mêmes quasi-identifiants."""
    return int(df.groupby(list(quasi_identifiers)).size().min())


def share_below_k(df: pd.DataFrame, k: int = 5,
                  quasi_identifiers=("gender", "age_at_enrollment", "nationality", "course")) -> float:
    """Part des étudiants appartenant à un groupe de quasi-identifiants de taille < k (risque de ré-identification)."""
    sizes = df.groupby(list(quasi_identifiers))[list(quasi_identifiers)[0]].transform("size")
    return float((sizes < k).mean())


def generalize_for_sharing(df: pd.DataFrame) -> pd.DataFrame:
    """Version partageable : âge regroupé en tranches et nationalités rares regroupées."""
    out = df.copy()
    out["age_at_enrollment"] = pd.cut(out["age_at_enrollment"], [0, 20, 25, 30, 40, 100],
                                      labels=["<=20", "21-25", "26-30", "31-40", ">40"]).astype(str)
    out["nationality"] = out["nationality"].where(out["nationality"] == 1, 0)  # 1 = portugaise, 0 = autre
    return out


class StudentStore:
    """Stockage SQLite des profils étudiants et des prédictions (aucun identifiant direct)."""

    def __init__(self, db_path: Path | str = config.DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS predictions (pseudo_id TEXT, created_at TEXT, scenario TEXT, "
                "model TEXT, p_dropout REAL, p_enrolled REAL, p_graduate REAL, risk_level TEXT)")

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def save_students(self, df: pd.DataFrame, source: str, replace: bool = False,
                      features: list[str] | None = None) -> pd.Series:
        """Valide puis enregistre des étudiants et renvoie leurs pseudo-identifiants.
        La cible est facultative ; les variables hors scénario (`features`) sont stockées à NULL."""
        problems = validate(df, require_target=config.TARGET in df.columns, features=features)
        if problems:
            raise ValueError("Données refusées : " + " | ".join(problems))
        data = df.copy()
        if "pseudo_id" not in data.columns:
            stamp = datetime.now().isoformat()
            data.insert(0, "pseudo_id", [pseudo_id(f"{source}:{stamp}:{i}") for i in range(len(data))])
        data["source"] = source
        data["collected_at"] = datetime.now().isoformat(timespec="seconds")
        data = data.reindex(columns=list(dict.fromkeys(list(data.columns) + config.FEATURES + [config.TARGET])))
        cols = ["pseudo_id", "source", "collected_at"] + config.FEATURES + [config.TARGET]
        with self._connect() as con:
            data[cols].to_sql("students", con, if_exists="replace" if replace else "append", index=False)
        return data["pseudo_id"]

    def load_students(self, source: str | None = None) -> pd.DataFrame:
        query, params = "SELECT * FROM students", ()
        if source:
            query, params = query + " WHERE source = ?", (source,)
        with self._connect() as con:
            return pd.read_sql_query(query, con, params=params)

    def save_prediction(self, pseudo: str, scenario: str, model: str, proba: dict, risk_level: str) -> None:
        with self._connect() as con:
            con.execute("INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (pseudo, datetime.now().isoformat(timespec="seconds"), scenario, model,
                         proba["Dropout"], proba["Enrolled"], proba["Graduate"], risk_level))

    def load_predictions(self) -> pd.DataFrame:
        with self._connect() as con:
            return pd.read_sql_query("SELECT * FROM predictions ORDER BY created_at DESC", con)


def build_data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for canon, original in config.COLUMNS.items():
        s = df[canon]
        if canon == config.TARGET:
            kind = "cible (multiclasse)"
        elif canon in config.NOMINAL:
            kind = "catégorielle nominale"
        elif canon in config.BINARY:
            kind = "binaire"
        else:
            kind = "numérique"
        if canon == config.TARGET:
            moment = "fin de parcours"
        elif canon in config.SEM1:
            moment = "fin du 1er semestre"
        elif canon in config.SEM2:
            moment = "fin du 2e semestre"
        else:
            moment = "inscription" + (" (date de mesure ambiguë)" if canon in config.AMBIGUOUS_TIMING else "")
        numeric = pd.api.types.is_numeric_dtype(s)
        rows.append({
            "variable": canon, "nom_original_uci": original, "description": DESCRIPTIONS[canon],
            "type": kind, "disponible_a": moment, "valeurs_distinctes": s.nunique(),
            "min": s.min() if numeric else "", "max": s.max() if numeric else "",
            "exemple_codes": "; ".join(f"{k}={v}" for k, v in list(LABELS.get(canon, YES_NO if canon in config.BINARY else {}).items())[:6]),
        })
    return pd.DataFrame(rows)


def main() -> None:
    df = load_raw()
    problems = validate(df)
    print(f"Dataset : {df.shape[0]} lignes x {df.shape[1]} colonnes")
    print("Validation :", "OK" if not problems else problems)
    print(f"Doublons : {df.duplicated().sum()} | valeurs manquantes : {int(df.isna().sum().sum())}")

    anon = anonymize(df)
    shared = generalize_for_sharing(anon)
    print(f"Part des étudiants dans un groupe < 5 (sexe, âge, nationalité, cursus) : brut {share_below_k(df):.1%}"
          f" -> après généralisation {share_below_k(shared):.1%}")

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.DATA_SAMPLE.mkdir(parents=True, exist_ok=True)
    anon.to_csv(config.DATA_PROCESSED / "students_anonymized.csv", index=False)
    shared.sample(30, random_state=config.RANDOM_STATE).to_csv(
        config.DATA_SAMPLE / "echantillon_anonymise_30.csv", index=False)
    build_data_dictionary(df).to_csv(config.ROOT / "data" / "data_dictionary.csv", index=False, encoding="utf-8-sig")

    store = StudentStore()
    n = len(store.save_students(anon, source="uci_697", replace=True))
    print(f"{n} étudiants enregistrés dans {config.DB_PATH.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
