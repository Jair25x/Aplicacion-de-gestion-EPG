# db.py
import sqlite3
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns():
    """
    Asegura columnas que se fueron agregando progresivamente
    (compatibilidad hacia atrás si la DB se creó con un schema antiguo).
    """
    conn = get_db_connection()
    cur = conn.cursor()

    def table_exists(table: str) -> bool:
        row = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    def column_exists(table: str, col: str) -> bool:
        rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r["name"] == col for r in rows)

    # Solo si existe la tabla curso_programado
    if table_exists("curso_programado"):
        # Campo opcional de 'matriculados' propio del curso
        if not column_exists("curso_programado", "matriculados"):
            cur.execute(
                "ALTER TABLE curso_programado "
                "ADD COLUMN matriculados INTEGER NULL"
            )

        # Campos para cartas (código, categoría, semanas)
        for col, ddl in [
            ("codigo", "TEXT"),
            ("categoria", "TEXT"),
            ("sem1", "TEXT"),
            ("sem2", "TEXT"),
        ]:
            if not column_exists("curso_programado", col):
                cur.execute(f"ALTER TABLE curso_programado ADD COLUMN {col} {ddl}")

        # Modalidad específica del dictado del curso
        if not column_exists("curso_programado", "modalidad_dictado"):
            cur.execute(
                "ALTER TABLE curso_programado "
                "ADD COLUMN modalidad_dictado TEXT NOT NULL DEFAULT 'PRESENCIAL'"
            )

    conn.commit()
    conn.close()
