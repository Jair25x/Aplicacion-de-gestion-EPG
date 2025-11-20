import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from add_cursos_diciembre_2025 import (
    DB_PATH,
    split_sem1_sem2,
    cursos_diciembre,
    get_programa_id,
)

BASE_DIR = Path(__file__).resolve().parent

def main():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # Buscar periodo diciembre 2025
    cursor.execute("SELECT id FROM periodo WHERE anio = ? AND mes = ?", (2025, 12))
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("No se encontró el periodo 2025-12.")
    periodo_dic_2025_id = row[0]

    actualizados = 0
    for curso in cursos_diciembre:
        programa_label = curso["programa"]
        programa_id = get_programa_id(conn, cursor, programa_label)

        ciclo = curso["ciclo"]
        asignatura = curso["asignatura"]
        fechas_texto = curso["fechas"]

        sem1, sem2 = split_sem1_sem2(fechas_texto)

        cursor.execute(
            """
            UPDATE curso_programado
               SET sem1 = ?, sem2 = ?
             WHERE periodo_id = ?
               AND programa_id = ?
               AND ciclo = ?
               AND asignatura = ?
               AND fechas_texto = ?;
            """,
            (sem1, sem2, periodo_dic_2025_id, programa_id, ciclo, asignatura, fechas_texto),
        )
        if cursor.rowcount > 0:
            actualizados += cursor.rowcount
            print(f"✔ Actualizado {asignatura} ({programa_label}) -> sem1='{sem1}', sem2='{sem2}'")

    conn.commit()
    conn.close()
    print(f"✅ Registros actualizados: {actualizados}")

if __name__ == "__main__":
    main()
