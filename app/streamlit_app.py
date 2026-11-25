"""Étape 4 - Interface d'alerte précoce du décrochage (Streamlit).

Lancement :  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.data_collection import DESCRIPTIONS, LABELS, YES_NO, StudentStore, load_raw, validate  # noqa: E402
from src.models import MODEL_LABELS  # noqa: E402
from src.predict import DISCLAIMER, explain, load_bundle, predict  # noqa: E402

st.set_page_config(page_title="Alerte précoce du décrochage", page_icon="🎓", layout="wide")

RISK_STYLE = {"Risque faible": ("🟢", "success"), "Risque moyen": ("🟠", "warning"), "Risque élevé": ("🔴", "error")}
FIG = config.FIGURES_DIR


@st.cache_data
def dataset() -> pd.DataFrame:
    return load_raw()


@st.cache_data
def metrics():
    summary = json.loads((config.METRICS_DIR / "training_summary.json").read_text(encoding="utf-8"))
    eda = json.loads((config.METRICS_DIR / "eda_summary.json").read_text(encoding="utf-8"))
    return summary, eda, pd.read_csv(config.METRICS_DIR / "cv_results.csv"), pd.read_csv(config.METRICS_DIR / "test_results.csv")


def label_of(col: str, code) -> str:
    if isinstance(code, float) and code.is_integer():
        code = int(code)
    elif isinstance(code, float):
        code = round(code, 2)
    if col in LABELS:
        return f"{code} - {LABELS[col].get(int(code), 'code ' + str(code))}"
    if col in config.BINARY:
        return f"{code} - {YES_NO[int(code)]}"
    return str(code)


def show_figure(name: str, caption: str = "") -> None:
    path = FIG / name
    if path.exists():
        st.image(str(path), caption=caption, width="stretch")


def require_artifacts() -> bool:
    missing = [p for p in [config.METRICS_DIR / "training_summary.json", config.MODELS_DIR / "model_B_fin_S1.joblib"]
               if not p.exists()]
    if missing:
        st.error("Les modèles ne sont pas encore entraînés. Exécutez : `python run_pipeline.py`")
        return False
    return True


# ------------------------------------------------------------------------------------------ pages
def page_home(summary, eda):
    st.title("🎓 Alerte précoce du décrochage universitaire")
    st.caption("Mini-projet 7 - Programmation avancée avec Python · Sujet 3 · Binôme : Mariam & Iheb")
    st.markdown(
        "Cet outil estime, à partir du profil d'un étudiant, la probabilité qu'il **abandonne** (*Dropout*), "
        "soit **encore inscrit** (*Enrolled*) ou soit **diplômé** (*Graduate*), traduit ce résultat en **niveau "
        "de risque** et affiche les **facteurs associés** à la prédiction.")
    st.warning("⚠️ " + DISCLAIMER)
    c = st.columns(4)
    c[0].metric("Étudiants (dataset UCI)", f"{eda['n_rows']:,}".replace(",", " "))
    c[1].metric("Variables explicatives", eda["n_features"])
    c[2].metric("Taux d'abandon observé", f"{eda['class_share']['Dropout']:.1%}")
    b = summary["scenarios"]["B_fin_S1"]["alert_at_medium"]
    c[3].metric("Décrocheurs détectés dès la fin du S1*", f"{b['rappel']:.0%}")
    st.caption("*Scénario B, jeu de test (885 étudiants), alerte = risque moyen ou élevé.")

    st.subheader("Trois moments de prédiction")
    st.table(pd.DataFrame([
        {"Scénario": s["label"], "Variables": len(s["features"]), "Description": s["description"],
         "Modèle retenu": MODEL_LABELS[summary["scenarios"][k]["retained_model"]]}
        for k, s in config.SCENARIOS.items()]))
    st.markdown(
        "**Pourquoi trois scénarios ?** Les résultats des semestres 1 et 2 ne sont pas connus à l'inscription. "
        "Les utiliser pour une prédiction « à l'inscription » serait une *fuite de données*. Le scénario **B** "
        "est le meilleur compromis pour une alerte réellement **précoce**.")


def page_data(df, eda):
    st.header("📊 Données et analyse exploratoire")
    st.markdown("Source : [UCI ML Repository #697](https://archive.ics.uci.edu/dataset/697) "
                "(Realinho et al., 2022, licence CC BY 4.0), aussi publié sur Kaggle. Données déjà anonymisées.")
    problems = validate(df)
    st.success("Validation du schéma : OK") if not problems else st.error(problems)
    c = st.columns(3)
    for col, (k, v) in zip(c, eda["class_counts"].items()):
        col.metric(k, v, f"{eda['class_share'][k]:.1%}", delta_color="off")

    tabs = st.tabs(["Répartition", "Résultats académiques", "Engagement", "Facteurs sociaux", "Âge & cursus",
                    "Corrélations", "Variables pertinentes", "Explorer"])
    with tabs[0]:
        show_figure("eda_01_class_distribution.png")
        st.info("Classes déséquilibrées : Graduate ≈ 50 %, Dropout ≈ 32 %, Enrolled ≈ 18 %. L'accuracy seule "
                "serait trompeuse : un modèle naïf « tout Graduate » obtient déjà 50 %.")
    with tabs[1]:
        show_figure("eda_03_academic_results_by_status.png")
        m = eda["median_by_class"]["cu_1st_approval_rate"]
        st.markdown(f"Taux médian d'UE validées au S1 : **Dropout {m['Dropout']:.0%}**, Enrolled {m['Enrolled']:.0%}, "
                    f"Graduate {m['Graduate']:.0%}. La réussite du 1er semestre est le signal le plus fort.")
    with tabs[2]:
        show_figure("eda_04_engagement_proxies.png")
        st.markdown("Le dataset ne contient **ni absences ni connexions aux plateformes numériques**. "
                    "Nous utilisons des *proxies* : nombre d'évaluations passées et UE sans évaluation. "
                    "Ne passer **aucune évaluation** au S1 est associé à 70 % d'abandon.")
    with tabs[3]:
        show_figure("eda_05_dropout_rate_binary_factors.png")
        st.markdown("Associations (pas forcément causales) : frais non à jour → 87 % d'abandon ; "
                    "boursiers → 12 % contre 39 %.")
    with tabs[4]:
        show_figure("eda_06_age_and_course.png")
    with tabs[5]:
        show_figure("eda_07_correlations.png")
    with tabs[6]:
        show_figure("eda_02_mutual_information.png")
        tests = pd.read_csv(config.METRICS_DIR / "statistical_tests.csv")
        st.dataframe(tests.head(15).style.format({"statistique": "{:.1f}", "p_value": "{:.2e}", "taille_effet": "{:.3f}"}),
                     width="stretch")
    with tabs[7]:
        var = st.selectbox("Variable", [c for c in config.FEATURES], format_func=lambda c: f"{c} - {DESCRIPTIONS[c]}")
        if var in config.NOMINAL or var in config.BINARY:
            tab = pd.crosstab(df[var].map(lambda v: label_of(var, v)), df[config.TARGET], normalize="index")
            st.bar_chart(tab[config.CLASSES], horizontal=True, color=["#2a78d6", "#eb6834", "#1baf7a"])
        else:
            st.dataframe(df.groupby(config.TARGET)[var].describe().round(2), width="stretch")


def page_models(summary, cv, test):
    st.header("🤖 Modèles, métriques et choix")
    st.markdown(
        "**Protocole** : test stratifié de 20 % (885 étudiants) mis de côté ; GridSearchCV en validation croisée "
        "stratifiée à 5 plis sur les 80 % restants ; SMOTE, encodage et standardisation **dans** le pipeline. "
        "**Règle de choix** (validation croisée uniquement) : parmi les modèles à moins de 0,02 du meilleur "
        "macro-F1, on retient celui qui a le meilleur rappel Dropout.")
    show_figure("model_comparison_cv.png")
    scen = st.radio("Scénario", list(config.SCENARIOS), format_func=lambda s: config.SCENARIOS[s]["label"], horizontal=True)
    cols = ["model_label", "cv_f1_macro", "cv_std_f1_macro", "cv_recall_dropout", "cv_balanced_accuracy", "cv_roc_auc_ovr",
            "search_time_s"]
    st.markdown("**Validation croisée (apprentissage)**")
    st.dataframe(cv[cv.scenario == scen][cols].set_index("model_label").round(3), width="stretch")
    st.markdown("**Jeu de test (évaluation finale)**")
    tcols = ["model_label", "accuracy", "balanced_accuracy", "f1_macro", "f1_weighted", "recall_dropout",
             "precision_dropout", "f1_dropout", "recall_enrolled", "recall_graduate", "roc_auc_dropout", "pr_auc_dropout"]
    st.dataframe(test[test.scenario == scen][tcols].set_index("model_label").round(3), width="stretch")

    s = summary["scenarios"][scen]
    st.subheader(f"Modèle retenu : {MODEL_LABELS[s['retained_model']]}")
    c1, c2 = st.columns(2)
    with c1:
        show_figure(f"model_confusion_{scen}.png")
    with c2:
        show_figure(f"model_importance_{scen}.png")
    st.markdown(f"**Niveaux de risque** - seuils sur P(Dropout) : moyen ≥ {s['thresholds']['seuil_moyen']:.2f}, "
                f"élevé ≥ {s['thresholds']['seuil_eleve']:.2f} (calculés hors-échantillon sur l'apprentissage).")
    lv = pd.DataFrame(s["risk_levels"]).set_index("niveau")
    st.dataframe(lv.style.format({"taux_abandon_reel": "{:.1%}", "part_des_dropouts": "{:.1%}"}), width="stretch")
    a = s["alert_at_medium"]
    st.info(f"En déclenchant une alerte dès le risque moyen : **{a['rappel']:.0%} des décrocheurs détectés** "
            f"({a['faux_negatifs']} faux négatifs sur 284), au prix de {a['faux_positifs']} fausses alertes "
            f"({a['part_signalee']:.0%} des étudiants signalés).")
    st.markdown("**Équité** - performance de l'alerte par sous-groupe (jeu de test)")
    st.dataframe(pd.read_csv(config.METRICS_DIR / f"fairness_{scen}.csv").round(3), width="stretch")

    st.subheader("Courbes ROC / précision-rappel (détection Dropout)")
    show_figure("model_roc_pr_dropout.png")
    st.subheader("Vérification des résultats de la présentation de référence")
    rows = []
    for m, r in summary["reference_reproduction"].items():
        for k in ("accuracy", "f1_macro", "recall_dropout", "recall_enrolled", "recall_graduate"):
            rows.append({"modèle": MODEL_LABELS[m], "métrique": k, "annoncé": r["annonce_presentation"][k],
                         "obtenu": round(r["obtenu"][k], 3)})
    st.dataframe(pd.DataFrame(rows).pivot(index="modèle", columns="métrique", values=["annoncé", "obtenu"]),
                 width="stretch")
    st.caption("Le « ≈ 75 % d'étudiants à risque identifiés » correspond au rappel de la classe Dropout du "
               "Random Forest (36 variables, test de 885 étudiants). Nous l'avons reproduit.")


def manual_form(df: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    ref = bundle["reference_profile"]
    values = {}
    groups = [("Informations générales et parcours", [c for c in config.ENROLLMENT if c not in
                                                      ("unemployment_rate", "inflation_rate", "gdp")]),
              ("Contexte économique (année d'entrée)", ["unemployment_rate", "inflation_rate", "gdp"]),
              ("1er semestre", config.SEM1), ("2e semestre", config.SEM2)]
    for title, cols in groups:
        cols = [c for c in cols if c in bundle["features"]]
        if not cols:
            continue
        with st.expander(title, expanded=title.startswith(("1er", "Informations"))):
            grid = st.columns(3)
            for i, c in enumerate(cols):
                with grid[i % 3]:
                    if c in config.NOMINAL or c in config.BINARY:
                        opts = sorted(df[c].unique().tolist())
                        default = opts.index(int(ref[c])) if int(ref[c]) in opts else 0
                        values[c] = st.selectbox(c, opts, index=default, format_func=lambda v, c=c: label_of(c, v),
                                                 help=DESCRIPTIONS[c])
                    elif c in ("unemployment_rate", "inflation_rate", "gdp"):
                        opts = sorted(df[c].unique().tolist())
                        values[c] = st.selectbox(c, opts, index=opts.index(min(opts, key=lambda v: abs(v - ref[c]))),
                                                 help=DESCRIPTIONS[c])
                    else:
                        is_int = pd.api.types.is_integer_dtype(df[c])
                        lo, hi = df[c].min(), df[c].max()
                        values[c] = st.number_input(
                            c, min_value=int(lo) if is_int else float(lo), max_value=int(hi) if is_int else float(hi),
                            value=int(round(ref[c])) if is_int else float(ref[c]), step=1 if is_int else 0.1,
                            help=DESCRIPTIONS[c])
    return pd.DataFrame([values])[bundle["features"]]


def show_result(row: pd.Series, profile: pd.DataFrame, scen: str) -> None:
    icon, kind = RISK_STYLE[row["niveau_risque"]]
    getattr(st, kind)(f"{icon} **{row['niveau_risque']}** - probabilité estimée de décrochage : "
                      f"**{row['p_dropout']:.0%}** (statut le plus probable : {row['statut_predit']})")
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.markdown("**Probabilités par statut**")
        probs = pd.DataFrame({"probabilité": [row["p_dropout"], row["p_enrolled"], row["p_graduate"]]},
                             index=config.CLASSES)
        st.bar_chart(probs, horizontal=True, color="#2a78d6")
    with c2:
        st.markdown("**Principaux facteurs associés à cette prédiction**")
        ex = explain(profile, scen)
        if ex.empty:
            st.write("Profil très proche du profil de référence : aucun facteur saillant.")
        else:
            ex["effet"] = ex["contribution"].map(lambda v: "↑ augmente le risque" if v > 0 else "↓ diminue le risque")
            ex["valeur"] = [label_of(v, x) for v, x in zip(ex["variable"], ex["valeur"])]
            ex["reference"] = [label_of(v, x) if v in config.NOMINAL + config.BINARY else round(x, 2)
                               for v, x in zip(ex["variable"], ex["reference"])]
            ex["Δ P(Dropout)"] = ex["contribution"].map(lambda v: f"{v:+.1%}")
            st.dataframe(ex[["variable", "valeur", "reference", "Δ P(Dropout)", "effet"]], hide_index=True,
                         width="stretch")
            st.caption("Δ = variation de P(Dropout) si la variable reprenait la valeur d'un étudiant « typique » "
                       "(médiane / modalité la plus fréquente). Association apprise, **pas une cause**.")


def page_predict(df: pd.DataFrame):
    st.header("🔎 Estimer le risque d'un étudiant")
    scen = st.radio("Moment de la prédiction", list(config.SCENARIOS), index=1,
                    format_func=lambda s: config.SCENARIOS[s]["label"], horizontal=True)
    bundle = load_bundle(scen)
    st.caption(f"{config.SCENARIOS[scen]['description']} Modèle : {bundle['model_label']} · "
               f"{len(bundle['features'])} variables · entraîné le {bundle['trained_at']}")
    mode = st.segmented_control("Source des données", ["Saisie manuelle", "Importer un CSV"], default="Saisie manuelle")

    if mode == "Importer un CSV":
        st.markdown("Le fichier doit contenir les colonnes du scénario (noms UCI, Kaggle ou snake_case). "
                    "Exemple : `data/sample/profils_fictifs_demo.csv` (profils **fictifs**).")
        up = st.file_uploader("Fichier CSV", type="csv")
        if up is not None:
            data = pd.read_csv(up, sep=None, engine="python", encoding="utf-8-sig")
            try:
                res = predict(data, scen)
            except ValueError as e:
                st.error(str(e)); return
            ids = data["pseudo_id"] if "pseudo_id" in data.columns else pd.Series(range(len(data)), name="ligne")
            table = pd.concat([ids.rename("id"), res], axis=1)
            st.dataframe(table.style.format({c: "{:.1%}" for c in res.columns if c.startswith("p_")}),
                         hide_index=True, width="stretch")
            st.download_button("Télécharger les résultats", table.to_csv(index=False).encode("utf-8"),
                               "predictions.csv", "text/csv")
            pick = st.selectbox("Détailler l'étudiant", table.index, format_func=lambda i: str(table.loc[i, "id"]))
            show_result(res.loc[pick], data.loc[[pick]], scen)
        return

    st.info("Les valeurs par défaut sont celles d'un étudiant **fictif** « typique » (médiane / modalité la plus "
            "fréquente de l'apprentissage). Modifiez-les pour décrire le profil à évaluer.")
    profile = manual_form(df, bundle)
    if {"cu_1st_sem_approved", "cu_1st_sem_enrolled"} <= set(profile.columns):
        p = profile.iloc[0]
        if p["cu_1st_sem_approved"] > p["cu_1st_sem_enrolled"] + p["cu_1st_sem_credited"]:
            st.warning("Incohérence : plus d'UE validées au S1 qu'inscrites + créditées.")
    if st.button("Estimer le risque", type="primary"):
        st.session_state["last"] = (scen, profile)
    if st.session_state.get("last") and st.session_state["last"][0] == scen:
        _, prof = st.session_state["last"]
        res = predict(prof, scen).iloc[0]
        show_result(res, prof, scen)
        st.warning("⚠️ " + DISCLAIMER)
        if st.button("Enregistrer ce profil et la prédiction (pseudonymisés)"):
            store = StudentStore()
            stored = store.save_students(prof, source="interface", features=bundle["features"]).iloc[0]
            store.save_prediction(stored, scen, bundle["model_name"],
                                  {"Dropout": res["p_dropout"], "Enrolled": res["p_enrolled"], "Graduate": res["p_graduate"]},
                                  res["niveau_risque"])
            st.success(f"Enregistré sous le pseudonyme {stored} dans data/students.db")


def page_history():
    st.header("🗂️ Historique des prédictions enregistrées")
    preds = StudentStore().load_predictions()
    if preds.empty:
        st.write("Aucune prédiction enregistrée pour l'instant.")
    else:
        st.dataframe(preds, hide_index=True, width="stretch")


def page_tunisia():
    from src import tunisia

    st.header("🧪 Évaluation sur des étudiants tunisiens")
    st.markdown(
        "Les réponses du **Google Form** d'évaluation sont converties en variables du modèle, puis les prédictions "
        "sont comparées à la **situation réelle** déclarée par chaque répondant. Pour obtenir le fichier : ouvrir la "
        "feuille Google Sheets des réponses, puis **Fichier › Télécharger › Valeurs séparées par des virgules (.csv)**.")
    up = st.file_uploader("Export CSV des réponses du formulaire", type="csv")
    demo = st.button("Tester avec l'exemple FICTIF")
    if up is not None or demo:
        path = config.TUNISIA_UPLOAD if up is not None else config.DATA_SAMPLE / "reponses_formulaire_FICTIVES.csv"
        if up is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(up.getvalue())
        st.session_state["tn"] = tunisia.run(path)
    res = st.session_state.get("tn")
    if res is None and tunisia.RESULTS_PATH.exists():
        res = json.loads(tunisia.RESULTS_PATH.read_text(encoding="utf-8"))
    if res is None:
        st.info("Aucune évaluation pour l'instant : importez l'export CSV du formulaire.")
        return
    if "FICTIVES" in res.get("source", ""):
        st.error("⚠️ Résultats calculés sur des réponses **INVENTÉES** (test du code uniquement). "
                 "Ils ne disent rien du modèle : ne pas les présenter comme des résultats.")
    c = st.columns(3)
    c[0].metric("Réponses (avec consentement)", res["n_reponses"])
    c[1].metric("Statut réel connu", res["n_statut_connu"])
    c[2].metric("Abandons déclarés", res["statuts"].get("Dropout", 0))
    st.caption(f"Source : {res.get('source', '?')} · calculé le {res['date']}")
    for issue in res.get("problemes_conversion", []):
        st.warning(issue)

    ic = lambda v: f"{v[0]:.2f} - {v[1]:.2f}" if v else "-"
    rows = []
    for scen, r in res["scenarios"].items():
        a = r.get("alerte_risque_moyen", {})
        rows.append({"Scénario": r["label"], "Évaluables": r["n_evaluables"], "Abandons": r["n_dropout"],
                     "Macro-F1 Tunisie": r.get("f1_macro"), "IC 95 %": ic(r.get("f1_macro_ic95")),
                     "Macro-F1 Portugal": r["reference_portugal"]["f1_macro"],
                     "Rappel alerte (risque ≥ moyen)": a.get("rappel"), "IC 95 % rappel": ic(r.get("rappel_alerte_ic95")),
                     "Étudiants signalés": a.get("part_signalee")})
    st.dataframe(pd.DataFrame(rows).style.format(
        {"Macro-F1 Tunisie": "{:.3f}", "Macro-F1 Portugal": "{:.3f}", "Rappel alerte (risque ≥ moyen)": "{:.0%}",
         "Étudiants signalés": "{:.0%}"}, na_rep="-"), hide_index=True, width="stretch")

    scen = st.radio("Détail du scénario", list(res["scenarios"]), index=1,
                    format_func=lambda s: config.SCENARIOS[s]["label"], horizontal=True)
    r = res["scenarios"][scen]
    (st.success if r["verdict"].startswith("Performances") else st.warning)(f"**Conclusion proposée** : {r['verdict']}")
    if "confusion_matrix" in r:
        st.markdown("**Matrice de confusion** (lignes = situation réelle, colonnes = prédiction)")
        st.dataframe(pd.DataFrame(r["confusion_matrix"], index=config.CLASSES, columns=config.CLASSES), width="stretch")
    st.markdown("**Comparaison des profils** (moyennes) : un grand écart signale que le modèle portugais "
                "doit être adapté.")
    conv = config.ROOT / "data" / "tunisia" / "reponses_converties.csv"
    if conv.exists():
        X = pd.read_csv(conv)
        st.dataframe(tunisia.distribution_shift(X), hide_index=True, width="stretch")
        st.download_button("Télécharger les réponses converties (pour un futur ré-entraînement)",
                           conv.read_bytes(), "reponses_converties.csv", "text/csv")
    st.caption("Règle de conclusion (choisie par le binôme) : au moins 30 réponses évaluables dont 10 abandons ; "
               "puis rappel de l'alerte ≥ 80 % et macro-F1 au plus 0,10 sous le résultat portugais.")


def page_limits():
    st.header("⚖️ Limites, éthique et bon usage")
    st.markdown("""
- **Outil d'aide à la décision** : la prédiction déclenche un *entretien* ou un *accompagnement*, jamais une sanction.
- **Corrélation ≠ causalité** : « frais non à jour » est fortement associé à l'abandon, mais peut en être une
  conséquence (l'étudiant a déjà quitté) plutôt qu'une cause.
- **Données d'un seul établissement portugais (2008-2019)** : il faut ré-entraîner le modèle et le valider sur les
  données locales avant toute utilisation en Tunisie ou ailleurs.
- **Variables absentes** : absences, usage des plateformes numériques, satisfaction, motivation, santé mentale.
- **Équité** : les erreurs ne sont pas réparties de façon égale (faux négatifs plus fréquents chez les boursiers et
  les moins de 20 ans, voir la page Modèles). Le sexe est une variable du modèle : son usage doit être discuté.
- **Confidentialité** : aucun identifiant direct n'est stocké ; les profils saisis sont pseudonymisés.
""")


def main():
    if not require_artifacts():
        return
    df = dataset()
    summary, eda, cv, test = metrics()
    pages = {"Accueil": lambda: page_home(summary, eda), "Données & EDA": lambda: page_data(df, eda),
             "Modèles & résultats": lambda: page_models(summary, cv, test), "Prédiction": lambda: page_predict(df),
             "Historique": page_history, "Évaluation Tunisie": page_tunisia, "Limites & éthique": page_limits}
    choice = st.sidebar.radio("Navigation", list(pages))
    st.sidebar.markdown("---")
    st.sidebar.caption("ISI / UVT · Mini-projet 7 · Sujet 3  \nBinôme : Mariam & Iheb")
    pages[choice]()


main()
