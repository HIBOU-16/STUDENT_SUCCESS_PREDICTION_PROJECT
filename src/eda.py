"""Étape 2 - Analyse exploratoire et visualisation.

Produit dans reports/ :
  metrics/eda_summary.json            chiffres clés réutilisés par le rapport et l'application
  metrics/descriptive_by_class.csv    moyennes des variables numériques par statut
  metrics/statistical_tests.csv       tests Kruskal-Wallis / Chi² + tailles d'effet, triés
  figures/eda_*.png                   visualisations

Usage :  python -m src.eda
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import mutual_info_classif

from src import config
from src.data_collection import LABELS, load_raw
from src.features import FeatureEngineer

# Palette catégorielle validée (ordre fixe) : une couleur par statut, identique dans toutes les figures.
CLASS_COLORS = {"Dropout": "#2a78d6", "Enrolled": "#eb6834", "Graduate": "#1baf7a"}
INK, INK_MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight", "font.size": 10,
    "axes.edgecolor": INK_MUTED, "axes.labelcolor": INK, "xtick.color": INK_MUTED, "ytick.color": INK_MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 11,
})


def _save(fig, name: str) -> None:
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / name, facecolor="white")
    plt.close(fig)


def dropout_rate_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.groupby(col, observed=True)[config.TARGET]
    return pd.DataFrame({"effectif": g.size(), "taux_dropout": g.apply(lambda s: (s == "Dropout").mean())})


def statistical_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Association de chaque variable avec la cible.
    Numériques : Kruskal-Wallis (non paramétrique) + epsilon² ; catégorielles/binaires : Chi² + V de Cramér."""
    rows, y = [], df[config.TARGET]
    for c in [c for c in df.columns if c != config.TARGET]:
        if c in config.NOMINAL or c in config.BINARY:
            table = pd.crosstab(df[c], y)
            chi2, p, _, _ = stats.chi2_contingency(table)
            effect = np.sqrt(chi2 / (table.values.sum() * (min(table.shape) - 1)))
            rows.append({"variable": c, "test": "Chi2", "statistique": chi2, "p_value": p,
                         "taille_effet": effect, "mesure_effet": "V de Cramér"})
        else:
            groups = [df.loc[y == k, c] for k in config.CLASSES]
            h, p = stats.kruskal(*groups)
            effect = (h - len(groups) + 1) / (len(df) - len(groups))
            rows.append({"variable": c, "test": "Kruskal-Wallis", "statistique": h, "p_value": p,
                         "taille_effet": effect, "mesure_effet": "epsilon²"})
    return pd.DataFrame(rows).sort_values("taille_effet", ascending=False).reset_index(drop=True)


def run() -> dict:
    df = load_raw()
    eng = FeatureEngineer().fit(df[config.FEATURES]).transform(df[config.FEATURES])
    eng[config.TARGET] = df[config.TARGET]
    summary: dict = {"n_rows": len(df), "n_features": len(config.FEATURES)}

    # 1. Distribution des classes ---------------------------------------------------------------
    counts = df[config.TARGET].value_counts().reindex(config.CLASSES)
    summary["class_counts"] = counts.to_dict()
    summary["class_share"] = (counts / len(df)).round(4).to_dict()
    fig, ax = plt.subplots(figsize=(6, 3.6))
    bars = ax.bar(counts.index, counts.values, color=[CLASS_COLORS[c] for c in counts.index], width=0.6)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 30, f"{v}  ({v / len(df):.1%})", ha="center", color=INK)
    ax.set_title("Répartition du statut académique (n = 4 424)")
    ax.set_ylabel("Nombre d'étudiants")
    ax.grid(axis="x", visible=False)
    _save(fig, "eda_01_class_distribution.png")

    # 2. Statistiques descriptives par classe ------------------------------------------------------
    numeric = [c for c in eng.columns if c not in config.NOMINAL + config.BINARY + [config.TARGET]]
    desc = eng.groupby(config.TARGET)[numeric].mean().T.round(3)
    desc.to_csv(config.METRICS_DIR / "descriptive_by_class.csv")
    eng[numeric].describe().T.round(3).to_csv(config.METRICS_DIR / "descriptive_global.csv")

    # 3. Tests statistiques + information mutuelle -> variables les plus pertinentes -----------------
    tests = statistical_tests(eng)
    tests.to_csv(config.METRICS_DIR / "statistical_tests.csv", index=False)
    summary["top_associations"] = tests.head(10)[["variable", "test", "taille_effet"]].round(3).to_dict("records")

    X = eng.drop(columns=config.TARGET)
    discrete = [c in config.NOMINAL + config.BINARY for c in X.columns]
    mi = pd.Series(mutual_info_classif(X, eng[config.TARGET], discrete_features=discrete,
                                       random_state=config.RANDOM_STATE), index=X.columns).sort_values()
    mi.to_csv(config.METRICS_DIR / "mutual_information.csv", header=["mutual_information"])
    fig, ax = plt.subplots(figsize=(7, 6))
    top = mi.tail(15)
    colors = ["#2a78d6" if c.startswith("cu_") or c == "grade_trend" else "#86b6ef" for c in top.index]
    ax.barh(top.index, top.values, color=colors, height=0.65)
    ax.set_title("Information mutuelle avec le statut (15 premières variables)")
    ax.set_xlabel("Information mutuelle (nats)")
    ax.grid(axis="y", visible=False)
    ax.text(0.99, 0.02, "foncé = résultats semestriels\nclair = connu à l'inscription", transform=ax.transAxes,
            ha="right", va="bottom", color=INK_MUTED, fontsize=8)
    _save(fig, "eda_02_mutual_information.png")
    summary["top_mutual_information"] = mi.tail(10)[::-1].round(4).to_dict()

    # 4. Relation résultats S1 (réussite) / statut --------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, col, title in zip(
        axes,
        ["cu_1st_approval_rate", "cu_1st_sem_grade", "admission_grade"],
        ["Taux d'UE validées au S1", "Moyenne S1 (/20)", "Note d'admission (/200)"],
    ):
        data = [eng.loc[eng[config.TARGET] == k, col] for k in config.CLASSES]
        bp = ax.boxplot(data, patch_artist=True, widths=0.55, medianprops={"color": INK, "linewidth": 1.5},
                        flierprops={"markersize": 2, "markerfacecolor": INK_MUTED, "markeredgecolor": "none"})
        for patch, k in zip(bp["boxes"], config.CLASSES):
            patch.set_facecolor(CLASS_COLORS[k]); patch.set_alpha(0.85); patch.set_edgecolor("white")
        ax.set_xticks(range(1, 4), config.CLASSES)
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Résultats académiques selon le statut final", fontweight="bold")
    _save(fig, "eda_03_academic_results_by_status.png")
    summary["median_by_class"] = {col: eng.groupby(config.TARGET)[col].median().round(3).to_dict()
                                  for col in ["cu_1st_approval_rate", "cu_1st_sem_grade", "cu_2nd_approval_rate",
                                              "admission_grade", "age_at_enrollment"]}

    # 5. Engagement / "assiduité" (proxies) et réussite ----------------------------------------------
    eng["s1_engagement"] = pd.cut(eng["cu_1st_eval_per_unit"], [-0.01, 0, 1, 1.5, 100],
                                  labels=["0 éval.", "≤1 éval./UE", "1-1,5", ">1,5"])
    eng["s1_no_eval"] = np.where(eng["cu_1st_sem_without_evaluations"] > 0, "≥1 UE sans évaluation", "Aucune")
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), gridspec_kw={"wspace": 0.75})
    for ax, col, title in zip(axes, ["s1_engagement", "s1_no_eval"],
                              ["Évaluations passées par UE inscrite (S1)", "UE sans aucune évaluation (S1)"]):
        tab = pd.crosstab(eng[col], eng[config.TARGET], normalize="index")[config.CLASSES]
        n = eng[col].value_counts().reindex(tab.index)
        left = np.zeros(len(tab))
        for k in config.CLASSES:
            ax.barh(range(len(tab)), tab[k], left=left, color=CLASS_COLORS[k], label=k,
                    edgecolor="white", linewidth=2, height=0.6)
            for i, (l, v) in enumerate(zip(left, tab[k])):
                if v > 0.08:
                    ax.text(l + v / 2, i, f"{v:.0%}", ha="center", va="center", color="white", fontsize=8)
            left += tab[k].values
        ax.set_yticks(range(len(tab)), [f"{i} (n={c})" for i, c in zip(tab.index, n)])
        ax.set_xlim(0, 1); ax.set_title(title); ax.grid(visible=False)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    axes[0].legend(ncol=3, loc="lower center", bbox_to_anchor=(1.2, -0.32), frameon=False)
    _save(fig, "eda_04_engagement_proxies.png")
    summary["dropout_rate_engagement_s1"] = dropout_rate_by(eng, "s1_engagement")["taux_dropout"].round(3).to_dict()
    summary["dropout_rate_no_eval_s1"] = dropout_rate_by(eng, "s1_no_eval")["taux_dropout"].round(3).to_dict()

    # 6. Facteurs socio-économiques connus à l'inscription -----------------------------------------
    factors = {"tuition_fees_up_to_date": "Frais à jour", "debtor": "Débiteur", "scholarship_holder": "Boursier",
               "gender": "Homme", "displaced": "Déplacé", "daytime_evening_attendance": "Cours du jour"}
    rates = {lab: dropout_rate_by(df, col)["taux_dropout"] for col, lab in factors.items()}
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = list(rates)
    y = np.arange(len(labels))
    ax.barh(y + 0.18, [rates[l].get(1, np.nan) for l in labels], height=0.34, color="#2a78d6", label="Oui (=1)")
    ax.barh(y - 0.18, [rates[l].get(0, np.nan) for l in labels], height=0.34, color="#86b6ef", label="Non (=0)")
    ax.axvline((df[config.TARGET] == "Dropout").mean(), color=INK_MUTED, ls="--", lw=1)
    ax.text((df[config.TARGET] == "Dropout").mean(), len(labels) - 0.4, " taux global", color=INK_MUTED, fontsize=8)
    ax.set_yticks(y, labels); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_title("Taux d'abandon selon les facteurs binaires"); ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", visible=False)
    _save(fig, "eda_05_dropout_rate_binary_factors.png")
    summary["dropout_rate_binary"] = {lab: {int(k): round(float(v), 3) for k, v in r.items()} for lab, r in rates.items()}

    # 7. Âge et cursus --------------------------------------------------------------------------------
    eng["age_band"] = pd.cut(df["age_at_enrollment"], [0, 20, 25, 30, 40, 100],
                             labels=["≤20", "21-25", "26-30", "31-40", ">40"])
    by_age = dropout_rate_by(eng, "age_band")
    by_course = dropout_rate_by(df, "course").sort_values("taux_dropout")
    by_course.index = [LABELS["course"].get(c, c) for c in by_course.index]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.6]})
    axes[0].bar(by_age.index.astype(str), by_age["taux_dropout"], color="#2a78d6", width=0.6)
    for i, (r, n) in enumerate(zip(by_age["taux_dropout"], by_age["effectif"])):
        axes[0].text(i, r + 0.01, f"{r:.0%}\nn={n}", ha="center", fontsize=8, color=INK)
    axes[0].set_title("Taux d'abandon par tranche d'âge"); axes[0].grid(axis="x", visible=False)
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    axes[1].barh(by_course.index, by_course["taux_dropout"], color="#2a78d6", height=0.65)
    axes[1].set_title("Taux d'abandon par cursus"); axes[1].grid(axis="y", visible=False)
    axes[1].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    _save(fig, "eda_06_age_and_course.png")
    summary["dropout_rate_age"] = by_age["taux_dropout"].round(3).astype(float).to_dict()

    # 8. Corrélations entre variables numériques (Spearman) -----------------------------------------
    corr_cols = ["admission_grade", "previous_qualification_grade", "age_at_enrollment", "cu_1st_sem_enrolled",
                 "cu_1st_sem_approved", "cu_1st_sem_grade", "cu_1st_approval_rate", "cu_2nd_sem_approved",
                 "cu_2nd_sem_grade", "cu_2nd_approval_rate", "unemployment_rate", "inflation_rate", "gdp"]
    corr = eng[corr_cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_cols)), corr_cols, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr_cols)), corr_cols, fontsize=8)
    for i in range(len(corr_cols)):
        for j in range(len(corr_cols)):
            v = corr.iloc[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5, color="white" if abs(v) > 0.6 else INK)
    ax.grid(False); fig.colorbar(im, ax=ax, fraction=0.04, label="ρ de Spearman")
    ax.set_title("Corrélations (Spearman) entre variables numériques")
    _save(fig, "eda_07_correlations.png")
    summary["corr_s1_s2_grade"] = round(float(corr.loc["cu_1st_sem_grade", "cu_2nd_sem_grade"]), 3)
    summary["corr_s1_s2_approved"] = round(float(corr.loc["cu_1st_sem_approved", "cu_2nd_sem_approved"]), 3)

    # 9. Indicateurs macro-économiques -------------------------------------------------------------
    summary["macro_unique_years"] = int(df[["unemployment_rate", "inflation_rate", "gdp"]].drop_duplicates().shape[0])

    with open(config.METRICS_DIR / "eda_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=float)
    return summary


if __name__ == "__main__":
    config.METRICS_DIR.mkdir(parents=True, exist_ok=True)
    s = run()
    print(json.dumps({k: s[k] for k in ("class_counts", "top_associations", "dropout_rate_binary")},
                     ensure_ascii=False, indent=1, default=float))
