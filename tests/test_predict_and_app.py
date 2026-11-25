"""Tests des modèles sauvegardés, du module de prédiction et de l'interface (nécessitent `python -m src.train`)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config
from src.data_collection import load_raw
from src.predict import explain, load_bundle, predict
from src.train import split_data

pytestmark = pytest.mark.skipif(not (config.MODELS_DIR / "model_C_fin_S2.joblib").exists(),
                                reason="modèles non entraînés : lancer python -m src.train")
DEMO = config.DATA_SAMPLE / "profils_fictifs_demo.csv"


@pytest.fixture(scope="module")
def test_set():
    return split_data(load_raw())[1]


@pytest.mark.parametrize("scen", list(config.SCENARIOS))
def test_bundle_is_consistent(scen, test_set):
    b = load_bundle(scen)
    assert b["features"] == config.SCENARIOS[scen]["features"]
    assert b["classes"] == config.CLASSES
    assert 0 < b["thresholds"]["seuil_moyen"] < b["thresholds"]["seuil_eleve"] < 1
    res = predict(test_set, scen)
    assert np.allclose(res[["p_dropout", "p_enrolled", "p_graduate"]].sum(1), 1)
    acc = (res["statut_predit"] == test_set[config.TARGET]).mean()
    assert np.isclose(acc, b["test_metrics"]["accuracy"])      # mêmes transformations qu'à l'entraînement


def test_column_order_and_names_do_not_matter(test_set):
    sample = test_set.head(20)
    shuffled = sample[sample.columns[::-1]]
    renamed = sample.rename(columns={c: o for c, o in config.COLUMNS.items()})
    ref = predict(sample, "C_fin_S2")
    pd.testing.assert_frame_equal(ref, predict(shuffled, "C_fin_S2"))
    pd.testing.assert_frame_equal(ref, predict(renamed, "C_fin_S2"))


def test_missing_column_is_reported(test_set):
    with pytest.raises(ValueError, match="cu_1st_sem_grade"):
        predict(test_set.drop(columns="cu_1st_sem_grade").head(2), "B_fin_S1")


def test_demo_profiles_are_ranked_sensibly():
    demo = pd.read_csv(DEMO)
    assert demo["pseudo_id"].str.startswith("FICTIF").all()
    for scen in config.SCENARIOS:
        p = predict(demo, scen)["p_dropout"].values
        assert p[0] < p[1] < p[2]


def test_local_explanation_returns_factors():
    demo = pd.read_csv(DEMO)
    ex = explain(demo.iloc[[2]], "B_fin_S1")
    assert len(ex) > 0 and {"variable", "valeur", "contribution"} <= set(ex.columns)
    assert ex["contribution"].abs().is_monotonic_decreasing


def test_streamlit_app_runs_without_error():
    from streamlit.testing.v1 import AppTest
    app = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=120).run()
    assert not at.exception
    for page in ["Données & EDA", "Modèles & résultats", "Prédiction", "Historique", "Évaluation Tunisie",
                 "Limites & éthique"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
    at.sidebar.radio[0].set_value("Prédiction").run()
    at.button[0].click().run()                              # "Estimer le risque" sur le profil par défaut
    assert not at.exception
    assert any("probabilité estimée de décrochage" in e.value for e in [*at.success, *at.warning, *at.error])
