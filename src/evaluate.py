"""Métriques d'évaluation, seuils de risque, analyse d'équité et graphiques d'évaluation."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             classification_report, confusion_matrix, f1_score, fbeta_score,
                             precision_recall_curve, roc_auc_score, roc_curve)

from src import config
from src.eda import INK, INK_MUTED, _save

RISK_LEVELS = ["Risque faible", "Risque moyen", "Risque élevé"]


def compute_metrics(y_true, y_pred, proba: np.ndarray, classes) -> dict:
    """Toutes les métriques sur un jeu de données (proba : colonnes dans l'ordre de `classes`)."""
    classes = list(classes)
    d = classes.index(config.RISK_CLASS)
    report = classification_report(y_true, y_pred, labels=classes, output_dict=True, zero_division=0)
    is_dropout = (np.asarray(y_true) == config.RISK_CLASS).astype(int)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted"),
        "roc_auc_ovr_macro": roc_auc_score(y_true, proba, multi_class="ovr", average="macro", labels=classes),
        "roc_auc_dropout": roc_auc_score(is_dropout, proba[:, d]),
        "pr_auc_dropout": average_precision_score(is_dropout, proba[:, d]),
        "per_class": {c: {k: report[c][k] for k in ("precision", "recall", "f1-score", "support")} for c in classes},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
    }


def risk_thresholds(y_true, p_dropout, target_recall: float = 0.90) -> dict:
    """Seuils sur P(Dropout), calculés sur des prédictions hors-échantillon (out-of-fold) de l'entraînement :
    - seuil_eleve : maximise le F1 de la détection Dropout-vs-reste (alerte prioritaire) ;
    - seuil_moyen : plus grand seuil garantissant un rappel >= target_recall (filet de sécurité contre les
      faux négatifs, conformément à l'énoncé)."""
    y = (np.asarray(y_true) == config.RISK_CLASS).astype(int)
    precision, recall, thr = precision_recall_curve(y, p_dropout)
    f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    high = float(thr[np.argmax(f1)])
    ok = thr[recall[:-1] >= target_recall]
    medium = float(ok.max()) if len(ok) else float(thr.min())
    if medium >= high:
        medium = high * 0.6
    return {"seuil_moyen": round(medium, 4), "seuil_eleve": round(high, 4), "rappel_vise_seuil_moyen": target_recall}


def risk_level(p_dropout: float | np.ndarray, thresholds: dict):
    levels = np.where(np.asarray(p_dropout) >= thresholds["seuil_eleve"], RISK_LEVELS[2],
                      np.where(np.asarray(p_dropout) >= thresholds["seuil_moyen"], RISK_LEVELS[1], RISK_LEVELS[0]))
    return levels.item() if levels.ndim == 0 else levels


def risk_level_table(y_true, p_dropout, thresholds: dict) -> pd.DataFrame:
    """Pour chaque niveau : effectif, taux réel d'abandon, et part des Dropout captés en cumulé."""
    levels = pd.Series(risk_level(p_dropout, thresholds), name="niveau")
    is_d = pd.Series(np.asarray(y_true) == config.RISK_CLASS)
    tab = pd.DataFrame({"effectif": levels.value_counts(), "dropouts": is_d.groupby(levels).sum()}).reindex(RISK_LEVELS).fillna(0)
    tab["taux_abandon_reel"] = tab["dropouts"] / tab["effectif"].replace(0, np.nan)
    tab["part_des_dropouts"] = tab["dropouts"] / is_d.sum()
    return tab


def dropout_detection_at(y_true, p_dropout, threshold: float) -> dict:
    y = (np.asarray(y_true) == config.RISK_CLASS)
    flagged = np.asarray(p_dropout) >= threshold
    tp, fn, fp = int((flagged & y).sum()), int((~flagged & y).sum()), int((flagged & ~y).sum())
    return {"seuil": threshold, "rappel": tp / max(tp + fn, 1), "precision": tp / max(tp + fp, 1),
            "f2": fbeta_score(y, flagged, beta=2), "faux_negatifs": fn, "faux_positifs": fp,
            "part_signalee": float(flagged.mean())}


def fairness_report(X_test: pd.DataFrame, y_true, p_dropout, threshold: float) -> pd.DataFrame:
    """Rappel / taux de faux négatifs de l'alerte (P(Dropout) >= seuil) par sous-groupe sensible."""
    groups = {
        "Sexe": X_test["gender"].map({1: "Homme", 0: "Femme"}),
        "Âge": pd.cut(X_test["age_at_enrollment"], [0, 20, 25, 100], labels=["≤20", "21-25", ">25"]).astype(str),
        "Boursier": X_test["scholarship_holder"].map({1: "Oui", 0: "Non"}),
        "International": X_test["international"].map({1: "Oui", 0: "Non"}),
    }
    y = pd.Series(np.asarray(y_true) == config.RISK_CLASS, index=X_test.index)
    flagged = pd.Series(np.asarray(p_dropout) >= threshold, index=X_test.index)
    rows = []
    for gname, g in groups.items():
        for val in sorted(g.unique()):
            m = g == val
            tp, pos = int((flagged & y & m).sum()), int((y & m).sum())
            fp, neg = int((flagged & ~y & m).sum()), int((~y & m).sum())
            rows.append({"attribut": gname, "groupe": val, "effectif": int(m.sum()), "dropouts": pos,
                         "rappel": tp / pos if pos else np.nan, "taux_faux_negatifs": 1 - tp / pos if pos else np.nan,
                         "taux_faux_positifs": fp / neg if neg else np.nan, "part_signalee": float(flagged[m].mean())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- graphiques
def plot_confusion(cm, classes, title: str, filename: str) -> None:
    cm = np.asarray(cm)
    pct = cm / cm.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(pct, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, f"{cm[i, j]}\n{pct[i, j]:.0%}", ha="center", va="center", fontsize=9,
                    color="white" if pct[i, j] > 0.55 else INK)
    ax.set_xticks(range(len(classes)), classes); ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Classe prédite"); ax.set_ylabel("Classe réelle"); ax.grid(False)
    ax.set_title(title, fontsize=10)
    _save(fig, filename)


def plot_model_comparison(cv_table: pd.DataFrame, filename: str) -> None:
    """Macro-F1 et rappel Dropout (validation croisée) par modèle, pour chaque scénario."""
    model_colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    models = [m for m in cv_table["model"].unique() if m != "baseline_majority"]
    scen = list(cv_table["scenario"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    width = 0.8 / len(models)
    for ax, metric, title in zip(axes, ["cv_f1_macro", "cv_recall_dropout"],
                                 ["Macro-F1 (validation croisée 5 plis)", "Rappel Dropout (validation croisée 5 plis)"]):
        for k, (m, col) in enumerate(zip(models, model_colors)):
            sub = cv_table[cv_table["model"] == m].set_index("scenario").reindex(scen)
            x = np.arange(len(scen)) + (k - (len(models) - 1) / 2) * width
            ax.bar(x, sub[metric], width=width - 0.02, color=col, label=sub["model_label"].iloc[0],
                   yerr=sub[metric.replace("cv_", "cv_std_")], ecolor=INK_MUTED, capsize=2)
        ax.set_xticks(range(len(scen)), [s.replace("_", " ") for s in scen])
        ax.set_ylim(0, 1); ax.set_title(title); ax.grid(axis="x", visible=False)
    axes[0].legend(fontsize=8, frameon=False, loc="lower left", ncol=2, bbox_to_anchor=(0, -0.32))
    _save(fig, filename)


def plot_roc_pr(curves: dict, filename: str) -> None:
    """Courbes ROC et précision-rappel de la détection Dropout pour le modèle retenu de chaque scénario."""
    colors = ["#2a78d6", "#eb6834", "#1baf7a"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for (scen, (y, p)), col in zip(curves.items(), colors):
        fpr, tpr, _ = roc_curve(y, p)
        prec, rec, _ = precision_recall_curve(y, p)
        lab = config.SCENARIOS[scen]["label"]
        axes[0].plot(fpr, tpr, color=col, lw=2, label=f"{lab} (AUC={roc_auc_score(y, p):.3f})")
        axes[1].plot(rec, prec, color=col, lw=2, label=f"{lab} (AP={average_precision_score(y, p):.3f})")
    axes[0].plot([0, 1], [0, 1], ls="--", color=INK_MUTED, lw=1)
    axes[0].set(xlabel="Taux de faux positifs", ylabel="Rappel (taux de vrais positifs)", title="ROC - détection Dropout")
    axes[1].set(xlabel="Rappel", ylabel="Précision", title="Précision-Rappel - détection Dropout")
    for ax in axes:
        ax.legend(fontsize=8, frameon=False, loc="lower right" if ax is axes[0] else "lower left")
    _save(fig, filename)


def plot_importance(imp: pd.DataFrame, title: str, filename: str) -> None:
    top = imp.head(15)[::-1]
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.barh(top["variable"], top["importance_mean"], xerr=top["importance_std"], color="#2a78d6",
            ecolor=INK_MUTED, height=0.65)
    ax.set_xlabel("Baisse du macro-F1 quand la variable est permutée")
    ax.set_title(title, fontsize=10); ax.grid(axis="y", visible=False)
    _save(fig, filename)
