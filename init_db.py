# init_db.py

import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_PATH = Path(os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db")))
SCHEMA_PATH = Path(os.getenv("DOCENTES_SCHEMA_PATH", str(BASE_DIR / "schema.sql")))


# =========================================================
# 1) Cargar schema.sql completo
# =========================================================
def seed_schema(conn: sqlite3.Connection) -> None:
    """
    Carga y ejecuta el schema completo desde schema.sql.

    El schema ya incluye:
      - periodo.periodo_academico
      - columnas observaciones en facultad, programa_academico, periodo,
        programa_periodo, docente, docente_propuesto, etc.
      - tablas para grados académicos del docente, carga académica y sugerencias.
    """
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()


# =========================================================
# 2) Facultades
# =========================================================
def seed_facultades(conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Inserta las facultades base y devuelve un mapa {nombre_facultad: id}.
    La columna 'observaciones' se deja en NULL por defecto.
    """
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


# =========================================================
# 3) Períodos (mes / año)
# =========================================================
def seed_periodos(conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Inserta períodos mensuales (año/mes) y les asigna un período académico.
    Devuelve un mapa 'YYYY-MM' -> id.

    Actualmente cargamos 2025-III (setiembre–diciembre 2025).
    La columna 'observaciones' en periodo se deja NULL.
    """
    periodos = [
        (2025, 9,  "Setiembre 2025", "2025-III"),
        (2025, 10, "Octubre 2025",   "2025-III"),
        (2025, 11, "Noviembre 2025", "2025-III"),
        (2025, 12, "Diciembre 2025", "2025-III"),
    ]

    for anio, mes, etiqueta, periodo_academico in periodos:
        conn.execute(
            """
            INSERT OR IGNORE INTO periodo (anio, mes, etiqueta, periodo_academico)
            VALUES (?, ?, ?, ?);
            """,
            (anio, mes, etiqueta, periodo_academico),
        )
    conn.commit()

    periodo_map: Dict[str, int] = {}
    for (anio, mes, _et, _pa) in periodos:
        row = conn.execute(
            "SELECT id FROM periodo WHERE anio = ? AND mes = ?;",
            (anio, mes),
        ).fetchone()
        if row:
            periodo_map[f"{anio}-{mes:02d}"] = row[0]

    return periodo_map


# =========================================================
# 4) Programas académicos
# =========================================================
def seed_programas(
    conn: sqlite3.Connection,
    facultad_map: Dict[str, int],
) -> Dict[str, int]:
    """
    Inserta programas académicos normalizados.

    Campo 'tipo' alineado al schema: 'DOCTORADO' | 'MAESTRIA' | 'PREGRADO'.
    Campo 'modalidad' se estandariza a: 'PRESENCIAL' | 'DISTANCIA' | 'MIXTA'.
    Devuelve un dict {nombre_corto: id_programa}.

    La columna 'observaciones' en programa_academico se deja en NULL.
    """
    programas = [
        # ==========================
        # FCH - Ciencias y Humanidades
        # ==========================
        ("Facultad de Ciencias y Humanidades", "DOCTORADO",
         "Doctorado en Ciencias de la Educación 15va Promoción", "15va Promoción", "PRESENCIAL"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO",
            "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial", "2da Promoción", "MIXTA"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO",
            "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO",
            "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "DOCTORADO",
            "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),

        ("Facultad de Ciencias y Humanidades", "MAESTRIA",
            "Maestría en Docencia Universitaria 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",
            "Maestría en Docencia Universitaria 5ta Promoción a Distancia", "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",
            "Maestría en Docencia Universitaria 6ta Promoción a Distancia", "6ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias y Humanidades", "MAESTRIA",
            "Maestría en Docencia Universitaria 7ma Promoción a Distancia", "7ma Promoción", "DISTANCIA"),

        # ==========================
        # FCS - Ciencias de la Salud
        # ==========================
        ("Facultad de Ciencias de la Salud", "DOCTORADO",
            "Doctorado en Psicología 1ra Promoción a Distancia", "1ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO",
            "Doctorado en Psicología 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO",
            "Doctorado en Ciencias de la Salud 2da Promoción a Distancia", "2da Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO",
            "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia", "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias de la Salud", "DOCTORADO",
            "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia", "4ta Promoción", "DISTANCIA"),

        # ==========================
        # FIA - Ingenierías y Arquitectura
        # ==========================
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO",
            "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial / Distancia",
            "2da Promoción", "MIXTA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO",
            "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia/Presencial",
            "3ra Promoción", "MIXTA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO",
            "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO",
            "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
            "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO",
            "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
            "6ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "DOCTORADO",
            "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",
            "12va Promoción", "PRESENCIAL"),

        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
            "5ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
            "6ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
            "7ma Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia",
            "2da Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ingenierías y Arquitectura", "MAESTRIA",
            "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
            "2da Promoción", "PRESENCIAL"),

        # ==========================
        # FCEC - Ciencias Económicas y Contables
        # ==========================
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO",
            "Doctorado en Administración 2da Promoción a Distancia/Presencial",
            "2da Promoción", "MIXTA"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO",
            "Doctorado en Administración 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO",
            "Doctorado en Administración 4ta Promoción Presencial",
            "4ta Promoción", "PRESENCIAL"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO",
            "Doctorado en Administración 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "DOCTORADO",
            "Doctorado en Contabilidad 2da Promoción a Distancia",
            "2da Promoción", "DISTANCIA"),

        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",
            "Maestría en Administración de Negocios 2da Promoción a Distancia",
            "2da Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",
            "Maestría en Administración de Negocios 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",
            "Maestría en Administración de Negocios 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",
            "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",
            "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Ciencias Económicas y Contables", "MAESTRIA",
            "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
            "5ta Promoción", "DISTANCIA"),

        # ==========================
        # FDCP - Derecho y Ciencia Política
        # ==========================
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO",
            "Doctorado en Derecho 2da Promoción a Distancia",
            "2da Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO",
            "Doctorado en Derecho 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO",
            "Doctorado en Derecho 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO",
            "Doctorado en Derecho 5ta Promoción a Distancia",
            "5ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "DOCTORADO",
            "Doctorado en Derecho 6ta Promoción a Distancia",
            "6ta Promoción", "DISTANCIA"),

        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
            "2da Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
            "2da Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
            "3ra Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
            "5ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
        ("Facultad de Derecho y Ciencia Política", "MAESTRIA",
            "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
            "4ta Promoción", "DISTANCIA"),
    ]

    nombre_to_id: Dict[str, int] = {}

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


# =========================================================
# 5) Matriculados por programa / período
# =========================================================
def seed_programa_periodo_matriculados(
    conn: sqlite3.Connection,
    periodo_map: Dict[str, int],
    program_name_to_id: Dict[str, int],
) -> None:
    """
    Carga los 'matriculados' por programa para 2025-III.

    Usamos como base tu cuadro de DICIEMBRE 2025 y lo aplicamos a
    NOVIEMBRE y DICIEMBRE 2025 (ambos en 2025-III).

    La columna 'observaciones' se usa para dejar trazabilidad de origen.
    """
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

        # FCEC – Maestrías
        "Maestría en Administración de Negocios 2da Promoción a Distancia": 14,
        "Maestría en Administración de Negocios 3ra Promoción a Distancia": 8,
        "Maestría en Administración de Negocios 4ta Promoción a Distancia": 12,
        "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia": 22,
        "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia": 8,
        "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia": 15,

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

    nov_id = periodo_map["2025-11"]
    dic_id = periodo_map["2025-12"]

    for nombre_corto, n in matric.items():
        prog_id = program_name_to_id.get(nombre_corto)
        if not prog_id:
            # Si no existe en catálogo (typo/nombre distinto), lo saltamos.
            continue
        for periodo_id in (nov_id, dic_id):
            conn.execute(
                """
                INSERT OR REPLACE INTO programa_periodo
                    (programa_id, periodo_id, matriculados, observaciones)
                VALUES (?, ?, ?, ?);
                """,
                (
                    prog_id,
                    periodo_id,
                    n,
                    "Constante 2025-III (cargado desde cuadro diciembre)",
                ),
            )

    conn.commit()


# =========================================================
# 6) Docentes recomendados para diciembre 2025
# =========================================================

def _normalizar_tipo_docente(tipo: Optional[str]) -> Optional[str]:
    if not tipo:
        return None
    t = tipo.strip().upper()
    if t.startswith("LOCAL"):
        return "LOCAL"
    if t.startswith("EXTERNO"):
        return "EXTERNO"
    return t or None


def _get_or_create_docente(
    conn: sqlite3.Connection,
    nombre_completo: str,
    dni: Optional[str],
    especialidad: Optional[str],
    telefono: Optional[str],
    correo: Optional[str],
    tipo_docente: Optional[str],
    tiene_cv: int,
) -> int:
    """
    Devuelve el id del docente. Si no existe, lo inserta.

    - Si tiene DNI, buscamos por DNI (único).
    - Si no tiene DNI, buscamos por nombre_completo.
    """
    # Normalizar vacíos
    dni = dni or None
    telefono = telefono or None
    correo = correo or None
    tipo_norm = _normalizar_tipo_docente(tipo_docente)

    # 1) Buscar por DNI, si existe
    if dni:
        row = conn.execute(
            "SELECT id FROM docente WHERE dni = ?;",
            (dni,),
        ).fetchone()
        if row:
            return row[0]

    # 2) Buscar por nombre_completo si no tiene DNI
    row = conn.execute(
        "SELECT id FROM docente WHERE nombre_completo = ?;",
        (nombre_completo,),
    ).fetchone()
    if row:
        return row[0]

    # 3) Insertar
    cursor = conn.execute(
        """
        INSERT INTO docente (
            apellido_paterno,
            apellido_materno,
            nombres,
            nombre_completo,
            especialidad,
            dni,
            correo,
            telefono,
            tipo_docente,
            tiene_cv
        )
        VALUES (NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            nombre_completo,
            especialidad,
            dni,
            correo,
            telefono,
            tipo_norm,
            tiene_cv,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def seed_docentes_recomendados_diciembre(
    conn: sqlite3.Connection,
    periodo_map: Dict[str, int],
) -> None:
    """
    Inserta los 11 docentes que indicaste y los marca como PROPUESOS
    (recomendados) para diciembre 2025 en la tabla docente_propuesto.
    """
    periodo_clave = "2025-12"
    if periodo_clave not in periodo_map:
        raise RuntimeError(f"No se encontró el período {periodo_clave} en periodo_map.")
    periodo_id = periodo_map[periodo_clave]

    # Datos de los docentes (según tu tabla)
    docentes_data = [
        {
            "nombre": "ANIBAL TORRES CASTILLO",
            "dni": None,  # DNI pendiente
            "tipo_docente": None,
            "especialidad": (
                "Magister en Administracion de Negocios CENTRUM-PUCP - "
                "Licenciado en Administracion Universidad Nacional Mayor de San Marcos"
            ),
            "telefono": "941809999",
            "correo": "anibaltorres6308@gmail.com",
            "tiene_cv": 1,  # CV recibido
        },
        {
            "nombre": "ARMANDO MEJIA GONZALES",
            "dni": None,  # DNI pendiente
            "tipo_docente": "Externo",
            "especialidad": (
                "Universidad de Piura, Maestría en Dirección de Empresas para Ejecutivos - "
                "Universidad Nacional de Ingeniería, Ingeniero Electrónico"
            ),
            "telefono": "999040770",
            "correo": "amejiag@uni.pe",
            "tiene_cv": 1,
        },
        {
            "nombre": "Dilson Elvis Loaiza Cruz",
            "dni": "43259519",
            "tipo_docente": "Local",
            "especialidad": (
                "Ingenieria del terreno e ingenieria sismica especialidad en ingenieria geotecnica - "
                "Ingeniero Civil"
            ),
            "telefono": "941863934",
            "correo": None,
            "tiene_cv": 1,
        },
        {
            "nombre": "ELBERTH HERNAN SAMALVIDES MARQUEZ",
            "dni": None,
            "tipo_docente": None,
            "especialidad": (
                "Doctor en Administración Universidad Privada de Tacna - "
                "Magister en Administración y Dirección de Empresas - "
                "Contador Público Colegiado Certificado Universidad Nacional Jorge Basadre Grohmann de Tacna."
            ),
            "telefono": "959297098",
            "correo": "elberths@hotmail.com",
            "tiene_cv": 1,
        },
        {
            "nombre": "EMILIO RHAL PAUCAR AGUIRRE",
            "dni": None,
            "tipo_docente": "Externo",
            "especialidad": (
                "DOCTORADO UNIVERSIDAD ANDINA DE CUSCO en Administración de Empresas - "
                "CENTRUM CATOLICA Graduado de la Maestría en Administración de Negocios. - "
                "UNIVERSIDAD SAN ANTONIO ABAD DEL CUSCO Licenciado en Administración de Empresas"
            ),
            "telefono": "920020544",
            "correo": "emilio.paucar@pucp.pe",
            "tiene_cv": 1,
        },
        {
            "nombre": "GRACE VIOLETA ESPINOZA PARDO",
            "dni": "41997432",
            "tipo_docente": "Externo",
            "especialidad": (
                "Doctora en ciencias biologicas: Fisiologia - "
                "Magister en Ciencias Biologicas - Bach Psicologia"
            ),
            "telefono": None,  # '-'
            "correo": "grace.pardo@gmail.com",
            "tiene_cv": 1,
        },
        {
            "nombre": "Giovanni Alexis Sumerente Cortez",
            "dni": "43537566",
            "tipo_docente": "Local",
            "especialidad": "Magister en Ingenieria Civil - Ingeniero civil",
            "telefono": "984421421",
            "correo": None,
            "tiene_cv": 1,
        },
        {
            "nombre": "JAVIER FRANCISCO ALVAREZ ALVAREZ",
            "dni": "43097451",
            "tipo_docente": "Local",
            "especialidad": "Maestría en Gerencia de la Construcción - Ingeniero civil",
            "telefono": "984417845",
            "correo": "jarival@gmail.com",
            "tiene_cv": 1,
        },
        {
            "nombre": "JESSIKA FARFAN RODRIGUEZ",
            "dni": "23920646",
            "tipo_docente": "Local",
            "especialidad": (
                "Doctorado en ciencias de la educación - Maestro en Gestion publica y desarrollo Regional - "
                "Economista"
            ),
            "telefono": "979379007",
            "correo": None,
            "tiene_cv": 1,
        },
        {
            "nombre": "JULIO CESAR CHALCO FERNANDEZ",
            "dni": "247144058",
            "tipo_docente": "Local",
            "especialidad": (
                "Doctor en Educacion - Maestro en linguistica y aplicaciones tecnologicas - "
                "Licenciado en Educacion San Marcos"
            ),
            "telefono": "974295724",
            "correo": "jchalcof@uandina.edu.pe",
            "tiene_cv": 0,  # Sin CV
        },
        {
            "nombre": "Mg. Edixon Laime Calvo",
            "dni": "42157485",
            "tipo_docente": "Local",
            "especialidad": "Maestro en Gestion y administracion de la construccion - Ingeniero civil",
            "telefono": "966742232",
            "correo": None,
            "tiene_cv": 1,
        },
    ]

    for d in docentes_data:
        docente_id = _get_or_create_docente(
            conn=conn,
            nombre_completo=d["nombre"],
            dni=d["dni"],
            especialidad=d["especialidad"],
            telefono=d["telefono"],
            correo=d["correo"],
            tipo_docente=d["tipo_docente"],
            tiene_cv=d["tiene_cv"],
        )

        # Insertar en docente_propuesto como PROPUESTO
        conn.execute(
            """
            INSERT OR IGNORE INTO docente_propuesto (
                docente_id,
                periodo_id,
                estado,
                observaciones
            )
            VALUES (?, ?, 'PROPUESTO', ?);
            """,
            (
                docente_id,
                periodo_id,
                "Recomendado para cursos de diciembre 2025",
            ),
        )

    conn.commit()


# =========================================================
# 7) init_db: orquestador
# =========================================================
def init_db() -> None:
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    # Asegurar integridad referencial
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        seed_schema(conn)
        print("Esquema creado correctamente ✅")

        facultad_map = seed_facultades(conn)
        print(f"Facultades insertadas: {facultad_map} ✅")

        periodo_map = seed_periodos(conn)
        print(f"Períodos insertados: {periodo_map} ✅")

        prog_name_to_id = seed_programas(conn, facultad_map)
        print(f"Programas académicos insertados: {len(prog_name_to_id)} ✅")

        seed_programa_periodo_matriculados(conn, periodo_map, prog_name_to_id)
        print("Matriculados por programa/período cargados (2025-III) ✅")

        seed_docentes_recomendados_diciembre(conn, periodo_map)
        print("Docentes recomendados para diciembre 2025 cargados ✅")

        print("Base de datos inicializada (schema + catálogos + docentes recomendados) 🎉")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
