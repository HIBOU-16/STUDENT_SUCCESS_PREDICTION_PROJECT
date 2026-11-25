"""Tests de l'Étape 1 : chargement, validation, anonymisation, stockage."""
import pandas as pd
import pytest

from src import config
from src.data_collection import (StudentStore, anonymize, build_data_dictionary, load_raw, normalize_columns,
                                 share_below_k, validate)


@pytest.fixture(scope="module")
def df():
    return load_raw()


def test_dataset_matches_documentation(df):
    assert df.shape == (4424, 37)
    assert df[config.TARGET].value_counts().to_dict() == {"Graduate": 2209, "Dropout": 1421, "Enrolled": 794}
    assert df.isna().sum().sum() == 0
    assert validate(df) == []


def test_column_names_are_normalized(df):
    assert list(df.columns) == list(config.COLUMNS)   # tabulation, BOM et "Nacionality" gérés


def test_kaggle_style_file_is_accepted(df, tmp_path):
    kaggle = df.rename(columns={c: o for c, o in config.COLUMNS.items()}).rename(
        columns={"Nacionality": "Nationality", "Daytime/evening attendance": "Daytime/evening attendance\t"})
    path = tmp_path / "kaggle.csv"
    kaggle.to_csv(path, index=False)          # séparateur ','
    again = load_raw(path)
    assert list(again.columns) == list(config.COLUMNS)
    pd.testing.assert_frame_equal(again, df)


def test_validate_detects_problems(df):
    bad = df.head(20).copy()
    bad.loc[0, "gender"] = 3
    bad.loc[1, "cu_1st_sem_grade"] = 25
    bad.loc[2, config.TARGET] = "Unknown"
    problems = " ".join(validate(bad))
    assert "gender" in problems and "cu_1st_sem_grade" in problems and "Cible" in problems
    assert "Colonnes manquantes" in validate(bad.drop(columns="course"))[0]


def test_validate_scenario_subset(df):
    subset = config.SCENARIOS["A_inscription"]["features"]
    assert validate(df[subset], require_target=False, features=subset) == []


def test_anonymize_removes_direct_identifiers(df):
    raw = df.head(5).assign(nom=["a", "b", "c", "d", "e"], email="x@y.z")
    anon = anonymize(raw)
    assert "nom" not in anon.columns and "email" not in anon.columns
    assert anon["pseudo_id"].is_unique and anon["pseudo_id"].str.startswith("ETU-").all()
    assert 0 <= share_below_k(df) <= 1


def test_store_roundtrip(df, tmp_path):
    store = StudentStore(tmp_path / "t.db")
    ids = store.save_students(df.head(10), source="test")
    assert len(ids) == 10
    profile = df[config.SCENARIOS["A_inscription"]["features"]].head(1)
    pid = store.save_students(profile, source="interface", features=list(profile.columns)).iloc[0]
    loaded = store.load_students()
    assert len(loaded) == 11
    assert loaded.loc[loaded.pseudo_id == pid, "cu_1st_sem_grade"].isna().all()   # pas de zéros inventés
    store.save_prediction(pid, "A_inscription", "m", {"Dropout": .5, "Enrolled": .2, "Graduate": .3}, "Risque élevé")
    assert store.load_predictions().iloc[0]["risk_level"] == "Risque élevé"


def test_store_rejects_invalid_data(df, tmp_path):
    bad = df.head(3).copy()
    bad.loc[0, "debtor"] = 7
    with pytest.raises(ValueError):
        StudentStore(tmp_path / "t.db").save_students(bad, source="test")


def test_data_dictionary_is_complete(df):
    dd = build_data_dictionary(df)
    assert len(dd) == 37 and dd["description"].str.len().gt(5).all()
    assert normalize_columns(pd.DataFrame(columns=["Output"])).columns[0] == config.TARGET
