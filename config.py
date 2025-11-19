# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Carpeta base del proyecto
BASE_DIR = Path(__file__).resolve().parent

# .env opcional
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Ruta a la base de datos
DB_PATH = os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db"))

# Carpeta donde se guardan las cartas generadas
CARTAS_OUTPUT_DIR = BASE_DIR / "cartas_invitacion"
CARTAS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Plantilla de la carta de invitación
PLANTILLA_CARTA = BASE_DIR / "plantilla_carta.docx"

# Secret key de Flask
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "cambia-esto-por-algo-mas-seguro")

# Soporte PDF (docx2pdf)
TRY_PDF_WEB = True
try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    TRY_PDF_WEB = False
    docx2pdf_convert = None
