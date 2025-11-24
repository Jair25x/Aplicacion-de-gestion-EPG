# seed_diciembre_2025.py
import os
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List
import unicodedata
import re

# ============================
# Configuración de rutas
# ============================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db")))

# -----------------------------
# Utilidades de normalización
# -----------------------------
def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _canon(s: str) -> str:
    """minúsculas, sin acentos, espacios colapsados."""
    s2 = _strip_accents(s or "").lower()
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2

def _remove_modalidad_tokens(s: str) -> str:
    """
    Normaliza nombre_corto ignorando modalidad:
    soporta 'presencial', 'a distancia', 'distancia/presencial', etc.
    """
    s2 = _canon(s)
    s2 = s2.replace("/", " ").replace("|", " ").replace("-", " ")
    s2 = re.sub(r"\b(a\s+)?distancia\b", "", s2)
    s2 = re.sub(r"\b(a\s+)?presencial\b", "", s2)
    s2 = re.sub(r"\b(a\s+)?mixta\b", "", s2)
    s2 = re.sub(r"\s+", " ", s2).strip(" _-,|/")
    return s2

def _infer_modalidad(s: str) -> Optional[str]:
    """
    Retorna 'PRESENCIAL', 'DISTANCIA' o 'MIXTA' si se detecta; si no, None.
    Si aparecen ambas ('distancia' y 'presencial'), retorna None.
    """
    can = _canon(s)
    has_pres = "presencial" in can
    has_dist = "distancia" in can
    has_mixta = "mixta" in can

    if has_mixta:
        return "MIXTA"
    if has_pres and not has_dist:
        return "PRESENCIAL"
    if has_dist and not has_pres:
        return "DISTANCIA"
    return None

# -----------------------------
# Utilidades de nombres/fechas
# -----------------------------
def parse_nombre(nombre_completo: str) -> Tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """
    Separa nombres y apellidos detectando título.
    Retorna:
        (nombre_con_titulo,
         nombre_sin_titulo,
         nombres,
         apellido_paterno,
         apellido_materno)
    """
    if not nombre_completo:
        return "", "", None, None, None

    original = nombre_completo.strip()

    titulo_prefixes = {
        "DR.", "DRA.", "DR", "DRA",
        "MG.", "MGT.", "MTRA.", "LIC.",
        "ING.", "ING", "ABG.", "ABG",
        "ARQ.", "ARQ",
        "Mg.", "Mgt.", "Mtra.", "Lic."
    }

    parts = original.split()
    titulo = None

    # Detectar título en el primer token
    if parts and parts[0].rstrip(".").upper() in {p.rstrip(".").upper() for p in titulo_prefixes}:
        token = parts[0].rstrip(".").upper()
        titulo = token + "."  # normaliza a "DR.", "MG.", etc.
        parts = parts[1:]     # para parsear solo nombres/apellidos

    if not parts:
        # Caso raro: solo vino el título
        return original, "", None, None, None

    nombre_sin_titulo = " ".join(parts)

    # ---- misma lógica de apellidos que ya tenías, pero con parts sin título ----
    if len(parts) == 1:
        return original, nombre_sin_titulo, parts[0], None, None

    if len(parts) == 2:
        nombres = parts[0]
        ap_paterno = parts[1]
        return original, nombre_sin_titulo, nombres, ap_paterno, None

    apellido_paterno = parts[-2]
    apellido_materno = parts[-1]
    nombres = " ".join(parts[:-2])
    return original, nombre_sin_titulo, nombres, apellido_paterno, apellido_materno

def split_fechas_en_semanas(fechas_texto: str) -> Tuple[str, str]:
    """
    '05, 06, 07, 19, 20 y 21 de diciembre 2025' -> sem1='05, 06, 07', sem2='19, 20, 21'
    Si no hay 6 días, todo va en sem1.
    """
    if not fechas_texto:
        return "", ""

    lower = fechas_texto.lower()
    idx = lower.find(" de ")
    solo_dias = fechas_texto[:idx] if idx != -1 else fechas_texto
    solo_dias = solo_dias.replace(" Y ", ", ").replace(" y ", ", ")
    tokens = [t.strip() for t in solo_dias.split(",") if t.strip()]

    dias = []
    for t in tokens:
        num = "".join(ch for ch in t if ch.isdigit())
        if num:
            dias.append(num)

    if len(dias) == 6:
        return ", ".join(dias[:3]), ", ".join(dias[3:])
    return ", ".join(dias), ""

# -----------------------------
# Acceso base
# -----------------------------
def get_periodo_id(conn: sqlite3.Connection, anio: int, mes: int) -> int:
    cur = conn.execute("SELECT id FROM periodo WHERE anio=? AND mes=?", (anio, mes))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(
            f"No existe periodo {anio}-{mes:02d}. "
            f"Ejecuta primero init_db.py para sembrar periodos."
        )
    return row[0]

def _catalogo_programas_por_facultad(conn: sqlite3.Connection, facultad_nombre: str) -> List[Tuple[int, str, str]]:
    """Devuelve [(id, nombre_corto, modalidad)] para una facultad."""
    fac = facultad_nombre.strip()
    cur = conn.execute(
        """
        SELECT p.id, p.nombre_corto, p.modalidad
        FROM programa_academico p
        JOIN facultad f ON f.id = p.facultad_id
        WHERE LOWER(f.nombre) = LOWER(?) AND p.activo = 1
        """,
        (fac,),
    )
    return cur.fetchall()

def get_programa_id(conn: sqlite3.Connection, facultad_nombre: str, programa_nombre_corto: str) -> int:
    """
    Resuelve programa por facultad + nombre_corto (tolerante a modalidad).
    """
    fac = facultad_nombre.strip()

    cur = conn.execute(
        """
        SELECT p.id
        FROM programa_academico p
        JOIN facultad f ON f.id = p.facultad_id
        WHERE LOWER(f.nombre) = LOWER(?) 
          AND p.nombre_corto = ?
          AND p.activo = 1
        """,
        (fac, programa_nombre_corto),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cat = _catalogo_programas_por_facultad(conn, facultad_nombre)
    objetivo = _remove_modalidad_tokens(programa_nombre_corto)

    candidatos = []
    for pid, nombre_corto, modalidad in cat:
        if _remove_modalidad_tokens(nombre_corto) == objetivo:
            candidatos.append((pid, nombre_corto, modalidad))

    if len(candidatos) == 1:
        return candidatos[0][0]

    if len(candidatos) > 1:
        pref = _infer_modalidad(programa_nombre_corto)
        if pref:
            by_pref = [c for c in candidatos if pref in (c[2] or "").upper()]
            if len(by_pref) == 1:
                return by_pref[0][0]
            exact = [c for c in candidatos if (c[2] or "").upper() == pref]
            if len(exact) == 1:
                return exact[0][0]

        opciones = [f"{nc} ({mod})" for _pid, nc, mod in candidatos]
        raise RuntimeError(
            f"Ambigüedad al resolver programa '{programa_nombre_corto}' en '{facultad_nombre}'. "
            f"Coinciden (ignorando modalidad): {opciones}. "
            f"Incluye una modalidad inequívoca."
        )

    existentes = [f"{nc} ({mod})" for _pid, nc, mod in cat]
    raise RuntimeError(
        f"No se encontró el programa '{programa_nombre_corto}' en facultad '{facultad_nombre}'. "
        f"Programas existentes: {existentes}"
    )

# -----------------------------
# Upserts de docentes
# -----------------------------
def upsert_docente(
    conn: sqlite3.Connection,
    dni: str,
    nombre_completo: str,
    tipo_docente: str,
    universidad_procedencia: Optional[str] = None,
):
    """Inserta/actualiza un docente según DNI."""
    nombre_full, _nombre_sin_titulo, nombres, apellido_paterno, apellido_materno = parse_nombre(nombre_completo)

    cur = conn.execute("SELECT id FROM docente WHERE dni = ?", (dni,))
    row = cur.fetchone()

    antecedentes = None
    if universidad_procedencia:
        antecedentes = f"Universidad de procedencia: {universidad_procedencia}"

    if row:
        conn.execute(
            """
            UPDATE docente
            SET nombre_completo       = COALESCE(?, nombre_completo),
                nombres              = COALESCE(?, nombres),
                apellido_paterno     = COALESCE(?, apellido_paterno),
                apellido_materno     = COALESCE(?, apellido_materno),
                tipo_docente         = COALESCE(?, tipo_docente),
                universidad_procedencia = COALESCE(?, universidad_procedencia),
                antecedentes         = CASE
                    WHEN ? IS NOT NULL AND (antecedentes IS NULL OR TRIM(antecedentes) = '')
                    THEN ?
                    ELSE antecedentes
                END,
                activo               = 1,
                updated_at           = datetime('now')
            WHERE dni = ?
            """,
            (
                nombre_full,
                nombres,
                apellido_paterno,
                apellido_materno,
                tipo_docente,
                universidad_procedencia,
                antecedentes,
                antecedentes,
                dni,
            ),
        )
        cur2 = conn.execute("SELECT id FROM docente WHERE dni = ?", (dni,))
        return cur2.fetchone()[0]
    else:
        conn.execute(
            """
            INSERT INTO docente (
                apellido_paterno,
                apellido_materno,
                nombres,
                nombre_completo,
                dni,
                tipo_docente,
                antecedentes,
                universidad_procedencia,
                activo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                apellido_paterno,
                apellido_materno,
                nombres,
                nombre_full,   # <-- con título
                dni,
                tipo_docente,
                antecedentes,
                universidad_procedencia,
            ),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def upsert_docente_sin_dni(
    conn: sqlite3.Connection,
    nombre_completo: str,
    tipo_docente: str,
    universidad_procedencia: Optional[str] = None,
):
    """Upsert por NOMBRE cuando no hay DNI."""
    nombre_full, nombre_sin_titulo, nombres, apellido_paterno, apellido_materno = parse_nombre(nombre_completo)

    cur = conn.execute(
        """
        SELECT id, dni
        FROM docente
        WHERE LOWER(nombre_completo) = LOWER(?)
           OR LOWER(nombre_completo) = LOWER(?)
        LIMIT 1
        """,
        (nombre_full, nombre_sin_titulo),
    )
    row = cur.fetchone()

    antecedentes = None
    if universidad_procedencia:
        antecedentes = f"Universidad de procedencia: {universidad_procedencia}"

    if row:
        docente_id, _dni_existente = row
        conn.execute(
            """
            UPDATE docente
            SET nombre_completo = COALESCE(?, nombre_completo),
                nombres = COALESCE(?, nombres),
                apellido_paterno = COALESCE(?, apellido_paterno),
                apellido_materno = COALESCE(?, apellido_materno),
                tipo_docente = COALESCE(?, tipo_docente),
                universidad_procedencia = COALESCE(?, universidad_procedencia),
                antecedentes = CASE
                    WHEN ? IS NOT NULL AND (antecedentes IS NULL OR TRIM(antecedentes) = '')
                    THEN ?
                    ELSE antecedentes
                END,
                activo = 1,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                nombre_full,   # <-- asegura título en BD
                nombres, apellido_paterno, apellido_materno,
                tipo_docente,
                universidad_procedencia,
                antecedentes, antecedentes,
                docente_id
            )
        )
        return docente_id

    conn.execute(
        """
        INSERT INTO docente (
            apellido_paterno,
            apellido_materno,
            nombres,
            nombre_completo,
            dni,
            tipo_docente,
            antecedentes,
            universidad_procedencia,
            activo
        )
        VALUES (?, ?, ?, ?, NULL, ?, ?, ?, 1)
        """,
        (
            apellido_paterno,
            apellido_materno,
            nombres,
            nombre_full,   # <-- con título
            tipo_docente,
            antecedentes,
            universidad_procedencia,
        )
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

# -----------------------------
# Robustez / Idempotencia
# -----------------------------
def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return any(r[1] == column for r in cur.fetchall())

def ensure_indexes(conn: sqlite3.Connection):
    """
    Índice único = misma regla de idempotencia que usabas:
    periodo + programa + ciclo + asignatura + fechas_texto.
    Evita duplicados aunque corras el script varias veces.
    """
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_curso_programado_key
        ON curso_programado (periodo_id, programa_id, ciclo, asignatura, fechas_texto)
    """)

def infer_modalidad_dictado(conn: sqlite3.Connection, programa_id: int, programa_label: str) -> Optional[str]:
    cur = conn.execute("SELECT modalidad FROM programa_academico WHERE id=?", (programa_id,))
    row = cur.fetchone()
    if row and row[0]:
        return (row[0] or "").upper()

    can = _canon(programa_label)
    if "distancia" in can and "presencial" not in can:
        return "DISTANCIA"
    if "presencial" in can and "distancia" not in can:
        return "PRESENCIAL"
    return None

def insert_curso_programado_idempotente(
    conn: sqlite3.Connection,
    periodo_id: int,
    programa_id: int,
    docente_id: Optional[int],
    dni_docente: Optional[str],
    ciclo: str,
    asignatura: str,
    fechas_texto: str,
    remuneracion_texto: Optional[str],
    remuneracion_monto: Optional[float],
    poi: Optional[str],
    tipo_docente_mes: str,
    estado_programacion: str = "CONFIRMADO",
    codigo: Optional[str] = None,
    categoria: Optional[str] = None,
    observaciones: Optional[str] = None,
    programa_label: Optional[str] = None,
) -> bool:
    """
    Inserta un curso programado sin duplicar.
    Retorna True si insertó, False si ya existía.
    """
    sem1, sem2 = split_fechas_en_semanas(fechas_texto)

    col_modalidad_dictado = has_column(conn, "curso_programado", "modalidad_dictado")
    modalidad_dictado = infer_modalidad_dictado(conn, programa_id, programa_label or "") if col_modalidad_dictado else None

    if col_modalidad_dictado:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO curso_programado
                (periodo_id, programa_id, docente_id,
                 ciclo, asignatura, fechas_texto,
                 modalidad_dictado,
                 remuneracion_monto, remuneracion_texto, poi,
                 dni_docente, tipo_docente_mes, estado_programacion,
                 observaciones, codigo, categoria, sem1, sem2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                periodo_id, programa_id, docente_id,
                ciclo, asignatura, fechas_texto,
                modalidad_dictado,
                remuneracion_monto, remuneracion_texto, poi,
                dni_docente, tipo_docente_mes, estado_programacion,
                observaciones, codigo, categoria, sem1, sem2
            )
        )
    else:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO curso_programado
                (periodo_id, programa_id, docente_id,
                 ciclo, asignatura, fechas_texto,
                 remuneracion_monto, remuneracion_texto, poi,
                 dni_docente, tipo_docente_mes, estado_programacion,
                 observaciones, codigo, categoria, sem1, sem2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                periodo_id, programa_id, docente_id,
                ciclo, asignatura, fechas_texto,
                remuneracion_monto, remuneracion_texto, poi,
                dni_docente, tipo_docente_mes, estado_programacion,
                observaciones, codigo, categoria, sem1, sem2
            )
        )

    return cur.rowcount == 1  # 1 insertó, 0 ignoró

# -----------------------------
# Datos DICIEMBRE 2025
# -----------------------------
DICIEMBRE = [
    # ---- FACULTAD DE CIENCIAS Y HUMANIDADES ----
    # Doctorado en Ciencias de la Educación
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. EDDY TELLO YARIN",
        "dni": "40543399",
        "universidad": "UNIVERSIDAD CESAR VALLEJO",
        "programa": "Doctorado en Ciencias de la Educación 15va Promoción Presencial",
        "ciclo": "VI",
        "asignatura": "DEFENSA NACIONAL Y SEGURIDAD",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257423",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DR. ELIAS MELENDREZ VELASCO",
        "dni": "23863492",
        "universidad": "UNIVERSIDAD CESAR VALLEJO",
        "programa": "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial",
        "ciclo": "IV",
        "asignatura": "TECNOLOGÍAS DE INFORMACIÓN Y COMUNICACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257429",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DR. JORGE LEONCIO RIVERA MUÑOZ",
        "dni": "08742823",
        "universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "programa": "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SISTEMAS DE EVALUACIÓN DEL APRENDIZAJE",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257430",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. JESSIKA FARFAN RODRIGUEZ",
        "dni": "23920646",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "RESPONSABILIDAD ETICO SOCIAL",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257431",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. FANNY MARTINEZ",
        "dni": "",
        "universidad": None,
        "programa": "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "ÉTICA EN LA EDUCACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257432",
        "tipo": "LOCAL",
    },

    # Maestría en Docencia Universitaria
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "MG. MARIANA LILIANA PEÑA FARFAN",
        "dni": "43541716",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257403",
        "tipo": "LOCAL",
        "obs": "No encontre sumilla en lo que tengo de las sumillas",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "MG. DINA LIZBETH APARICIO JURADO",
        "dni": "42482929",
        "universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "programa": "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257404",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "MG. MIGUEL JAINER CAMPOS CORNEJO",
        "dni": "",
        "universidad": None,
        "programa": "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257405",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "MG. JOSE EDUARDO VILLAVICENCIO QUISPE",
        "dni": "25301405",
        "universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "programa": "Maestría en Docencia Universitaria 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "PLANIFICACIÓN Y GESTIÓN DE LA CALIDAD DE LA EDUCACIÓN",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257406",
        "tipo": "LOCAL",
    },

    # ---- FACULTAD DE CIENCIAS DE LA SALUD ----
    # Doctorado en Psicología
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DRA. LILIA LUCY CAMPOS CORNEJO",
        "dni": "22401702",
        "universidad": "UNIVERSIDAD NACIONAL HERMILIO VALDIZÁN DE HUÁNUCO",
        "programa": "Doctorado en Psicología 1ra Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "SEMINARIO DE TESIS V",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257446",
        "tipo": "LOCAL",
        "obs": "lilialucy@hotmail.com",
    },
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. GARETH DEL CASTILLO ESTRADA",
        "dni": "41884386",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Psicología 3ra Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": None,
        "tipo": "LOCAL",
        "obs": "Llevara con el Doctorado en Salud 4ta Promocion a Distancia",
    },

    # Doctorado en Ciencias de la Salud
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. JOSE VICTOR MANCHEGO ENRIQUEZ",
        "dni": "01332872",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN DE AREQUIPA",
        "programa": "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "SEMINARIO TEMÁTICO",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257443",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. PABLO FIDEL GRAJEDA ANCCA",
        "dni": "23842238",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA",
        "programa": "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SEMINARIO DE TESIS II",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257444",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. GARETH DEL CASTILLO ESTRADA",
        "dni": "41884386",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257445",
        "tipo": "LOCAL",
        "obs": "Doctorado en Psicología 3ra Promoción a Distancia",
    },

    # ---- FACULTAD DE INGENIERÍAS Y ARQUITECTURA ----
    # Doctorado en Medio Ambiente y Desarrollo Sostenible
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. CRAYLA ALFARO AUCCA",
        "dni": "40767295",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial / Distancia",
        "ciclo": "VI",
        "asignatura": "ELABORACIÓN Y PUBLICACIÓN DE ARTÍCULOS CIENTÍFICOS",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257438",
        "tipo": "LOCAL",
        "obs": "El caso anterior de la Dra Karen preguntar si llevaran a distancia nuevamente",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. KAREN MELISSA GARCES PORRAS",
        "dni": "47025143",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia/Presencial",
        "ciclo": "V",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257439",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. LORNEL ANTONIO RIVAS MAGO",
        "dni": "49079955",
        "universidad": "UNIVERSIDAD SIMÓN BOLÍVAR",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SISTEMAS DE INFORMACIÓN AMBIENTAL",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257440",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. MILUSKA FRISANCHO CAMERO",
        "dni": "23894327",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "BIOÉTICA",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257441",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. TEODORO HUARHUA CHIPANI",
        "dni": "45924301",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",
        "ciclo": "II",
        "asignatura": "LEGISLACIÓN AMBIENTAL",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257424",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. EDWIN FREDDY BOCARDO DELGADO",
        "dni": "29227646",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257442",
        "tipo": "LOCAL",
    },

    # Maestría en Ingeniería Civil
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. ENRIQUE NUÑEZ DEL PRADO COLL",
        "dni": "23904327",
        "universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TEMAS AVANZADOS DE INGENIERIA ESTRUCTURAL EN LA HIDRAULICA",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257416",
        "tipo": "LOCAL",
        "obs": "Nuñez del prado dicto en julio solicitud a la Mg Ana cecilia",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. ELIOT PEZO ZEGARRA",
        "dni": "24006901",
        "universidad": "PONTIFÍCIA UNIVERSIDADE CATÓLICA DO RIO DE JANEIRO",
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TEMAS ESPECIALES",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257420",
        "tipo": "LOCAL",
        "obs": "Consignar bien el nombre del curso buscar en el ERP ESTA CORRECTO",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. ELVIS YURI MAMANI VARGAS",
        "dni": "41610570",
        "universidad": "PONTIFÍCIA UNIVERSIDADE CATÓLICA DO RIO DE JANEIRO",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257417",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. CARMEN CECILIA GIL RODRIGUEZ",
        "dni": "23877911",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257396",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. ALVARO HORACIO FLORES BOZA",
        "dni": "23858562",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257418",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. EDIXON LAIME CALVO",
        "dni": "42157485",
        "universidad": "UNIVERSIDAD NACIONAL DE INGENIERÍA",
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TRATAMIENTO DE AGUAS SERVIDAS E INDUSTRIALES",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257421",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. JAVIER FRANCISCO ALVAREZ ALVAREZ",
        "dni": "43097451",
        "universidad": "UNIVERSIDAD PERUANA DE CIENCIAS APLICADAS S.A.C.",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "COMPORTAMIENTO Y DISEÑO DEL CONCRETO",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257419",
        "tipo": "LOCAL",
    },

    # ---- FACULTAD DE CIENCIAS ECONÓMICAS Y CONTABLES ----
    # Doctorado en Administración
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. ABRAHAM PUENTE DE LA VEGA CACERES",
        "dni": "41206297",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Administración 2da Promoción a Distancia/Presencial",
        "ciclo": "V",
        "asignatura": "GESTIÓN DE RIESGOS Y TOMA DE DECISIONES EN INCERTIDUMBRE",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257425",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DRA. BENEDICTA SOLEDAD URRUTIA MELLADO",
        "dni": "23815007",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA",
        "programa": "Doctorado en Administración 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "MACROECONOMÍA Y POLÍTICAS ECONÓMICAS",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257426",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. ABRAHAM EDGARD CANAHUIRE MONTUFAR",
        "dni": "23961090",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Administración 4ta Promoción Presencial",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257422",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. WALDO ENRIQUE CAMPAÑA MORRO",
        "dni": "23933923",
        "universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "programa": "Doctorado en Administración 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "RESPONSABILIDAD SOCIAL EMPRESARIAL",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257427",
        "tipo": "LOCAL",
    },

    # Doctorado en Contabilidad
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. CARLOS EDWIN ROJAS SALDIVAR",
        "dni": "01317302",
        "universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "programa": "Doctorado en Contabilidad 2da Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "POLÍTICA ECONÓMICA Y GLOBALIZACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257428",
        "tipo": "LOCAL",
    },

    # Maestría en Administración de Negocios
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. EDISON ALAN ALVES CHOQUE",
        "dni": "40551283",
        "universidad": "UNIVERSIDAD SAN IGNACIO DE LOYOLA S.A",
        "programa": "Maestría en Administración de Negocios 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257397",
        "tipo": "LOCAL",
        "obs": "ealvescusco@gmail.com",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. ERICK JOEL ZUNIGA VIZCARRA",
        "dni": "45150991",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Administración de Negocios 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257398",
        "tipo": "LOCAL",
        "obs": "Llevara con Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. MANUEL JUAN CARDENAS HOLGADO",
        "dni": "41765306",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Administración de Negocios 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACION",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257399",
        "tipo": "LOCAL",
    },

    # Maestría en Contabilidad mención Auditoría y Control Interno
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DRA. ESTELA QUISPE RAMOS",
        "dni": "25199031",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257400",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DRA. MIRIAM CLEDY ZARATE MUÑIZ",
        "dni": "23805928",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "AUDITORIA FINANCIERA I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257402",
        "tipo": "LOCAL",
        "obs": "Docente qye se propone revisar si tenemos CV Miriam Cledy Zarate Muñiz SI TENEMOS",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. ERICK JOEL ZUNIGA VIZCARRA",
        "dni": "45150991",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": None,
        "rem_monto": None,
        "poi": None,
        "tipo": "LOCAL",
        "obs": "Llevaran con maestria en administracion 3ra promocion",
    },

    # ---- FACULTAD DE DERECHO Y CIENCIA POLÍTICA ----
    # Doctorado en Derecho
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. RENNE WILFREDO PEREZ VILLAFUERTE",
        "dni": "23847092",
        "universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLARREAL",
        "programa": "Doctorado en Derecho 2da Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257433",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. JOSEPH WALLTON ESPINOZA SOLORZANO",
        "dni": "43294047",
        "universidad": "UNIVERSIDAD CESAR VALLEJO",
        "programa": "Doctorado en Derecho 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "SEMINARIO DE TESIS III",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257434",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. JULIO TRINIDAD RIOS MAYORGA",
        "dni": "23821151",
        "universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "programa": "Doctorado en Derecho 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "MEDIOS ALTERNATIVOS PARA LA RESOLUCION DE CONFLICTOS",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257435",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. SIDNEY ALEX BRAVO MELGAR",
        "dni": "28268722",
        "universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "programa": "Doctorado en Derecho 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO: TEORIAS AVANZADAS DEL DERECHO PENAL EN EL SIGLO XXI",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257436",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. JORGE PAUL ARCE ZANS",
        "dni": "40876494",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Doctorado en Derecho 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "CIENCIA POLITICA Y GOBERNABILIDAD",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257437",
        "tipo": "LOCAL",
    },

    # Maestría en Derecho
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "MTRA. CLORINDA POZO ROLDAN",
        "dni": "23950891",
        "universidad": "UNIVERSIDAD DEL PAÍS VASCO/EUSKAL HERRIKO UNIBERTSITATEA",
        "programa": "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257413",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "MIGUEL ANGEL ZUÑIGA MARINO",
        "dni": "41249533",
        "universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "programa": "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257410",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "MGT. YULIANO QUISPE ANDRADE",
        "dni": "45827055",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257407",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA. LILIANA CORONADO GAMARRA",
        "dni": "23987320",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257414",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA. ARACELY ACUÑA CHAVEZ",
        "dni": "40846406",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TEMAS ESPECIALES",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257408",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA. DUNIA VICTORIA TERRAZAS GONZALES",
        "dni": "24713007",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257411",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA. GABRIELA FERNANDA PINARES PAYNE",
        "dni": "73435847",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257409",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. RENZO GUILLERMO ORTIZ DIAZ",
        "dni": "07267102",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "DERECHO INMOBILIARIO I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257412",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. JORGE ANTONIO MARTIN ORTIZ PASCO",
        "dni": "07919053",
        "universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        "programa": "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TUTELA JURÍDICA DE LA POSESIÓN Y LA PROPIEDAD",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257415",
        "tipo": "LOCAL",
    },
]

def main():
    print(f"Conectando a {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_indexes(conn)

        periodo_id = get_periodo_id(conn, 2025, 12)
        print(f"Periodo Diciembre 2025 id={periodo_id}")

        docentes_upsert = 0
        cursos_insertados = 0
        cursos_omitidos = 0

        for item in DICIEMBRE:
            programa_label = item["programa"]
            prog_id = get_programa_id(conn, item["facultad"], programa_label)

            dni = (item.get("dni") or "").strip()
            if dni:
                docente_id = upsert_docente(
                    conn=conn,
                    dni=dni,
                    nombre_completo=item["docente"],
                    tipo_docente=item["tipo"],
                    universidad_procedencia=item.get("universidad"),
                )
            else:
                print(f"⚠️  Docente sin DNI: {item['docente']} -> upsert por nombre.")
                docente_id = upsert_docente_sin_dni(
                    conn=conn,
                    nombre_completo=item["docente"],
                    tipo_docente=item["tipo"],
                    universidad_procedencia=item.get("universidad"),
                )

            docentes_upsert += 1

            inserted = insert_curso_programado_idempotente(
                conn=conn,
                periodo_id=periodo_id,
                programa_id=prog_id,
                docente_id=docente_id,
                dni_docente=dni if dni else None,
                ciclo=item["ciclo"],
                asignatura=item["asignatura"],
                fechas_texto=item["fechas"],
                remuneracion_texto=item.get("rem_texto"),
                remuneracion_monto=item.get("rem_monto"),
                poi=item.get("poi"),
                tipo_docente_mes=item["tipo"],
                estado_programacion="CONFIRMADO",
                observaciones=item.get("obs"),
                programa_label=programa_label,
            )

            if inserted:
                cursos_insertados += 1
            else:
                cursos_omitidos += 1

        conn.commit()
        print(f"✔ Docentes procesados (upsert): {docentes_upsert}")
        print(f"✔ Cursos programados insertados: {cursos_insertados}")
        print(f"ℹ Cursos omitidos por duplicado: {cursos_omitidos}")
        print("Diciembre 2025 cargado correctamente 🎉")

    finally:
        conn.close()

if __name__ == "__main__":
    main()