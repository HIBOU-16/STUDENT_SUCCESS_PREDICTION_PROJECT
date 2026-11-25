@echo off
REM Lanceur Windows : double-cliquez sur ce fichier.
cd /d "%~dp0"
if not exist ".venv" (
    echo Creation de l'environnement virtuel...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
if not exist "models\model_B_fin_S1.joblib" python run_pipeline.py --skip-tests
streamlit run app\streamlit_app.py
pause
