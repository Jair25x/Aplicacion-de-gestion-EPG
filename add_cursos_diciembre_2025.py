# add_cursos_diciembre_2025.py

import os
import re
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Tuple, List

# ============================
# Configuración de rutas / .env
# ============================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_PATH = os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db"))


# ============================
# Utilidades
# ============================
def parse_monto(monto_str: Optional[str]) -> Optional[float]:
    """
    Convierte 'S/. 5,900.00' -> 5900.00
    Devuelve None si viene vacío o '-'/'--'.
    """
    if not monto_str:
        return None
    s = monto_str.strip()
    if s in ("-", "--", ""):
        return None
    for pref in ("S/.", "S/", "s/.", "s/"):
        s = s.replace(pref, "")
    s = s.replace(" ", "")
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def split_sem1_sem2(fechas_texto: str):
    """
    Divide el texto de fechas en sem1 y sem2.

    Ejemplos de entrada:
      "05, 06, 07, 19, 20 y 21 de diciembre 2025"
      "12,13,14, 26,27 y 28 de diciembre 2025"

    Regla general:
      - 1 a 3 fechas  -> todas en sem1, sem2 vacío
      - 4 fechas      -> 2 y 2
      - 5 fechas      -> 3 y 2
      - 6 o más fechas-> 3 y (resto)

    El sufijo ("de diciembre 2025") se conserva en ambos.
    """
    if not fechas_texto:
        return "", ""

    texto = fechas_texto.strip()

    # 1) Separar la parte de días del sufijo "de <mes> ..."
    m = re.search(r"\sde\s", texto)
    if m:
        # Parte de días, ej: "05, 06, 07, 19, 20 y 21"
        dias_part = texto[: m.start()].strip()
        # Sufijo, ej: "de diciembre 2025" (sin espacios extra)
        sufijo = texto[m.start():].strip()
    else:
        # Si no encontramos " de ", trabajamos todo como días y sin sufijo.
        dias_part = texto
        sufijo = ""

    # 2) Normalizar " y " a coma para facilitar el split
    dias_norm = dias_part.replace(" y ", ", ")
    # Ahora spliteamos por coma
    tokens = [t.strip() for t in dias_norm.split(",") if t.strip()]

    if not tokens:
        return "", ""

    n = len(tokens)

    # 3) Decidir cómo partimos sem1 / sem2 según la cantidad
    if n <= 3:
        sem1_tokens = tokens
        sem2_tokens = []
    elif n == 4:
        sem1_tokens = tokens[:2]
        sem2_tokens = tokens[2:]
    elif n == 5:
        sem1_tokens = tokens[:3]
        sem2_tokens = tokens[3:]
    else:  # n >= 6
        sem1_tokens = tokens[:3]
        sem2_tokens = tokens[3:]

    def formatear(lista):
        if not lista:
            return ""
        if not sufijo:
            # Sin sufijo (caso extremo)
            if len(lista) == 1:
                return lista[0]
            if len(lista) == 2:
                return f"{lista[0]} y {lista[1]}"
            return f"{', '.join(lista[:-1])} y {lista[-1]}"

        # Con sufijo, ej: "de diciembre 2025"
        if len(lista) == 1:
            return f"{lista[0]} {sufijo}"
        if len(lista) == 2:
            return f"{lista[0]} y {lista[1]} {sufijo}"
        # 3 o más
        return f"{', '.join(lista[:-1])} y {lista[-1]} {sufijo}"

    sem1 = formatear(sem1_tokens)
    sem2 = formatear(sem2_tokens)

    return sem1, sem2


# ============================
# Resolución de Programas
# ============================
# Mapea el "label" que usas en el cuadro/contrato → nombre_corto EXACTO
# en la BD (sembrado por init_db.py)
PROGRAMA_NAME_CANON = {
    # FCH – Doctorado en Ciencias de la Educación
    "Doctorado en Ciencias de la Educación 15va Promoción Presencial":
        "Doctorado en Ciencias de la Educación 15va Promoción",
    "Doctorado en Ciencias de la Educación 2da Promoción a Distancia":
        "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial",
    "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia":
        "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia",
    "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia":
        "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
    "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia":
        "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",

    # FCH – Maestría en Docencia Universitaria
    "Maestría en Docencia Universitaria 4ta Promoción a Distancia":
        "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
    "Maestría en Docencia Universitaria 5ta Promoción a Distancia":
        "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
    "Maestría en Docencia Universitaria 6ta Promoción a Distancia":
        "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
    "Maestría en Docencia Universitaria 7ma Promoción a Distancia":
        "Maestría en Docencia Universitaria 7ma Promoción a Distancia",

    # FCS – Psicología y Ciencias de la Salud
    "Doctorado en Psicología 1ra Promoción a Distancia":
        "Doctorado en Psicología 1ra Promoción a Distancia",
    "Doctorado en Psicología 3ra Promoción a Distancia":
        "Doctorado en Psicología 3ra Promoción a Distancia",
    "Doctorado en Ciencias de la Salud 2da Promoción a Distancia":
        "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
    "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia":
        "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
    "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia":
        "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",

    # FIA – DMADS
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción a Distancia":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial / Distancia",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia/Presencial",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",

    # FIA – Maestrías Ingeniería Civil
    "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia":
        "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
    "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia":
        "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
    "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia":
        "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
    "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia":
        "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
    "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia":
        "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia",
    "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia":
        "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
    "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial":
        "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",

    # FCEC – Doctorados
    "Doctorado en Administración 2da Promoción a Distancia":
        "Doctorado en Administración 2da Promoción a Distancia/Presencial",
    "Doctorado en Administración 3ra Promoción a Distancia":
        "Doctorado en Administración 3ra Promoción a Distancia",
    "Doctorado en Administración 4ta Promoción Presencial":
        "Doctorado en Administración 4ta Promoción Presencial",
    "Doctorado en Administración 4ta Promoción a Distancia":
        "Doctorado en Administración 4ta Promoción a Distancia",
    "Doctorado en Contabilidad 2da Promoción a Distancia":
        "Doctorado en Contabilidad 2da Promoción a Distancia",

    # FCEC – Maestrías
    "Maestría en Administración de Negocios 2da Promoción a Distancia":
        "Maestría en Administración de Negocios 2da Promoción a Distancia",
    "Maestría en Administración de Negocios 3ra Promoción a Distancia":
        "Maestría en Administración de Negocios 3ra Promoción a Distancia",
    "Maestría en Administración de Negocios 4ta Promoción a Distancia":
        "Maestría en Administración de Negocios 4ta Promoción a Distancia",
    "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia":
        "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
    "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia":
        "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
    "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia":
        "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",

    # FDCP – Doctorados en Derecho
    "Doctorado en Derecho 2da Promoción a Distancia":
        "Doctorado en Derecho 2da Promoción a Distancia",
    "Doctorado en Derecho 3ra Promoción a Distancia":
        "Doctorado en Derecho 3ra Promoción a Distancia",
    "Doctorado en Derecho 4ta Promoción a Distancia":
        "Doctorado en Derecho 4ta Promoción a Distancia",
    "Doctorado en Derecho 5ta Promoción a Distancia":
        "Doctorado en Derecho 5ta Promoción a Distancia",
    "Doctorado en Derecho 6ta Promoción a Distancia":
        "Doctorado en Derecho 6ta Promoción a Distancia",

    # FDCP – Maestrías en Derecho
    "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia":
        "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
    "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia":
        "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
    "Maestría en Derecho Constitucional 3ra Promoción a Distancia":
        "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
    "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia":
        "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
    "Maestría en Derecho Constitucional 4ta Promoción a Distancia":
        "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
    "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia":
        "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
    "Maestría en Derecho Constitucional 5ta Promoción a Distancia":
        "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
    "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia":
        "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
    "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia":
        "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
}

# Programas “posiblemente nuevos” (fallback).
# Hoy no debería usarse porque init_db.py ya los incluye, pero lo dejamos coherente
# con el schema actual (usa 'observaciones', no 'universidad_procedencia').
NEW_PROGRAM_INFO = {
    "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia": {
        "facultad": "Facultad de Ciencias y Humanidades",
        "tipo": "DOCTORADO",
        "promocion": "3ra Promoción",
        "modalidad": "DISTANCIA",
        "observaciones": "Creado automáticamente desde add_cursos_diciembre_2025",
    },
    "Doctorado en Psicología 3ra Promoción a Distancia": {
        "facultad": "Facultad de Ciencias de la Salud",
        "tipo": "DOCTORADO",
        "promocion": "3ra Promoción",
        "modalidad": "DISTANCIA",
        "observaciones": "Creado automáticamente desde add_cursos_diciembre_2025",
    },
    "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia": {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "tipo": "MAESTRIA",
        "promocion": "2da Promoción",
        "modalidad": "DISTANCIA",
        "observaciones": "Creado automáticamente desde add_cursos_diciembre_2025",
    },
}


def get_programa_id(conn: sqlite3.Connection, cursor: sqlite3.Cursor, programa_label: str) -> int:
    """
    Dado el texto de PROGRAMA que usas en tu lista,
    devuelve el id de programa_academico.
    - Resuelve con PROGRAMA_NAME_CANON.
    - Si no existe en la BD y está en NEW_PROGRAM_INFO => lo crea
      usando el schema actual (modalidad, observaciones).
    """
    db_name = PROGRAMA_NAME_CANON.get(programa_label, programa_label)

    cursor.execute("SELECT id FROM programa_academico WHERE nombre_corto = ?", (db_name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    info = NEW_PROGRAM_INFO.get(db_name)
    if not info:
        raise RuntimeError(
            f"❌ No se encontró el programa '{db_name}' en la BD "
            f"y tampoco está definido en NEW_PROGRAM_INFO. "
            f"Revisa el mapeo PROGRAMA_NAME_CANON."
        )

    cursor.execute("SELECT id FROM facultad WHERE nombre = ?", (info["facultad"],))
    fac = cursor.fetchone()
    if not fac:
        raise RuntimeError(f"❌ No se encontró la facultad '{info['facultad']}' en la tabla facultad.")

    facultad_id = fac[0]
    cursor.execute(
        """
        INSERT INTO programa_academico
            (facultad_id, tipo, nombre_corto, mencion, promocion,
             modalidad, observaciones, activo)
        VALUES (?, ?, ?, NULL, ?, ?, ?, 1);
        """,
        (
            facultad_id,
            info["tipo"],
            db_name,
            info.get("promocion"),
            info.get("modalidad"),
            info.get("observaciones"),
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    print(f"✅ Programa creado: {db_name} (id={new_id})")
    return new_id


# ============================
# Datos – Cursos DICIEMBRE 2025 (sin docente asignado)
# ============================
# NOTA: si algún curso en particular quieres marcar como PRESENCIAL, puedes
# añadir la clave "modalidad_dictado": "PRESENCIAL" en su dict.
cursos_diciembre = [
    # ========= FCH – Doctorado en Ciencias de la Educación =========
    {
        "nro": 1,
        "programa": "Doctorado en Ciencias de la Educación 15va Promoción Presencial",
        "ciclo": "VI",
        "asignatura": "DEFENSA NACIONAL Y SEGURIDAD",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257423",
        "observaciones": None,
    },
    {
        "nro": 2,
        "programa": "Doctorado en Ciencias de la Educación 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TECNOLOGÍAS DE INFORMACIÓN Y COMUNICACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257429",
        "observaciones": None,
    },
    {
        "nro": 3,
        "programa": "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SISTEMAS DE EVALUACIÓN DEL APRENDIZAJE",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257430",
        "observaciones": None,
    },
    {
        "nro": 4,
        "programa": "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "RESPONSABILIDAD ETICO SOCIAL",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257431",
        "observaciones": None,
    },
    {
        "nro": 5,
        "programa": "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "ÉTICA EN LA EDUCACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257432",
        "observaciones": "Dra. Liliam Lucy Campos Cornejo – 980580459 – Confirmó el 21/10 en reunión.",
    },

    # ========= FCH – Maestría en Docencia Universitaria =========
    {
        "nro": 6,
        "programa": "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257403",
        "observaciones": None,
    },
    {
        "nro": 7,
        "programa": "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257404",
        "observaciones": None,
    },
    {
        "nro": 8,
        "programa": "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257405",
        "observaciones": None,
    },
    {
        "nro": 9,
        "programa": "Maestría en Docencia Universitaria 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "PLANIFICACIÓN Y GESTIÓN DE LA CALIDAD DE LA EDUCACIÓN",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257406",
        "observaciones": None,
    },

    # ========= FCS – Doctorado en Psicología / Ciencias de la Salud =========
    {
        "nro": 10,
        "programa": "Doctorado en Psicología 1ra Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "SEMINARIO DE TESIS V",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257446",
        "observaciones": None,
    },
    {
        "nro": 11,
        "programa": "Doctorado en Psicología 3ra Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": None,
        "poi": None,
        "observaciones": "Llevará con el Doctorado en Ciencias de la Salud 4ta Promoción a Distancia.",
    },
    {
        "nro": 12,
        "programa": "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "SEMINARIO TEMÁTICO",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257443",
        "observaciones": None,
    },
    {
        "nro": 13,
        "programa": "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SEMINARIO DE TESIS II",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257444",
        "observaciones": None,
    },
    {
        "nro": 14,
        "programa": "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257445",
        "observaciones": "Llevará con el Doctorado en Psicología 3ra Promoción a Distancia.",
    },

    # ========= FIA – DMADS =========
    {
        "nro": 15,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "ELABORACIÓN Y PUBLICACIÓN DE ARTÍCULOS CIENTÍFICOS",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257438",
        "observaciones": None,
    },
    {
        "nro": 16,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257439",
        "observaciones": None,
    },
    {
        "nro": 17,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SISTEMAS DE INFORMACIÓN AMBIENTAL",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257440",
        "observaciones": None,
    },
    {
        "nro": 18,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "BIOÉTICA",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257441",
        "observaciones": None,
    },
    {
        "nro": 19,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción",
        "ciclo": "II",
        "asignatura": "LEGISLACIÓN AMBIENTAL",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257424",
        "observaciones": None,
    },
    {
        "nro": 20,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257442",
        "observaciones": None,
    },

    # ========= FIA – Maestría en Ingeniería Civil =========
    {
        "nro": 21,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TEMAS AVANZADOS DE INGENIERIA ESTRUCTURAL EN LA HIDRAULICA",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257416",
        "observaciones": "Núñez del Prado dictó en julio. Solicitud a la Mg. Ana Cecilia.",
    },
    {
        "nro": 22,
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TEMAS ESPECIALES",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257420",
        "observaciones": "Consignar bien el nombre del curso, buscar en el ERP.",
    },
    {
        "nro": 23,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257417",
        "observaciones": None,
    },
    {
        "nro": 24,
        "programa": "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257396",
        "observaciones": None,
    },
    {
        "nro": 25,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257418",
        "observaciones": None,
    },
    {
        "nro": 26,
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TRATAMIENTO DE AGUAS SERVIDAS E INDUSTRIALES",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257421",
        "observaciones": None,
    },
    {
        "nro": 27,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "COMPORTAMIENTO Y DISEÑO DEL CONCRETO",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257419",
        "observaciones": None,
    },

    # ========= FCEC – Doctorados =========
    {
        "nro": 28,
        "programa": "Doctorado en Administración 2da Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "GESTIÓN DE RIESGOS Y TOMA DE DECISIONES EN INCERTIDUMBRE",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257425",
        "observaciones": None,
    },
    {
        "nro": 29,
        "programa": "Doctorado en Administración 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "MACROECONOMÍA Y POLÍTICAS ECONÓMICAS",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257426",
        "observaciones": None,
    },
    {
        "nro": 30,
        "programa": "Doctorado en Administración 4ta Promoción Presencial",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257422",
        "observaciones": None,
    },
    {
        "nro": 31,
        "programa": "Doctorado en Administración 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "RESPONSABILIDAD SOCIAL EMPRESARIAL",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257427",
        "observaciones": None,
    },

    # ========= FCEC – Doctorado en Contabilidad =========
    {
        "nro": 32,
        "programa": "Doctorado en Contabilidad 2da Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "POLÍTICA ECONÓMICA Y GLOBALIZACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257428",
        "observaciones": None,
    },

    # ========= FCEC – MAN / MCONT-AUD =========
    {
        "nro": 33,
        "programa": "Maestría en Administración de Negocios 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257397",
        "observaciones": None,
    },
    {
        "nro": 34,
        "programa": "Maestría en Administración de Negocios 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257398",
        "observaciones": "Llevará con Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia.",
    },
    {
        "nro": 35,
        "programa": "Maestría en Administración de Negocios 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACION",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257399",
        "observaciones": None,
    },
    {
        "nro": 36,
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257400",
        "observaciones": None,
    },
    {
        "nro": 37,
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "AUDITORIA FINANCIERA I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257402",
        "observaciones": "Docente que se propone. Revisar si tenemos CV de Miriam Cledy Zarate Muñiz.",
    },
    {
        "nro": 38,
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": None,
        "poi": None,
        "observaciones": "Llevarán con Maestría en Administración 3ra Promoción.",
    },

    # ========= FDCP – Doctorado en Derecho =========
    {
        "nro": 39,
        "programa": "Doctorado en Derecho 2da Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257433",
        "observaciones": None,
    },
    {
        "nro": 40,
        "programa": "Doctorado en Derecho 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "SEMINARIO DE TESIS III",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257434",
        "observaciones": None,
    },
    {
        "nro": 41,
        "programa": "Doctorado en Derecho 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "MEDIOS ALTERNATIVOS PARA LA RESOLUCION DE CONFLICTOS",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257435",
        "observaciones": None,
    },
    {
        "nro": 42,
        "programa": "Doctorado en Derecho 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO: TEORIAS AVANZADAS DEL DERECHO PENAL EN EL SIGLO XXI",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257436",
        "observaciones": None,
    },
    {
        "nro": 43,
        "programa": "Doctorado en Derecho 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "CIENCIA POLITICA Y GOBERNABILIDAD",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257437",
        "observaciones": None,
    },

    # ========= FDCP – Maestrías en Derecho =========
    {
        "nro": 44,
        "programa": "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257413",
        "observaciones": None,
    },
    {
        "nro": 45,
        "programa": "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257410",
        "observaciones": None,
    },
    {
        "nro": 46,
        "programa": "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257407",
        "observaciones": None,
    },
    {
        "nro": 47,
        "programa": "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257414",
        "observaciones": None,
    },
    {
        "nro": 48,
        "programa": "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TEMAS ESPECIALES",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257408",
        "observaciones": None,
    },
    {
        "nro": 49,
        "programa": "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257411",
        "observaciones": None,
    },
    {
        "nro": 50,
        "programa": "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257409",
        "observaciones": None,
    },
    {
        "nro": 51,
        "programa": "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "DERECHO INMOBILIARIO I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257412",
        "observaciones": None,
    },
    {
        "nro": 52,
        "programa": "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TUTELA JURÍDICA DE LA POSESIÓN Y LA PROPIEDAD",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257415",
        "observaciones": None,
    },
]


# ============================
# Main
# ============================
def main():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1) Verificar período Diciembre 2025
    cursor.execute("SELECT id FROM periodo WHERE anio = ? AND mes = ?", (2025, 12))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise RuntimeError(
            "❌ No se encontró el periodo 2025-12. "
            "Primero crea 'Diciembre 2025' en la tabla periodo (init_db.py ya lo hace)."
        )
    periodo_dic_2025_id = row[0]
    print(f"Periodo Diciembre 2025 ID: {periodo_dic_2025_id}")

    insertados = 0
    saltados = 0

    for curso in cursos_diciembre:
        programa_label = curso["programa"]
        programa_id = get_programa_id(conn, cursor, programa_label)

        # Intentamos obtener la modalidad base del programa académico
        cursor.execute("SELECT modalidad FROM programa_academico WHERE id = ?", (programa_id,))
        row_mod = cursor.fetchone()
        modalidad_base = row_mod[0] if row_mod else None

        ciclo = curso["ciclo"]
        asignatura = curso["asignatura"]
        fechas_texto = curso["fechas"]
        remuneracion_texto = curso["remuneracion_texto"]
        remuneracion_monto = parse_monto(remuneracion_texto)
        poi = curso["poi"]
        observaciones = curso["observaciones"]

        sem1_texto, sem2_texto = split_sem1_sem2(fechas_texto)

        # Determinar modalidad_dictado (campo de curso_programado)
        modalidad_dictado = curso.get("modalidad_dictado") or modalidad_base
        if not modalidad_dictado:
            # Heurística simple si no hay nada en BD:
            if "distancia" in programa_label.lower():
                modalidad_dictado = "DISTANCIA"
            else:
                modalidad_dictado = "PRESENCIAL"

        # Idempotencia: mismo periodo, programa, ciclo, asignatura y fechas_texto
        cursor.execute(
            """
            SELECT id FROM curso_programado
            WHERE periodo_id = ?
              AND programa_id = ?
              AND ciclo = ?
              AND asignatura = ?
              AND fechas_texto = ?;
            """,
            (periodo_dic_2025_id, programa_id, ciclo, asignatura, fechas_texto),
        )
        ya_existe = cursor.fetchone()
        if ya_existe:
            saltados += 1
            print(
                f"⚠️  Ya existe curso (periodo={periodo_dic_2025_id}, programa='{programa_label}', "
                f"ciclo='{ciclo}', asignatura='{asignatura}'). Se omite."
            )
            continue

        cursor.execute(
            """
            INSERT INTO curso_programado
                (periodo_id, programa_id, docente_id,
                 ciclo, asignatura, fechas_texto,
                 modalidad_dictado,
                 remuneracion_monto, remuneracion_texto,
                 poi, dni_docente, tipo_docente_mes,
                 observaciones, sem1, sem2)
            VALUES (?, ?, NULL,
                    ?, ?, ?,
                    ?,
                    ?, ?,
                    ?, NULL, NULL,
                    ?, ?, ?);
            """,
            (
                periodo_dic_2025_id,
                programa_id,
                ciclo,
                asignatura,
                fechas_texto,
                modalidad_dictado,
                remuneracion_monto,
                remuneracion_texto,
                poi,
                observaciones,
                sem1_texto,
                sem2_texto,
            ),
        )
        insertados += 1

    conn.commit()
    conn.close()

    print(f"✅ Cursos de Diciembre 2025 insertados: {insertados}")
    print(f"ℹ️ Cursos ya existentes (no se duplicaron): {saltados}")


if __name__ == "__main__":
    main()
