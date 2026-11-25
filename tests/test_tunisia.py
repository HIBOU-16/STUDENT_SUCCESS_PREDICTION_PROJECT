"""Tests du formulaire d'évaluation tunisien : script Google généré, conversion des réponses, évaluation."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config
from src.tunisia import evaluate, fictitious_responses, map_responses, read_responses
from src.tunisia_form import SECTIONS, all_questions

ROOT = Path(__file__).resolve().parents[1]
GS = ROOT / "forms" / "creer_formulaire_google.gs"
pytestmark = pytest.mark.skipif(not (config.MODELS_DIR / "model_C_fin_S2.joblib").exists(),
                                reason="modèles non entraînés : lancer python -m src.train")


def test_generated_script_is_up_to_date():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bgf", ROOT / "forms" / "build_google_form.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert GS.read_text(encoding="utf-8") == mod.build(), "relancer : python forms/build_google_form.py"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js absent")
def test_google_script_runs_on_simulated_formapp():
    out = subprocess.run(["node", str(ROOT / "tests" / "formapp_mock.js"), str(GS)], capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    r = json.loads(out)
    assert r["settings"]["collectEmail"] is False and r["settings"]["destination"]["type"] == "SPREADSHEET"
    questions = [it for it in r["items"] if it["kind"] != "page"]
    assert [q["title"] for q in questions] == [q["title"] for q in all_questions()]
    assert r["pageCount"] == sum(1 for s in SECTIONS if s["title"])
    consent = questions[0]
    assert [c["nav"] for c in consent["choices"]] == ["CONTINUE", "SUBMIT"]
    branch = next(q for q in questions if q["title"].startswith("Avez-vous suivi le 2e semestre"))
    assert [c["nav"]["page"][:2] for c in branch["choices"]] == ["3.", "4."]
    assert all(q["validation"] for q in r["items"] if q["kind"] == "text")


def _one(**overrides):
    df = fictitious_responses(1, seed=3)
    for k, v in overrides.items():
        title = next(q["title"] for q in all_questions() if q["id"] == k)
        df[title] = v
    return df


def test_mapping_follows_documented_conventions(tmp_path):
    df = pd.concat([
        _one(moyenne_bac="13,45", rang_choix="12", s1_valides="0", s1_moyenne="9.5", s2_fait="Non",
             statut="Je suis encore inscrit(e), dans la durée normale"),
        _one(moyenne_bac="15.2", nationalite="Autre nationalité",
             statut="J'ai quitté cette formation sans le diplôme (abandon, réorientation, autre établissement)"),
        _one(consentement="Non, je ne souhaite pas participer"),
    ], ignore_index=True)
    path = tmp_path / "export.csv"; df.to_csv(path, index=False)
    X, y, extras, issues = map_responses(read_responses(path))
    assert len(X) == 2                                   # sans consentement -> ignoré
    assert X.loc[0, "admission_grade"] == pytest.approx(134.5) and X.loc[0, "application_order"] == 9
    assert X.loc[0, "cu_1st_sem_grade"] == 0             # aucun module validé -> moyenne 0 (convention UCI)
    assert X.loc[0, config.SEM2].isna().all()            # S2 non suivi
    assert np.isnan(y[0]) and y[1] == "Dropout"
    assert (X.loc[1, "nationality"], X.loc[1, "international"]) == (100, 1)
    assert list(X.columns) == config.FEATURES and "s1_absences" in extras.columns
    assert any("consentement" in i for i in issues)


def test_unknown_answer_is_reported(tmp_path):
    path = tmp_path / "e.csv"; _one(genre="Autre").to_csv(path, index=False)
    _, _, _, issues = map_responses(read_responses(path))
    assert any(i.startswith("gender") or i.startswith("genre") for i in issues)


def test_evaluation_on_fictitious_data(tmp_path):
    path = tmp_path / "f.csv"; fictitious_responses(80, seed=1).to_csv(path, index=False)
    X, y, _, _ = map_responses(read_responses(path))
    res = evaluate(X, y)
    assert set(res["scenarios"]) == set(config.SCENARIOS)
    b, c = res["scenarios"]["B_fin_S1"], res["scenarios"]["C_fin_S2"]
    assert c["n_evaluables"] <= b["n_evaluables"] == int(y.notna().sum())
    assert 0 <= b["f1_macro"] <= 1 and len(b["confusion_matrix"]) == 3 and b["verdict"]
