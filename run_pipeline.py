"""Reproduit TOUT le projet en une commande : collecte -> EDA -> entraînement -> tests.

    python run_pipeline.py            (complet, ~3 min)
    python run_pipeline.py --quick    (grilles réduites, ~1 min)
"""
import argparse
import subprocess
import sys

from src import data_collection, eda, train
from src.config import METRICS_DIR

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    print("== Étape 1 : collecte, validation, anonymisation, stockage")
    data_collection.main()
    print("== Étape 2 : analyse exploratoire")
    eda.run()
    print("== Étape 3 : entraînement et évaluation des modèles")
    train.run(quick=args.quick)
    if not args.skip_tests:
        print("== Tests automatisés")
        sys.exit(subprocess.call([sys.executable, "-m", "pytest"]))
