"""Configuration centrale du projet : chemins, graine aléatoire, groupes de variables et scénarios.

Toutes les autres briques (collecte, EDA, entraînement, application) importent ce module :
modifier une valeur ici la modifie partout, ce qui garantit la cohérence code / modèle / interface.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw" / "students_dropout_uci.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_SAMPLE = ROOT / "data" / "sample"
DB_PATH = ROOT / "data" / "students.db"
TUNISIA_UPLOAD = ROOT / "data" / "tunisia" / "reponses_formulaire.csv"   # dernier export importé dans l'application
MODELS_DIR = ROOT / "models"
FIGURES_DIR = ROOT / "reports" / "figures"
METRICS_DIR = ROOT / "reports" / "metrics"

RANDOM_STATE = 42
TEST_SIZE = 0.20          # 20 % -> 885 étudiants en test, comme dans la présentation de référence
CV_FOLDS = 5

TARGET = "target"
CLASSES = ["Dropout", "Enrolled", "Graduate"]   # ordre alphabétique = ordre du LabelEncoder
RISK_CLASS = "Dropout"

# Nom canonique (snake_case) -> nom original UCI. Le chargeur accepte aussi les variantes Kaggle.
COLUMNS = {
    "marital_status": "Marital status",
    "application_mode": "Application mode",
    "application_order": "Application order",
    "course": "Course",
    "daytime_evening_attendance": "Daytime/evening attendance",
    "previous_qualification": "Previous qualification",
    "previous_qualification_grade": "Previous qualification (grade)",
    "nationality": "Nacionality",
    "mother_qualification": "Mother's qualification",
    "father_qualification": "Father's qualification",
    "mother_occupation": "Mother's occupation",
    "father_occupation": "Father's occupation",
    "admission_grade": "Admission grade",
    "displaced": "Displaced",
    "educational_special_needs": "Educational special needs",
    "debtor": "Debtor",
    "tuition_fees_up_to_date": "Tuition fees up to date",
    "gender": "Gender",
    "scholarship_holder": "Scholarship holder",
    "age_at_enrollment": "Age at enrollment",
    "international": "International",
    "cu_1st_sem_credited": "Curricular units 1st sem (credited)",
    "cu_1st_sem_enrolled": "Curricular units 1st sem (enrolled)",
    "cu_1st_sem_evaluations": "Curricular units 1st sem (evaluations)",
    "cu_1st_sem_approved": "Curricular units 1st sem (approved)",
    "cu_1st_sem_grade": "Curricular units 1st sem (grade)",
    "cu_1st_sem_without_evaluations": "Curricular units 1st sem (without evaluations)",
    "cu_2nd_sem_credited": "Curricular units 2nd sem (credited)",
    "cu_2nd_sem_enrolled": "Curricular units 2nd sem (enrolled)",
    "cu_2nd_sem_evaluations": "Curricular units 2nd sem (evaluations)",
    "cu_2nd_sem_approved": "Curricular units 2nd sem (approved)",
    "cu_2nd_sem_grade": "Curricular units 2nd sem (grade)",
    "cu_2nd_sem_without_evaluations": "Curricular units 2nd sem (without evaluations)",
    "unemployment_rate": "Unemployment rate",
    "inflation_rate": "Inflation rate",
    "gdp": "GDP",
    TARGET: "Target",
}
FEATURES = [c for c in COLUMNS if c != TARGET]

# Codes nominaux : un code plus grand ne signifie pas "plus" -> encodage one-hot (pas de traitement ordinal).
NOMINAL = [
    "marital_status", "application_mode", "course", "previous_qualification", "nationality",
    "mother_qualification", "father_qualification", "mother_occupation", "father_occupation",
]
BINARY = [
    "daytime_evening_attendance", "displaced", "educational_special_needs", "debtor",
    "tuition_fees_up_to_date", "gender", "scholarship_holder", "international",
]

ENROLLMENT = [c for c in FEATURES if not c.startswith("cu_")]
SEM1 = [c for c in FEATURES if c.startswith("cu_1st_sem")]
SEM2 = [c for c in FEATURES if c.startswith("cu_2nd_sem")]

# Moment de la prédiction -> variables admissibles (prévention de la fuite temporelle de données).
SCENARIOS = {
    "A_inscription": {
        "label": "A - À l'inscription",
        "features": ENROLLMENT,
        "description": "Uniquement les informations connues au moment de l'inscription.",
    },
    "B_fin_S1": {
        "label": "B - Après le 1er semestre",
        "features": ENROLLMENT + SEM1,
        "description": "Inscription + résultats du 1er semestre : alerte précoce recommandée.",
    },
    "C_fin_S2": {
        "label": "C - Après le 2e semestre",
        "features": ENROLLMENT + SEM1 + SEM2,
        "description": "Toutes les variables (protocole de la présentation de référence).",
    },
}
# Variables dont la date de mesure n'est pas précisée par la documentation UCI (analyse de sensibilité).
AMBIGUOUS_TIMING = ["debtor", "tuition_fees_up_to_date"]

# Variables sensibles pour l'analyse d'équité.
SENSITIVE = ["gender", "age_at_enrollment", "scholarship_holder", "international"]
