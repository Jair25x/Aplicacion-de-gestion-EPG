# add_docentes_noviembre_2025.py
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List
import unicodedata
import re

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "docentes.db"

# -----------------------------
# Utilidades de normalización
# -----------------------------
def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _canon(s: str) -> str:
    """
    Normaliza: minúsculas, sin acentos, espacios colapsados.
    """
    s2 = _strip_accents(s or "").lower()
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2

def _remove_modalidad_tokens(s: str) -> str:
    """
    Normaliza nombre_corto ignorando modalidad:
    soporta 'presencial', 'a distancia', 'distancia/presencial', 'presencial / distancia', etc.
    """
    s2 = _canon(s)
    # normaliza separadores a espacio para evitar '... /' colgante
    s2 = s2.replace("/", " ").replace("|", " ").replace("-", " ")
    # elimina tokens de modalidad (con o sin 'a ')
    s2 = re.sub(r"\b(a\s+)?distancia\b", "", s2)
    s2 = re.sub(r"\b(a\s+)?presencial\b", "", s2)
    s2 = re.sub(r"\b(a\s+)?mixta\b", "", s2)  # por si acaso
    # colapsa espacios y limpia separadores residuales en bordes
    s2 = re.sub(r"\s+", " ", s2).strip(" _-,|/")
    return s2

def _infer_modalidad(s: str) -> Optional[str]:
    """
    Lee la modalidad mencionada en el string original (antes de normalizar):
    retorna 'PRESENCIAL', 'DISTANCIA' o 'MIXTA' si se detecta; si no, None.
    Si aparecen ambas ('distancia' y 'presencial'), retorna None para forzar ambigüedad explícita.
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
    # si están ambas o ninguna, no inferimos
    return None

# -----------------------------
# Utilidades de nombres/fechas
# -----------------------------
def parse_nombre(nombre_completo: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Separa nombres y apellidos desde 'DR./DRA./Mg. ...'.

    Retorna:
        (nombre_normalizado_sin_títulos,
         nombres,
         apellido_paterno,
         apellido_materno)

    Convención usada:
      - Se eliminan prefijos de título (DR., DRA., MG., LIC., etc.).
      - Se asume el patrón: NOMBRES ... APELLIDO_PATERNO APELLIDO_MATERNO
        cuando hay 3 o más partes.
    """
    if not nombre_completo:
        return "", None, None, None

    titulo_prefixes = {
        "DR.", "DRA.", "DR", "DRA",
        "MG.", "MGT.", "MTRA.", "LIC.",
        "ING.", "ING", "ABG.", "ABG",
        "ARQ.", "ARQ",
        "Mg.", "Mgt.", "Mtra.", "Lic."
    }
    parts = nombre_completo.strip().split()
    # quitar título inicial si coincide
    if parts and parts[0].rstrip(".").upper() in {p.rstrip(".").upper() for p in titulo_prefixes}:
        parts = parts[1:]

    if not parts:
        return nombre_completo.strip(), None, None, None

    # nombre_normalizado (sin título, pero respetando mayúsculas y acentos)
    nombre_norm = " ".join(parts)

    if len(parts) == 1:
        # solo un token: lo tratamos como nombres
        return nombre_norm, parts[0], None, None

    if len(parts) == 2:
        # dos tokens: asumimos "NOMBRE APELLIDO_PATERNO"
        nombres = parts[0]
        ap_paterno = parts[1]
        ap_materno = None
        return nombre_norm, nombres, ap_paterno, ap_materno

    # 3 o más tokens: NOMBRES ... APELLIDO_PATERNO APELLIDO_MATERNO
    apellido_paterno = parts[-2]
    apellido_materno = parts[-1]
    nombres = " ".join(parts[:-2])
    return nombre_norm, nombres, apellido_paterno, apellido_materno

def split_fechas_en_semanas(fechas_texto: str) -> Tuple[str, str]:
    """
    '07, 08, 09, 21, 22 Y 23 de noviembre 2025' -> sem1='07, 08, 09', sem2='21, 22, 23' (si hay 6 días).
    Otros casos: todo en sem1.
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
        raise RuntimeError(f"No existe periodo {anio}-{mes:02d}. Ejecuta primero init_db.py para sembrar periodos.")
    return row[0]

def _catalogo_programas_por_facultad(conn: sqlite3.Connection, facultad_nombre: str) -> List[Tuple[int, str, str]]:
    """
    Devuelve [(id, nombre_corto, modalidad)] para una facultad.
    Búsqueda INSENSIBLE a mayúsculas/minúsculas en el nombre de la facultad.
    """
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
    Resuelve el programa por facultad + nombre_corto (tolerante a modalidad).
    1) Intento exacto (facultad case-insensitive).
    2) Intento por nombre_corto sin modalidad (normalizado).
    """
    fac = facultad_nombre.strip()

    # Intento exacto primero (facultad insensible a mayúsculas/minúsculas)
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

    # Fallback: normalización sin modalidad
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
            f"Incluye una modalidad inequívoca en el dataset (p. ej., '... Presencial' o '... a Distancia')."
        )

    existentes = [f"{nc} ({mod})" for _pid, nc, mod in cat]
    raise RuntimeError(
        f"No se encontró el programa '{programa_nombre_corto}' en facultad '{facultad_nombre}'. "
        f"Revisa mayúsculas/acentos. Programas existentes: {existentes}"
    )

def upsert_docente(
    conn: sqlite3.Connection,
    dni: str,
    nombre_completo: str,
    tipo_docente: str,
    universidad_procedencia: Optional[str] = None,
):
    """
    Inserta/actualiza un docente en la tabla 'docente' según el DNI.
    Se alinea al schema actual:
      - apellido_paterno
      - apellido_materno
      - nombres
      - nombre_completo
      - universidad_procedencia
      - tipo_docente
      - antecedentes

    El resto de campos SUNEDU quedan en NULL por ahora.
    """

    # AHORA parse_nombre devuelve:
    # (nombre_normalizado_sin_títulos, nombres, apellido_paterno, apellido_materno)
    nombre_norm, nombres, apellido_paterno, apellido_materno = parse_nombre(nombre_completo)

    cur = conn.execute("SELECT id FROM docente WHERE dni = ?", (dni,))
    row = cur.fetchone()

    antecedentes = None
    if universidad_procedencia:
        antecedentes = f"Universidad de procedencia: {universidad_procedencia}"

    if row:
        # UPDATE
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
                nombre_norm,
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
        # INSERT
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
                nombre_norm,
                dni,
                tipo_docente,
                antecedentes,
                universidad_procedencia,
            ),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def insert_curso_programado(
    conn: sqlite3.Connection,
    periodo_id: int,
    programa_id: int,
    docente_id: Optional[int],
    dni_docente: Optional[str],
    ciclo: str,
    asignatura: str,
    fechas_texto: str,
    remuneracion_texto: str,
    remuneracion_monto: float,
    poi: str,
    tipo_docente_mes: str,
    estado_programacion: str = "CONFIRMADO",
    codigo: Optional[str] = None,
    categoria: Optional[str] = None,
    observaciones: Optional[str] = None,
):
    """
    Inserta un registro en curso_programado usando el esquema actual.
    Los campos no provistos (fecha_inicio, fecha_fin, modalidad_dictado, horas_texto)
    se dejan a NULL o valor por defecto (modalidad_dictado='PRESENCIAL').
    """
    sem1, sem2 = split_fechas_en_semanas(fechas_texto)

    conn.execute(
        """
        INSERT INTO curso_programado
            (periodo_id, programa_id, docente_id,
             ciclo, asignatura, fechas_texto,
             remuneracion_monto, remuneracion_texto, poi,
             dni_docente, tipo_docente_mes, estado_programacion,
             observaciones, codigo, categoria, sem1, sem2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            periodo_id,
            programa_id,
            docente_id,
            ciclo,
            asignatura,
            fechas_texto,
            remuneracion_monto,
            remuneracion_texto,
            poi,
            dni_docente,
            tipo_docente_mes,
            estado_programacion,
            observaciones,
            codigo,
            categoria,
            sem1,
            sem2,
        ),
    )

# -----------------------------
# Datos NOVIEMBRE 2025
# -----------------------------
# Para mantener trazabilidad exacta con tu documento, cada item incluye:
# facultad, universidad_procedencia (solo para docente.antecedentes),
# programa.nombre_corto, ciclo, asignatura, fechas, rem_texto, rem_monto, poi, dni, tipo_docente_mes.
NOVIEMBRE = [
    # ---- FACULTAD DE CIENCIAS Y HUMANIDADES ----
    # Doctorado en Ciencias de la Educación
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DR. ELIAS MELENDREZ VELASCO",
        "dni": "23863492",
        "universidad": "UNIVERSIDAD CESAR VALLEJO",
        "programa": "Doctorado en Ciencias de la Educación 15va Promoción",
        "ciclo": "VI",
        "asignatura": "SEMINARIO DE TESIS V",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257423",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. EDDY TELLO YARIN",
        "dni": "40543399",
        "universidad": "UNIVERSIDAD CESAR VALLEJO",
        "programa": "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial",
        "ciclo": "IV",
        "asignatura": "GESTIÓN EDUCATIVA Y LIDERAZGO",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257429",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. JHAKELINNE YOVANNA VILA GARRAFA",
        "dni": "42780119",
        "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        "programa": "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "REFORMAS Y POLÍTICAS EDUCATIVAS",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257431",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DR. BEYMAR PEDRO SOLIS TRUJILLO",
        "dni": "40290670",
        "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        "programa": "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257432",
        "tipo": "LOCAL",
    },

    # Maestría en Docencia Universitaria
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. PAULA PATRICIA LUKSIC GIBAJA",
        "dni": "23963570",
        "universidad": "UNIVERSIDAD ANDINA NESTOR CACERES VELASQUEZ DE JULIACA",
        "programa": "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "PLANIFICACIÓN DE LOS APRENDIZAJES - SILABO Y SESION DE CLASE",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257403",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "MG. WILBERT COLQUE CANDIA",
        "dni": "40634924",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "CURRÍCULO Y FORMACIÓN POR COMPETENCIAS EN LA EDUCACIÓN SUPERIOR",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257405",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DR. LORNEL ANTONIO RIVAS MAGO",
        "dni": "49079955",
        "universidad": "UNIVERSIDAD SIMÓN BOLÍVAR",
        "programa": "Maestría en Docencia Universitaria 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "METODOLOGÍA CIENTÍFICA DE LA INVESTIGACIÓN",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257406",
        "tipo": "LOCAL",
    },

    # ---- FACULTAD DE CIENCIAS DE LA SALUD ----
    # Doctorado en Psicología
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. JUAN AGLIBERTO QUIJANO PACHECO",
        "dni": "06580697",
        "universidad": "UNIVERSIDAD PRIVADA CÉSAR VALLEJO",
        "programa": "Doctorado en Psicología 1ra Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "ELABORACIÓN Y PUBLICACIÓN DE ARTÍCULOS CIENTÍFICOS",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257446",
        "tipo": "LOCAL",
    },

    # Doctorado en Ciencias de la Salud
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. GARETH DEL CASTILLO ESTRADA",
        "dni": "41884386",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "MARKETING APLICADO A CIENCIA DE LA SALUD",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257445",
        "tipo": "LOCAL",
    },

    # ---- FACULTAD DE INGENIERÍAS Y ARQUITECTURA ----
    # Doctorado en Medio Ambiente y Desarrollo Sostenible
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. KAREN MELISSA GARCES PORRAS",
        "dni": "47025143",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial",
        "ciclo": "VI",
        "asignatura": "CALIDAD Y SALUD AMBIENTAL",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257441",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. CAROLINA DIANA PARADA QUINAYA",
        "dni": "002219801",
        "universidad": "PONTIFÍCIA UNIVERSIDADE CATÓLICA DO RIO DE JANEIRO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "CULTURA ACADÉMICA Y DOCENCIA",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257439",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. TEODORO HUARHUA CHIPANI",
        "dni": "45924301",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257441",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. LIZET VARGAS VERA",
        "dni": "24004480",
        "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",
        "ciclo": "II",
        "asignatura": "DESARROLLO SOSTENIBLE Y POLÍTICAS PÚBLICAS",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257424",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. MILUSKA FRISANCHO CAMERO",
        "dni": "23894327",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "CONTAMINACIÓN AMBIENTAL Y PROPUESTA DE ACCIONES",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257442",
        "tipo": "LOCAL",
    },

    # Maestría en Ingeniería Civil
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. ALVARO HORACIO FLORES BOZA",
        "dni": "23858562",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257416",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. MIJAIL MONTESINOS ESCOBAR",
        "dni": "44885194",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TEMAS AVANZADOS DE INGENIERIA ESTRUCTURAL EN LA GEOTECNICA",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257417",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. ED GUTIERREZ CARLOTTO",
        "dni": "46086133",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
        "ciclo": "III",
        "asignatura": "OPERACIONES DE TRÁFICO",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257396",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. JULIO CESAR SUCASACA RODRIGUEZ",
        "dni": "70747162",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE CHILE",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "INGENIERIA SISMORESISTENTE Y SISMOTECTONICA",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257418",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "MG. GORKI FEDERICO ASCUE SALAS",
        "dni": "24484766",
        "universidad": "UNIVERSIDAD MAYOR DE SAN SIMÓN",
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "ECOLOGIA Y MEDIO AMBIENTE",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257421",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DR. RAUL APAZA MENESES",
        "dni": "23865073",
        "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACION",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257419",
        "tipo": "LOCAL",
    },

    # ---- FACULTAD DE CIENCIAS ECONÓMICAS Y CONTABLES ----
    # Doctorado en Administración
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "Dr. ABRAHAM PUENTE DE LA VEGA CACERES",
        "dni": "41206297",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Administración 2da Promoción a Distancia/presencial",
        "ciclo": "V",
        "asignatura": "FINANZAS CORPORATIVAS AVANZADAS",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257425",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DRA. EVELYN JESUS CARAZAS ARAUJO",
        "dni": "41826776",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Doctorado en Administración 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "DIRECCIÓN DE NEGOCIOS INTERNACIONALES",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257426",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. MARIO NICANOR VARGAS BEJARANO",
        "dni": "43581088",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Administración 4ta Promoción presencial",
        "ciclo": "II",
        "asignatura": "ANÁLISIS DE INVERSIONES",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257422",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. CLETO DE LA TORRE DUEÑAS",
        "dni": "23988416",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA",
        "programa": "Doctorado en Administración 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "ESTADÍSTICA APLICADA A LOS NEGOCIOS",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257427",
        "tipo": "LOCAL",
    },

    # Doctorado en Contabilidad
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. RENNE WILFREDO PEREZ VILLAFUERTE",
        "dni": "23847092",
        "universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLARREAL",
        "programa": "Doctorado en Contabilidad 2da Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SEMINARIO DE TESIS II",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257428",
        "tipo": "LOCAL",
    },

    # Maestría en Administración de Negocios
    {
        "facultad": "Facultad de Ciencias Económicas Y Contables",
        "docente": "MG. WERNHER OMAR GUEVARA MONTESINOS",
        "dni": "08687564",
        "universidad": "UNIVERSIDAD DEL PACÍFICO",
        "programa": "Maestría en Administración de Negocios 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "GERENCIA ESTRATEGICA Y POLITICAS DE EMPRESA",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257397",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "DR. WALDO ALEX PANDO DIAZ",
        "dni": "23998983",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Administración de Negocios 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "FORMULACION, EVALUACION Y GESTION DE PROYECTOS",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257398",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. HUGO ESPETIA HUAMANGA",
        "dni": "23983332",
        "universidad": "ESCUELA DE POSGRADO NEWMAN",
        "programa": "Maestría en Administración de Negocios 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "ADMINISTRACIÓN DE SISTEMAS DE INFORMACIÓN",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257399",
        "tipo": "LOCAL",
    },

    # Maestría en Contabilidad mención en Auditoría y Control Interno
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. LUIS ALBERTO ESPINOZA PANTY",
        "dni": "44683350",
        "universidad": "UNIVERSIDAD DEL PACÍFICO",
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TOPICOS ESPECIALES DE AUDITORIA TRIBUTARIA",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257400",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. GABRIEL MOZO AYMA",
        "dni": "23806625",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "PERITAJE CONTABLE",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257401",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Ciencias Económicas y Contables",
        "docente": "MG. TATIANA CHOQUEHUANCA CONTRERAS",
        "dni": "23994524",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "METODOLOGÍA CIENTÍFICA DE LA INVESTIGACIÓN",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257402",
        "tipo": "LOCAL",
    },

    # ---- FACULTAD DE DERECHO Y CIENCIA POLÍTICA ----
    # Doctorado en Derecho
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. EDWARDS JESUS AGUIRRE ESPINOZA",
        "dni": "23854868",
        "universidad": "UNIVERSIDAD ANDINA NÉSTOR CÁCERES VÉLASQUEZ",
        "programa": "Doctorado en Derecho 2da Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "CULTURA ACADEMICA Y DOCENCIA",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257433",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. SIDNEY ALEX BRAVO MELGAR",
        "dni": "28268722",
        "universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "programa": "Doctorado en Derecho 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TEORIA DE LOS DERECHOS HUMANOS",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257433",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. ISAAC ENRIQUE CASTRO CUBA BARINEZA",
        "dni": "10281126",
        "universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        "programa": "Doctorado en Derecho 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257436",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. PAUL JOSE CASAFRANCA BUOB",
        "dni": "23839206",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Doctorado en Derecho 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "TEORIA GENERAL DEL DERECHO",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257437",
        "tipo": "LOCAL",
    },

    # Maestría en Derecho
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA. GABRIELA FERNANDA PINARES PAYNE",
        "dni": "73435847",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TUTELA JURÍDICA CIVIL Y TUTELA JURISDICCIONAL",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257413",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA. DUNIA VICTORIA TERRAZAS GONZALES",
        "dni": "24713007",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "DERECHO INMOBILIARIO III",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257410",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "Mg. MIGUEL ALEJANDRO ESTELA LA PUENTE",
        "dni": "47307488",
        "universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        "programa": "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "DERECHO CONSTITUCIONAL ECONÓMICO",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257407",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. MARIO ANDREA CAMOIRANO GARAVENTA",
        "dni": "06664112",
        "universidad": "UNIVERSIDAD DEL PACÍFICO",
        "programa": "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "CONTRATOS INTERNACIONALES",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257414",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. JUAN COSIO MUÑOZ",
        "dni": "24008206",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "programa": "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257408",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. RENZO GUILLERMO ORTIZ DIAZ",
        "dni": "07267102",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "DERECHO INMOBILIARIO II",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257411",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "MGT. YULIANO QUISPE ANDRADE",
        "dni": "45827055",
        "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "programa": "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "LA JURISDICCIÓN CONSTITUCIONAL",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257409",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DRA LILIANA CORONADO GAMARRA",
        "dni": "23987320",
        "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "programa": "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACIÓN",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257412",
        "tipo": "LOCAL",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "MTRA. CLORINDA POZO ROLDAN",
        "dni": "23950891",
        "universidad": "UNIVERSIDAD DEL PAÍS VASCO/EUSKAL HERRIKO UNIBERTSITATEA",
        "programa": "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257415",
        "tipo": "LOCAL",
    },

    # ---- DOCENTES ORDINARIZADOS ----
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DR. GUIDO AMERICO TORRES CASTILLO",
        "dni": "24484917",
        "universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "programa": "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SALUD PÚBLICA",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257444",
        "tipo": "ORDINARIZADO",
    },
    {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "docente": "DRA. BENEDICTA SOLEDAD URRUTIA MELLADO",
        "dni": "23815007",
        "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA",
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "ECONOMÍA ECOLÓGICA",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257440",
        "tipo": "ORDINARIZADO",
    },
    {
        "facultad": "Facultad de Derecho y Ciencia Política",
        "docente": "DR. JULIO TRINIDAD RIOS MAYORGA",
        "dni": "23821151",
        "universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "programa": "Doctorado en Derecho 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "PRODUCCION INTELECTUAL",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257434",
        "tipo": "ORDINARIZADO",
    },
    {
        "facultad": "Facultad de Ciencias de la Salud",
        "docente": "DRA. GLADIS EDITH ROJAS SALAS",
        "dni": "07933864",
        "universidad": "UNIVERSIDAD CATOLICA SANTA MARIA DE AREQUIPA",
        "programa": "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "BIOÉTICA",
        "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
        "rem_texto": "S/. 5,900.00",
        "rem_monto": 5900.00,
        "poi": "257445",
        "tipo": "ORDINARIZADO",
    },
    {
        "facultad": "Facultad de Ciencias y Humanidades",
        "docente": "DRA. HERMINIA CALLO SANCHEZ",
        "dni": "23913968",
        "universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "programa": "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "EVALUACIÓN EN EDUCACIÓN",
        "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
        "rem_texto": "S/. 4,140.00",
        "rem_monto": 4140.00,
        "poi": "257404",
        "tipo": "ORDINARIZADO",
    },
]

def main():
    print(f"Conectando a {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        periodo_id = get_periodo_id(conn, 2025, 11)
        print(f"Periodo Noviembre 2025 id={periodo_id}")

        inserted_docentes = 0
        inserted_cursos = 0

        for item in NOVIEMBRE:
            prog_id = get_programa_id(conn, item["facultad"], item["programa"])

            docente_id = upsert_docente(
                conn=conn,
                dni=item["dni"],
                nombre_completo=item["docente"],
                tipo_docente=item["tipo"],
                universidad_procedencia=item.get("universidad"),
            )
            inserted_docentes += 1

            insert_curso_programado(
                conn=conn,
                periodo_id=periodo_id,
                programa_id=prog_id,
                docente_id=docente_id,
                dni_docente=item["dni"],
                ciclo=item["ciclo"],
                asignatura=item["asignatura"],
                fechas_texto=item["fechas"],
                remuneracion_texto=item["rem_texto"],
                remuneracion_monto=float(item["rem_monto"]),
                poi=item["poi"],
                tipo_docente_mes=item["tipo"],
                estado_programacion="CONFIRMADO",
            )
            inserted_cursos += 1

        conn.commit()
        print(f"✔ Docentes procesados (upsert): {inserted_docentes}")
        print(f"✔ Cursos programados insertados: {inserted_cursos}")
        print("Noviembre 2025 cargado correctamente 🎉")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
