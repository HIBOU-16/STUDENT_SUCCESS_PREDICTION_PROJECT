"""Génère le schéma d'architecture (docs/architecture.png) : python docs/make_architecture.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BLUE, LIGHT, INK, MUTED = "#2a78d6", "#cde2fb", "#0b0b0b", "#52514e"
fig, ax = plt.subplots(figsize=(13, 7.2))
ax.set_xlim(0, 13); ax.set_ylim(0, 7.2); ax.axis("off")


def box(x, y, w, h, title, lines, fill=LIGHT):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fill, ec=BLUE, lw=1.4))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=10.5, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.68, "\n".join(lines), ha="center", va="top", fontsize=8.3, color=MUTED, linespacing=1.45)


def arrow(x1, y1, x2, y2, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, color=INK, lw=1.2))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.14, label, ha="center", fontsize=7.8, color=MUTED)


ax.text(6.5, 7.0, "Architecture du système d'alerte précoce du décrochage", ha="center", fontsize=13, weight="bold")
box(0.2, 4.3, 2.6, 2.2, "Source", ["UCI #697 / Kaggle", "data.csv (4 424 x 37)", "séparateur ; ou ,"], fill="white")
box(3.3, 4.3, 3.0, 2.2, "1. data_collection.py", ["normalisation des colonnes", "validation du schéma", "anonymisation + k-anonymat", "dictionnaire de données"])
box(6.8, 4.3, 2.6, 2.2, "Stockage", ["SQLite students.db", "tables students,", "predictions", "CSV anonymisés"], fill="white")
box(9.9, 4.3, 2.9, 2.2, "2. eda.py", ["statistiques par statut", "Kruskal-Wallis / Chi²", "information mutuelle", "7 figures"])
box(0.2, 0.5, 4.4, 3.1, "3. train.py (+ features, models,\nevaluate, explain)",
    ["", "split stratifié 80/20 (seed 42)", "3 scénarios : A inscription, B fin S1, C fin S2",
     "Pipeline : FeatureEngineer -> OneHot/Scaler", "-> [SMOTE] -> classifieur",
     "GridSearchCV 5 plis (refit macro-F1)", "choix : rappel Dropout | seuils de risque OOF", "test final, équité, importance"])
box(5.1, 0.5, 2.7, 3.1, "models/*.joblib", ["pipeline entraîné", "liste ordonnée des variables", "seuils faible/moyen/élevé",
                                             "profil de référence", "métriques de test"], fill="white")
box(8.3, 0.5, 2.0, 3.1, "predict.py", ["prepare() : mêmes", "colonnes, même ordre", "predict()", "explain()", "CLI CSV"])
box(10.8, 0.5, 2.0, 3.1, "Streamlit", ["accueil", "données & EDA", "modèles", "prédiction", "historique", "éthique"])
arrow(2.8, 5.4, 3.3, 5.4, "CSV")
arrow(6.3, 5.4, 6.8, 5.4)
arrow(9.4, 5.4, 9.9, 5.4)
arrow(4.8, 4.3, 2.6, 3.6)
ax.text(3.9, 3.95, "données validées", ha="left", fontsize=7.8, color=MUTED)
arrow(4.6, 2.05, 5.1, 2.05)
arrow(7.8, 2.05, 8.3, 2.05)
arrow(10.3, 2.05, 10.8, 2.05)
arrow(11.8, 3.6, 8.6, 4.3)
ax.text(11.0, 3.95, "profils + prédictions\npseudonymisés", ha="left", fontsize=7.8, color=MUTED)
fig.savefig(Path(__file__).with_name("architecture.png"), dpi=150, bbox_inches="tight", facecolor="white")
