"""Définition UNIQUE du formulaire d'évaluation tunisien.

Cette liste sert à deux choses, ce qui garantit qu'elles restent synchronisées :
  1. générer le script Google Apps Script qui crée le formulaire (forms/build_google_form.py) ;
  2. relire les réponses exportées depuis Google Sheets et les convertir en variables du modèle (src/tunisia.py).

Chaque question a un `id` interne, un `title` (texte affiché = en-tête de colonne dans Google Sheets) et,
pour les questions à choix, un dictionnaire {libellé affiché: code du modèle UCI}.
Les correspondances avec les codes UCI sont des APPROXIMATIONS documentées (contexte portugais -> tunisien).
"""
from __future__ import annotations

YES_NO = {"Oui": 1, "Non": 0}

INTRO = (
    "Ce questionnaire fait partie d'un projet académique (ISI / UVT, mini-projet « Alerte précoce du décrochage "
    "universitaire », binôme Mariam & Iheb). Il sert à vérifier si un modèle de prédiction, entraîné sur des "
    "étudiants portugais, fonctionne aussi pour des étudiants tunisiens.\n\n"
    "• Le questionnaire est ANONYME : aucun nom, email, numéro d'inscription ni CIN n'est demandé.\n"
    "• Il concerne votre PREMIÈRE ANNÉE dans une formation universitaire (licence ou équivalent).\n"
    "• Si vous ne vous souvenez pas d'un chiffre exact, donnez une estimation.\n"
    "• Durée : environ 8 minutes. La participation est volontaire ; vous pouvez arrêter à tout moment.\n"
    "• Les réponses sont utilisées uniquement dans le cadre pédagogique de ce projet.\n\n"
    "Les étudiants qui ont quitté leur formation sont particulièrement importants pour cette étude : "
    "n'hésitez pas à transmettre le lien."
)

SECTIONS = [
    {
        "id": "consentement",
        "title": None,  # première page du formulaire (sans saut de page)
        "questions": [
            {"id": "consentement", "title": "J'ai lu les informations ci-dessus et j'accepte de participer",
             "type": "choice", "required": True,
             "choices": {"Oui, j'accepte": 1, "Non, je ne souhaite pas participer": 0}},
        ],
    },
    {
        "id": "profil",
        "title": "1. Votre profil à l'entrée en 1re année",
        "help": "Répondez pour le moment où vous êtes entré(e) en 1re année de cette formation.",
        "questions": [
            {"id": "repondant", "title": "Qui remplit ce questionnaire ?", "type": "choice", "required": True,
             "choices": {"Je réponds pour moi-même (étudiant ou ancien étudiant)": "etudiant",
                         "Je suis un membre du personnel et je saisis un dossier anonymisé": "personnel"}},
            {"id": "annee_entree", "title": "Année d'entrée en 1re année", "type": "number", "required": True,
             "min": 2000, "max": 2030, "help": "Exemple : 2022"},
            {"id": "filiere", "title": "Domaine de la formation", "type": "choice", "required": True,
             "maps_to": "course",
             "choices": {"Informatique / génie logiciel / réseaux": 9119, "Gestion / économie": 9147,
                         "Gestion (cours du soir)": 9991, "Marketing / publicité": 9670,
                         "Journalisme / communication": 9773, "Design / multimédia": 171,
                         "Design graphique / communication visuelle": 9070, "Tourisme": 9254,
                         "Sciences infirmières / santé": 9500, "Agronomie": 9003, "Service social": 9238,
                         "Sciences de l'éducation / enseignement": 9853, "Vétérinaire / soins animaliers": 9085,
                         "Autre domaine": 0}},
            {"id": "genre", "title": "Sexe", "type": "choice", "required": True, "maps_to": "gender",
             "choices": {"Homme": 1, "Femme": 0}},
            {"id": "age_entree", "title": "Âge à l'entrée en 1re année (en années)", "type": "number",
             "required": True, "min": 15, "max": 70, "maps_to": "age_at_enrollment"},
            {"id": "etat_civil", "title": "État civil à l'entrée", "type": "choice", "required": True,
             "maps_to": "marital_status",
             "choices": {"Célibataire": 1, "Marié(e)": 2, "Divorcé(e)": 4, "Veuf / veuve": 3}},
            {"id": "nationalite", "title": "Nationalité", "type": "choice", "required": True,
             "choices": {"Tunisienne": "TN", "Autre nationalité": "AUTRE"}},
            {"id": "diplome_avant", "title": "Diplôme le plus élevé obtenu AVANT cette inscription",
             "type": "choice", "required": True, "maps_to": "previous_qualification",
             "choices": {"Baccalauréat": 1, "Licence ou diplôme universitaire de 1er cycle": 3, "Master": 4,
                         "BTS / diplôme technique supérieur": 42,
                         "Formation professionnelle ou technologique": 39,
                         "Baccalauréat non obtenu (accès spécial)": 9}},
            {"id": "section_bac", "title": "Section du baccalauréat", "type": "choice", "required": False,
             "choices": {"Mathématiques": "maths", "Sciences expérimentales": "sciences",
                         "Sciences techniques": "technique", "Sciences de l'informatique": "informatique",
                         "Économie et gestion": "eco", "Lettres": "lettres", "Sport": "sport",
                         "Autre / pas de bac": "autre"}},
            {"id": "moyenne_bac", "title": "Moyenne générale au baccalauréat (sur 20)", "type": "number",
             "required": True, "min": 0, "max": 20, "decimal": True,
             "help": "Utilisez un point pour les décimales, par exemple 13.45"},
            {"id": "mode_admission", "title": "Comment avez-vous été admis(e) dans cette formation ?",
             "type": "choice", "required": True, "maps_to": "application_mode",
             "choices": {"Orientation universitaire - 1er tour": 1, "Orientation universitaire - 2e tour": 17,
                         "Orientation universitaire - 3e tour / orientation finale": 18,
                         "Réorientation (changement de filière)": 43,
                         "Transfert depuis un autre établissement": 42,
                         "Titulaire d'un autre diplôme supérieur": 7,
                         "Formation continue / candidat de plus de 23 ans": 39,
                         "Étudiant étranger (admission internationale)": 15}},
            {"id": "rang_choix", "title": "Rang de cette formation dans votre fiche de vœux (1 = premier choix)",
             "type": "number", "required": True, "min": 1, "max": 30, "maps_to": "application_order",
             "help": "Si vous ne savez pas, mettez votre meilleure estimation."},
            {"id": "regime", "title": "Régime des cours", "type": "choice", "required": True,
             "maps_to": "daytime_evening_attendance",
             "choices": {"Cours du jour": 1, "Cours du soir": 0, "À distance / hybride": 0}},
            {"id": "niveau_mere", "title": "Niveau d'études de la mère", "type": "choice", "required": True,
             "maps_to": "mother_qualification", "choices": "PARENT_LEVEL"},
            {"id": "niveau_pere", "title": "Niveau d'études du père", "type": "choice", "required": True,
             "maps_to": "father_qualification", "choices": "PARENT_LEVEL"},
            {"id": "profession_mere", "title": "Profession de la mère", "type": "choice", "required": True,
             "maps_to": "mother_occupation", "choices": "PARENT_JOB"},
            {"id": "profession_pere", "title": "Profession du père", "type": "choice", "required": True,
             "maps_to": "father_occupation", "choices": "PARENT_JOB"},
            {"id": "loge_hors_famille",
             "title": "Pendant la 1re année, logiez-vous hors du domicile familial (foyer, location) ?",
             "type": "choice", "required": True, "maps_to": "displaced", "choices": YES_NO},
            {"id": "besoins_specifiques", "title": "Aviez-vous des besoins éducatifs particuliers (handicap, trouble…) ?",
             "type": "choice", "required": True, "maps_to": "educational_special_needs", "choices": YES_NO},
            {"id": "boursier", "title": "Étiez-vous boursier / boursière en 1re année ?", "type": "choice",
             "required": True, "maps_to": "scholarship_holder", "choices": YES_NO},
            {"id": "frais_a_jour", "title": "Vos frais d'inscription de 1re année ont-ils été payés à temps ?",
             "type": "choice", "required": True, "maps_to": "tuition_fees_up_to_date", "choices": YES_NO},
            {"id": "dette",
             "title": "Aviez-vous une dette envers l'établissement en 1re année (frais, foyer, bibliothèque…) ?",
             "type": "choice", "required": True, "maps_to": "debtor", "choices": YES_NO},
            # Variables citées par l'énoncé mais absentes du dataset UCI : collectées pour un futur ré-entraînement.
            {"id": "distance_km", "title": "Distance entre votre domicile et l'établissement (en km)",
             "type": "number", "required": False, "min": 0, "max": 1000, "extra": True},
            {"id": "transport", "title": "Moyen de transport principal", "type": "choice", "required": False,
             "extra": True, "choices": {"À pied": "pied", "Transport en commun (bus, métro, train, louage)": "commun",
                                        "Voiture / moto": "voiture", "Logé(e) sur place / foyer": "foyer",
                                        "Cours à distance": "distance"}},
            {"id": "temps_trajet", "title": "Temps de trajet aller (en minutes)", "type": "number",
             "required": False, "min": 0, "max": 400, "extra": True},
            {"id": "emploi", "title": "Aviez-vous un emploi pendant la 1re année ?", "type": "choice",
             "required": False, "extra": True,
             "choices": {"Non": "non", "Oui, à temps partiel": "partiel", "Oui, à temps plein": "plein"}},
        ],
    },
    {
        "id": "s1",
        "title": "2. Votre 1er semestre de 1re année",
        "help": "Un « module » = une matière évaluée séparément. Donnez une estimation si vous n'êtes pas sûr(e).",
        "questions": [
            {"id": "s1_inscrits", "title": "S1 - Nombre de modules auxquels vous étiez inscrit(e)",
             "type": "number", "required": True, "min": 0, "max": 30, "maps_to": "cu_1st_sem_enrolled"},
            {"id": "s1_credites", "title": "S1 - Nombre de modules validés par équivalence ou dispense (sans les passer)",
             "type": "number", "required": True, "min": 0, "max": 30, "maps_to": "cu_1st_sem_credited",
             "help": "En général 0."},
            {"id": "s1_evaluations",
             "title": "S1 - Nombre d'examens finaux passés (session principale + rattrapage)",
             "type": "number", "required": True, "min": 0, "max": 60, "maps_to": "cu_1st_sem_evaluations"},
            {"id": "s1_valides", "title": "S1 - Nombre de modules validés", "type": "number", "required": True,
             "min": 0, "max": 30, "maps_to": "cu_1st_sem_approved"},
            {"id": "s1_moyenne", "title": "S1 - Moyenne générale du semestre (sur 20)", "type": "number",
             "required": True, "min": 0, "max": 20, "decimal": True, "maps_to": "cu_1st_sem_grade",
             "help": "Utilisez un point pour les décimales, par exemple 11.25"},
            {"id": "s1_sans_eval", "title": "S1 - Nombre de modules pour lesquels vous n'avez passé AUCUN examen",
             "type": "number", "required": True, "min": 0, "max": 30, "maps_to": "cu_1st_sem_without_evaluations"},
            {"id": "s1_absences", "title": "S1 - Combien de séances avez-vous manquées environ ?", "type": "choice",
             "required": False, "extra": True,
             "choices": {"Aucune": "0", "1 à 3": "1-3", "4 à 10": "4-10", "Plus de 10": "10+"}},
            {"id": "s1_plateforme",
             "title": "S1 - À quelle fréquence utilisiez-vous la plateforme en ligne (Moodle, Classroom…) ?",
             "type": "choice", "required": False, "extra": True,
             "choices": {"Jamais": "jamais", "Moins d'une fois par semaine": "rare",
                         "1 à 3 fois par semaine": "hebdo", "Presque tous les jours": "quotidien"}},
            {"id": "s1_participation", "title": "S1 - Votre participation aux activités (TD, TP, projets)",
             "type": "scale", "required": False, "extra": True, "low": "Très faible", "high": "Très forte"},
            {"id": "s1_travail_perso", "title": "S1 - Heures de travail personnel par semaine (environ)",
             "type": "number", "required": False, "min": 0, "max": 80, "extra": True},
            {"id": "s2_fait", "title": "Avez-vous suivi le 2e semestre de la 1re année ?", "type": "branch",
             "required": True, "choices": {"Oui": "s2", "Non": "situation"}},
        ],
    },
    {
        "id": "s2",
        "title": "3. Votre 2e semestre de 1re année",
        "help": "Mêmes questions que pour le 1er semestre.",
        "questions": [
            {"id": "s2_inscrits", "title": "S2 - Nombre de modules auxquels vous étiez inscrit(e)",
             "type": "number", "required": True, "min": 0, "max": 30, "maps_to": "cu_2nd_sem_enrolled"},
            {"id": "s2_credites", "title": "S2 - Nombre de modules validés par équivalence ou dispense (sans les passer)",
             "type": "number", "required": True, "min": 0, "max": 30, "maps_to": "cu_2nd_sem_credited"},
            {"id": "s2_evaluations",
             "title": "S2 - Nombre d'examens finaux passés (session principale + rattrapage)",
             "type": "number", "required": True, "min": 0, "max": 60, "maps_to": "cu_2nd_sem_evaluations"},
            {"id": "s2_valides", "title": "S2 - Nombre de modules validés", "type": "number", "required": True,
             "min": 0, "max": 30, "maps_to": "cu_2nd_sem_approved"},
            {"id": "s2_moyenne", "title": "S2 - Moyenne générale du semestre (sur 20)", "type": "number",
             "required": True, "min": 0, "max": 20, "decimal": True, "maps_to": "cu_2nd_sem_grade"},
            {"id": "s2_sans_eval", "title": "S2 - Nombre de modules pour lesquels vous n'avez passé AUCUN examen",
             "type": "number", "required": True, "min": 0, "max": 30, "maps_to": "cu_2nd_sem_without_evaluations"},
        ],
    },
    {
        "id": "situation",
        "title": "4. Votre situation aujourd'hui",
        "help": "C'est la question la plus importante : elle permet de vérifier si le modèle avait raison.",
        "questions": [
            {"id": "statut", "title": "Quelle est votre situation aujourd'hui dans CETTE formation ?",
             "type": "choice", "required": True,
             "choices": {"J'ai obtenu le diplôme de cette formation": "Graduate",
                         "Je suis encore inscrit(e) et j'ai dépassé la durée normale (redoublement)": "Enrolled",
                         "Je suis encore inscrit(e), dans la durée normale": "",
                         "J'ai quitté cette formation sans le diplôme (abandon, réorientation, autre établissement)": "Dropout"}},
            {"id": "annee_depart", "title": "Si vous avez quitté la formation : pendant quelle année d'études ?",
             "type": "choice", "required": False, "extra": True,
             "choices": {"1re année": "1", "2e année": "2", "3e année ou plus": "3+"}},
            {"id": "raisons_depart", "title": "Si vous avez quitté la formation : pour quelles raisons ?",
             "type": "checkbox", "required": False, "extra": True,
             "choices": {"Difficultés financières": "finances", "Résultats insuffisants": "resultats",
                         "Formation non choisie / mauvaise orientation": "orientation",
                         "Transport ou distance": "transport", "Santé": "sante", "Travail": "travail",
                         "Perte de motivation": "motivation", "Raisons familiales": "famille"}},
            {"id": "satisfaction", "title": "Votre satisfaction vis-à-vis de la formation", "type": "scale",
             "required": False, "extra": True, "low": "Pas du tout satisfait(e)", "high": "Très satisfait(e)"},
        ],
    },
    {
        "id": "avis",
        "title": "5. Votre avis sur un outil d'alerte précoce",
        "questions": [
            {"id": "utilite",
             "title": "Un outil qui aide l'université à repérer tôt les étudiants en difficulté serait-il utile ?",
             "type": "scale", "required": False, "extra": True, "low": "Pas du tout utile", "high": "Très utile"},
            {"id": "aide_souhaitee", "title": "Quelle aide auriez-vous souhaité recevoir en cas de difficulté ?",
             "type": "checkbox", "required": False, "extra": True,
             "choices": {"Tutorat / soutien pédagogique": "tutorat", "Entretien avec un enseignant": "entretien",
                         "Aide financière": "financier", "Soutien psychologique": "psy",
                         "Aide à la réorientation": "reorientation", "Aucune": "aucune"}},
            {"id": "accord_donnees",
             "title": "Seriez-vous d'accord pour que des données anonymes servent à ce type d'outil ?",
             "type": "choice", "required": False, "extra": True,
             "choices": {"Oui": "oui", "Oui, seulement avec mon accord explicite": "accord", "Non": "non"}},
            {"id": "commentaire", "title": "Commentaire libre (facultatif)", "type": "paragraph", "required": False,
             "extra": True},
        ],
    },
]

CHOICE_LISTS = {
    # Codes UCI « qualification des parents »
    "PARENT_LEVEL": {"Non scolarisé(e) / ne sait pas lire": 35, "Primaire": 37,
                     "Collège (enseignement de base jusqu'à la 9e)": 19, "Secondaire sans baccalauréat": 9,
                     "Baccalauréat": 1, "Licence (bac+3)": 3, "Master / ingénieur (bac+5)": 4,
                     "Doctorat": 5, "Je ne sais pas": 34},
    # Codes UCI « profession des parents » (grands groupes de la classification des professions)
    "PARENT_JOB": {"Étudiant(e)": 0, "Cadre supérieur / directeur / élu": 1,
                   "Profession intellectuelle ou scientifique (ingénieur, médecin, enseignant…)": 2,
                   "Technicien / profession intermédiaire": 3, "Employé(e) administratif / de bureau": 4,
                   "Commerce, services, sécurité": 5, "Agriculteur / pêcheur": 6,
                   "Ouvrier qualifié / artisan / bâtiment": 7, "Conducteur / opérateur de machines": 8,
                   "Ouvrier non qualifié": 9, "Forces armées": 10,
                   "Sans emploi / au foyer / retraité(e)": 90, "Décédé(e) / je ne sais pas": 99},
}


def choices_of(q: dict) -> dict:
    c = q.get("choices", {})
    return CHOICE_LISTS[c] if isinstance(c, str) else c


def all_questions() -> list[dict]:
    return [q for s in SECTIONS for q in s["questions"]]


def question(qid: str) -> dict:
    return next(q for q in all_questions() if q["id"] == qid)


def check_spec() -> None:
    """Titres uniques (ils deviennent les en-têtes de colonnes Google Sheets) et libellés uniques par question."""
    titles = [q["title"] for q in all_questions()]
    dup = {t for t in titles if titles.count(t) > 1}
    if dup:
        raise ValueError(f"Titres en double : {dup}")
    for q in all_questions():
        labels = list(choices_of(q))
        if len(labels) != len(set(labels)):
            raise ValueError(f"Choix en double dans {q['id']}")


check_spec()
