# init_db.py
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "docentes.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

def seed_schema(conn):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)

def seed_facultades(conn):
    facultades = [
        ("Facultad de Ciencias y Humanidades", "FCH"),
        ("Facultad de Ciencias de la Salud", "FCS"),
        ("Facultad de Ingenierías y Arquitectura", "FIA"),
        ("Facultad de Ciencias Económicas y Contables", "FCEC"),
        ("Facultad de Derecho y Ciencia Política", "FDCP"),
    ]
    conn.executemany(
        "INSERT INTO facultad (nombre, codigo, activo) VALUES (?, ?, 1);",
        facultades,
    )
    conn.commit()
    rows = conn.execute("SELECT id, nombre FROM facultad;").fetchall()
    return {nombre: fid for fid, nombre in rows}

def seed_periodos(conn):
    periodos = [
        (2025, 11, "Noviembre 2025"),
        (2025, 12, "Diciembre 2025"),
    ]
    for anio, mes, etiqueta in periodos:
        conn.execute(
            "INSERT OR IGNORE INTO periodo (anio, mes, etiqueta) VALUES (?, ?, ?);",
            (anio, mes, etiqueta),
        )
    conn.commit()
    periodo_map = {}
    for (anio, mes, _et) in periodos:
        row = conn.execute("SELECT id FROM periodo WHERE anio=? AND mes=?;", (anio, mes)).fetchone()
        periodo_map[f"{anio}-{mes:02d}"] = row[0] if row else None
    return periodo_map

def seed_programas(conn, facultad_map):
    """
    Inserta programas académicos (normalizados) SIN 'universidad_procedencia'.
    Devuelve un dict {nombre_corto: id}.
    """
    programas = [
        # FCH
        ("Facultad de Ciencias y Humanidades", "DOCTORADO", "Doctorado en Ciencias de la Educación 15va Promoción", "15va Promoción", "PRESENCIAL"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO", "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial", "2da Promoción", "DISTANCIA/PRESENCIAL"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO", "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO", "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO", "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",  "Maestría en Docencia Universitaria 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",  "Maestría en Docencia Universitaria 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",  "Maestría en Docencia Universitaria 6ta Promoción a Distancia", "6ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",  "Maestría en Docencia Universitaria 7ma Promoción a Distancia", "7ma Promoción", "DISTANCIA"),

        # FCS
        ("Facultad de Ciencias de la Salud", "DOCTORADO", "Doctorado en Psicología 1ra Promoción a Distancia", "1ra Promoción", "DISTANCIA"),
        # Agrego la 3ra promo de Psicología (aparece en tu cuadro de diciembre)
        ("Facultad de Ciencias de la Salud", "DOCTORADO", "Doctorado en Psicología 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO", "Doctorado en Ciencias de la Salud 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO", "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO", "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),

        # FIA
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO", "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial / Distancia", "2da Promoción", "DISTANCIA/PRESENCIAL"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO", "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia/Presencial", "3ra Promoción", "DISTANCIA/PRESENCIAL"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO", "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO", "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO", "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia", "6ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO", "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial", "12va Promoción", "PRESENCIAL"),

        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia", "6ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia", "7ma Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA", "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial", "2da Promoción", "PRESENCIAL"),

        # FCEC
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO", "Doctorado en Administración 2da Promoción a Distancia/Presencial", "2da Promoción", "DISTANCIA/PRESENCIAL"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO", "Doctorado en Administración 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO", "Doctorado en Administración 4ta Promoción Presencial", "4ta Promoción", "PRESENCIAL"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO", "Doctorado en Administración 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO", "Doctorado en Contabilidad 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),

        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",  "Maestría en Administración de Negocios 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",  "Maestría en Administración de Negocios 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",  "Maestría en Administración de Negocios 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",  "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",  "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",  "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),

        # FDCP
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO", "Doctorado en Derecho 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO", "Doctorado en Derecho 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO", "Doctorado en Derecho 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO", "Doctorado en Derecho 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO", "Doctorado en Derecho 6ta Promoción a Distancia", "6ta Promoción", "DISTANCIA"),

        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Constitucional 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Constitucional 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Constitucional 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",  "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
    ]

    nombre_to_id = {}
    for fac, tipo, nombre_corto, promo, modalidad in programas:
        fac_id = facultad_map[fac]
        conn.execute(
            """
            INSERT INTO programa_academico
                (facultad_id, tipo, nombre_corto, mencion, promocion, modalidad, activo)
            VALUES (?, ?, ?, NULL, ?, ?, 1);
            """,
            (fac_id, tipo, nombre_corto, promo, modalidad),
        )
        prog_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]
        nombre_to_id[nombre_corto] = prog_id

    conn.commit()
    return nombre_to_id

def seed_programa_periodo_matriculados(conn, periodo_map, program_name_to_id):
    """
    Carga los 'matriculados' constantes por programa para 2025-III.
    Usamos como base tu cuadro de DICIEMBRE 2025 y lo aplicamos a NOVIEMBRE 2025 también.
    """
    # Mapa: nombre_corto -> matriculados (según tu cuadro de diciembre)
    matric = {
        # FCH – Doctorado en Ciencias de la Educación
        "Doctorado en Ciencias de la Educación 15va Promoción": 11,
        "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial": 9,
        "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia": 4,
        "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia": 16,
        "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia": 15,
        # FCH – Maestría en Docencia Universitaria
        "Maestría en Docencia Universitaria 4ta Promoción a Distancia": 21,
        "Maestría en Docencia Universitaria 5ta Promoción a Distancia": 18,
        "Maestría en Docencia Universitaria 6ta Promoción a Distancia": 38,
        "Maestría en Docencia Universitaria 7ma Promoción a Distancia": 36,

        # FCS – Psicología y Ciencias de la Salud
        "Doctorado en Psicología 1ra Promoción a Distancia": 13,
        "Doctorado en Psicología 3ra Promoción a Distancia": 5,
        "Doctorado en Ciencias de la Salud 2da Promoción a Distancia": 5,
        "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia": 11,
        "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia": 14,

        # FIA – DMADS
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial / Distancia": 4,
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia/Presencial": 13,
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia": 8,
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia": 18,
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial": 12,
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia": 15,

        # FIA – Maestrías Ingeniería Civil
        "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia": 14,
        "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia": 4,
        "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia": 21,
        "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial": 10,
        "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia": 37,
        "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia": 19,
        "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia": 23,

        # FCEC – Doctorados
        "Doctorado en Administración 2da Promoción a Distancia/Presencial": 11,
        "Doctorado en Administración 3ra Promoción a Distancia": 11,
        "Doctorado en Administración 4ta Promoción Presencial": 16,
        "Doctorado en Administración 4ta Promoción a Distancia": 8,
        "Doctorado en Contabilidad 2da Promoción a Distancia": 11,

        # FCEC – Maestrías (MAN y MCONT-AUD)
        "Maestría en Administración de Negocios 2da Promoción a Distancia": 14,
        "Maestría en Administración de Negocios 3ra Promoción a Distancia": 8,
        "Maestría en Administración de Negocios 4ta Promoción a Distancia": 12,
        "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia": 22,
        "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia": 15,
        "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia": 8,

        # FDCP – Doctorado en Derecho
        "Doctorado en Derecho 2da Promoción a Distancia": 14,
        "Doctorado en Derecho 3ra Promoción a Distancia": 11,
        "Doctorado en Derecho 4ta Promoción a Distancia": 5,
        "Doctorado en Derecho 5ta Promoción a Distancia": 24,
        "Doctorado en Derecho 6ta Promoción a Distancia": 15,

        # FDCP – Maestrías en Derecho
        "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia": 9,
        "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia": 15,
        "Maestría en Derecho Constitucional 3ra Promoción a Distancia": 15,
        "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia": 13,
        "Maestría en Derecho Constitucional 4ta Promoción a Distancia": 8,
        "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia": 8,
        "Maestría en Derecho Constitucional 5ta Promoción a Distancia": 14,
        "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia": 19,
        "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia": 15,
    }

    # Periodos destino
    nov_id = periodo_map["2025-11"]
    dic_id = periodo_map["2025-12"]

    # Inserta para NOV y DIC (constante 2025-III)
    for nombre_corto, n in matric.items():
        prog_id = program_name_to_id.get(nombre_corto)
        if not prog_id:
            # Si no existe en catálogo (typo/nombre distinto), lo saltamos silenciosamente.
            continue
        for periodo_id in (nov_id, dic_id):
            conn.execute(
                """
                INSERT OR REPLACE INTO programa_periodo
                    (programa_id, periodo_id, matriculados, observaciones)
                VALUES (?, ?, ?, ?);
                """,
                (prog_id, periodo_id, n, "Constante 2025-III (cargado desde cuadro diciembre)"),
            )

    conn.commit()

def init_db():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        seed_schema(conn)
        print("Esquema creado correctamente ✅")

        fac_map = seed_facultades(conn)
        per_map = seed_periodos(conn)
        print(f"Periodos insertados: {per_map} ✅")

        prog_name_to_id = seed_programas(conn, fac_map)
        print(f"Programas académicos insertados: {len(prog_name_to_id)} ✅")

        seed_programa_periodo_matriculados(conn, per_map, prog_name_to_id)
        print("Matriculados por programa/período cargados (2025-III) ✅")

        print("Base de datos inicializada (facultades, periodos, programas y matriculados) 🎉")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
