"""Tests méthodologiques : fuite de données, SMOTE, protocole de sélection, seuils de risque."""
import numpy as np
import pandas as pd
import pytest
from imblearn.over_sampling import SMOTE

from src import config
from src.data_collection import load_raw
from src.evaluate import risk_level, risk_thresholds
from src.features import FeatureEngineer, build_preprocessor, engineered_columns
from src.models import build_models
from src.train import select_retained, split_data


@pytest.fixture(scope="module")
def df():
    return load_raw()


def test_scenarios_do_not_leak_future_information():
    a, b, c = (config.SCENARIOS[k]["features"] for k in ("A_inscription", "B_fin_S1", "C_fin_S2"))
    assert not any(f.startswith("cu_") for f in a)
    assert not any(f.startswith("cu_2nd") for f in b) and any(f.startswith("cu_1st") for f in b)
    assert set(c) == set(config.FEATURES) and config.TARGET not in c
    assert "grade_trend" not in engineered_columns(b) and "grade_trend" in engineered_columns(c)


def test_feature_engineering_handles_zero_enrolled():
    X = pd.DataFrame({"cu_1st_sem_enrolled": [0, 5], "cu_1st_sem_approved": [0, 4], "cu_1st_sem_evaluations": [0, 6]})
    out = FeatureEngineer().fit(X).transform(X)
    assert out["cu_1st_approval_rate"].tolist() == [0.0, 0.8]
    assert np.isfinite(out["cu_1st_eval_per_unit"]).all()


def test_preprocessor_is_fitted_on_train_only_and_tolerates_unknown_codes(df):
    feats = config.SCENARIOS["A_inscription"]["features"]
    train, test = split_data(df)
    pipe = build_preprocessor(feats)
    pipe.fit(FeatureEngineer().fit(train[feats]).transform(train[feats]))
    new = test[feats].head(1).copy()
    new["course"] = 123456                     # code jamais vu
    Xt = pipe.transform(FeatureEngineer().fit(new).transform(new))
    assert Xt.shape[0] == 1 and np.isfinite(Xt).all()
    scaler = pipe.named_transformers_["numeric"]
    assert np.isclose(scaler.mean_[list(scaler.feature_names_in_).index("admission_grade")],
                      train["admission_grade"].mean())


def test_split_is_stratified_and_reproducible(df):
    tr1, te1 = split_data(df)
    _, te2 = split_data(df)
    assert len(te1) == 885 and te1.index.equals(te2.index)
    assert te1[config.TARGET].value_counts().to_dict() == {"Graduate": 442, "Dropout": 284, "Enrolled": 159}
    assert not set(tr1.index) & set(te1.index)


class SpySMOTE(SMOTE):
    calls = []

    def fit_resample(self, X, y):
        SpySMOTE.calls.append(len(X))
        return super().fit_resample(X, y)


def test_smote_is_applied_only_during_training(df):
    feats = config.SCENARIOS["B_fin_S1"]["features"]
    train, test = split_data(df)
    pipe, _ = build_models(feats)["random_forest_smote"]
    pipe.set_params(smote=SpySMOTE(sampling_strategy="not majority", random_state=0), clf__n_estimators=20)
    SpySMOTE.calls.clear()
    pipe.fit(train[feats], train[config.TARGET])
    assert SpySMOTE.calls == [len(train)]
    proba = pipe.predict_proba(test[feats])
    assert SpySMOTE.calls == [len(train)]          # aucun ré-échantillonnage du test
    assert proba.shape == (len(test), 3) and np.allclose(proba.sum(1), 1)


def test_selection_rule_prefers_dropout_recall_within_tolerance():
    rows = [{"model": "baseline_majority", "cv_f1_macro": .2, "cv_recall_dropout": 0},
            {"model": "a", "cv_f1_macro": .72, "cv_recall_dropout": .70},
            {"model": "b", "cv_f1_macro": .71, "cv_recall_dropout": .76},
            {"model": "c", "cv_f1_macro": .60, "cv_recall_dropout": .90}]
    assert select_retained(rows) == "b"


def test_risk_thresholds_are_ordered_and_reach_target_recall():
    rng = np.random.default_rng(0)
    y = np.array(["Dropout"] * 300 + ["Graduate"] * 700)
    p = np.clip(np.r_[rng.normal(.6, .2, 300), rng.normal(.25, .15, 700)], 0, 1)
    t = risk_thresholds(y, p)
    assert t["seuil_moyen"] < t["seuil_eleve"]
    assert ((p >= t["seuil_moyen"]) & (y == "Dropout")).sum() / 300 >= 0.90
    assert risk_level(0.0, t) == "Risque faible" and risk_level(1.0, t) == "Risque élevé"
