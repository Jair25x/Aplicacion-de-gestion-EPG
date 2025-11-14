import sqlite3
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_PATH = os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db"))

def add_periodo(anio: int, mes: int, etiqueta: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO periodo (anio, mes, etiqueta) VALUES (?, ?, ?)",
            (anio, mes, etiqueta),
        )
        conn.commit()
        print(f"Periodo agregado: {etiqueta} ({mes}/{anio}) ✅")
    except sqlite3.IntegrityError as e:
        print(f"No se pudo insertar periodo (quizá ya existe): {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # EJEMPLO: Diciembre 2025
    # Cambia estos valores según necesites
    anio = 2025
    mes = 12
    etiqueta = "Diciembre 2025"

    add_periodo(anio, mes, etiqueta)
